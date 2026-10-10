import json
import os
import stat
import zipfile
from pathlib import Path

import pytest

from protocolledger.data import acquire as acq

TOP = f"WNUT_2020_NER-{acq.COMMIT}/"

SYNTHETIC = {
    "LICENSE": b"MIT License\n",
    "Readme.md": b"# readme\n",
    "data/Readme.md": b"# data readme\n",
    "data/train_data/Standoff_Format/protocol_1.txt": b"Add water.\n",
    "data/train_data/Standoff_Format/protocol_1.ann": b"T1\tAction 0 3\tAdd\n",
    "data/dev_data/Standoff_Format/protocol_2.txt": b"Mix.\n",
    "data/test_data_2020/Standoff_Format/protocol_0003.txt": b"Spin.\n",
    # Not selected: other folder variants and the legacy test split.
    "data/train_data/Conll_Format/protocol_1.conll": b"Add\tB-Action\n",
    "data/test_data/Standoff_Format/protocol_9.ann": b"T1\tAction 0 1\tx\n",
    "code/script.py": b"print('x')\n",
}


def make_zip(path: Path, members: dict[str, bytes], top: str = TOP) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(top, b"")
        for name, data in members.items():
            zf.writestr(top + name, data)
    return path


@pytest.fixture
def paths(tmp_path: Path) -> acq.Paths:
    p = acq.Paths.under(tmp_path)
    p.archive.parent.mkdir(parents=True)
    make_zip(p.archive, SYNTHETIC)
    return p


def _quiet(_msg: str) -> None:
    pass


def test_selects_only_pinned_directories_and_notices(paths: acq.Paths) -> None:
    selected = acq.read_selected(paths.archive)
    assert set(selected) == {
        "LICENSE",
        "Readme.md",
        "data/Readme.md",
        "data/train_data/Standoff_Format/protocol_1.txt",
        "data/train_data/Standoff_Format/protocol_1.ann",
        "data/dev_data/Standoff_Format/protocol_2.txt",
        "data/test_data_2020/Standoff_Format/protocol_0003.txt",
    }


@pytest.mark.parametrize("bad", ["../evil.txt", "/abs.txt", "top/../../evil.txt", "top\\x.txt"])
def test_rejects_unsafe_member_paths(tmp_path: Path, bad: str) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(bad, b"x")
    with pytest.raises(acq.AcquisitionError):
        acq.read_selected(archive)


def test_compare_reports_every_kind_of_difference() -> None:
    expected = {"a": acq.FileRecord("1", 1), "b": acq.FileRecord("2", 1)}
    actual = {"a": acq.FileRecord("9", 1), "c": acq.FileRecord("3", 1)}
    assert acq.compare(actual, expected) == ["missing: b", "unexpected: c", "hash mismatch: a"]


def test_manifest_counts_and_round_trip(paths: acq.Paths) -> None:
    manifest = acq.create_manifest(paths, log=_quiet)
    assert manifest["split_file_counts"] == {
        "train_data": {"txt": 1, "ann": 1},
        "dev_data": {"txt": 1, "ann": 0},
        "test_data_2020": {"txt": 1, "ann": 0},
    }
    reloaded = acq.load_manifest(paths.manifest)
    assert acq.manifest_records(reloaded) == acq.records_for(acq.read_selected(paths.archive))


def test_manifest_is_frozen(paths: acq.Paths) -> None:
    acq.create_manifest(paths, log=_quiet)
    with pytest.raises(acq.AcquisitionError, match="frozen"):
        acq.create_manifest(paths, log=_quiet)


def test_acquire_extracts_read_only_and_verifies(paths: acq.Paths) -> None:
    acq.create_manifest(paths, log=_quiet)
    acq.acquire(paths, log=_quiet)
    assert acq.verify(paths) == []
    txt = paths.raw / "data/train_data/Standoff_Format/protocol_1.txt"
    assert txt.read_bytes() == b"Add water.\n"
    assert not txt.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    # Re-running on a matching tree is a no-op.
    acq.acquire(paths, log=_quiet)


def test_tampered_raw_tree_is_detected_and_not_overwritten(paths: acq.Paths) -> None:
    acq.create_manifest(paths, log=_quiet)
    acq.acquire(paths, log=_quiet)
    txt = paths.raw / "data/train_data/Standoff_Format/protocol_1.txt"
    os.chmod(txt, stat.S_IRUSR | stat.S_IWUSR)
    txt.write_bytes(b"Add oil.\n")
    assert acq.verify(paths) == ["hash mismatch: data/train_data/Standoff_Format/protocol_1.txt"]
    with pytest.raises(acq.AcquisitionError, match="does not match"):
        acq.acquire(paths, log=_quiet)
    assert txt.read_bytes() == b"Add oil.\n"


def test_downloaded_files_differing_from_manifest_fail(paths: acq.Paths) -> None:
    acq.create_manifest(paths, log=_quiet)
    changed = dict(SYNTHETIC, **{"data/dev_data/Standoff_Format/protocol_2.txt": b"Stir.\n"})
    paths.archive.unlink()
    make_zip(paths.archive, changed)
    with pytest.raises(acq.AcquisitionError, match="do not match"):
        acq.acquire(paths, log=_quiet)
    assert not paths.raw.exists()


def test_archive_repackaging_alone_is_tolerated(paths: acq.Paths) -> None:
    acq.create_manifest(paths, log=_quiet)
    paths.archive.unlink()
    make_zip(paths.archive, SYNTHETIC, top="WNUT_2020_NER-master/")
    messages: list[str] = []
    acq.acquire(paths, log=messages.append)
    assert any("differs from manifest" in m for m in messages)
    assert acq.verify(paths) == []


def test_manifest_with_wrong_commit_is_rejected(paths: acq.Paths) -> None:
    acq.create_manifest(paths, log=_quiet)
    manifest = json.loads(paths.manifest.read_text())
    manifest["source"]["commit"] = "0" * 40
    paths.manifest.write_text(json.dumps(manifest))
    with pytest.raises(acq.AcquisitionError, match="pinned commit"):
        acq.acquire(paths, log=_quiet)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_committed_manifest_matches_audited_file_counts() -> None:
    manifest = acq.load_manifest(acq.Paths.under(REPO_ROOT).manifest)
    assert manifest["split_file_counts"] == {
        "train_data": {"txt": 370, "ann": 370},
        "dev_data": {"txt": 122, "ann": 122},
        "test_data_2020": {"txt": 111, "ann": 111},
    }
    assert len(manifest["files"]) == 2 * 603 + len(acq.EXTRA_FILES)


@pytest.mark.slow
def test_local_raw_tree_matches_committed_manifest() -> None:
    paths = acq.Paths.under(REPO_ROOT)
    if not paths.raw.exists():
        pytest.skip("run scripts/acquire.py first")
    assert acq.verify(paths) == []
