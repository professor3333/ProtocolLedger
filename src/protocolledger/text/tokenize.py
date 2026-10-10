"""A small offset-preserving tokenizer for the baselines.

Tokens are numbers (``14,000``, ``0.5``), runs of letters (``mL``, ``µl``, ``Tris``) or
single other non-space characters (``°``, ``-``, ``%``). Digits and letters are always
separated, so ``30s`` becomes ``30`` + ``s`` and ``10mM`` becomes ``10`` + ``mM``. Every
token keeps its ``[start, end)`` offsets into the raw text; nothing is normalized.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TOKEN = re.compile(r"\d+(?:[.,]\d+)*|[^\W\d_]+|\S")


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int

    @property
    def is_number(self) -> bool:
        return self.text[0].isdigit()


def tokenize(text: str, start: int = 0, end: int | None = None) -> list[Token]:
    """Tokens of ``text[start:end]`` with offsets into the full ``text``."""
    stop = len(text) if end is None else end
    return [Token(m.group(), m.start(), m.end()) for m in _TOKEN.finditer(text, start, stop)]
