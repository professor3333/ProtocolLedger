# scibert-lr2e-5-s21: dev results (best epoch 5)

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.802 | [0.781, 0.825] |
| Entity macro-F1 (18 labels) | 0.751 | |
| Relation micro-F1 (end-to-end) | 0.638 | [0.612, 0.664] |
| Relation macro-F1 (14 labels) | 0.446 | |
| Quantity attachment accuracy (3183) | 0.782 | [0.751, 0.809] |
| Complete-step exact match (2540) | 0.255 | [0.216, 0.302] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.880 | 0.921 | 0.900 | 3812 |
| Reagent | 0.810 | 0.835 | 0.822 | 3432 |
| Modifier | 0.612 | 0.585 | 0.598 | 1478 |
| Location | 0.735 | 0.755 | 0.745 | 1352 |
| Amount | 0.924 | 0.883 | 0.903 | 1044 |
| Time | 0.925 | 0.917 | 0.921 | 687 |
| Device | 0.670 | 0.700 | 0.685 | 574 |
| Method | 0.561 | 0.526 | 0.543 | 506 |
| Temperature | 0.960 | 0.947 | 0.953 | 452 |
| Concentration | 0.792 | 0.851 | 0.820 | 397 |
| Measure-Type | 0.566 | 0.531 | 0.548 | 309 |
| Numerical | 0.644 | 0.657 | 0.651 | 251 |
| Speed | 0.980 | 0.952 | 0.966 | 208 |
| Generic-Measure | 0.427 | 0.355 | 0.388 | 124 |
| Size | 0.794 | 0.631 | 0.703 | 122 |
| Seal | 0.782 | 0.726 | 0.753 | 84 |
| Mention | 0.713 | 0.760 | 0.736 | 75 |
| pH | 0.893 | 0.862 | 0.877 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.731 | 0.700 | 0.715 | 2827 |
| Measure | 0.676 | 0.736 | 0.705 | 1510 |
| Setting | 0.772 | 0.777 | 0.775 | 1482 |
| Mod-Link | 0.560 | 0.503 | 0.530 | 1389 |
| Site | 0.569 | 0.698 | 0.627 | 1073 |
| Using | 0.521 | 0.450 | 0.483 | 731 |
| Meronym | 0.420 | 0.344 | 0.378 | 366 |
| Or | 0.483 | 0.392 | 0.433 | 181 |
| Coreference-Link | 0.400 | 0.306 | 0.347 | 124 |
| Measure-Type-Link | 0.376 | 0.395 | 0.385 | 119 |
| Product | 0.268 | 0.148 | 0.191 | 101 |
| Count | 0.500 | 0.515 | 0.507 | 99 |
| Commands | 0.059 | 0.054 | 0.056 | 37 |
| Of-Type | 0.182 | 0.077 | 0.108 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.996 | [0.992, 0.998] |
| Entity macro-F1 (18 labels) | 0.997 | |
| Relation micro-F1 (end-to-end) | 0.825 | [0.806, 0.841] |
| Relation macro-F1 (14 labels) | 0.642 | |
| Quantity attachment accuracy (3183) | 0.878 | [0.855, 0.900] |
| Complete-step exact match (2523) | 0.464 | [0.429, 0.501] |

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
| Acts-on | 0.918 | 0.827 | 0.870 | 2827 |
| Measure | 0.868 | 0.912 | 0.889 | 1510 |
| Setting | 0.854 | 0.847 | 0.851 | 1482 |
| Mod-Link | 0.925 | 0.808 | 0.862 | 1389 |
| Site | 0.767 | 0.885 | 0.822 | 1073 |
| Using | 0.795 | 0.662 | 0.722 | 731 |
| Meronym | 0.665 | 0.462 | 0.545 | 366 |
| Or | 0.657 | 0.519 | 0.580 | 181 |
| Coreference-Link | 0.618 | 0.379 | 0.470 | 124 |
| Measure-Type-Link | 0.812 | 0.765 | 0.788 | 119 |
| Product | 0.348 | 0.158 | 0.218 | 101 |
| Count | 0.864 | 0.768 | 0.813 | 99 |
| Commands | 0.143 | 0.054 | 0.078 | 37 |
| Of-Type | 0.625 | 0.385 | 0.476 | 26 |
