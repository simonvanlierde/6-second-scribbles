"""The contracts check must run on any backend app change, not only protocol and schemas."""

from pathlib import Path

APP_FILTER = "- 'backend/app/**'"
APP_PATTERN = r"|backend/app/.*"
REPO = Path(__file__).resolve().parents[3]


def test_ci_contracts_filter_watches_the_backend_app() -> None:
    """types.py or state.py can change a schema without touching schemas.py."""
    ci = (REPO / ".github/workflows/ci.yml").read_text()
    assert APP_FILTER in ci.split("contracts:\n              - 'contracts/**'", 1)[1].split("root:", 1)[0]


def test_precommit_contracts_hook_watches_the_backend_app() -> None:
    """The pre-push hook uses the same trigger list as CI."""
    config = (REPO / ".pre-commit-config.yaml").read_text()
    hook = config.split("id: contracts", 1)[1].split("stages:", 1)[0]
    assert APP_PATTERN in hook
