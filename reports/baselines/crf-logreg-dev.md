# CRF + logistic regression baseline: dev results

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.756 | [0.733, 0.779] |
| Entity macro-F1 (18 labels) | 0.700 | |
| Relation micro-F1 (end-to-end) | 0.582 | [0.553, 0.611] |
| Relation macro-F1 (14 labels) | 0.375 | |
| Quantity attachment accuracy (3183) | 0.708 | [0.674, 0.739] |
| Complete-step exact match (2539) | 0.231 | [0.198, 0.272] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.869 | 0.871 | 0.870 | 3812 |
| Reagent | 0.747 | 0.783 | 0.765 | 3432 |
| Modifier | 0.587 | 0.486 | 0.532 | 1478 |
| Location | 0.716 | 0.669 | 0.692 | 1352 |
| Amount | 0.874 | 0.853 | 0.863 | 1044 |
| Time | 0.923 | 0.905 | 0.914 | 687 |
| Device | 0.593 | 0.565 | 0.579 | 574 |
| Method | 0.487 | 0.441 | 0.463 | 506 |
| Temperature | 0.938 | 0.943 | 0.940 | 452 |
| Concentration | 0.774 | 0.783 | 0.778 | 397 |
| Measure-Type | 0.525 | 0.443 | 0.481 | 309 |
| Numerical | 0.622 | 0.550 | 0.584 | 251 |
| Speed | 0.945 | 0.909 | 0.926 | 208 |
| Generic-Measure | 0.351 | 0.323 | 0.336 | 124 |
| Size | 0.774 | 0.590 | 0.670 | 122 |
| Seal | 0.727 | 0.667 | 0.696 | 84 |
| Mention | 0.712 | 0.560 | 0.627 | 75 |
| pH | 0.893 | 0.862 | 0.877 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.662 | 0.630 | 0.645 | 2827 |
| Measure | 0.673 | 0.664 | 0.668 | 1510 |
| Setting | 0.795 | 0.714 | 0.752 | 1482 |
| Mod-Link | 0.516 | 0.404 | 0.453 | 1389 |
| Site | 0.564 | 0.550 | 0.557 | 1073 |
| Using | 0.440 | 0.362 | 0.397 | 731 |
| Meronym | 0.508 | 0.172 | 0.257 | 366 |
| Or | 0.516 | 0.265 | 0.350 | 181 |
| Coreference-Link | 0.568 | 0.202 | 0.298 | 124 |
| Measure-Type-Link | 0.365 | 0.353 | 0.359 | 119 |
| Product | 0.188 | 0.059 | 0.090 | 101 |
| Count | 0.413 | 0.434 | 0.424 | 99 |
| Commands | 0.000 | 0.000 | 0.000 | 37 |
| Of-Type | 0.000 | 0.000 | 0.000 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 1.000 | [1.000, 1.000] |
| Entity macro-F1 (18 labels) | 1.000 | |
| Relation micro-F1 (end-to-end) | 0.812 | [0.795, 0.829] |
| Relation macro-F1 (14 labels) | 0.593 | |
| Quantity attachment accuracy (3183) | 0.867 | [0.844, 0.888] |
| Complete-step exact match (2523) | 0.451 | [0.414, 0.486] |

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
| Acts-on | 0.870 | 0.845 | 0.858 | 2827 |
| Measure | 0.895 | 0.911 | 0.903 | 1510 |
| Setting | 0.899 | 0.824 | 0.860 | 1482 |
| Mod-Link | 0.859 | 0.765 | 0.810 | 1389 |
| Site | 0.800 | 0.795 | 0.798 | 1073 |
| Using | 0.784 | 0.654 | 0.713 | 731 |
| Meronym | 0.750 | 0.279 | 0.406 | 366 |
| Or | 0.748 | 0.525 | 0.617 | 181 |
| Coreference-Link | 0.717 | 0.266 | 0.388 | 124 |
| Measure-Type-Link | 0.829 | 0.815 | 0.822 | 119 |
| Product | 0.258 | 0.079 | 0.121 | 101 |
| Count | 0.709 | 0.737 | 0.723 | 99 |
| Commands | 0.000 | 0.000 | 0.000 | 37 |
| Of-Type | 0.556 | 0.192 | 0.286 | 26 |
