# bert-lr2e-5-s13: dev results (best epoch 8)

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.795 | [0.775, 0.816] |
| Entity macro-F1 (18 labels) | 0.741 | |
| Relation micro-F1 (end-to-end) | 0.634 | [0.611, 0.657] |
| Relation macro-F1 (14 labels) | 0.431 | |
| Quantity attachment accuracy (3183) | 0.764 | [0.736, 0.791] |
| Complete-step exact match (2538) | 0.242 | [0.207, 0.286] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.890 | 0.904 | 0.897 | 3812 |
| Reagent | 0.808 | 0.822 | 0.815 | 3432 |
| Modifier | 0.592 | 0.603 | 0.598 | 1478 |
| Location | 0.759 | 0.740 | 0.749 | 1352 |
| Amount | 0.895 | 0.882 | 0.889 | 1044 |
| Time | 0.935 | 0.918 | 0.927 | 687 |
| Device | 0.643 | 0.683 | 0.662 | 574 |
| Method | 0.516 | 0.508 | 0.512 | 506 |
| Temperature | 0.949 | 0.947 | 0.948 | 452 |
| Concentration | 0.766 | 0.851 | 0.807 | 397 |
| Measure-Type | 0.567 | 0.521 | 0.543 | 309 |
| Numerical | 0.625 | 0.618 | 0.621 | 251 |
| Speed | 0.985 | 0.957 | 0.971 | 208 |
| Generic-Measure | 0.372 | 0.258 | 0.305 | 124 |
| Size | 0.794 | 0.631 | 0.703 | 122 |
| Seal | 0.759 | 0.786 | 0.772 | 84 |
| Mention | 0.711 | 0.720 | 0.715 | 75 |
| pH | 0.897 | 0.897 | 0.897 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.710 | 0.712 | 0.711 | 2827 |
| Measure | 0.702 | 0.713 | 0.708 | 1510 |
| Setting | 0.769 | 0.767 | 0.768 | 1482 |
| Mod-Link | 0.536 | 0.513 | 0.524 | 1389 |
| Site | 0.619 | 0.647 | 0.633 | 1073 |
| Using | 0.529 | 0.458 | 0.491 | 731 |
| Meronym | 0.380 | 0.265 | 0.312 | 366 |
| Or | 0.469 | 0.337 | 0.392 | 181 |
| Coreference-Link | 0.402 | 0.315 | 0.353 | 124 |
| Measure-Type-Link | 0.371 | 0.412 | 0.390 | 119 |
| Product | 0.231 | 0.119 | 0.157 | 101 |
| Count | 0.439 | 0.475 | 0.456 | 99 |
| Commands | 0.032 | 0.027 | 0.029 | 37 |
| Of-Type | 0.167 | 0.077 | 0.105 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.996 | [0.992, 0.998] |
| Entity macro-F1 (18 labels) | 0.997 | |
| Relation micro-F1 (end-to-end) | 0.821 | [0.806, 0.836] |
| Relation macro-F1 (14 labels) | 0.639 | |
| Quantity attachment accuracy (3183) | 0.864 | [0.840, 0.888] |
| Complete-step exact match (2523) | 0.452 | [0.417, 0.488] |

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
| Acts-on | 0.891 | 0.841 | 0.865 | 2827 |
| Measure | 0.904 | 0.883 | 0.893 | 1510 |
| Setting | 0.843 | 0.841 | 0.842 | 1482 |
| Mod-Link | 0.899 | 0.806 | 0.850 | 1389 |
| Site | 0.825 | 0.824 | 0.824 | 1073 |
| Using | 0.791 | 0.665 | 0.723 | 731 |
| Meronym | 0.679 | 0.434 | 0.530 | 366 |
| Or | 0.691 | 0.530 | 0.600 | 181 |
| Coreference-Link | 0.588 | 0.403 | 0.478 | 124 |
| Measure-Type-Link | 0.798 | 0.832 | 0.815 | 119 |
| Product | 0.292 | 0.139 | 0.188 | 101 |
| Count | 0.810 | 0.818 | 0.814 | 99 |
| Commands | 0.083 | 0.027 | 0.041 | 37 |
| Of-Type | 0.667 | 0.385 | 0.488 | 26 |
