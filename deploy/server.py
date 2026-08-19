"""Container entrypoint for the hosted app.

`bluffhouse serve` binds 127.0.0.1 and opens a browser, which is right for a
laptop and wrong for a container. This builds the same FastAPI app and hands
it to uvicorn on 0.0.0.0.
"""

import os
from pathlib import Path

from bluffhouse.harness.serve import create_app

RUNS = Path(os.environ.get("BLUFFHOUSE_RUNS", "/app/runs"))
RUNS.mkdir(parents=True, exist_ok=True)

app = create_app(RUNS)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        log_level="info",
    )
