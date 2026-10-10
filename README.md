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
