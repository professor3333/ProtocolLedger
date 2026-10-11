import random

from protocolledger.eval.robustness import SUBSTITUTIONS, perturb


def test_perturbation_preserves_length_and_only_substitutes_listed_characters() -> None:
    text = "Add 5 µL of Tris-HCl at 4 °C; mix 1-2 min."
    out = perturb(text, random.Random(0), rate=1.0)
    assert len(out) == len(text)
    for a, b in zip(text, out, strict=True):
        assert a == b or SUBSTITUTIONS[a] == b
    assert " " in out and "μ" in out and "º" in out and "‐" in out


def test_perturbation_is_seeded() -> None:
    text = "Add 5 mL of water to the tube, then mix for 30 s."
    assert perturb(text, random.Random(1)) == perturb(text, random.Random(1))
    assert perturb(text, random.Random(1), rate=0.0) == text
