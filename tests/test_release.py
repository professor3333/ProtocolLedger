import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_cli", ROOT / "scripts" / "release.py")
assert spec and spec.loader
release_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_cli)


def ev(event: str, rid: str) -> dict[str, Any]:
    return {"event": event, "release": {"id": rid}}


def test_previous_is_the_last_good_release() -> None:
    entries = [ev("activated", "r1"), ev("activated", "r2"), ev("activated", "r3")]
    assert release_cli.current(entries)["id"] == "r3"
    assert release_cli.previous(entries)["id"] == "r2"


def test_rolled_back_release_is_never_a_rollback_target_again() -> None:
    entries = [ev("activated", "r1"), ev("activated", "r2"), ev("rolled_back", "r1")]
    assert release_cli.current(entries)["id"] == "r1"
    assert release_cli.previous(entries) is None  # r2 was rejected


def test_failed_release_is_skipped_and_rollbacks_walk_back() -> None:
    entries = [
        ev("activated", "r1"),
        ev("activated", "r2"),
        ev("activated", "r3"),
        ev("failed", "r4"),
        ev("rolled_back", "r3"),
    ]
    assert release_cli.current(entries)["id"] == "r3"
    assert release_cli.previous(entries)["id"] == "r2"
    entries.append(ev("rolled_back", "r2"))  # manual rollback from r3
    assert release_cli.previous(entries)["id"] == "r1"


def test_no_history_has_no_previous() -> None:
    assert release_cli.previous([]) is None
    assert release_cli.current([]) is None
