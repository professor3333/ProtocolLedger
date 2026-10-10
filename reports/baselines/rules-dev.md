# Rule-based baseline: dev results

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.692 | [0.666, 0.715] |
| Entity macro-F1 (18 labels) | 0.647 | |
| Relation micro-F1 (end-to-end) | 0.355 | [0.322, 0.386] |
| Relation macro-F1 (14 labels) | 0.177 | |
| Quantity attachment accuracy (3183) | 0.521 | [0.475, 0.561] |
| Complete-step exact match (2538) | 0.112 | [0.091, 0.140] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.798 | 0.840 | 0.818 | 3812 |
| Reagent | 0.658 | 0.597 | 0.626 | 3432 |
| Modifier | 0.528 | 0.521 | 0.524 | 1478 |
| Location | 0.631 | 0.560 | 0.594 | 1352 |
| Amount | 0.864 | 0.864 | 0.864 | 1044 |
| Time | 0.921 | 0.901 | 0.911 | 687 |
| Device | 0.513 | 0.425 | 0.465 | 574 |
| Method | 0.471 | 0.344 | 0.398 | 506 |
| Temperature | 0.942 | 0.927 | 0.934 | 452 |
| Concentration | 0.752 | 0.809 | 0.779 | 397 |
| Measure-Type | 0.555 | 0.508 | 0.530 | 309 |
| Numerical | 0.503 | 0.343 | 0.408 | 251 |
| Speed | 0.916 | 0.731 | 0.813 | 208 |
| Generic-Measure | 0.279 | 0.137 | 0.184 | 124 |
| Size | 0.694 | 0.484 | 0.570 | 122 |
| Seal | 0.753 | 0.726 | 0.739 | 84 |
| Mention | 0.593 | 0.720 | 0.651 | 75 |
| pH | 0.857 | 0.828 | 0.842 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.359 | 0.376 | 0.367 | 2827 |
| Measure | 0.436 | 0.457 | 0.446 | 1510 |
| Setting | 0.696 | 0.603 | 0.646 | 1482 |
| Mod-Link | 0.294 | 0.303 | 0.298 | 1389 |
| Site | 0.217 | 0.228 | 0.223 | 1073 |
| Using | 0.088 | 0.052 | 0.065 | 731 |
| Meronym | 0.000 | 0.000 | 0.000 | 366 |
| Or | 0.000 | 0.000 | 0.000 | 181 |
| Coreference-Link | 0.000 | 0.000 | 0.000 | 124 |
| Measure-Type-Link | 0.190 | 0.387 | 0.255 | 119 |
| Product | 0.000 | 0.000 | 0.000 | 101 |
| Count | 0.214 | 0.151 | 0.177 | 99 |
| Commands | 0.000 | 0.000 | 0.000 | 37 |
| Of-Type | 0.000 | 0.000 | 0.000 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 1.000 | [1.000, 1.000] |
| Entity macro-F1 (18 labels) | 1.000 | |
| Relation micro-F1 (end-to-end) | 0.604 | [0.577, 0.633] |
| Relation macro-F1 (14 labels) | 0.345 | |
| Quantity attachment accuracy (3183) | 0.789 | [0.759, 0.816] |
| Complete-step exact match (2523) | 0.268 | [0.235, 0.302] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 1.000 | 1.000 | 1.000 | 3812 |
| Reagent | 1.000 | 1.000 | 1.000 | 3432 |
| Modifier | 1.000 | 1.000 | 1.000 | 1478 |
| Location | 1.000 | 1.000 | 1.000 | 1352 |
| Amount | 1.000 | 1.000 | 1.000 | 1044 |
| Time | 1.000 | 1.000 | 1.000 | 687 |
| Device | 1.000 | 1.000 | 1.000 | 574 |
| Method | 1.000 | 1.000 | 1.000 | 506 |
| Temperature | 1.000 | 1.000 | 1.000 | 452 |
| Concentration | 1.000 | 1.000 | 1.000 | 397 |
| Measure-Type | 1.000 | 1.000 | 1.000 | 309 |
| Numerical | 1.000 | 1.000 | 1.000 | 251 |
| Speed | 1.000 | 1.000 | 1.000 | 208 |
| Generic-Measure | 1.000 | 1.000 | 1.000 | 124 |
| Size | 1.000 | 1.000 | 1.000 | 122 |
| Seal | 1.000 | 1.000 | 1.000 | 84 |
| Mention | 1.000 | 1.000 | 1.000 | 75 |
| pH | 1.000 | 1.000 | 1.000 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.565 | 0.655 | 0.607 | 2827 |
| Measure | 0.756 | 0.868 | 0.808 | 1510 |
| Setting | 0.794 | 0.762 | 0.777 | 1482 |
| Mod-Link | 0.665 | 0.702 | 0.683 | 1389 |
| Site | 0.409 | 0.499 | 0.450 | 1073 |
| Using | 0.252 | 0.189 | 0.216 | 731 |
| Meronym | 0.000 | 0.000 | 0.000 | 366 |
| Or | 0.000 | 0.000 | 0.000 | 181 |
| Coreference-Link | 0.000 | 0.000 | 0.000 | 124 |
| Measure-Type-Link | 0.449 | 0.916 | 0.602 | 119 |
| Product | 0.000 | 0.000 | 0.000 | 101 |
| Count | 0.441 | 0.414 | 0.427 | 99 |
| Commands | 0.000 | 0.000 | 0.000 | 37 |
| Of-Type | 0.286 | 0.231 | 0.255 | 26 |
