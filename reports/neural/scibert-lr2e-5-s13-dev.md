# scibert-lr2e-5-s13: dev results (best epoch 8)

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.802 | [0.782, 0.824] |
| Entity macro-F1 (18 labels) | 0.748 | |
| Relation micro-F1 (end-to-end) | 0.641 | [0.617, 0.667] |
| Relation macro-F1 (14 labels) | 0.452 | |
| Quantity attachment accuracy (3183) | 0.760 | [0.727, 0.791] |
| Complete-step exact match (2538) | 0.255 | [0.217, 0.299] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.898 | 0.906 | 0.902 | 3812 |
| Reagent | 0.823 | 0.830 | 0.826 | 3432 |
| Modifier | 0.596 | 0.605 | 0.600 | 1478 |
| Location | 0.757 | 0.743 | 0.750 | 1352 |
| Amount | 0.899 | 0.878 | 0.889 | 1044 |
| Time | 0.925 | 0.920 | 0.923 | 687 |
| Device | 0.686 | 0.693 | 0.690 | 574 |
| Method | 0.540 | 0.541 | 0.541 | 506 |
| Temperature | 0.947 | 0.947 | 0.947 | 452 |
| Concentration | 0.783 | 0.856 | 0.818 | 397 |
| Measure-Type | 0.582 | 0.553 | 0.567 | 309 |
| Numerical | 0.625 | 0.610 | 0.617 | 251 |
| Speed | 0.990 | 0.952 | 0.971 | 208 |
| Generic-Measure | 0.430 | 0.347 | 0.384 | 124 |
| Size | 0.783 | 0.590 | 0.673 | 122 |
| Seal | 0.773 | 0.809 | 0.791 | 84 |
| Mention | 0.729 | 0.680 | 0.703 | 75 |
| pH | 0.893 | 0.862 | 0.877 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.720 | 0.710 | 0.715 | 2827 |
| Measure | 0.704 | 0.713 | 0.708 | 1510 |
| Setting | 0.774 | 0.767 | 0.771 | 1482 |
| Mod-Link | 0.546 | 0.523 | 0.535 | 1389 |
| Site | 0.624 | 0.661 | 0.642 | 1073 |
| Using | 0.540 | 0.461 | 0.497 | 731 |
| Meronym | 0.427 | 0.344 | 0.381 | 366 |
| Or | 0.568 | 0.348 | 0.431 | 181 |
| Coreference-Link | 0.471 | 0.323 | 0.383 | 124 |
| Measure-Type-Link | 0.430 | 0.462 | 0.445 | 119 |
| Product | 0.284 | 0.188 | 0.226 | 101 |
| Count | 0.408 | 0.424 | 0.416 | 99 |
| Commands | 0.027 | 0.027 | 0.027 | 37 |
| Of-Type | 0.214 | 0.115 | 0.150 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.996 | [0.992, 0.998] |
| Entity macro-F1 (18 labels) | 0.997 | |
| Relation micro-F1 (end-to-end) | 0.826 | [0.808, 0.843] |
| Relation macro-F1 (14 labels) | 0.649 | |
| Quantity attachment accuracy (3183) | 0.865 | [0.837, 0.888] |
| Complete-step exact match (2523) | 0.468 | [0.432, 0.505] |

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
| Measure | 0.908 | 0.889 | 0.899 | 1510 |
| Setting | 0.851 | 0.839 | 0.845 | 1482 |
| Mod-Link | 0.914 | 0.837 | 0.874 | 1389 |
| Site | 0.814 | 0.839 | 0.826 | 1073 |
| Using | 0.803 | 0.646 | 0.716 | 731 |
| Meronym | 0.628 | 0.484 | 0.546 | 366 |
| Or | 0.700 | 0.503 | 0.585 | 181 |
| Coreference-Link | 0.657 | 0.387 | 0.487 | 124 |
| Measure-Type-Link | 0.802 | 0.815 | 0.808 | 119 |
| Product | 0.350 | 0.208 | 0.261 | 101 |
| Count | 0.806 | 0.798 | 0.802 | 99 |
| Commands | 0.130 | 0.081 | 0.100 | 37 |
| Of-Type | 0.625 | 0.385 | 0.476 | 26 |
