# Error analysis: crf-logreg-4a9d8cc549 on challenge (test, vs. machine labels)

## Entities (242 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 188 | 77.7% |
| wrong type | 9 | 3.7% |
| wrong boundary | 22 | 9.1% |
| wrong boundary and type | 16 | 6.6% |
| missed | 7 | 2.9% |

## Relations (182 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 100 | 54.9% |
| endpoint error | 57 | 31.3% |
| wrong label | 4 | 2.2% |
| wrong attachment | 7 | 3.9% |
| missed | 14 | 7.7% |

Spurious entities (no overlapping gold): Modifier 3, Action 3, Reagent 1

Spurious relations: 14 between gold entities, 35 with a spurious endpoint.

## Slices

| Reagent names | Gold | Recall |
|---|---:|---:|
| seen in training | 44 | 0.773 |
| unseen in training | 34 | 0.794 |

Examples withheld: this is a locked test portion.

Not classified automatically: normalization errors and unsupported inferences (need human-checked labels).
