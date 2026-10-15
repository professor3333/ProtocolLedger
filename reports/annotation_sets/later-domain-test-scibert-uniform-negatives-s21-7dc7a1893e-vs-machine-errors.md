# Error analysis: scibert-uniform-negatives-s21-7dc7a1893e on later-domain (test, vs. machine labels)

## Entities (1543 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 1267 | 82.1% |
| wrong type | 76 | 4.9% |
| wrong boundary | 99 | 6.4% |
| wrong boundary and type | 33 | 2.1% |
| missed | 68 | 4.4% |

## Relations (1100 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 688 | 62.5% |
| endpoint error | 274 | 24.9% |
| wrong label | 21 | 1.9% |
| wrong attachment | 44 | 4.0% |
| missed | 73 | 6.6% |

Spurious entities (no overlapping gold): Modifier 27, Method 21, Reagent 19, Time 12, Action 11, Measure-Type 11, Location 5, Device 4

Spurious relations: 113 between gold entities, 264 with a spurious endpoint.

## Slices

| Reagent names | Gold | Recall |
|---|---:|---:|
| seen in training | 210 | 0.919 |
| unseen in training | 234 | 0.829 |

Examples withheld: this is a locked test portion.

Not classified automatically: normalization errors and unsupported inferences (need human-checked labels).
