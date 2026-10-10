"""Fetch the pinned WNUT-2020 corpus and verify it against the acquisition manifest.

The archive is downloaded by commit, not by branch, so the source cannot drift. GitHub
generates archives on demand and does not guarantee byte-stable zips, so the per-file
SHA-256 hashes in the manifest are authoritative; the archive hash is recorded and a
mismatch is reported, but only a file-level mismatch fails acquisition.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

MANIFEST_VERSION = 1

SOURCE_REPO = "https://github.com/jeniyat/WNUT_2020_NER"
SOURCE_LICENSE = "MIT"
COMMIT = "9a02914e00f0a16c0c6820c4285dd72403a5a5a8"
ARCHIVE_URL = f"https://codeload.github.com/jeniyat/WNUT_2020_NER/zip/{COMMIT}"

# The only annotation directories used. Other folder variants in the repository
# (Conll_Format, Standoff_Format_Merged, the legacy test_data/) are not interchangeable;
# legacy test_data/Standoff_Format has entity records but no event or relation records.
SELECTED_DIRS: tuple[str, ...] = (
    "data/train_data/Standoff_Format",
    "data/dev_data/Standoff_Format",
    "data/test_data_2020/Standoff_Format",
)
# Notices and format documentation kept alongside the data.
EXTRA_FILES: tuple[str, ...] = ("LICENSE", "Readme.md", "data/Readme.md")

_CHUNK = 1 << 20


class AcquisitionError(RuntimeError):
    """Raised when downloaded data cannot be trusted."""


@dataclass(frozen=True)
class FileRecord:
    sha256: str
    bytes: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> Path:
    """Download ``url`` to ``dest`` via a temporary file so a partial download never
    masquerades as a complete one."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".partial")
    with urllib.request.urlopen(url, timeout=120) as resp, partial.open("wb") as out:
        while chunk := resp.read(_CHUNK):
            out.write(chunk)
    partial.replace(dest)
    return dest


def _safe_relpath(member_name: str) -> str | None:
    """Return the member path with the archive's top-level folder stripped, or None for
    directories. Rejects absolute paths and parent-directory traversal."""
    if member_name.endswith("/"):
        return None
    if "\\" in member_name:
        raise AcquisitionError(f"Backslash in archive member name: {member_name!r}")
    path = PurePosixPath(member_name)
    if path.is_absolute() or ".." in path.parts:
        raise AcquisitionError(f"Unsafe archive member path: {member_name!r}")
    if len(path.parts) < 2:
        raise AcquisitionError(f"Archive member outside a top-level folder: {member_name!r}")
    return PurePosixPath(*path.parts[1:]).as_posix()


def is_selected(relpath: str) -> bool:
    if relpath in EXTRA_FILES:
        return True
    parent = PurePosixPath(relpath).parent.as_posix()
    return parent in SELECTED_DIRS


def select_members(zf: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    selected: dict[str, zipfile.ZipInfo] = {}
    for info in zf.infolist():
        relpath = _safe_relpath(info.filename)
        if relpath is None or not is_selected(relpath):
            continue
        if relpath in selected:
            raise AcquisitionError(f"Duplicate archive member: {relpath}")
        selected[relpath] = info
    return selected


def read_selected(archive: Path) -> dict[str, bytes]:
    """Read every selected member into memory (the selected corpus is a few MB)."""
    with zipfile.ZipFile(archive) as zf:
        return {rel: zf.read(info) for rel, info in sorted(select_members(zf).items())}


def records_for(contents: dict[str, bytes]) -> dict[str, FileRecord]:
    return {rel: FileRecord(sha256_bytes(data), len(data)) for rel, data in contents.items()}


def compare(actual: dict[str, FileRecord], expected: dict[str, FileRecord]) -> list[str]:
    """Describe every difference between two file inventories; empty means identical."""
    problems: list[str] = []
    for rel in sorted(expected.keys() - actual.keys()):
        problems.append(f"missing: {rel}")
    for rel in sorted(actual.keys() - expected.keys()):
        problems.append(f"unexpected: {rel}")
    for rel in sorted(expected.keys() & actual.keys()):
        if actual[rel] != expected[rel]:
            problems.append(f"hash mismatch: {rel}")
    return problems


def write_tree(contents: dict[str, bytes], dest: Path) -> None:
    """Write files under ``dest`` and mark them read-only: raw data is never edited."""
    if dest.exists():
        raise AcquisitionError(f"{dest} already exists; refusing to overwrite raw data")
    for rel, data in contents.items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def scan_tree(root: Path) -> dict[str, FileRecord]:
    records: dict[str, FileRecord] = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            records[rel] = FileRecord(sha256_file(path), path.stat().st_size)
    return records


def split_file_counts(records: dict[str, FileRecord]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for selected_dir in SELECTED_DIRS:
        split = PurePosixPath(selected_dir).parts[1]
        in_dir = [r for r in records if PurePosixPath(r).parent.as_posix() == selected_dir]
        counts[split] = {
            "txt": sum(r.endswith(".txt") for r in in_dir),
            "ann": sum(r.endswith(".ann") for r in in_dir),
        }
    return counts


def build_manifest(archive_sha256: str, records: dict[str, FileRecord]) -> dict[str, Any]:
    return {
        "manifest_version": MANIFEST_VERSION,
        "source": {
            "repo": SOURCE_REPO,
            "commit": COMMIT,
            "license": SOURCE_LICENSE,
            "archive_url": ARCHIVE_URL,
            "archive_sha256": archive_sha256,
            "archive_note": (
                "Per-file hashes are authoritative. GitHub archives are generated on demand; "
                "the by-commit archive differs in bytes from the refs/heads/master archive "
                "(sha256 ae7a31bc...1d44f, audited 2026-10-10) only by its top-level folder "
                "name, and both contain identical files."
            ),
        },
        "selected_dirs": list(SELECTED_DIRS),
        "extra_files": list(EXTRA_FILES),
        "split_file_counts": split_file_counts(records),
        "files": {
            rel: {"sha256": r.sha256, "bytes": r.bytes} for rel, r in sorted(records.items())
        },
    }


def load_manifest(path: Path) -> dict[str, Any]:
    manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise AcquisitionError(f"Unsupported manifest version in {path}")
    if manifest["source"]["commit"] != COMMIT:
        raise AcquisitionError("Manifest commit does not match the pinned commit")
    return manifest


def manifest_records(manifest: dict[str, Any]) -> dict[str, FileRecord]:
    return {
        rel: FileRecord(entry["sha256"], entry["bytes"]) for rel, entry in manifest["files"].items()
    }


def write_manifest(manifest: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=1, sort_keys=False) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class Paths:
    archive: Path
    raw: Path
    manifest: Path

    @classmethod
    def under(cls, root: Path) -> Paths:
        return cls(
            archive=root / "data" / "downloads" / f"WNUT_2020_NER-{COMMIT}.zip",
            raw=root / "data" / "raw" / "wnut2020",
            manifest=root / "data" / "manifests" / "acquisition.json",
        )


def _fetch_archive(paths: Paths, log: Any) -> str:
    if not paths.archive.exists():
        log(f"downloading {ARCHIVE_URL}")
        download(ARCHIVE_URL, paths.archive)
    return sha256_file(paths.archive)


def create_manifest(paths: Paths, log: Any = print) -> dict[str, Any]:
    """One-time: record the pinned corpus. Refuses to replace an existing manifest."""
    if paths.manifest.exists():
        raise AcquisitionError(f"{paths.manifest} exists; the acquisition manifest is frozen")
    archive_sha = _fetch_archive(paths, log)
    manifest = build_manifest(archive_sha, records_for(read_selected(paths.archive)))
    write_manifest(manifest, paths.manifest)
    log(f"wrote {paths.manifest} ({len(manifest['files'])} files)")
    return manifest


def verify(paths: Paths) -> list[str]:
    """Check an extracted raw tree against the manifest."""
    expected = manifest_records(load_manifest(paths.manifest))
    if not paths.raw.exists():
        return [f"missing raw directory: {paths.raw}"]
    return compare(scan_tree(paths.raw), expected)


def acquire(paths: Paths, log: Any = print) -> None:
    """Download (if needed), verify against the manifest, then extract read-only."""
    manifest = load_manifest(paths.manifest)
    expected = manifest_records(manifest)
    if paths.raw.exists():
        problems = compare(scan_tree(paths.raw), expected)
        if problems:
            raise AcquisitionError(
                f"{paths.raw} does not match the manifest ({len(problems)} problems, first: "
                f"{problems[0]}). Remove it manually and re-run."
            )
        log(f"{paths.raw} already matches the manifest ({len(expected)} files)")
        return
    archive_sha = _fetch_archive(paths, log)
    if archive_sha != manifest["source"]["archive_sha256"]:
        log(f"note: archive sha256 {archive_sha} differs from manifest; checking file hashes")
    contents = read_selected(paths.archive)
    problems = compare(records_for(contents), expected)
    if problems:
        raise AcquisitionError(
            f"Downloaded files do not match the manifest ({len(problems)} problems, first: "
            f"{problems[0]})"
        )
    write_tree(contents, paths.raw)
    log(f"extracted {len(contents)} verified files to {paths.raw}")
