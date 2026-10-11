# scibert-frozen-s13: dev results (best epoch 9)

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.695 | [0.675, 0.716] |
| Entity macro-F1 (18 labels) | 0.639 | |
| Relation micro-F1 (end-to-end) | 0.487 | [0.462, 0.509] |
| Relation macro-F1 (14 labels) | 0.317 | |
| Quantity attachment accuracy (3183) | 0.544 | [0.510, 0.570] |
| Complete-step exact match (2534) | 0.113 | [0.094, 0.132] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.829 | 0.859 | 0.844 | 3812 |
| Reagent | 0.695 | 0.599 | 0.643 | 3432 |
| Modifier | 0.528 | 0.432 | 0.475 | 1478 |
| Location | 0.674 | 0.573 | 0.619 | 1352 |
| Amount | 0.823 | 0.787 | 0.805 | 1044 |
| Time | 0.903 | 0.852 | 0.876 | 687 |
| Device | 0.604 | 0.399 | 0.481 | 574 |
| Method | 0.530 | 0.292 | 0.377 | 506 |
| Temperature | 0.942 | 0.863 | 0.901 | 452 |
| Concentration | 0.712 | 0.698 | 0.705 | 397 |
| Measure-Type | 0.536 | 0.456 | 0.493 | 309 |
| Numerical | 0.630 | 0.406 | 0.494 | 251 |
| Speed | 0.927 | 0.851 | 0.887 | 208 |
| Generic-Measure | 0.433 | 0.105 | 0.169 | 124 |
| Size | 0.585 | 0.393 | 0.471 | 122 |
| Seal | 0.743 | 0.655 | 0.696 | 84 |
| Mention | 0.740 | 0.720 | 0.730 | 75 |
| pH | 0.857 | 0.828 | 0.842 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.619 | 0.498 | 0.551 | 2827 |
| Measure | 0.544 | 0.434 | 0.483 | 1510 |
| Setting | 0.707 | 0.648 | 0.676 | 1482 |
| Mod-Link | 0.488 | 0.318 | 0.385 | 1389 |
| Site | 0.524 | 0.482 | 0.502 | 1073 |
| Using | 0.413 | 0.201 | 0.271 | 731 |
| Meronym | 0.296 | 0.139 | 0.190 | 366 |
| Or | 0.438 | 0.155 | 0.229 | 181 |
| Coreference-Link | 0.558 | 0.234 | 0.330 | 124 |
| Measure-Type-Link | 0.347 | 0.286 | 0.313 | 119 |
| Product | 0.206 | 0.069 | 0.104 | 101 |
| Count | 0.440 | 0.333 | 0.379 | 99 |
| Commands | 0.021 | 0.027 | 0.024 | 37 |
| Of-Type | 0.000 | 0.000 | 0.000 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.996 | [0.992, 0.998] |
| Entity macro-F1 (18 labels) | 0.997 | |
| Relation micro-F1 (end-to-end) | 0.809 | [0.792, 0.825] |
| Relation macro-F1 (14 labels) | 0.620 | |
| Quantity attachment accuracy (3183) | 0.851 | [0.826, 0.875] |
| Complete-step exact match (2523) | 0.424 | [0.386, 0.461] |

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
| Acts-on | 0.892 | 0.831 | 0.860 | 2827 |
| Measure | 0.894 | 0.893 | 0.894 | 1510 |
| Setting | 0.847 | 0.819 | 0.833 | 1482 |
| Mod-Link | 0.906 | 0.808 | 0.854 | 1389 |
| Site | 0.767 | 0.804 | 0.785 | 1073 |
| Using | 0.767 | 0.586 | 0.664 | 731 |
| Meronym | 0.641 | 0.385 | 0.481 | 366 |
| Or | 0.714 | 0.442 | 0.546 | 181 |
| Coreference-Link | 0.709 | 0.315 | 0.436 | 124 |
| Measure-Type-Link | 0.814 | 0.773 | 0.793 | 119 |
| Product | 0.375 | 0.178 | 0.242 | 101 |
| Count | 0.809 | 0.727 | 0.766 | 99 |
| Commands | 0.071 | 0.027 | 0.039 | 37 |
| Of-Type | 0.667 | 0.385 | 0.488 | 26 |
