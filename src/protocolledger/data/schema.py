"""The WNUT-2020 annotation schema: label inventories and role-name normalization."""

from __future__ import annotations

import re

ENTITY_LABELS: frozenset[str] = frozenset(
    {
        "Action",
        "Amount",
        "Concentration",
        "Device",
        "Generic-Measure",
        "Location",
        "Measure-Type",
        "Mention",
        "Method",
        "Modifier",
        "Numerical",
        "Reagent",
        "Seal",
        "Size",
        "Speed",
        "Temperature",
        "Time",
        "pH",
    }
)

RELATION_LABELS: frozenset[str] = frozenset(
    {
        "Acts-on",
        "Commands",
        "Coreference-Link",
        "Count",
        "Measure",
        "Measure-Type-Link",
        "Meronym",
        "Mod-Link",
        "Of-Type",
        "Or",
        "Product",
        "Setting",
        "Site",
        "Using",
    }
)

# The single BRAT event type in this corpus; its trigger is an Action span.
EVENT_TYPE = "Action"

_REPEAT_SUFFIX = re.compile(r"^(?P<role>.*?\D)\d+$")


def normalize_role(role: str) -> str:
    """Strip BRAT's numeric suffix for repeated event roles: ``Acts-on2`` -> ``Acts-on``."""
    match = _REPEAT_SUFFIX.match(role)
    return match.group("role") if match else role
