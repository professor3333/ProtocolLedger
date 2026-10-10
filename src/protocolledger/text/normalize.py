"""Encoder-view character substitutions.

Applied only to the word strings handed to a subword tokenizer. Offsets always come from
the original tokens, so raw-text coordinates are never affected.

Each substitution replaces a character that the pinned encoder vocabularies cannot
represent (it becomes ``[UNK]`` or vanishes) with an equivalent they can. This was
checked on 2026-10-10 against SciBERT ``scivocab_cased`` and BERT ``base-cased``:

* U+00B5 MICRO SIGN -> U+03BC GREEK SMALL LETTER MU (SciBERT: ``µL`` -> ``[UNK]``)
* U+00BA MASCULINE ORDINAL INDICATOR -> U+00B0 DEGREE SIGN (common in ``ºC``)
* U+02DA RING ABOVE -> U+00B0 DEGREE SIGN (``˚C``)
* U+2103 DEGREE CELSIUS -> ``°C``
* U+00AD SOFT HYPHEN -> ``-`` (otherwise produces no subwords at all)
"""

from __future__ import annotations

ENCODER_VIEW_VERSION = "1"

_MAP = str.maketrans(
    {
        "µ": "μ",
        "º": "°",
        "˚": "°",
        "℃": "°C",
        "­": "-",
    }
)


def encoder_view(word: str) -> str:
    return word.translate(_MAP)
