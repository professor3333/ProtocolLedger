# ProtocolLedger

Structured review of scientific instructions: turn a written lab protocol into a
traceable preparation sheet, review uncertain interpretations, and export the
corrected result.

ProtocolLedger extracts actions, materials, quantities, equipment and operating
conditions from English protocol text, links every prediction to the exact source
characters that support it, and routes uncertain or implicit interpretations to a
human reviewer.

## Status

Early development. No extraction model, API or interface exists yet; this README
describes only what is in the repository today and will grow as features land.

## Development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12.

```bash
uv sync
uv run pytest -m "not slow"
uv run ruff check && uv run ruff format --check && uv run mypy src/
```

## Data acquisition

The corpus is the WNUT-2020 Wet Lab Protocol corpus
([jeniyat/WNUT_2020_NER](https://github.com/jeniyat/WNUT_2020_NER), MIT), pinned at
commit `9a02914e00f0a16c0c6820c4285dd72403a5a5a8`. Only these directories are used:

| Directory | Protocols |
|---|---|
| `data/train_data/Standoff_Format` | 370 |
| `data/dev_data/Standoff_Format` | 122 |
| `data/test_data_2020/Standoff_Format` | 111 |

```bash
uv run python scripts/acquire.py           # download by commit, verify, extract read-only to data/raw/
uv run python scripts/acquire.py --verify  # re-check data/raw/ against the manifest
```

`data/manifests/acquisition.json` records the SHA-256 of every selected file. Those
per-file hashes are authoritative: GitHub generates archives on demand, so the archive
hash is recorded but only a file-level mismatch fails acquisition. Downloaded data is
not committed. The protocol texts originate from [protocols.io](https://www.protocols.io),
where user content is published under CC BY; keep the repository notice and protocol
attribution when redistributing text.
