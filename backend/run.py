"""Development entrypoint.

On Windows, psycopg async needs a selector-based event loop; uvicorn otherwise
forces ProactorEventLoop. We pass a custom loop factory to work around this.
Run with: python run.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        loop="app.loops:selector_loop_factory",
        reload=False,
    )
