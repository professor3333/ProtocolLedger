# Error analysis: scibert-uniform-negatives-s21-7dc7a1893e on challenge (test, vs. machine labels)

## Entities (242 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 202 | 83.5% |
| wrong type | 5 | 2.1% |
| wrong boundary | 20 | 8.3% |
| wrong boundary and type | 10 | 4.1% |
| missed | 5 | 2.1% |

## Relations (182 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 116 | 63.7% |
| endpoint error | 48 | 26.4% |
| wrong label | 5 | 2.8% |
| wrong attachment | 5 | 2.8% |
| missed | 8 | 4.4% |

Spurious entities (no overlapping gold): Modifier 6, Action 4, Time 2, Reagent 1

Spurious relations: 20 between gold entities, 44 with a spurious endpoint.

## Slices

| Reagent names | Gold | Recall |
|---|---:|---:|
| seen in training | 44 | 0.886 |
| unseen in training | 34 | 0.824 |

Examples withheld: this is a locked test portion.

Not classified automatically: normalization errors and unsupported inferences (need human-checked labels).
