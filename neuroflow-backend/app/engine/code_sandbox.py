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
import subprocess
from pathlib import Path
from typing import Any, Literal

WALL_CLOCK_TIMEOUT_SECONDS = 30
MAX_OLD_SPACE_MB = 128

_RUNNER_PATH = Path(__file__).parent / "js_sandbox_runner.js"


class CodeSandboxError(RuntimeError):
    pass


class CodeSandboxTimeoutError(CodeSandboxError):
    pass


def _run_sync(payload: bytes) -> tuple[bytes, bytes]:
    # subprocess.run (blocking, run off the event loop via asyncio.to_thread
    # below) rather than asyncio.create_subprocess_exec: the latter needs a
    # ProactorEventLoop on Windows, but app.core.database forces the
    # Selector policy there for psycopg's async driver -- the two loop
    # requirements can't coexist in one process. subprocess.run doesn't
    # touch the event loop's subprocess transport at all, so it works
    # under either policy and behaves identically on Linux/Docker prod.
    try:
        # Fixed argv, no shell, no user-controlled executable/path -- the
        # untrusted `code` travels only through stdin `payload`, never the
        # command line. S603/S607 target shell-injection/PATH-hijack shapes
        # that don't apply here.
        completed = subprocess.run(  # noqa: S603
            ["node", f"--max-old-space-size={MAX_OLD_SPACE_MB}", str(_RUNNER_PATH)],  # noqa: S607
            input=payload,
            capture_output=True,
            timeout=WALL_CLOCK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise CodeSandboxTimeoutError(
            f"Code node exceeded the {WALL_CLOCK_TIMEOUT_SECONDS}s wall-clock limit"
        ) from exc
    return completed.stdout, completed.stderr


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

    stdout, stderr = await asyncio.to_thread(_run_sync, payload)

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
