from typing import Any

import pytest

from protocolledger.values import normalize_value

SUPPORTED: list[tuple[str, str, dict[str, Any]]] = [
    ("5 mL", "Amount", {"kind": "number", "value": 5, "unit": "mL"}),
    ("1,400 mL", "Amount", {"kind": "number", "value": 1400, "unit": "mL"}),
    ("2.5ul", "Amount", {"kind": "number", "value": 2.5, "unit": "µL"}),
    ("100 µl", "Amount", {"kind": "number", "value": 100, "unit": "µL"}),
    ("1 μL", "Amount", {"kind": "number", "value": 1, "unit": "µL"}),
    ("2 µl", "Amount", {"kind": "number", "value": 2, "unit": "µL"}),
    ("1 g", "Amount", {"kind": "number", "value": 1, "unit": "g"}),
    ("30 s", "Time", {"kind": "number", "value": 30, "unit": "s"}),
    ("15 minutes", "Time", {"kind": "number", "value": 15, "unit": "min"}),
    ("1-2 minutes", "Time", {"kind": "range", "low": 1, "high": 2, "unit": "min"}),
    ("30–60 min", "Time", {"kind": "range", "low": 30, "high": 60, "unit": "min"}),
    ("1 to 2 h", "Time", {"kind": "range", "low": 1, "high": 2, "unit": "h"}),
    ("two minutes", "Time", {"kind": "number", "value": 2, "unit": "min"}),
    (
        "~30 min",
        "Time",
        {"kind": "number", "value": 30, "unit": "min", "qualifier": "approximately"},
    ),
    ("overnight", "Time", {"kind": "symbolic", "value": "overnight"}),
    ("4 °C", "Temperature", {"kind": "number", "value": 4, "unit": "°C"}),
    ("37°C", "Temperature", {"kind": "number", "value": 37, "unit": "°C"}),
    ("-80ºC", "Temperature", {"kind": "number", "value": -80, "unit": "°C"}),
    ("–20°C", "Temperature", {"kind": "number", "value": -20, "unit": "°C"}),
    ("95C", "Temperature", {"kind": "number", "value": 95, "unit": "°C"}),
    ("RT", "Temperature", {"kind": "symbolic", "value": "room temperature"}),
    ("on ice", "Temperature", {"kind": "symbolic", "value": "on ice"}),
    ("14,000 x g", "Speed", {"kind": "number", "value": 14000, "unit": "×g"}),
    ("14,000xg", "Speed", {"kind": "number", "value": 14000, "unit": "×g"}),
    ("6000g", "Speed", {"kind": "number", "value": 6000, "unit": "×g"}),
    ("3,000rpm", "Speed", {"kind": "number", "value": 3000, "unit": "rpm"}),
    ("max speed", "Speed", {"kind": "symbolic", "value": "maximum speed"}),
    ("10 mM", "Concentration", {"kind": "number", "value": 10, "unit": "mM"}),
    ("0.5M", "Concentration", {"kind": "number", "value": 0.5, "unit": "M"}),
    ("80%", "Concentration", {"kind": "number", "value": 80, "unit": "%"}),
    ("10X", "Concentration", {"kind": "number", "value": 10, "unit": "X"}),
    ("1:1000", "Concentration", {"kind": "ratio", "numerator": 1, "denominator": 1000}),
    ("pH 8.0", "pH", {"kind": "number", "value": 8, "unit": "pH"}),
    ("2 mm", "Size", {"kind": "number", "value": 2, "unit": "mm"}),
    ("10", "Numerical", {"kind": "number", "value": 10}),
    ("twice", "Numerical", {"kind": "number", "value": 2, "unit": "times"}),
]


@pytest.mark.parametrize(("text", "label", "expected"), SUPPORTED)
def test_supported_formats(text: str, label: str, expected: dict[str, Any]) -> None:
    value, reason = normalize_value(text, label)
    assert (value, reason) == (expected, "ok")


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("4 degrees", "Temperature"),  # Celsius or Fahrenheit: refuse to guess
        ("1 x 108", "Numerical"),  # superscript lost from 1×10^8
        ("10", "Amount"),  # an amount without a unit
        ("5 m", "Time"),  # minutes or metres
        ("10-5 min", "Time"),  # decreasing range
        ("appropriate concentration", "Concentration"),
        ("14K", "Speed"),
    ],
)
def test_ambiguous_or_unsupported_formats_are_refused(text: str, label: str) -> None:
    value, reason = normalize_value(text, label)
    assert value is None and reason != "ok"


def test_unit_case_carries_meaning() -> None:
    assert normalize_value("2 mM", "Concentration")[0] == {
        "kind": "number",
        "value": 2,
        "unit": "mM",
    }
    assert normalize_value("2 mm", "Size")[0] == {"kind": "number", "value": 2, "unit": "mm"}
    assert normalize_value("2 M", "Concentration")[0] == {"kind": "number", "value": 2, "unit": "M"}
