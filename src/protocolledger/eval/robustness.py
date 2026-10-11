"""Meaning-preserving perturbations for robustness evaluation.

Every substitution replaces one character with one character, so gold offsets stay
valid on the perturbed text and the same gold annotations can be scored directly:

* ordinary space -> NO-BREAK SPACE (U+00A0)
* MICRO SIGN (U+00B5) <-> GREEK SMALL LETTER MU (U+03BC)
* DEGREE SIGN (U+00B0) -> MASCULINE ORDINAL INDICATOR (U+00BA), as in "4 ºC"
* HYPHEN-MINUS -> HYPHEN (U+2010)

Each eligible character is substituted independently with probability ``rate`` under a
fixed seed, so results are reproducible.
"""

from __future__ import annotations

import random

SUBSTITUTIONS = {
    " ": " ",
    "µ": "μ",
    "μ": "µ",
    "°": "º",
    "-": "‐",
}


def perturb(text: str, rng: random.Random, rate: float = 0.5) -> str:
    out = [SUBSTITUTIONS[ch] if ch in SUBSTITUTIONS and rng.random() < rate else ch for ch in text]
    perturbed = "".join(out)
    assert len(perturbed) == len(text)
    return perturbed
