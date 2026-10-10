"""Linear-chain CRF entity tagger with lexical and character features.

Each protocol step (line) is a sequence of tokens tagged with BIO labels. A BIO tagger
cannot represent overlapping entities, and it cannot represent an entity whose
boundaries fall inside a token. Such gold entities are counted by ``bio_encode`` and
reported; they are still scored as misses, never dropped from evaluation.
"""

from __future__ import annotations

import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pycrfsuite

from protocolledger.data.convert import step_spans
from protocolledger.text.tokenize import Token, tokenize

CRF_VERSION = "1"


@dataclass(frozen=True)
class CRFConfig:
    c1: float = 0.1
    c2: float = 0.05
    max_iterations: int = 150
    min_feature_freq: int = 1


def _shape(word: str) -> str:
    shape = re.sub(r"[A-Z]", "X", word)
    shape = re.sub(r"[a-z]", "x", shape)
    shape = re.sub(r"\d", "d", shape)
    return shape


def _short_shape(word: str) -> str:
    return re.sub(r"(.)\1+", r"\1", _shape(word))


def token_features(tokens: Sequence[Token], i: int) -> list[str]:
    tok = tokens[i]
    w = tok.text
    lower = w.casefold()
    feats = [
        "bias",
        f"w={w}",
        f"lw={lower}",
        f"p2={lower[:2]}",
        f"p3={lower[:3]}",
        f"s2={lower[-2:]}",
        f"s3={lower[-3:]}",
        f"sh={_shape(w)}",
        f"ssh={_short_shape(w)}",
        f"len={min(len(w), 8)}",
        f"pos={min(i, 3)}",
    ]
    if tok.is_number:
        feats.append("is_num")
    if w.isupper():
        feats.append("is_upper")
    if w[:1].isupper():
        feats.append("is_title")
    if not w[0].isalnum():
        feats.append("is_symbol")
    if i > 0 and tokens[i - 1].end == tok.start:
        feats.append("glued_left")
    for off in (-2, -1, 1, 2):
        j = i + off
        if 0 <= j < len(tokens):
            n = tokens[j].text
            feats += [f"{off}:lw={n.casefold()}", f"{off}:ssh={_short_shape(n)}"]
            if tokens[j].is_number:
                feats.append(f"{off}:is_num")
        else:
            feats.append(f"{off}:pad")
    if i > 0:
        feats.append(f"bigram={tokens[i - 1].text.casefold()}|{lower}")
    if i + 1 < len(tokens):
        feats.append(f"bigram+={lower}|{tokens[i + 1].text.casefold()}")
    return feats


@dataclass
class EncodeStats:
    entities: int = 0
    misaligned: int = 0
    overlapping: int = 0

    def __add__(self, other: EncodeStats) -> EncodeStats:
        return EncodeStats(
            self.entities + other.entities,
            self.misaligned + other.misaligned,
            self.overlapping + other.overlapping,
        )


def bio_encode(
    tokens: Sequence[Token], entities: Sequence[Mapping[str, Any]]
) -> tuple[list[str], EncodeStats]:
    tags = ["O"] * len(tokens)
    stats = EncodeStats()
    for e in sorted(entities, key=lambda e: (e["start"], -e["end"])):
        stats.entities += 1
        idx = [k for k, t in enumerate(tokens) if t.start >= e["start"] and t.end <= e["end"]]
        if not idx or tokens[idx[0]].start != e["start"] or tokens[idx[-1]].end != e["end"]:
            stats.misaligned += 1
            continue
        if any(tags[k] != "O" for k in idx):
            stats.overlapping += 1
            continue
        tags[idx[0]] = f"B-{e['label']}"
        for k in idx[1:]:
            tags[k] = f"I-{e['label']}"
    return tags, stats


def bio_decode(tokens: Sequence[Token], tags: Sequence[str]) -> list[tuple[int, int, str]]:
    """Spans from BIO tags; an ``I-`` that does not continue its entity starts a new one."""
    spans: list[tuple[int, int, str]] = []
    current: list[Any] | None = None
    for tok, tag in zip(tokens, tags, strict=True):
        if tag == "O":
            current = None
            continue
        kind, label = tag.split("-", 1)
        if kind == "I" and current is not None and current[2] == label:
            current[1] = tok.end
            spans[-1] = (current[0], current[1], label)
        else:
            current = [tok.start, tok.end, label]
            spans.append((tok.start, tok.end, label))
    return spans


def _doc_steps(doc: Mapping[str, Any]) -> list[tuple[list[Token], list[Mapping[str, Any]]]]:
    text = doc["text"]
    out = []
    for s_start, s_end in step_spans(text):
        toks = tokenize(text, s_start, s_end)
        ents = [e for e in doc.get("entities", []) if s_start <= e["start"] < s_end + 1]
        out.append((toks, ents))
    return out


def encode_stats(docs: Sequence[Mapping[str, Any]]) -> EncodeStats:
    total = EncodeStats()
    for doc in docs:
        for toks, ents in _doc_steps(doc):
            total = total + bio_encode(toks, ents)[1]
    return total


class CRFTagger:
    def __init__(self, config: CRFConfig, model_bytes: bytes) -> None:
        self.config = config
        self._model_bytes = model_bytes
        self._tmp = tempfile.NamedTemporaryFile(suffix=".crfsuite")  # noqa: SIM115
        self._tmp.write(model_bytes)
        self._tmp.flush()
        self._tagger = pycrfsuite.Tagger()
        self._tagger.open(self._tmp.name)

    @classmethod
    def fit(cls, docs: Sequence[Mapping[str, Any]], config: CRFConfig | None = None) -> CRFTagger:
        cfg = config or CRFConfig()
        trainer = pycrfsuite.Trainer(verbose=False)
        for doc in docs:
            for toks, ents in _doc_steps(doc):
                if not toks:
                    continue
                tags, _ = bio_encode(toks, ents)
                xseq = [token_features(toks, i) for i in range(len(toks))]
                trainer.append(xseq, tags)
        trainer.set_params(
            {
                "c1": cfg.c1,
                "c2": cfg.c2,
                "max_iterations": cfg.max_iterations,
                "feature.minfreq": cfg.min_feature_freq,
                "feature.possible_transitions": True,
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.crfsuite"
            trainer.train(str(path))
            return cls(cfg, path.read_bytes())

    def predict_entities(self, text: str) -> list[dict[str, Any]]:
        found: list[tuple[int, int, str]] = []
        for s_start, s_end in step_spans(text):
            toks = tokenize(text, s_start, s_end)
            if not toks:
                continue
            xseq = [token_features(toks, i) for i in range(len(toks))]
            found.extend(bio_decode(toks, self._tagger.tag(xseq)))
        return [
            {"id": f"P{i}", "label": label, "start": start, "end": end}
            for i, (start, end, label) in enumerate(sorted(found), start=1)
        ]

    @property
    def model_bytes(self) -> bytes:
        return self._model_bytes

    def config_json(self) -> dict[str, Any]:
        return {"crf_version": CRF_VERSION, **asdict(self.config)}
