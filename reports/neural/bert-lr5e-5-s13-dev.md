# bert-lr5e-5-s13: dev results (best epoch 2)

### End-to-end

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.795 | [0.774, 0.817] |
| Entity macro-F1 (18 labels) | 0.738 | |
| Relation micro-F1 (end-to-end) | 0.626 | [0.603, 0.649] |
| Relation macro-F1 (14 labels) | 0.411 | |
| Quantity attachment accuracy (3183) | 0.754 | [0.723, 0.782] |
| Complete-step exact match (2541) | 0.228 | [0.195, 0.267] |

| Entity label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Action | 0.893 | 0.902 | 0.897 | 3812 |
| Reagent | 0.790 | 0.830 | 0.810 | 3432 |
| Modifier | 0.596 | 0.607 | 0.602 | 1478 |
| Location | 0.761 | 0.754 | 0.757 | 1352 |
| Amount | 0.889 | 0.867 | 0.878 | 1044 |
| Time | 0.912 | 0.923 | 0.917 | 687 |
| Device | 0.663 | 0.697 | 0.680 | 574 |
| Method | 0.587 | 0.502 | 0.541 | 506 |
| Temperature | 0.964 | 0.943 | 0.953 | 452 |
| Concentration | 0.779 | 0.854 | 0.815 | 397 |
| Measure-Type | 0.520 | 0.586 | 0.551 | 309 |
| Numerical | 0.629 | 0.641 | 0.635 | 251 |
| Speed | 0.935 | 0.899 | 0.917 | 208 |
| Generic-Measure | 0.403 | 0.218 | 0.283 | 124 |
| Size | 0.700 | 0.631 | 0.664 | 122 |
| Seal | 0.813 | 0.726 | 0.767 | 84 |
| Mention | 0.700 | 0.747 | 0.723 | 75 |
| pH | 0.897 | 0.897 | 0.897 | 29 |

| Relation label | P | R | F1 | Support |
|---|---:|---:|---:|---:|
| Acts-on | 0.684 | 0.719 | 0.701 | 2827 |
| Measure | 0.686 | 0.709 | 0.698 | 1510 |
| Setting | 0.756 | 0.744 | 0.750 | 1482 |
| Mod-Link | 0.544 | 0.510 | 0.527 | 1389 |
| Site | 0.558 | 0.698 | 0.620 | 1073 |
| Using | 0.479 | 0.491 | 0.485 | 731 |
| Meronym | 0.409 | 0.191 | 0.261 | 366 |
| Or | 0.576 | 0.293 | 0.388 | 181 |
| Coreference-Link | 0.569 | 0.266 | 0.363 | 124 |
| Measure-Type-Link | 0.371 | 0.471 | 0.415 | 119 |
| Product | 0.158 | 0.030 | 0.050 | 101 |
| Count | 0.461 | 0.475 | 0.468 | 99 |
| Commands | 0.038 | 0.027 | 0.032 | 37 |
| Of-Type | 0.000 | 0.000 | 0.000 | 26 |

### Relations given gold entities

112 documents; 95% CIs from a document-level bootstrap.

| Metric | Value | 95% CI |
|---|---:|---|
| Entity micro-F1 (strict) | 0.996 | [0.992, 0.998] |
| Entity macro-F1 (18 labels) | 0.997 | |
| Relation micro-F1 (end-to-end) | 0.812 | [0.794, 0.827] |
| Relation macro-F1 (14 labels) | 0.603 | |
| Quantity attachment accuracy (3183) | 0.854 | [0.830, 0.877] |
| Complete-step exact match (2523) | 0.432 | [0.395, 0.467] |

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
| Acts-on | 0.868 | 0.858 | 0.863 | 2827 |
| Measure | 0.898 | 0.882 | 0.890 | 1510 |
| Setting | 0.835 | 0.823 | 0.829 | 1482 |
| Mod-Link | 0.901 | 0.783 | 0.837 | 1389 |
| Site | 0.741 | 0.890 | 0.809 | 1073 |
| Using | 0.717 | 0.722 | 0.720 | 731 |
| Meronym | 0.784 | 0.268 | 0.399 | 366 |
| Or | 0.692 | 0.409 | 0.514 | 181 |
| Coreference-Link | 0.679 | 0.290 | 0.407 | 124 |
| Measure-Type-Link | 0.842 | 0.807 | 0.824 | 119 |
| Product | 0.227 | 0.050 | 0.081 | 101 |
| Count | 0.849 | 0.737 | 0.789 | 99 |
| Commands | 0.333 | 0.027 | 0.050 | 37 |
| Of-Type | 0.727 | 0.308 | 0.432 | 26 |
