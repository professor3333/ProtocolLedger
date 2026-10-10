"""Logistic-regression relation classifier over candidate entity pairs.

Candidates are ordered pairs of distinct entities in the same protocol step whose
``(head type, tail type)`` combination occurs in training relations. Each candidate is
classified as one relation label or ``None`` from entity types, direction, distance,
the entities and words between the pair, and punctuation. Gold relations that the
candidate generator cannot produce (cross-step, unseen type pair) are counted and still
scored as misses.

Training uses gold entities; at inference the same classifier runs over whatever entity
predictions it is given.
"""

from __future__ import annotations

import pickle
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression

from protocolledger.data.convert import step_spans
from protocolledger.text.tokenize import tokenize

LOGREG_VERSION = "1"
NONE = "None"
PUNCT = {",": "comma", ";": "semicolon", ".": "period", "(": "paren", ")": "paren", ":": "colon"}
CUE_WORDS = frozenset({"then", "and", "or", "of", "with", "in", "to", "into", "at", "for", "from"})


@dataclass(frozen=True)
class LogRegConfig:
    C: float = 1.0
    max_iter: int = 2000
    max_between_words: int = 8


@dataclass
class CandidateStats:
    gold: int = 0
    cross_step: int = 0
    unseen_type_pair: int = 0
    multilabel_extra: int = 0
    candidates: int = 0
    by_label: Counter[str] = field(default_factory=Counter)


def _bucket(n: int) -> str:
    for limit in (0, 1, 2, 4, 7, 12):
        if n <= limit:
            return str(limit)
    return "13+"


class _Context:
    """Token index lookups for one document."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.steps = step_spans(text)
        self.tokens = tokenize(text)
        self.starts = [t.start for t in self.tokens]

    def step_of(self, offset: int) -> int:
        for i, (s, e) in enumerate(self.steps):
            if s <= offset <= e:
                return i
        return -1

    def token_index(self, offset: int) -> int:
        lo, hi = 0, len(self.starts)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.starts[mid] < offset:
                lo = mid + 1
            else:
                hi = mid
        return lo


def pair_features(
    ctx: _Context,
    head: Mapping[str, Any],
    tail: Mapping[str, Any],
    step_entities: Sequence[Mapping[str, Any]],
    max_between_words: int,
) -> dict[str, float]:
    first, second = (head, tail) if head["start"] <= tail["start"] else (tail, head)
    lo, hi = first["end"], second["start"]
    i_lo, i_hi = ctx.token_index(lo), ctx.token_index(hi)
    between = [t for t in ctx.tokens[i_lo:i_hi] if t.start >= lo and t.end <= hi]
    between_ents = [e for e in step_entities if lo <= e["start"] and e["end"] <= hi]
    hl, tl = head["label"], tail["label"]
    f: dict[str, float] = {
        f"h={hl}": 1,
        f"t={tl}": 1,
        f"pair={hl}|{tl}": 1,
        f"dir={'fwd' if head['start'] <= tail['start'] else 'bwd'}": 1,
        f"pair_dir={hl}|{tl}|{'fwd' if head['start'] <= tail['start'] else 'bwd'}": 1,
        f"dist={_bucket(len(between))}": 1,
        f"n_ents={_bucket(len(between_ents))}": 1,
        f"same_type_as_head_between={_bucket(sum(e['label'] == hl for e in between_ents))}": 1,
        f"same_type_as_tail_between={_bucket(sum(e['label'] == tl for e in between_ents))}": 1,
        f"h_text={ctx.text[head['start'] : head['end']].casefold()}": 1,
        f"t_text={ctx.text[tail['start'] : tail['end']].casefold()}": 1,
    }
    for e in between_ents:
        f[f"between_type={e['label']}"] = 1
    for tok in between:
        word = tok.text.casefold()
        if tok.text in PUNCT:
            f[f"punct={PUNCT[tok.text]}"] = 1
        elif word in CUE_WORDS:
            f[f"cue={word}"] = 1
    if len(between) <= max_between_words:
        for tok in between:
            f[f"bw={tok.text.casefold()}"] = 1
    else:
        f["bw=<long>"] = 1
    h_i, t_i = ctx.token_index(head["start"]), ctx.token_index(tail["start"])
    if t_i > 0:
        f[f"t_prev={ctx.tokens[t_i - 1].text.casefold()}"] = 1
    h_end = ctx.token_index(head["end"])
    if h_end < len(ctx.tokens):
        f[f"h_next={ctx.tokens[h_end].text.casefold()}"] = 1
    if h_i == 0 or ctx.step_of(head["start"]) != ctx.step_of(ctx.tokens[h_i - 1].start):
        f["h_step_initial"] = 1
    return f


def candidate_pairs(
    ctx: _Context, entities: Sequence[Mapping[str, Any]], type_pairs: set[tuple[str, str]]
) -> list[tuple[Mapping[str, Any], Mapping[str, Any], list[Mapping[str, Any]]]]:
    by_step: dict[int, list[Mapping[str, Any]]] = {}
    for e in entities:
        by_step.setdefault(ctx.step_of(e["start"]), []).append(e)
    out = []
    for members in by_step.values():
        for h in members:
            for t in members:
                if h is not t and (h["label"], t["label"]) in type_pairs:
                    out.append((h, t, members))
    return out


class LogRegRelations:
    def __init__(
        self,
        config: LogRegConfig,
        type_pairs: set[tuple[str, str]],
        vectorizer: DictVectorizer,
        classifier: LogisticRegression,
        stats: CandidateStats,
    ) -> None:
        self.config = config
        self.type_pairs = type_pairs
        self.vectorizer = vectorizer
        self.classifier = classifier
        self.train_stats = stats

    @classmethod
    def fit(
        cls, docs: Sequence[Mapping[str, Any]], config: LogRegConfig | None = None
    ) -> LogRegRelations:
        cfg = config or LogRegConfig()
        type_pairs: set[tuple[str, str]] = set()
        for doc in docs:
            ents = {e["id"]: e for e in doc["entities"]}
            ctx = _Context(doc["text"])
            for r in doc["relations"]:
                h, t = ents[r["head"]], ents[r["tail"]]
                if ctx.step_of(h["start"]) == ctx.step_of(t["start"]):
                    type_pairs.add((h["label"], t["label"]))
        stats = CandidateStats()
        rows: list[dict[str, float]] = []
        labels: list[str] = []
        for doc in docs:
            ctx = _Context(doc["text"])
            gold = cls._gold_map(doc, ctx, type_pairs, stats)
            for h, t, members in candidate_pairs(ctx, doc["entities"], type_pairs):
                rows.append(pair_features(ctx, h, t, members, cfg.max_between_words))
                labels.append(gold.get((h["id"], t["id"]), NONE))
        stats.candidates = len(rows)
        stats.by_label = Counter(labels)
        vectorizer = DictVectorizer()
        x = vectorizer.fit_transform(rows)
        classifier = LogisticRegression(C=cfg.C, max_iter=cfg.max_iter)
        classifier.fit(x, labels)
        return cls(cfg, type_pairs, vectorizer, classifier, stats)

    @staticmethod
    def _gold_map(
        doc: Mapping[str, Any],
        ctx: _Context,
        type_pairs: set[tuple[str, str]],
        stats: CandidateStats,
    ) -> dict[tuple[str, str], str]:
        ents = {e["id"]: e for e in doc["entities"]}
        gold: dict[tuple[str, str], str] = {}
        for r in doc["relations"]:
            stats.gold += 1
            h, t = ents[r["head"]], ents[r["tail"]]
            if ctx.step_of(h["start"]) != ctx.step_of(t["start"]):
                stats.cross_step += 1
            elif (h["label"], t["label"]) not in type_pairs:
                stats.unseen_type_pair += 1
            elif (r["head"], r["tail"]) in gold:
                stats.multilabel_extra += 1  # one label per pair; the extra is a miss
            else:
                gold[(r["head"], r["tail"])] = r["label"]
        return gold

    def reachability(self, docs: Sequence[Mapping[str, Any]]) -> CandidateStats:
        stats = CandidateStats()
        for doc in docs:
            self._gold_map(doc, _Context(doc["text"]), self.type_pairs, stats)
        return stats

    def predict_relations(
        self, text: str, entities: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, str]]:
        ctx = _Context(text)
        pairs = candidate_pairs(ctx, entities, self.type_pairs)
        if not pairs:
            return []
        rows = [pair_features(ctx, h, t, m, self.config.max_between_words) for h, t, m in pairs]
        predicted = self.classifier.predict(self.vectorizer.transform(rows))
        return [
            {"head": h["id"], "label": str(label), "tail": t["id"]}
            for (h, t, _), label in zip(pairs, predicted, strict=True)
            if label != NONE
        ]

    def config_json(self) -> dict[str, Any]:
        return {"logreg_version": LOGREG_VERSION, **asdict(self.config)}

    def to_bytes(self) -> bytes:
        """Pickle for a model bundle. Load only bytes whose hash the bundle verified."""
        payload = (asdict(self.config), sorted(self.type_pairs), self.vectorizer, self.classifier)
        return pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def from_bytes(cls, data: bytes) -> LogRegRelations:
        config, type_pairs, vectorizer, classifier = pickle.loads(data)
        return cls(
            LogRegConfig(**config),
            {tuple(p) for p in type_pairs},
            vectorizer,
            classifier,
            CandidateStats(),
        )
