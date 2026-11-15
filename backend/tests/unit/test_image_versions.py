"""Integration test containers run the same Postgres and Redis majors as compose."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
IMAGE_COUNT = 2
IMAGE = re.compile(r"(postgres|redis):(\d+)")


def _majors(path: Path) -> set[tuple[str, str]]:
    return set(IMAGE.findall(path.read_text()))


def test_integration_containers_match_compose_images() -> None:
    """Testing against an older major than production hides upgrade breakage."""
    conftest = _majors(REPO / "backend/tests/integration/conftest.py")
    compose = _majors(REPO / "compose.yml")
    assert conftest == compose
    assert len(compose) == IMAGE_COUNT
