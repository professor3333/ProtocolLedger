# scibert-no-structure-s13: dev results (best epoch 4)

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.803 | [0.783, 0.825] |
| Entity macro-F1 (18 labels) | 0.753 | |
| Relation micro-F1 (end-to-end) | 0.635 | [0.610, 0.660] |
| Relation macro-F1 (14 labels) | 0.436 | |
| Quantity attachment accuracy (3183) | 0.750 | [0.717, 0.780] |
| Complete-step exact match (2538) | 0.239 | [0.203, 0.283] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.884 | 0.918 | 0.901 | 3812 |
| Reagent | 0.820 | 0.832 | 0.826 | 3432 |
| Modifier | 0.608 | 0.606 | 0.607 | 1478 |
| Location | 0.753 | 0.753 | 0.753 | 1352 |
| Amount | 0.922 | 0.860 | 0.890 | 1044 |
| Time | 0.906 | 0.926 | 0.916 | 687 |
| Device | 0.683 | 0.695 | 0.689 | 574 |
| Method | 0.570 | 0.502 | 0.534 | 506 |
| Temperature | 0.947 | 0.951 | 0.949 | 452 |
| Concentration | 0.779 | 0.854 | 0.815 | 397 |
| Measure-Type | 0.533 | 0.605 | 0.567 | 309 |
| Numerical | 0.665 | 0.625 | 0.645 | 251 |
| Speed | 0.980 | 0.942 | 0.961 | 208 |
| Generic-Measure | 0.391 | 0.331 | 0.358 | 124 |
| Size | 0.796 | 0.639 | 0.709 | 122 |
| Seal | 0.817 | 0.798 | 0.807 | 84 |
| Mention | 0.724 | 0.733 | 0.729 | 75 |
| pH | 0.897 | 0.897 | 0.897 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.728 | 0.709 | 0.718 | 2827 |
| Measure | 0.696 | 0.715 | 0.706 | 1510 |
| Setting | 0.809 | 0.748 | 0.777 | 1482 |
| Mod-Link | 0.526 | 0.500 | 0.513 | 1389 |
| Site | 0.696 | 0.557 | 0.619 | 1073 |
| Using | 0.526 | 0.471 | 0.497 | 731 |
| Meronym | 0.396 | 0.361 | 0.378 | 366 |
| Or | 0.528 | 0.309 | 0.390 | 181 |
| Coreference-Link | 0.453 | 0.194 | 0.271 | 124 |
| Measure-Type-Link | 0.388 | 0.437 | 0.411 | 119 |
| Product | 0.241 | 0.129 | 0.168 | 101 |
| Count | 0.478 | 0.444 | 0.461 | 99 |
| Commands | 0.054 | 0.054 | 0.054 | 37 |
| Of-Type | 0.188 | 0.115 | 0.143 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.996 | [0.992, 0.998] |
| Entity macro-F1 (18 labels) | 0.997 | |
| Relation micro-F1 (end-to-end) | 0.788 | [0.771, 0.803] |
| Relation macro-F1 (14 labels) | 0.593 | |
| Quantity attachment accuracy (3183) | 0.842 | [0.816, 0.865] |
| Complete-step exact match (2523) | 0.395 | [0.362, 0.434] |

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
| Acts-on | 0.889 | 0.827 | 0.857 | 2827 |
| Measure | 0.881 | 0.870 | 0.875 | 1510 |
| Setting | 0.888 | 0.798 | 0.841 | 1482 |
| Mod-Link | 0.846 | 0.716 | 0.775 | 1389 |
| Site | 0.874 | 0.664 | 0.754 | 1073 |
| Using | 0.706 | 0.591 | 0.643 | 731 |
| Meronym | 0.612 | 0.478 | 0.537 | 366 |
| Or | 0.675 | 0.470 | 0.554 | 181 |
| Coreference-Link | 0.604 | 0.234 | 0.337 | 124 |
| Measure-Type-Link | 0.740 | 0.622 | 0.676 | 119 |
| Product | 0.277 | 0.129 | 0.176 | 101 |
| Count | 0.841 | 0.748 | 0.791 | 99 |
| Commands | 0.054 | 0.054 | 0.054 | 37 |
| Of-Type | 0.562 | 0.346 | 0.429 | 26 |
