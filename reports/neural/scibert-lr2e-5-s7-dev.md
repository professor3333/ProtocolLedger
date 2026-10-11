# scibert-lr2e-5-s7: dev results (best epoch 2)

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.802 | [0.782, 0.823] |
| Entity macro-F1 (18 labels) | 0.742 | |
| Relation micro-F1 (end-to-end) | 0.630 | [0.605, 0.655] |
| Relation macro-F1 (14 labels) | 0.427 | |
| Quantity attachment accuracy (3183) | 0.761 | [0.730, 0.788] |
| Complete-step exact match (2537) | 0.245 | [0.210, 0.289] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.870 | 0.923 | 0.896 | 3812 |
| Reagent | 0.800 | 0.844 | 0.821 | 3432 |
| Modifier | 0.633 | 0.592 | 0.612 | 1478 |
| Location | 0.773 | 0.752 | 0.762 | 1352 |
| Amount | 0.902 | 0.880 | 0.891 | 1044 |
| Time | 0.926 | 0.916 | 0.921 | 687 |
| Device | 0.660 | 0.727 | 0.692 | 574 |
| Method | 0.569 | 0.474 | 0.517 | 506 |
| Temperature | 0.962 | 0.947 | 0.954 | 452 |
| Concentration | 0.779 | 0.869 | 0.821 | 397 |
| Measure-Type | 0.638 | 0.508 | 0.566 | 309 |
| Numerical | 0.601 | 0.661 | 0.630 | 251 |
| Speed | 0.949 | 0.885 | 0.915 | 208 |
| Generic-Measure | 0.376 | 0.306 | 0.338 | 124 |
| Size | 0.748 | 0.607 | 0.670 | 122 |
| Seal | 0.789 | 0.667 | 0.723 | 84 |
| Mention | 0.731 | 0.760 | 0.745 | 75 |
| pH | 0.893 | 0.862 | 0.877 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.696 | 0.721 | 0.708 | 2827 |
| Measure | 0.666 | 0.731 | 0.697 | 1510 |
| Setting | 0.740 | 0.744 | 0.742 | 1482 |
| Mod-Link | 0.551 | 0.517 | 0.533 | 1389 |
| Site | 0.590 | 0.682 | 0.633 | 1073 |
| Using | 0.509 | 0.464 | 0.485 | 731 |
| Meronym | 0.375 | 0.355 | 0.365 | 366 |
| Or | 0.393 | 0.326 | 0.356 | 181 |
| Coreference-Link | 0.461 | 0.282 | 0.350 | 124 |
| Measure-Type-Link | 0.515 | 0.420 | 0.463 | 119 |
| Product | 0.125 | 0.020 | 0.034 | 101 |
| Count | 0.484 | 0.455 | 0.469 | 99 |
| Commands | 0.031 | 0.027 | 0.029 | 37 |
| Of-Type | 0.200 | 0.077 | 0.111 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.996 | [0.992, 0.998] |
| Entity macro-F1 (18 labels) | 0.997 | |
| Relation micro-F1 (end-to-end) | 0.816 | [0.799, 0.832] |
| Relation macro-F1 (14 labels) | 0.605 | |
| Quantity attachment accuracy (3183) | 0.867 | [0.840, 0.888] |
| Complete-step exact match (2523) | 0.455 | [0.418, 0.492] |

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
| Acts-on | 0.891 | 0.844 | 0.867 | 2827 |
| Measure | 0.872 | 0.905 | 0.888 | 1510 |
| Setting | 0.834 | 0.833 | 0.834 | 1482 |
| Mod-Link | 0.884 | 0.831 | 0.856 | 1389 |
| Site | 0.774 | 0.867 | 0.818 | 1073 |
| Using | 0.770 | 0.674 | 0.719 | 731 |
| Meronym | 0.571 | 0.465 | 0.512 | 366 |
| Or | 0.591 | 0.486 | 0.533 | 181 |
| Coreference-Link | 0.623 | 0.306 | 0.411 | 124 |
| Measure-Type-Link | 0.854 | 0.740 | 0.793 | 119 |
| Product | 0.200 | 0.020 | 0.036 | 101 |
| Count | 0.838 | 0.677 | 0.749 | 99 |
| Commands | 0.083 | 0.027 | 0.041 | 37 |
| Of-Type | 0.875 | 0.269 | 0.412 | 26 |
