# scibert-uniform-negatives-s21: dev results (best epoch 9)

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.800 | [0.780, 0.823] |
| Entity macro-F1 (18 labels) | 0.750 | |
| Relation micro-F1 (end-to-end) | 0.639 | [0.614, 0.665] |
| Relation macro-F1 (14 labels) | 0.451 | |
| Quantity attachment accuracy (3183) | 0.756 | [0.719, 0.789] |
| Complete-step exact match (2540) | 0.252 | [0.213, 0.299] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.882 | 0.912 | 0.897 | 3812 |
| Reagent | 0.821 | 0.831 | 0.826 | 3432 |
| Modifier | 0.610 | 0.587 | 0.598 | 1478 |
| Location | 0.757 | 0.738 | 0.747 | 1352 |
| Amount | 0.911 | 0.878 | 0.895 | 1044 |
| Time | 0.915 | 0.908 | 0.912 | 687 |
| Device | 0.661 | 0.704 | 0.682 | 574 |
| Method | 0.558 | 0.543 | 0.551 | 506 |
| Temperature | 0.941 | 0.947 | 0.944 | 452 |
| Concentration | 0.779 | 0.841 | 0.809 | 397 |
| Measure-Type | 0.549 | 0.566 | 0.557 | 309 |
| Numerical | 0.671 | 0.633 | 0.652 | 251 |
| Speed | 0.980 | 0.947 | 0.963 | 208 |
| Generic-Measure | 0.408 | 0.339 | 0.370 | 124 |
| Size | 0.793 | 0.598 | 0.682 | 122 |
| Seal | 0.775 | 0.821 | 0.798 | 84 |
| Mention | 0.704 | 0.760 | 0.731 | 75 |
| pH | 0.897 | 0.897 | 0.897 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.728 | 0.710 | 0.719 | 2827 |
| Measure | 0.706 | 0.711 | 0.708 | 1510 |
| Setting | 0.772 | 0.757 | 0.765 | 1482 |
| Mod-Link | 0.547 | 0.502 | 0.523 | 1389 |
| Site | 0.610 | 0.650 | 0.629 | 1073 |
| Using | 0.530 | 0.502 | 0.515 | 731 |
| Meronym | 0.424 | 0.320 | 0.364 | 366 |
| Or | 0.570 | 0.359 | 0.441 | 181 |
| Coreference-Link | 0.410 | 0.315 | 0.356 | 124 |
| Measure-Type-Link | 0.397 | 0.471 | 0.431 | 119 |
| Product | 0.286 | 0.178 | 0.220 | 101 |
| Count | 0.461 | 0.475 | 0.468 | 99 |
| Commands | 0.029 | 0.027 | 0.028 | 37 |
| Of-Type | 0.188 | 0.115 | 0.143 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.996 | [0.992, 0.998] |
| Entity macro-F1 (18 labels) | 0.997 | |
| Relation micro-F1 (end-to-end) | 0.830 | [0.813, 0.845] |
| Relation macro-F1 (14 labels) | 0.650 | |
| Quantity attachment accuracy (3183) | 0.865 | [0.839, 0.889] |
| Complete-step exact match (2523) | 0.478 | [0.443, 0.514] |

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
| Acts-on | 0.907 | 0.842 | 0.873 | 2827 |
| Measure | 0.911 | 0.891 | 0.901 | 1510 |
| Setting | 0.867 | 0.841 | 0.853 | 1482 |
| Mod-Link | 0.908 | 0.828 | 0.866 | 1389 |
| Site | 0.821 | 0.827 | 0.824 | 1073 |
| Using | 0.775 | 0.707 | 0.740 | 731 |
| Meronym | 0.675 | 0.448 | 0.539 | 366 |
| Or | 0.713 | 0.508 | 0.594 | 181 |
| Coreference-Link | 0.633 | 0.403 | 0.493 | 124 |
| Measure-Type-Link | 0.810 | 0.790 | 0.800 | 119 |
| Product | 0.351 | 0.198 | 0.253 | 101 |
| Count | 0.810 | 0.778 | 0.794 | 99 |
| Commands | 0.133 | 0.054 | 0.077 | 37 |
| Of-Type | 0.667 | 0.385 | 0.488 | 26 |
