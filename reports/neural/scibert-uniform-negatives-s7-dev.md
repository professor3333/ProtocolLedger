# scibert-uniform-negatives-s7: dev results (best epoch 3)

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.800 | [0.779, 0.822] |
| Entity macro-F1 (18 labels) | 0.746 | |
| Relation micro-F1 (end-to-end) | 0.637 | [0.612, 0.662] |
| Relation macro-F1 (14 labels) | 0.447 | |
| Quantity attachment accuracy (3183) | 0.755 | [0.721, 0.784] |
| Complete-step exact match (2539) | 0.248 | [0.212, 0.291] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.878 | 0.918 | 0.897 | 3812 |
| Reagent | 0.808 | 0.836 | 0.822 | 3432 |
| Modifier | 0.620 | 0.598 | 0.609 | 1478 |
| Location | 0.731 | 0.754 | 0.742 | 1352 |
| Amount | 0.925 | 0.866 | 0.895 | 1044 |
| Time | 0.918 | 0.918 | 0.918 | 687 |
| Device | 0.699 | 0.662 | 0.680 | 574 |
| Method | 0.562 | 0.516 | 0.538 | 506 |
| Temperature | 0.953 | 0.947 | 0.950 | 452 |
| Concentration | 0.808 | 0.856 | 0.831 | 397 |
| Measure-Type | 0.532 | 0.654 | 0.586 | 309 |
| Numerical | 0.617 | 0.673 | 0.644 | 251 |
| Speed | 0.935 | 0.904 | 0.919 | 208 |
| Generic-Measure | 0.423 | 0.290 | 0.344 | 124 |
| Size | 0.793 | 0.566 | 0.660 | 122 |
| Seal | 0.836 | 0.726 | 0.777 | 84 |
| Mention | 0.670 | 0.787 | 0.724 | 75 |
| pH | 0.897 | 0.897 | 0.897 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.705 | 0.706 | 0.706 | 2827 |
| Measure | 0.740 | 0.709 | 0.724 | 1510 |
| Setting | 0.732 | 0.756 | 0.744 | 1482 |
| Mod-Link | 0.555 | 0.517 | 0.535 | 1389 |
| Site | 0.620 | 0.659 | 0.639 | 1073 |
| Using | 0.570 | 0.423 | 0.485 | 731 |
| Meronym | 0.508 | 0.268 | 0.351 | 366 |
| Or | 0.517 | 0.332 | 0.404 | 181 |
| Coreference-Link | 0.568 | 0.169 | 0.261 | 124 |
| Measure-Type-Link | 0.424 | 0.513 | 0.464 | 119 |
| Product | 0.282 | 0.218 | 0.246 | 101 |
| Count | 0.505 | 0.535 | 0.520 | 99 |
| Commands | 0.031 | 0.027 | 0.029 | 37 |
| Of-Type | 0.143 | 0.154 | 0.148 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.996 | [0.992, 0.998] |
| Entity macro-F1 (18 labels) | 0.997 | |
| Relation micro-F1 (end-to-end) | 0.822 | [0.805, 0.838] |
| Relation macro-F1 (14 labels) | 0.629 | |
| Quantity attachment accuracy (3183) | 0.856 | [0.830, 0.879] |
| Complete-step exact match (2523) | 0.461 | [0.426, 0.498] |

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
| Acts-on | 0.903 | 0.841 | 0.871 | 2827 |
| Measure | 0.930 | 0.869 | 0.898 | 1510 |
| Setting | 0.820 | 0.845 | 0.832 | 1482 |
| Mod-Link | 0.904 | 0.831 | 0.866 | 1389 |
| Site | 0.825 | 0.837 | 0.831 | 1073 |
| Using | 0.809 | 0.620 | 0.702 | 731 |
| Meronym | 0.760 | 0.347 | 0.476 | 366 |
| Or | 0.661 | 0.475 | 0.553 | 181 |
| Coreference-Link | 0.828 | 0.194 | 0.314 | 124 |
| Measure-Type-Link | 0.844 | 0.773 | 0.807 | 119 |
| Product | 0.333 | 0.247 | 0.284 | 101 |
| Count | 0.810 | 0.818 | 0.814 | 99 |
| Commands | 0.077 | 0.027 | 0.040 | 37 |
| Of-Type | 0.457 | 0.615 | 0.525 | 26 |
