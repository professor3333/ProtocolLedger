# scibert-lr5e-5-s13: dev results (best epoch 8)

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.798 | [0.777, 0.820] |
| Entity macro-F1 (18 labels) | 0.744 | |
| Relation micro-F1 (end-to-end) | 0.639 | [0.616, 0.664] |
| Relation macro-F1 (14 labels) | 0.446 | |
| Quantity attachment accuracy (3183) | 0.769 | [0.737, 0.798] |
| Complete-step exact match (2539) | 0.256 | [0.219, 0.302] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.897 | 0.897 | 0.897 | 3812 |
| Reagent | 0.822 | 0.822 | 0.822 | 3432 |
| Modifier | 0.588 | 0.574 | 0.581 | 1478 |
| Location | 0.760 | 0.748 | 0.754 | 1352 |
| Amount | 0.908 | 0.877 | 0.892 | 1044 |
| Time | 0.933 | 0.918 | 0.926 | 687 |
| Device | 0.682 | 0.692 | 0.687 | 574 |
| Method | 0.547 | 0.536 | 0.541 | 506 |
| Temperature | 0.949 | 0.947 | 0.948 | 452 |
| Concentration | 0.783 | 0.864 | 0.822 | 397 |
| Measure-Type | 0.555 | 0.508 | 0.530 | 309 |
| Numerical | 0.652 | 0.614 | 0.632 | 251 |
| Speed | 0.990 | 0.957 | 0.973 | 208 |
| Generic-Measure | 0.382 | 0.339 | 0.359 | 124 |
| Size | 0.817 | 0.623 | 0.707 | 122 |
| Seal | 0.739 | 0.774 | 0.756 | 84 |
| Mention | 0.739 | 0.640 | 0.686 | 75 |
| pH | 0.893 | 0.862 | 0.877 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.712 | 0.708 | 0.710 | 2827 |
| Measure | 0.699 | 0.711 | 0.705 | 1510 |
| Setting | 0.777 | 0.771 | 0.774 | 1482 |
| Mod-Link | 0.544 | 0.509 | 0.526 | 1389 |
| Site | 0.625 | 0.671 | 0.647 | 1073 |
| Using | 0.562 | 0.465 | 0.509 | 731 |
| Meronym | 0.400 | 0.350 | 0.373 | 366 |
| Or | 0.519 | 0.381 | 0.440 | 181 |
| Coreference-Link | 0.429 | 0.290 | 0.346 | 124 |
| Measure-Type-Link | 0.403 | 0.420 | 0.411 | 119 |
| Product | 0.289 | 0.218 | 0.249 | 101 |
| Count | 0.434 | 0.465 | 0.449 | 99 |
| Commands | 0.049 | 0.054 | 0.051 | 37 |
| Of-Type | 0.083 | 0.038 | 0.053 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.996 | [0.992, 0.998] |
| Entity macro-F1 (18 labels) | 0.997 | |
| Relation micro-F1 (end-to-end) | 0.823 | [0.805, 0.839] |
| Relation macro-F1 (14 labels) | 0.656 | |
| Quantity attachment accuracy (3183) | 0.868 | [0.843, 0.892] |
| Complete-step exact match (2523) | 0.466 | [0.432, 0.504] |

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
| Acts-on | 0.884 | 0.847 | 0.865 | 2827 |
| Measure | 0.902 | 0.887 | 0.894 | 1510 |
| Setting | 0.852 | 0.848 | 0.850 | 1482 |
| Mod-Link | 0.911 | 0.793 | 0.848 | 1389 |
| Site | 0.803 | 0.842 | 0.822 | 1073 |
| Using | 0.799 | 0.665 | 0.726 | 731 |
| Meronym | 0.632 | 0.489 | 0.552 | 366 |
| Or | 0.688 | 0.525 | 0.596 | 181 |
| Coreference-Link | 0.676 | 0.403 | 0.505 | 124 |
| Measure-Type-Link | 0.805 | 0.798 | 0.802 | 119 |
| Product | 0.394 | 0.257 | 0.311 | 101 |
| Count | 0.786 | 0.778 | 0.782 | 99 |
| Commands | 0.200 | 0.135 | 0.161 | 37 |
| Of-Type | 0.588 | 0.385 | 0.465 | 26 |
