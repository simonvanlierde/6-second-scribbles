"""Guard the prod image against running more than one uvicorn worker."""

from __future__ import annotations

import json
from pathlib import Path

DOCKERFILE = Path(__file__).parents[2] / "Dockerfile"
SERVER = "uvicorn"
WORKERS_FLAG = "--workers"
SINGLE_WORKER = "1"


def test_prod_image_runs_a_single_worker() -> None:
    """Rooms live in one process's memory, so a second worker would split them."""
    stages = DOCKERFILE.read_text().split("\nFROM ")
    prod_stage = next(stage for stage in stages if stage.split("\n", 1)[0].endswith(" AS prod"))
    cmd_line = next(line for line in prod_stage.splitlines() if line.startswith("CMD "))
    cmd = json.loads(cmd_line.removeprefix("CMD "))

    assert cmd[0] == SERVER
    if WORKERS_FLAG in cmd:
        assert cmd[cmd.index(WORKERS_FLAG) + 1] == SINGLE_WORKER
