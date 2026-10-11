# scibert-uniform-negatives-s13: dev results (best epoch 9)

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.800 | [0.780, 0.822] |
| Entity macro-F1 (18 labels) | 0.750 | |
| Relation micro-F1 (end-to-end) | 0.644 | [0.619, 0.670] |
| Relation macro-F1 (14 labels) | 0.448 | |
| Quantity attachment accuracy (3183) | 0.761 | [0.727, 0.790] |
| Complete-step exact match (2538) | 0.253 | [0.215, 0.301] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.888 | 0.914 | 0.901 | 3812 |
| Reagent | 0.820 | 0.833 | 0.826 | 3432 |
| Modifier | 0.599 | 0.583 | 0.591 | 1478 |
| Location | 0.758 | 0.740 | 0.749 | 1352 |
| Amount | 0.912 | 0.887 | 0.899 | 1044 |
| Time | 0.931 | 0.917 | 0.924 | 687 |
| Device | 0.658 | 0.686 | 0.672 | 574 |
| Method | 0.542 | 0.522 | 0.532 | 506 |
| Temperature | 0.936 | 0.947 | 0.942 | 452 |
| Concentration | 0.780 | 0.849 | 0.813 | 397 |
| Measure-Type | 0.544 | 0.563 | 0.553 | 309 |
| Numerical | 0.618 | 0.594 | 0.606 | 251 |
| Speed | 0.985 | 0.947 | 0.966 | 208 |
| Generic-Measure | 0.422 | 0.347 | 0.381 | 124 |
| Size | 0.779 | 0.607 | 0.682 | 122 |
| Seal | 0.809 | 0.809 | 0.809 | 84 |
| Mention | 0.757 | 0.747 | 0.752 | 75 |
| pH | 0.897 | 0.897 | 0.897 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.735 | 0.712 | 0.723 | 2827 |
| Measure | 0.712 | 0.719 | 0.716 | 1510 |
| Setting | 0.773 | 0.765 | 0.769 | 1482 |
| Mod-Link | 0.566 | 0.504 | 0.533 | 1389 |
| Site | 0.626 | 0.669 | 0.647 | 1073 |
| Using | 0.524 | 0.475 | 0.498 | 731 |
| Meronym | 0.417 | 0.358 | 0.385 | 366 |
| Or | 0.550 | 0.332 | 0.414 | 181 |
| Coreference-Link | 0.437 | 0.306 | 0.360 | 124 |
| Measure-Type-Link | 0.410 | 0.479 | 0.442 | 119 |
| Product | 0.288 | 0.168 | 0.212 | 101 |
| Count | 0.385 | 0.404 | 0.394 | 99 |
| Commands | 0.029 | 0.027 | 0.028 | 37 |
| Of-Type | 0.231 | 0.115 | 0.154 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.996 | [0.992, 0.998] |
| Entity macro-F1 (18 labels) | 0.997 | |
| Relation micro-F1 (end-to-end) | 0.828 | [0.811, 0.844] |
| Relation macro-F1 (14 labels) | 0.646 | |
| Quantity attachment accuracy (3183) | 0.862 | [0.836, 0.886] |
| Complete-step exact match (2523) | 0.472 | [0.438, 0.509] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 1.000 | 0.996 | 0.998 | 3812 |
| Reagent | 1.000 | 0.982 | 0.991 | 3432 |
| Modifier | 1.000 | 0.997 | 0.998 | 1478 |
| Location | 1.000 | 0.996 | 0.998 | 1352 |
| Amount | 1.000 | 0.974 | 0.987 | 1044 |
| Time | 1.000 | 0.991 | 0.996 | 687 |
| Device | 1.000 | 0.997 | 0.998 | 574 |
| Method | 1.000 | 1.000 | 1.000 | 506 |
| Temperature | 1.000 | 0.998 | 0.999 | 452 |
| Concentration | 1.000 | 0.992 | 0.996 | 397 |
| Measure-Type | 1.000 | 0.990 | 0.995 | 309 |
| Numerical | 1.000 | 0.996 | 0.998 | 251 |
| Speed | 1.000 | 1.000 | 1.000 | 208 |
| Generic-Measure | 1.000 | 0.984 | 0.992 | 124 |
| Size | 1.000 | 1.000 | 1.000 | 122 |
| Seal | 1.000 | 1.000 | 1.000 | 84 |
| Mention | 1.000 | 1.000 | 1.000 | 75 |
| pH | 1.000 | 1.000 | 1.000 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.910 | 0.842 | 0.875 | 2827 |
| Measure | 0.901 | 0.889 | 0.895 | 1510 |
| Setting | 0.863 | 0.836 | 0.849 | 1482 |
| Mod-Link | 0.921 | 0.811 | 0.863 | 1389 |
| Site | 0.812 | 0.842 | 0.827 | 1073 |
| Using | 0.789 | 0.672 | 0.726 | 731 |
| Meronym | 0.638 | 0.486 | 0.552 | 366 |
| Or | 0.739 | 0.470 | 0.574 | 181 |
| Coreference-Link | 0.690 | 0.395 | 0.503 | 124 |
| Measure-Type-Link | 0.838 | 0.781 | 0.809 | 119 |
| Product | 0.370 | 0.198 | 0.258 | 101 |
| Count | 0.828 | 0.778 | 0.802 | 99 |
| Commands | 0.059 | 0.027 | 0.037 | 37 |
| Of-Type | 0.625 | 0.385 | 0.476 | 26 |
