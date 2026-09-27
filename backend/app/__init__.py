"""Kabadi Mitra backend package.

On Windows, psycopg async requires a selector-based event loop (the default
ProactorEventLoop is incompatible). Set the policy before any loop is created.
"""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
