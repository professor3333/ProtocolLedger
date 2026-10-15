# Error analysis: crf-logreg-4a9d8cc549 on later-domain (test, vs. machine labels)

## Entities (1543 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 1083 | 70.2% |
| wrong type | 91 | 5.9% |
| wrong boundary | 175 | 11.3% |
| wrong boundary and type | 97 | 6.3% |
| missed | 97 | 6.3% |

## Relations (1100 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 518 | 47.1% |
| endpoint error | 447 | 40.6% |
| wrong label | 22 | 2.0% |
| wrong attachment | 42 | 3.8% |
| missed | 71 | 6.5% |

Spurious entities (no overlapping gold): Reagent 28, Modifier 21, Action 19, Method 14, Time 7, Measure-Type 4, Location 4, Numerical 2

Spurious relations: 70 between gold entities, 279 with a spurious endpoint.

## Slices

| Reagent names | Gold | Recall |
|---|---:|---:|
| seen in training | 210 | 0.824 |
| unseen in training | 234 | 0.658 |

Examples withheld: this is a locked test portion.

Not classified automatically: normalization errors and unsupported inferences (need human-checked labels).
