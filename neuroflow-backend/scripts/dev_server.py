"""Local development entrypoint for Windows: `python scripts/dev_server.py`.

`uvicorn app.main:app` on the CLI creates its event loop (a Proactor loop
by Windows' default) *before* it imports the app string -- by the time
app.core.database runs, the incompatible loop already exists and setting
the policy from inside the app is too late. This script sets the policy
first, in the process that will actually call uvicorn.run(), which is the
only point where the ordering is guaranteed correct.

Not used in Docker/production: Linux already defaults to a selector loop,
so `uvicorn app.main:app` from the Dockerfile CMD needs no wrapper.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# `python scripts/dev_server.py` puts scripts/ on sys.path[0], not the
# backend root -- add it explicitly so `app.main` resolves regardless of
# the caller's current directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402 -- must import after the policy is set

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
