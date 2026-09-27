"""Custom uvicorn loop factory.

uvicorn hardcodes ProactorEventLoop on Windows, which psycopg async cannot use.
This factory returns SelectorEventLoop so `uvicorn ... --loop app.loops:selector`
works for local development on Windows. Production on Linux uses the default
uvicorn loop (uvloop/asyncio) and does not need this.
"""

import asyncio


def selector_loop_factory(use_subprocess: bool = False):  # noqa: ARG001
    return asyncio.SelectorEventLoop()
