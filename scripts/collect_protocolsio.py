"""Collect recent public protocols.io steps for the later-domain and challenge sets.

    uv run python -I scripts/collect_protocolsio.py

Uses the official API (token in ~/.config/protocolledger/protocolsio_token, never
printed). Every API response is cached once under data/raw/protocolsio/ and never
re-fetched or edited, so re-running rebuilds byte-identical sets from the same snapshot;
pass --refresh-search to take a new snapshot of the search results.

Candidates are the newest public protocols for a fixed list of wet-lab search terms,
interleaved round-robin across terms. A protocol is eligible when it was published on or
after --published-after, reads as English, keeps at least 5 usable steps (rules in
protocolledger/data/protocolsio.py) of which at least 30% state a quantity, and is not the
same protocol as a WNUT-2020 document or an already-chosen candidate (same near-duplicate
test as the corpus dedup). Eligible
protocols fill the later-domain set first (the first --steps-per-protocol usable steps
each, until --later-domain-steps steps from at least --min-protocols protocols); later
ones form the challenge pool, from which steps are chosen per category. The two sets
never share a protocol. Writes data/annotation/<set>/{sources.jsonl,texts/} and
data/manifests/protocolsio_collection.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from protocolledger.data.annotation_sets import assign_split, text_sha256
from protocolledger.data.protocolsio import (
    CATEGORIES,
    COLLECTION_VERSION,
    LICENSE,
    MIN_QUANTITY_SHARE,
    MIN_USABLE_STEPS,
    CleanStep,
    Lexicons,
    ProtocolIndex,
    authors,
    build_text,
    challenge_tags,
    clean_steps,
    looks_english,
    published_date,
    quantity_share,
    select_challenge,
    title,
    usable,
)
from protocolledger.data.splits import load_split

ROOT = Path(__file__).resolve().parents[1]
API = "https://www.protocols.io/api"
TOKEN = Path.home() / ".config" / "protocolledger" / "protocolsio_token"
KEYS = (
    "DNA",
    "RNA",
    "PCR",
    "protein",
    "buffer",
    "cell culture",
    "staining",
    "purification",
    "extraction",
    "transformation",
)


class Client:
    def __init__(self, token: str, cache: Path, delay: float) -> None:
        self.token, self.cache, self.delay = token, cache, delay
        self.fetched = 0

    def get(self, rel: str, url: str, refresh: bool = False) -> dict[str, Any]:
        path = self.cache / rel
        if path.exists() and not refresh:
            return json.loads(path.read_text("utf-8"))  # type: ignore[no-any-return]
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self.token}", "User-Agent": "ProtocolLedger"},
        )
        for attempt in range(4):
            time.sleep(self.delay * (2**attempt))
            try:
                with urllib.request.urlopen(req, timeout=60) as res:
                    payload = res.read()
                break
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise SystemExit(f"error: {url.split('?')[0]} returned HTTP {e.code}") from e
        body = json.loads(payload)
        if body.get("status_code") != 0:
            raise SystemExit(f"error: {url.split('?')[0]}: {body.get('error_message')}")
        self.fetched += 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return body  # type: ignore[no-any-return]


def search(client: Client, key: str, pages: int, refresh: bool) -> list[int]:
    ids: list[int] = []
    for page in range(1, pages + 1):
        query = urllib.parse.urlencode(
            {
                "filter": "public",
                "key": key,
                "order_field": "date",
                "order_dir": "desc",
                "page_size": 100,
                "page_id": page,
                "fields": "id",
            }
        )
        slug = key.replace(" ", "-")
        body = client.get(
            f"search/{slug}-{page}.json", f"{API}/v3/protocols?{query}", refresh=refresh
        )
        ids.extend(int(item["id"]) for item in body.get("items") or [])
        if not body.get("items") or len(body["items"]) < 100:
            break
    return ids


def interleave(lists: list[list[int]]) -> list[int]:
    seen: set[int] = set()
    out = []
    for i in range(max(map(len, lists), default=0)):
        for ids in lists:
            if i < len(ids) and ids[i] not in seen:
                seen.add(ids[i])
                out.append(ids[i])
    return out


def source_record(
    record: dict[str, Any], steps: list[CleanStep], split_key: str, **extra: Any
) -> dict[str, Any]:
    text, index = build_text(title(record), steps)
    if extra.get("categories"):
        for entry, tags in zip(index, extra.pop("categories"), strict=True):
            entry["categories"] = tags
    return {
        "source_id": split_key,
        "url": record["url"],
        "title": title(record),
        "authors": authors(record),
        "version": record.get("version_id"),
        "version_uri": record.get("version_uri"),
        "doi": record.get("doi"),
        "published": published_date(record),
        "license": record.get("license") or LICENSE,
        "steps": index,
        "text": text,
        "text_sha256": text_sha256(text),
        "split": assign_split(split_key),
        **extra,
    }


def shown(value: Any) -> Any:
    """Paths are recorded relative to the repository, never as local absolute paths."""
    if not isinstance(value, Path):
        return value
    path = value.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name


def write_set(set_dir: Path, sources: list[dict[str, Any]]) -> None:
    texts = set_dir / "texts"
    texts.mkdir(parents=True, exist_ok=True)
    for old in texts.glob("*.txt"):
        old.unlink()
    with (set_dir / "sources.jsonl").open("w", encoding="utf-8") as fh:
        for s in sources:
            fh.write(json.dumps(s, ensure_ascii=False, sort_keys=True) + "\n")
            (texts / f"{s['source_id']}.txt").write_text(s["text"], "utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--published-after", default="2025-01-01")
    parser.add_argument("--later-domain-steps", type=int, default=300)
    parser.add_argument("--min-protocols", type=int, default=30)
    parser.add_argument("--max-protocols", type=int, default=50)
    parser.add_argument("--steps-per-protocol", type=int, default=8)
    parser.add_argument("--challenge-per-category", type=int, default=10)
    parser.add_argument("--challenge-per-protocol", type=int, default=3)
    parser.add_argument("--challenge-protocols", type=int, default=40)
    parser.add_argument("--search-pages", type=int, default=2)
    parser.add_argument("--max-fetch", type=int, default=250)
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    parser.add_argument("--refresh-search", action="store_true")
    parser.add_argument("--cache", type=Path, default=ROOT / "data" / "raw" / "protocolsio")
    args = parser.parse_args(argv)
    if not TOKEN.exists():
        raise SystemExit(f"error: save the protocols.io client access token to {TOKEN}")
    client = Client(TOKEN.read_text("utf-8").strip(), args.cache, args.delay)

    train = load_split(ROOT, "train")
    seen_protocols = ProtocolIndex()
    for split in ("train", "dev", "test"):
        for d in train if split == "train" else load_split(ROOT, split):
            seen_protocols.add(f"wnut2020/{d['doc_id']}", d["text"])
    lexicons = Lexicons.from_train(train)

    candidates = interleave(
        [search(client, k, args.search_pages, args.refresh_search) for k in KEYS]
    )
    decisions: list[dict[str, Any]] = []
    later: list[dict[str, Any]] = []
    later_steps = 0
    pool: list[tuple[str, CleanStep, list[str]]] = []
    pool_records: dict[str, tuple[dict[str, Any], list[CleanStep]]] = {}
    skipped_steps: Counter[str] = Counter()
    dropped: Counter[str] = Counter()
    components: Counter[str] = Counter()
    raw_hashes: dict[str, str] = {}

    for pid in candidates[: args.max_fetch]:
        later_done = later_steps >= args.later_domain_steps and len(later) >= args.min_protocols
        if later_done and len(pool_records) >= args.challenge_protocols:
            break
        rel = f"protocols/{pid}.json"
        body = client.get(rel, f"{API}/v4/protocols/{pid}?content_format=html")
        raw_hashes[rel] = hashlib.sha256((args.cache / rel).read_bytes()).hexdigest()
        record = body["payload"]
        decision: dict[str, Any] = {"id": pid, "uri": record.get("uri")}
        decisions.append(decision)
        steps, seen = clean_steps(record.get("steps") or [])
        components.update(seen)
        reasons = Counter(usable(s, lexicons.actions) for s in steps)
        good = [s for s in steps if usable(s, lexicons.actions) is None]
        if not record.get("public"):
            decision["status"] = "excluded:not-public"
            continue
        if published_date(record) < args.published_after:
            decision["status"] = "excluded:published-before"
            continue
        if len(good) < MIN_USABLE_STEPS:
            decision["status"] = "excluded:few-usable-steps"
            continue
        if not looks_english([title(record), *(s.text for s in good)]):
            decision["status"] = "excluded:not-english"
            continue
        if quantity_share(good) < MIN_QUANTITY_SHARE:
            decision["status"] = "excluded:few-quantities"
            continue
        key = f"pio-{pid}"
        full = build_text(title(record), good)[0]
        other = seen_protocols.match(full)
        if other is not None:
            decision["status"] = f"excluded:same-protocol-as:{other}"
            continue
        seen_protocols.add(key, full)
        skipped_steps.update(r for r in reasons.elements() if r)
        for s in steps:
            dropped.update(s.dropped)
        if not later_done and len(later) < args.max_protocols:
            picked = good[: args.steps_per_protocol]
            later.append(source_record(record, picked, key))
            later_steps += len(picked)
            decision["status"] = "later-domain"
        else:
            pool_records[key] = (record, good)
            pool.extend((key, s, challenge_tags(s.text, lexicons)) for s in good)
            decision["status"] = "challenge-pool"

    selected = select_challenge(pool, args.challenge_per_category, args.challenge_per_protocol)
    by_source: dict[str, list[tuple[CleanStep, list[str]]]] = {}
    for key, step, tags in selected:
        by_source.setdefault(key, []).append((step, tags))
    challenge = []
    for key, (record, good) in pool_records.items():
        if key not in by_source:
            continue
        order = {s.step_id: i for i, s in enumerate(good)}
        chosen = sorted(by_source[key], key=lambda st: order[st[0].step_id])
        challenge.append(
            source_record(record, [s for s, _ in chosen], key, categories=[t for _, t in chosen])
        )

    annotation = ROOT / "data" / "annotation"
    write_set(annotation / "later-domain", later)
    write_set(annotation / "challenge", challenge)

    def summary(sources: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "protocols": len(sources),
            "steps": sum(len(s["steps"]) for s in sources),
            "by_split": {
                sp: {
                    "protocols": sum(s["split"] == sp for s in sources),
                    "steps": sum(len(s["steps"]) for s in sources if s["split"] == sp),
                }
                for sp in ("dev", "test")
            },
            "published": [
                min((s["published"] for s in sources), default=None),
                max((s["published"] for s in sources), default=None),
            ],
        }

    category_counts = Counter(
        t for s in challenge for entry in s["steps"] for t in entry.get("categories", [])
    )
    manifest = {
        "collection_version": COLLECTION_VERSION,
        "api": API,
        "search_keys": list(KEYS),
        "parameters": {k: shown(v) for k, v in vars(args).items()},
        "candidates_considered": len(decisions),
        "requests_made_this_run": client.fetched,
        "decisions": decisions,
        "status_counts": dict(
            Counter(
                d["status"].split(":")[0]
                + (":" + d["status"].split(":")[1] if d["status"].startswith("excluded") else "")
                for d in decisions
            )
        ),
        "skipped_steps_in_eligible_protocols": dict(skipped_steps),
        "dropped_components_in_eligible_protocols": dict(dropped),
        "components_seen": dict(components),
        "later_domain": summary(later),
        "challenge": {
            **summary(challenge),
            "category_steps": {c: category_counts[c] for c in CATEGORIES},
            "pool_steps": len(pool),
        },
        "raw_sha256": dict(sorted(raw_hashes.items())),
    }
    out = ROOT / "data" / "manifests" / "protocolsio_collection.json"
    out.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(
        json.dumps(
            {k: manifest[k] for k in ("status_counts", "later_domain", "challenge")}, indent=1
        )
    )
    print(f"requests this run: {client.fetched}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
