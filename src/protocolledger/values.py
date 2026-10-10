"""Deterministic normalization of quantity mentions.

The entity type is learned; turning its surface text into a value is a fixed rule. A
mention is normalized only when it matches a supported format. Anything else returns
``None`` together with a reason, so the interface shows the raw text instead of a
guess.

Supported forms:

* number + unit: ``5 mL``, ``1,400 mL``, ``-80°C``, ``14,000 x g``, ``10X``
* range + unit: ``1-2 min``, ``30–60 min``, ``1 to 2 h``, ``5-10 µl``
* unit-less numbers for counts: ``10``, ``2X``, ``8x``
* ratio: ``1:1000``
* ``pH 8.0`` and ``pH 7-8``
* symbolic values: room temperature / RT, overnight, on ice, maximum speed,
  number words (one … ten, once, twice, several)

Units are canonicalized case-sensitively where case carries meaning (``M`` molar vs.
``m`` metre). The entity label resolves ambiguous units: a bare ``g`` is grams for an
Amount but relative centrifugal force (``×g``) for a Speed, and a bare ``C`` after a
number means °C only for a Temperature.
"""

from __future__ import annotations

import re
from typing import Any

VALUES_VERSION = "1"

_MICRO = "(?:µ|μ|u)"
_UNIT_PATTERNS: list[tuple[str, str]] = [
    # (regex over the whitespace-collapsed unit text, canonical unit)
    (rf"^{_MICRO} ?[lL]$", "µL"),
    (r"^m[lL]$|^ML$", "mL"),
    (r"^n[lL]$", "nL"),
    (r"^[lL]$|^liters?$|^litres?$", "L"),
    (r"^mg$", "mg"),
    (r"^g$|^gm$|^grams?$", "g"),
    (r"^units?$|^U$", "U"),
    (r"^-?fold$", "X"),
    (r"^cycles?$", "cycles"),
    (r"^kDa$|^kD$", "kDa"),
    (r"^cm2$|^cm²$", "cm²"),
    (rf"^{_MICRO}g$", "µg"),
    (r"^ng$", "ng"),
    (r"^pg$", "pg"),
    (r"^kg$", "kg"),
    (r"^mM$", "mM"),
    (rf"^{_MICRO}M$", "µM"),
    (r"^nM$", "nM"),
    (r"^pM$", "pM"),
    (r"^M$", "M"),
    (r"^%$|^% \(?[wv] ?/ ?[wv]\)?$|^%[wv]/[wv]$", "%"),
    (r"^[xX×]$", "X"),
    (r"^mg ?/ ?m[lL]$", "mg/mL"),
    (rf"^{_MICRO}g ?/ ?m[lL]$", "µg/mL"),
    (r"^ng ?/ ?m[lL]$", "ng/mL"),
    (rf"^ng ?/ ?{_MICRO}[lL]$", "ng/µL"),
    (r"^g ?/ ?[lL]$", "g/L"),
    (rf"^U ?/ ?{_MICRO}[lL]$", "U/µL"),
    (r"^U ?/ ?m[lL]$", "U/mL"),
    (r"^(?:°|º|˚|⁰) ?C$|^℃$|^degrees? ?C(?:elsius)?$|^oC$", "°C"),
    (r"^(?:°|º|˚) ?F$", "°F"),
    (r"^s$|^secs?$|^seconds?$", "s"),
    (r"^mins?$|^minutes?$", "min"),
    (r"^h$|^hrs?$|^hours?$", "h"),
    (r"^days?$|^d$", "d"),
    (r"^weeks?$", "wk"),
    (r"^rpm$|^RPM$", "rpm"),
    (r"^[xX×] ?g$|^rcf$|^RCF$", "×g"),
    (r"^mm$", "mm"),
    (r"^cm$", "cm"),
    (rf"^{_MICRO}m$", "µm"),
    (r"^nm$", "nm"),
    (r"^bp$", "bp"),
    (r"^kb$", "kb"),
    (r"^V$", "V"),
    (r"^times$", "times"),
]
_COMPILED = [(re.compile(p), unit) for p, unit in _UNIT_PATTERNS]

_NUMBER = r"[-−–]?\d+(?:,\d{3})*(?:\.\d+)?|[-−–]?\.\d+"
_RANGE_SEP = r"\s*(?:-|–|‐|−|~|to)\s*"
_QUANTITY = re.compile(
    rf"^(?P<low>{_NUMBER})(?:{_RANGE_SEP}(?P<high>{_NUMBER}))?\s*(?P<unit>.*?)\s*\.?$"
)
_RATIO = re.compile(r"^(?P<a>\d+(?:\.\d+)?)\s*:\s*(?P<b>\d+(?:\.\d+)?)$")
_PH = re.compile(rf"^pH\s*(?P<low>{_NUMBER})(?:{_RANGE_SEP}(?P<high>{_NUMBER}))?$")

_SYMBOLIC = {
    "room temperature": "room temperature",
    "room temp": "room temperature",
    "room temp.": "room temperature",
    "rt": "room temperature",
    "ambient temperature": "room temperature",
    "overnight": "overnight",
    "over night": "overnight",
    "o/n": "overnight",
    "on ice": "on ice",
    "ice": "on ice",
    "max speed": "maximum speed",
    "maximum speed": "maximum speed",
    "full speed": "maximum speed",
    "top speed": "maximum speed",
    "several": "several",
    "several times": "several",
}
_COUNT_WORDS = dict(
    zip(
        [
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "once",
            "twice",
            "single",
            "double",
        ],
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 2, 1, 2),
        strict=True,
    )
)


_QUALIFIERS = {
    "~": "approximately",
    "approx.": "approximately",
    "approximately": "approximately",
    "ca.": "approximately",
    "about": "approximately",
    "<": "less than",
    ">": "more than",
    "≤": "at most",
    "≥": "at least",
    "<=": "at most",
    ">=": "at least",
    "up to": "at most",
    "at least": "at least",
    "at most": "at most",
}
_QUALIFIER = re.compile(
    r"^(?P<q>"
    + "|".join(re.escape(q) for q in sorted(_QUALIFIERS, key=len, reverse=True))
    + r")\s*(?=[\d.a-zA-Z])",
    re.IGNORECASE,
)
_UNIT_WORD_NUMBERS = {
    "a": "1",
    "an": "1",
    **{
        w: str(n)
        for w, n in [
            ("one", 1),
            ("two", 2),
            ("three", 3),
            ("four", 4),
            ("five", 5),
            ("six", 6),
            ("seven", 7),
            ("eight", 8),
            ("nine", 9),
            ("ten", 10),
            ("fifteen", 15),
            ("twenty", 20),
            ("thirty", 30),
        ]
    },
}


def _number(text: str) -> float:
    return float(text.replace(",", "").replace("−", "-").replace("–", "-"))


def _clean(value: float) -> int | float:
    return int(value) if value.is_integer() else value


def canonical_unit(unit: str, label: str) -> str | None:
    collapsed = " ".join(unit.split())
    if collapsed == "":
        return ""
    if collapsed == "g" and label == "Speed":
        return "×g"
    if collapsed == "N" and label == "Concentration":
        return "N"
    if collapsed == "C" and label == "Temperature":
        return "°C"
    if collapsed == "K" and label == "Speed":
        return None  # "14K" is a thousands shorthand, not kelvin; unsupported
    for pattern, canon in _COMPILED:
        if pattern.match(collapsed):
            return canon
    return None


def normalize_value(text: str, label: str) -> tuple[dict[str, Any] | None, str]:
    """Return (normalized value or None, reason)."""
    raw = " ".join(text.replace("\u00a0", " ").split())
    folded = raw.casefold().rstrip(".")
    if folded in _SYMBOLIC:
        return {"kind": "symbolic", "value": _SYMBOLIC[folded]}, "ok"
    if folded in _COUNT_WORDS:
        return {"kind": "number", "value": _COUNT_WORDS[folded], "unit": "times"}, "ok"

    qualifier = None
    if q := _QUALIFIER.match(raw):
        qualifier = _QUALIFIERS[q["q"].casefold()]
        raw = raw[q.end() :]
    words = raw.split(" ", 1)
    if len(words) == 2 and words[0].casefold() in _UNIT_WORD_NUMBERS:
        raw = f"{_UNIT_WORD_NUMBERS[words[0].casefold()]} {words[1]}"

    if ph := _PH.match(raw):
        low = _clean(_number(ph["low"]))
        if ph["high"]:
            high = _clean(_number(ph["high"]))
            return {"kind": "range", "low": low, "high": high, "unit": "pH"}, "ok"
        return {"kind": "number", "value": low, "unit": "pH"}, "ok"
    if ratio := _RATIO.match(raw):
        numerator, denominator = _clean(_number(ratio["a"])), _clean(_number(ratio["b"]))
        return {"kind": "ratio", "numerator": numerator, "denominator": denominator}, "ok"

    match = _QUANTITY.match(raw)
    if not match:
        return None, "unsupported format"
    unit = canonical_unit(match["unit"], label)
    if unit is None:
        return None, f"unsupported unit {match['unit']!r}"
    if unit == "" and label not in {"Numerical", "Generic-Measure", "Concentration"}:
        return None, "missing unit"
    low = _clean(_number(match["low"]))
    value: dict[str, Any]
    if match["high"]:
        high = _clean(_number(match["high"]))
        if high <= low:
            return None, "range is not increasing"
        value = {"kind": "range", "low": low, "high": high}
    else:
        value = {"kind": "number", "value": low}
    if unit:
        value["unit"] = unit
    if qualifier:
        value["qualifier"] = qualifier
    return value, "ok"
