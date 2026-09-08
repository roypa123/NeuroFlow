"""Subprocess-based Code node sandbox. See docs/12-execution-engine.md
#12.7 and docs/15-security-and-credentials.md #15.8.

Spawns a real `node` subprocess per invocation running
`js_sandbox_runner.js`, communicating over stdin/stdout JSON -- never runs
untrusted code in the worker's own event loop. Node is available in this
environment, so this is a genuinely live-testable code path.

Two independent timeouts, deliberately layered: `js_sandbox_runner.js`'s
own `vm.Script` timeout (25 s) catches a synchronous busy loop from inside
V8 itself; the `asyncio.wait_for` here (30 s, the documented hard cap) is
the backstop for anything that hangs the subprocess as a whole (e.g. stuck
I/O) rather than just spinning the CPU.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Literal

WALL_CLOCK_TIMEOUT_SECONDS = 30
MAX_OLD_SPACE_MB = 128

_RUNNER_PATH = Path(__file__).parent / "js_sandbox_runner.js"


class CodeSandboxError(RuntimeError):
    pass


class CodeSandboxTimeoutError(CodeSandboxError):
    pass


async def run_code(
    code: str,
    *,
    items: list[dict[str, Any]],
    mode: Literal["allItems", "perItem"] = "allItems",
    allow_network: bool = False,
) -> Any:
    payload = json.dumps(
        {"code": code, "items": items, "mode": mode, "allowNetwork": allow_network}
    ).encode()

    process = await asyncio.create_subprocess_exec(
        "node",
        f"--max-old-space-size={MAX_OLD_SPACE_MB}",
        str(_RUNNER_PATH),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(payload), timeout=WALL_CLOCK_TIMEOUT_SECONDS
        )
    except TimeoutError as exc:
        process.kill()
        await process.wait()
        raise CodeSandboxTimeoutError(
            f"Code node exceeded the {WALL_CLOCK_TIMEOUT_SECONDS}s wall-clock limit"
        ) from exc

    if not stdout:
        raise CodeSandboxError(
            stderr.decode(errors="replace") or "Sandbox produced no output"
        )
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise CodeSandboxError(f"Malformed sandbox output: {stdout!r}") from exc
    if not result.get("ok"):
        raise CodeSandboxError(result.get("error", "Unknown sandbox error"))
    return result["result"]
