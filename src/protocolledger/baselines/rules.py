"""Rule-based baseline: what inexpensive, training-derived rules achieve.

Entities, in priority order:

1. **Quantity patterns.** A number or numeric range followed by a known unit (``5 mL``,
   ``14,000 x g``, ``4 °C``), or preceded by a known prefix (``pH 8.0``). Units are learned
   from training spans, case preserved (``mM`` is a concentration, ``mm`` a size); each
   unit gets its majority label, and units whose training precision falls below a
   threshold are dropped.
2. **Training dictionary.** Longest-match lookup of case-folded training entity phrases
   (actions, materials, equipment, non-numeric quantities such as "overnight"), kept
   only when the phrase is annotated often enough wherever it occurs in training text.

Relations: within a clause, each entity attaches to the nearest entity of a compatible
type. The compatible ``(head type, relation)`` options for each tail type, and the rate
at which that tail type has any incoming relation, come from training gold.

Everything is fit on the training split only.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from protocolledger.data.convert import step_spans
from protocolledger.text.tokenize import Token, tokenize

RULES_VERSION = "1"
RANGE_TOKENS = frozenset({"-", "\u2013", "\u2010", "to", "~"})  # hyphen-minus, en dash, hyphen
CLAUSE_END = frozenset({".", ";", "!", "?"})
MAX_UNIT_TOKENS = 3


@dataclass(frozen=True)
class RulesConfig:
    unit_min_count: int = 2
    unit_min_precision: float = 0.5
    lexicon_min_count: int = 2
    lexicon_min_precision: float = 0.5
    lexicon_max_tokens: int = 6
    option_min_share: float = 0.1
    attach_min_rate: float = 0.5


@dataclass
class _Entity:
    id: str
    label: str
    start: int
    end: int


def _unit_key(prefix: Sequence[str], suffix: Sequence[str]) -> str:
    return " ".join(prefix) + "|" + " ".join(suffix)


def _quantity_matches(
    tokens: Sequence[Token], units: Mapping[str, Any]
) -> list[tuple[int, int, str]]:
    """(first token, end token exclusive, unit key) for each quantity match."""
    out: list[tuple[int, int, str]] = []
    i = 0
    while i < len(tokens):
        if not tokens[i].is_number:
            i += 1
            continue
        j = i
        if j + 2 < len(tokens) and tokens[j + 1].text in RANGE_TOKENS and tokens[j + 2].is_number:
            j += 2
        found = None
        prefixes: list[tuple[int, tuple[str, ...]]] = []
        if i > 0 and not tokens[i - 1].is_number:
            prefixes.append((i - 1, (tokens[i - 1].text,)))
        prefixes.append((i, ()))
        for length in range(MAX_UNIT_TOKENS, -1, -1):
            if j + 1 + length > len(tokens):
                continue
            suffix = tuple(t.text for t in tokens[j + 1 : j + 1 + length])
            for first, prefix in prefixes:
                key = _unit_key(prefix, suffix)
                if key in units:
                    found = (first, j + 1 + length, key)
                    break
            if found:
                break
        if found:
            out.append(found)
            i = found[1]
        else:
            i = j + 1
    return out


def _lexicon_matches(
    tokens: Sequence[Token], lexicon: Mapping[str, Any], blocked: set[int], max_len: int
) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    folded = [t.text.casefold() for t in tokens]
    i = 0
    while i < len(tokens):
        hit = None
        for length in range(min(max_len, len(tokens) - i), 0, -1):
            if any(k in blocked for k in range(i, i + length)):
                continue
            key = " ".join(folded[i : i + length])
            if key in lexicon:
                hit = (i, i + length, key)
                break
        if hit:
            out.append(hit)
            i = hit[1]
        else:
            i += 1
    return out


def clause_spans(text: str) -> list[tuple[int, int]]:
    """Clauses: each step split after ``. ; ! ?`` tokens and before the word "then"."""
    spans: list[tuple[int, int]] = []
    for s_start, s_end in step_spans(text):
        start = s_start
        for tok in tokenize(text, s_start, s_end):
            if tok.text.casefold() == "then" and tok.start > start:
                spans.append((start, tok.start))
                start = tok.start
            elif tok.text in CLAUSE_END:
                spans.append((start, tok.end))
                start = tok.end
        spans.append((start, s_end))
    return [(s, e) for s, e in spans if e > s]


def _clause_of(clauses: Sequence[tuple[int, int]], offset: int) -> int:
    for i, (s, e) in enumerate(clauses):
        if s <= offset < e:
            return i
    return -1


def _gap(a: _Entity, b: _Entity) -> int:
    if a.end <= b.start:
        return b.start - a.end
    if b.end <= a.start:
        return a.start - b.end
    return 0


@dataclass
class RulesModel:
    config: RulesConfig
    units: dict[str, dict[str, Any]] = field(default_factory=dict)
    lexicon: dict[str, dict[str, Any]] = field(default_factory=dict)
    attachment: dict[str, dict[str, Any]] = field(default_factory=dict)

    # ----------------------------------------------------------------- fitting

    @classmethod
    def fit(
        cls, docs: Sequence[Mapping[str, Any]], config: RulesConfig | None = None
    ) -> RulesModel:
        model = cls(config or RulesConfig())
        model._fit_units(docs)
        model._fit_lexicon(docs)
        model._fit_attachment(docs)
        return model

    def _fit_units(self, docs: Sequence[Mapping[str, Any]]) -> None:
        cfg = self.config
        labels: dict[str, Counter[str]] = defaultdict(Counter)
        for doc in docs:
            for e in doc["entities"]:
                toks = [t.text for t in tokenize(e["text"])]
                nums = [k for k, t in enumerate(toks) if t[0].isdigit()]
                if not nums:
                    continue
                prefix, suffix = toks[: nums[0]], toks[nums[-1] + 1 :]
                if len(prefix) > 1 or len(suffix) > MAX_UNIT_TOKENS:
                    continue
                labels[_unit_key(prefix, suffix)][e["label"]] += 1
        candidates = {k: c for k, c in labels.items() if sum(c.values()) >= cfg.unit_min_count}
        hits: Counter[str] = Counter()
        seen: Counter[str] = Counter()
        for doc in docs:
            gold = {(e["start"], e["end"]) for e in doc["entities"]}
            for s_start, s_end in step_spans(doc["text"]):
                line = tokenize(doc["text"], s_start, s_end)
                for first, last, key in _quantity_matches(line, candidates):
                    seen[key] += 1
                    hits[key] += (line[first].start, line[last - 1].end) in gold
        for key, counts in candidates.items():
            precision = hits[key] / seen[key] if seen[key] else 0.0
            if precision >= cfg.unit_min_precision:
                label, n = counts.most_common(1)[0]
                self.units[key] = {
                    "label": label,
                    "count": sum(counts.values()),
                    "label_share": round(n / sum(counts.values()), 4),
                    "precision": round(precision, 4),
                }

    def _fit_lexicon(self, docs: Sequence[Mapping[str, Any]]) -> None:
        cfg = self.config
        labels: dict[str, Counter[str]] = defaultdict(Counter)
        for doc in docs:
            for e in doc["entities"]:
                toks = [t.text.casefold() for t in tokenize(e["text"])]
                if 0 < len(toks) <= cfg.lexicon_max_tokens:
                    labels[" ".join(toks)][e["label"]] += 1
        candidates = {k: c for k, c in labels.items() if sum(c.values()) >= cfg.lexicon_min_count}
        occurrences: Counter[str] = Counter()
        for doc in docs:
            for s_start, s_end in step_spans(doc["text"]):
                folded = [t.text.casefold() for t in tokenize(doc["text"], s_start, s_end)]
                for i in range(len(folded)):
                    for length in range(1, min(cfg.lexicon_max_tokens, len(folded) - i) + 1):
                        key = " ".join(folded[i : i + length])
                        if key in candidates:
                            occurrences[key] += 1
        for key, counts in candidates.items():
            total = sum(counts.values())
            precision = min(1.0, total / occurrences[key]) if occurrences[key] else 0.0
            if precision >= cfg.lexicon_min_precision:
                label, n = counts.most_common(1)[0]
                self.lexicon[key] = {
                    "label": label,
                    "count": total,
                    "label_share": round(n / total, 4),
                    "precision": round(precision, 4),
                }

    def _fit_attachment(self, docs: Sequence[Mapping[str, Any]]) -> None:
        cfg = self.config
        totals: Counter[str] = Counter()
        attached: Counter[str] = Counter()
        options: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
        for doc in docs:
            clauses = clause_spans(doc["text"])
            ents = {e["id"]: e for e in doc["entities"]}
            clause = {eid: _clause_of(clauses, e["start"]) for eid, e in ents.items()}
            has_incoming: set[str] = set()
            for r in doc["relations"]:
                head, tail = ents[r["head"]], ents[r["tail"]]
                if clause[head["id"]] == clause[tail["id"]] != -1:
                    options[tail["label"]][(head["label"], r["label"])] += 1
                    has_incoming.add(tail["id"])
            for e in ents.values():
                totals[e["label"]] += 1
                attached[e["label"]] += e["id"] in has_incoming
        for label, counter in options.items():
            n = sum(counter.values())
            kept = [
                [head, rel, round(c / n, 4)]
                for (head, rel), c in counter.most_common()
                if c / n >= cfg.option_min_share
            ]
            self.attachment[label] = {
                "rate": round(attached[label] / totals[label], 4),
                "options": kept,
            }

    # --------------------------------------------------------------- inference

    def predict_entities(self, text: str) -> list[dict[str, Any]]:
        found: list[tuple[int, int, str]] = []
        for s_start, s_end in step_spans(text):
            toks = tokenize(text, s_start, s_end)
            blocked: set[int] = set()
            for first, last, key in _quantity_matches(toks, self.units):
                found.append((toks[first].start, toks[last - 1].end, self.units[key]["label"]))
                blocked.update(range(first, last))
            for first, last, key in _lexicon_matches(
                toks, self.lexicon, blocked, self.config.lexicon_max_tokens
            ):
                found.append((toks[first].start, toks[last - 1].end, self.lexicon[key]["label"]))
        found.sort()
        return [
            {"id": f"P{i}", "label": label, "start": start, "end": end}
            for i, (start, end, label) in enumerate(found, start=1)
        ]

    def predict_relations(
        self, text: str, entities: Iterable[Mapping[str, Any]]
    ) -> list[dict[str, str]]:
        clauses = clause_spans(text)
        ents = [_Entity(e["id"], e["label"], e["start"], e["end"]) for e in entities]
        by_clause: dict[int, list[_Entity]] = defaultdict(list)
        for e in ents:
            by_clause[_clause_of(clauses, e.start)].append(e)
        relations: list[dict[str, str]] = []
        for clause_id, members in by_clause.items():
            if clause_id == -1:
                continue
            for tail in members:
                rule = self.attachment.get(tail.label)
                if rule is None or rule["rate"] < self.config.attach_min_rate:
                    continue
                share = {head: s for head, _, s in rule["options"]}
                rel_for = {head: rel for head, rel, _ in reversed(rule["options"])}
                candidates = [h for h in members if h is not tail and h.label in share]
                if not candidates:
                    continue
                best = min(candidates, key=lambda h: (_gap(h, tail), -share[h.label], h.start))
                relations.append({"head": best.id, "label": rel_for[best.label], "tail": tail.id})
        return relations

    def predict(self, doc: Mapping[str, Any], gold_entities: bool = False) -> dict[str, Any]:
        """End-to-end prediction, or relations only over the gold entities."""
        if gold_entities:
            entities = [{k: e[k] for k in ("id", "label", "start", "end")} for e in doc["entities"]]
        else:
            entities = self.predict_entities(doc["text"])
        return {
            "doc_id": doc["doc_id"],
            "entities": entities,
            "relations": self.predict_relations(doc["text"], entities),
        }

    # ------------------------------------------------------------ persistence

    def to_json(self) -> dict[str, Any]:
        return {
            "rules_version": RULES_VERSION,
            "config": asdict(self.config),
            "units": self.units,
            "lexicon": self.lexicon,
            "attachment": self.attachment,
        }

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> RulesModel:
        if data.get("rules_version") != RULES_VERSION:
            raise ValueError("incompatible rules model version")
        return cls(
            RulesConfig(**data["config"]),
            dict(data["units"]),
            dict(data["lexicon"]),
            dict(data["attachment"]),
        )
