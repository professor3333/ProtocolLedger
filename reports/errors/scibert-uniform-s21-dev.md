# Error analysis: scibert-uniform-s21 (dev)

## Entities (14936 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 11972 | 80.2% |
| wrong type | 719 | 4.8% |
| wrong boundary | 893 | 6.0% |
| wrong boundary and type | 603 | 4.0% |
| missed | 749 | 5.0% |

## Relations (10065 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 6308 | 62.7% |
| endpoint error | 2789 | 27.7% |
| wrong label | 183 | 1.8% |
| wrong direction | 11 | 0.1% |
| wrong attachment | 288 | 2.9% |
| missed | 486 | 4.8% |

Spurious entities (no overlapping gold): Modifier 241, Action 212, Reagent 61, Method 38, Measure-Type 37, Mention 24, Location 21, Device 15

Spurious relations: 868 between gold entities, 2505 with a spurious endpoint.

## Slices

| Reagent names | Gold | Recall |
|---|---:|---:|
| seen in training | 2419 | 0.903 |
| unseen in training | 1013 | 0.658 |

| Documents | Gold relations | Relation recall |
|---|---:|---:|
| without | 8973 | 0.613 |
| with template sibling | 1092 | 0.740 |

## Examples

### entity/wrong_boundary

- dev_data/protocol_0: gold Reagent 'E. coli LB culture*', predicted Reagent 'E. coli LB culture' | tocol: High-copy plasmid DNA from E. coli Start with 1-5 ml [[E. coli LB culture]][[E. coli LB culture*]], pellet cells in a microcentrifuge for 30 sec at 11,000 x g
- dev_data/protocol_0: gold Reagent 'PB3 Neutralization Buffe', predicted Reagent 'PB3 Neutralization Buffer' | e for up to 5 min or until lysate appears clear. Add 300 µl [[PB3 Neutralization Buffe]][[PB3 Neutralization Buffer]]. Invert the tube 6-8 times to mix completely. Do not vortex
- dev_data/protocol_0: gold Modifier 'maximum', predicted Modifier 'maximum of' | asmid Binding Column in a Collection Tube (2 ml) and load a [[maximum]][[maximum of]] 750 µl of the supernatant (from the "Lysate Clarification"
- dev_data/protocol_0: gold Method 'Clarification', predicted Method 'Lysate Clarification' | and load a maximum of 750 µl of the supernatant (from the "[[Lysate Clarification]][[Clarification]]" section above) onto the column. Centrifuge for 1 min at 11
- dev_data/protocol_0: gold Reagent 'strains', predicted Reagent 'host strains' | nding Column into the Collection Tube (2 ml). Optional: For [[host strains]][[strains]] containing high levels of nucleases (e.g. HB101 or strains
- dev_data/protocol_1: gold Reagent 'protists', predicted Reagent 'unicellular protists' | Super simple In vivo Hoechst staining of [[unicellular protists]][[protists]] Add 1/1000 Hoechst dye (1 uL into 1 mL volume of cells).Kee
- dev_data/protocol_1: gold Modifier 'fresh growing', predicted Modifier 'fresh', Reagent 'growing medium' | ht. Centrifuge cells at 1000g for 5 minutes. Resuspend with [[fresh]][[fresh growing]][[growing medium]]. Use minimum volume of medium in order to plate in to the s
- dev_data/protocol_1: gold Reagent 'medium', predicted Reagent 'growing medium' | ntrifuge cells at 1000g for 5 minutes. Resuspend with fresh [[growing medium]][[medium]]. Use minimum volume of medium in order to plate in to the s

### entity/wrong_type

- dev_data/protocol_0: gold Mention 'liquid', predicted Reagent 'liquid' | ,000 x g. Discard the supernatant and remove as much of the [[liquid]][[liquid]] as possible. Add 250 µl PB1 Resuspension Buffer. Vortex or
- dev_data/protocol_0: gold Size '1.5 ml', predicted Amount '1.5 ml' | ube (2 ml). Place the SpinSmart Plasmid Binding Column in a [[1.5 ml]][[1.5 ml]] microcentrifuge tube (not provided) and add 50 µl PB6 Eluti
- dev_data/protocol_1: gold Action 'In vivo Hoechst staining', predicted Method 'In vivo Hoechst staining' | Super simple [[In vivo Hoechst staining]][[In vivo Hoechst staining]] of unicellular protists Add 1/1000 Hoechst dye (1 uL into 1
- dev_data/protocol_1: gold Concentration '1/1000', predicted Amount '1/1000' | simple In vivo Hoechst staining of unicellular protists Add [[1/1000]][[1/1000]] Hoechst dye (1 uL into 1 mL volume of cells).Keep cells wit
- dev_data/protocol_7: gold Reagent 'transformation', predicted Method 'transformation' | mL of fresh LB+antibiotic, 1:50 dilution, for each planned [[transformation]][[transformation]].Grow to an OD600 of 0.8 - 1.0 (37°C with 270 rpm shaking).T
- dev_data/protocol_7: gold Amount '2.5E8', predicted Numerical '2.5E8' | ytometer to calculate the required volume needed to collect [[2.5E8]][[2.5E8]] cells for each transformation. For each transformation, cen
- dev_data/protocol_7: gold Reagent 'transformation', predicted Method 'transformation' | the required volume needed to collect 2.5E8 cells for each [[transformation]][[transformation]]. For each transformation, centrifuge 50 mL of E. coli cultu
- dev_data/protocol_7: gold Reagent 'transformation', predicted Method 'transformation' | ed to collect 2.5E8 cells for each transformation. For each [[transformation]][[transformation]], centrifuge 50 mL of E. coli culture and the required Phaeo

### entity/missed

- dev_data/protocol_0: gold Modifier 'completely clear', predicted nothing | in at 11,000 x g at room temperature. If precipitate is not [[completely clear]] from the lysate, centrifuge again for 5 min at 11,000 x g a
- dev_data/protocol_0: gold Reagent 'JM series', predicted nothing | ning high levels of nucleases (e.g. HB101 or strains of the [[JM series]]), perform a wash step with 500 µl PB4 Wash Buffer pre-warme
- dev_data/protocol_1: gold Measure-Type 'volume', predicted nothing | unicellular protists Add 1/1000 Hoechst dye (1 uL into 1 mL [[volume]] of cells).Keep cells with dye protected from light. Incubat
- dev_data/protocol_1: gold Action 'protected', predicted nothing | st dye (1 uL into 1 mL volume of cells).Keep cells with dye [[protected]] from light. Incubate at room temperature for 10 minutes.Kee
- dev_data/protocol_1: gold Action 'protected', predicted nothing | bate at room temperature for 10 minutes.Keep cells with dye [[protected]] from light. Centrifuge cells at 1000g for 5 minutes. Resusp
- dev_data/protocol_1: gold Method 'observation', predicted nothing | in to the slide immediately. Mount your slide and ready for [[observation]] under microscope.
- dev_data/protocol_7: gold Reagent 'mid-log phase', predicted nothing | ation via Bacterial Conjugation) Grow the diatom culture to [[mid-log phase]] (≈ 8.0E6 cells/ml for Phaeodactylum tricornutum grown on F/
- dev_data/protocol_7: gold Modifier 'throughout the growth curve', predicted nothing | n on BG-11). We have investigated transformation efficiency [[throughout the growth curve]] and found this to be the sweetspot. Grow 1 mL of E. coli cu

### entity/wrong_boundary_and_type

- dev_data/protocol_0: gold Reagent 'Lysate', predicted Method 'Lysate Clarification' | and load a maximum of 750 µl of the supernatant (from the "[[Lysate]][[Lysate Clarification]]" section above) onto the column. Centrifuge for 1 min at 11
- dev_data/protocol_0: gold Method 'wash step', predicted Action 'wash' | cleases (e.g. HB101 or strains of the JM series), perform a [[wash]][[wash step]] with 500 µl PB4 Wash Buffer pre-warmed to 50°C. Centrifuge
- dev_data/protocol_1: gold Modifier 'unicellular', predicted Reagent 'unicellular protists' | Super simple In vivo Hoechst staining of [[unicellular]][[unicellular protists]] Add 1/1000 Hoechst dye (1 uL into 1 mL volume of cells).Kee
- dev_data/protocol_7: gold Method 'Full Contact Microbiology', predicted Modifier 'Full Contact' | [[Full Contact]][[Full Contact Microbiology]] (a.k.a Diatom Transformation via Bacterial Conjugation) Gro
- dev_data/protocol_7: gold Time 'On the day of transformation', predicted Method 'transformation' | (We grow them at 37°C at 270 rpm in a shaking incubator.). [[On the day of transformation]][[transformation]], use the overnight culture to inoculate 50 mL of fresh LB+a
- dev_data/protocol_7: gold Generic-Measure '1:50 dilution', predicted Concentration '1:50', Method 'dilution' | vernight culture to inoculate 50 mL of fresh LB+antibiotic, [[1:50]][[1:50 dilution]][[dilution]], for each planned transformation.Grow to an OD600 of 0.8 -
- dev_data/protocol_7: gold Generic-Measure 'OD600 of 0.8 - 1.0', predicted Measure-Type 'OD600', Numerical '0.8 - 1.0' | , 1:50 dilution, for each planned transformation.Grow to an [[OD600]][[OD600 of 0.8 - 1.0]][[0.8 - 1.0]] (37°C with 270 rpm shaking).This takes about 3-4 hours. Dur
- dev_data/protocol_7: gold Amount 'required volume', predicted Measure-Type 'volume' | entration with a FlowCam or haemocytometer to calculate the [[required volume]][[volume]] needed to collect 2.5E8 cells for each transformation. For

### relation/missed

- dev_data/protocol_0: gold Add -Setting-> 250 µl; predicted Add -Acts-on-> PB1 Resuspension Buffer; PB1 Resuspension Buffer -Measure-> 250 µl | e supernatant and remove as much of the liquid as possible. [[Add]] [[250 µl]] PB1 Resuspension Buffer. Vortex or pipet up and down to res
- dev_data/protocol_0: gold Vortex -Commands-> resuspend; predicted Vortex -Or-> pipet; resuspend -Acts-on-> cell pellet; resuspend -Mod-Link-> completely | the liquid as possible. Add 250 µl PB1 Resuspension Buffer. [[Vortex]] or pipet up and down to [[resuspend]] the cell pellet completely. No cell clumps should be visibl
- dev_data/protocol_0: gold pipet -Commands-> resuspend; predicted Vortex -Or-> pipet; pipet -Using-> up and down; resuspend -Acts-on-> cell pellet; resuspend -Mod-Link-> completely | as possible. Add 250 µl PB1 Resuspension Buffer. Vortex or [[pipet]] up and down to [[resuspend]] the cell pellet completely. No cell clumps should be visibl
- dev_data/protocol_0: gold Add -Setting-> 250 µl; predicted Add -Acts-on-> PB2 Lysis Buffer; PB2 Lysis Buffer -Measure-> 250 µl | e cell pellet completely. No cell clumps should be visible. [[Add]] [[250 µl]] PB2 Lysis Buffer. Invert the tube 6-8 times to mix complete
- dev_data/protocol_0: gold Invert -Commands-> mix; predicted Invert -Acts-on-> tube; Invert -Count-> 6-8; mix -Mod-Link-> completely | cell clumps should be visible. Add 250 µl PB2 Lysis Buffer. [[Invert]] the tube 6-8 times to [[mix]] completely. Do not vortex!. Incubate at room temperature fo
- dev_data/protocol_0: gold Add -Setting-> 300 µl; predicted Add -Acts-on-> PB3 Neutralization Buffer; PB3 Neutralization Buffer -Measure-> 300 µl | temperature for up to 5 min or until lysate appears clear. [[Add]] [[300 µl]] PB3 Neutralization Buffer. Invert the tube 6-8 times to mix
- dev_data/protocol_0: gold Invert -Commands-> mix; predicted Invert -Acts-on-> tube; Invert -Count-> 6-8; mix -Mod-Link-> completely | lysate appears clear. Add 300 µl PB3 Neutralization Buffer. [[Invert]] the tube 6-8 times to [[mix]] completely. Do not vortex!. Centrifuge for 5 min at 11,000
- dev_data/protocol_0: gold centrifuge -Coreference-Link-> precipitate; predicted centrifuge -Mod-Link-> again; centrifuge -Setting-> 5 min; centrifuge -Setting-> 11,000 x g; centrifuge -Setting-> room temperature | Centrifuge for 5 min at 11,000 x g at room temperature. If [[precipitate]] is not completely clear from the lysate, [[centrifuge]] again for 5 min at 11,000 x g at room temperature. Place a

### relation/wrong_attachment

- dev_data/protocol_0: gold Vortex -Acts-on-> cell pellet; predicted Vortex -Or-> pipet; resuspend -Acts-on-> cell pellet | the liquid as possible. Add 250 µl PB1 Resuspension Buffer. [[Vortex]] or pipet up and down to resuspend the [[cell pellet]] completely. No cell clumps should be visible. Add 250 µl PB
- dev_data/protocol_0: gold pipet -Acts-on-> cell pellet; predicted Vortex -Or-> pipet; pipet -Using-> up and down; resuspend -Acts-on-> cell pellet | as possible. Add 250 µl PB1 Resuspension Buffer. Vortex or [[pipet]] up and down to resuspend the [[cell pellet]] completely. No cell clumps should be visible. Add 250 µl PB
- dev_data/protocol_7: gold light incubator -Setting-> 18°C; predicted Move -Setting-> 18°C; Move -Site-> light incubator | e plates for 90 minutes at 30°C in the dark. Move plates to [[light incubator]] ([[18°C]] and 100 μmol photons m-2 s-1) for 2 days. Collect cells by
- dev_data/protocol_7: gold light incubator -Setting-> 100 μmol photons m-2 s-1; predicted Move -Setting-> 100 μmol photons m-2 s-1; Move -Site-> light incubator | e plates for 90 minutes at 30°C in the dark. Move plates to [[light incubator]] (18°C and [[100 μmol photons m-2 s-1]]) for 2 days. Collect cells by adding 1 mL of L1 medium. Use
- dev_data/protocol_10: gold adding -Acts-on-> TE; predicted adding -Acts-on-> Tris-HCl; TE -Measure-> 0.1X | d with the lid open. Elute the DNA target from the beads by [[adding]] 30 μl of 10 mM Tris-HCl, pH 8.0 or 0.1X [[TE]].Note: Be sure not to transfer any beads. Trace amounts of b
- dev_data/protocol_10: gold TE -Measure-> pH 8.0; predicted Tris-HCl -Measure-> pH 8.0; TE -Measure-> 0.1X | NA target from the beads by adding 30 μl of 10 mM Tris-HCl, [[pH 8.0]] or 0.1X [[TE]].Note: Be sure not to transfer any beads. Trace amounts of b
- dev_data/protocol_11: gold Digest -Acts-on-> DNA; predicted Digest -Acts-on-> plasmid DNA; Digest -Acts-on-> H2O; Digest -Site-> reaction; DNA -Measure-> 1 μl | horylation using CIP in Restriction Enzyme Reaction (M0290) [[Digest]] 1–5 μg of plasmid DNA in a 20 μl reaction as follows: [[DNA]] ≥ 1 μl; Restriction Enzyme Buffer (10X) 2 μl; Restriction
- dev_data/protocol_11: gold Digest -Acts-on-> Restriction Enzyme Buffer; predicted Digest -Acts-on-> plasmid DNA; Digest -Acts-on-> H2O; Digest -Site-> reaction; Restriction Enzyme Buffer -Measure-> 10X; Restriction Enzyme Buffer -Measure-> 2 μl | horylation using CIP in Restriction Enzyme Reaction (M0290) [[Digest]] 1–5 μg of plasmid DNA in a 20 μl reaction as follows: DNA ≥ 1 μl; [[Restriction Enzyme Buffer]] (10X) 2 μl; Restriction Endonuclease 1 μl; H2O, purifie

### relation/wrong_label

- dev_data/protocol_0: gold perform -Acts-on-> PB4 Wash Buffer; predicted perform -Using-> PB4 Wash Buffer; PB4 Wash Buffer -Measure-> 500 µl; pre-warmed -Acts-on-> PB4 Wash Buffer | vels of nucleases (e.g. HB101 or strains of the JM series), [[perform]] a wash step with 500 µl [[PB4 Wash Buffer]] pre-warmed to 50°C. Centrifuge for 1 min at 11,000 x g befo
- dev_data/protocol_0: gold proceeding -Acts-on-> Buffer PB5; predicted proceeding -Using-> Buffer PB5 | e-warmed to 50°C. Centrifuge for 1 min at 11,000 x g before [[proceeding]] with [[Buffer PB5]]. Add 600 µl PB5 Wash Buffer (make sure EtOH has been added)
- dev_data/protocol_7: gold grown -Site-> F/2 media; predicted grown -Acts-on-> Phaeodactylum tricornutum; grown -Using-> F/2 media | d-log phase (≈ 8.0E6 cells/ml for Phaeodactylum tricornutum [[grown]] on [[F/2 media]] or 5.0 E7 cell/ml when grown on BG-11). We have investigate
- dev_data/protocol_7: gold grow -Site-> shaking incubator; predicted grow -Acts-on-> them; grow -Setting-> 37°C; grow -Setting-> 270 rpm; grow -Using-> shaking incubator | rs) in LB+antibiotics, for each planned transformation. (We [[grow]] them at 37°C at 270 rpm in a [[shaking incubator]].). On the day of transformation, use the overnight culture
- dev_data/protocol_7: gold measure -Site-> FlowCam; predicted measure -Acts-on-> Phaeodactylum tricornutum cell; measure -Measure-Type-Link-> concentration; measure -Using-> FlowCam; measure -Using-> haemocytometer; FlowCam -Or-> haemocytometer | hours. During the 3-4 hours the E. coli culture is growing, [[measure]] the Phaeodactylum tricornutum cell concentration with a [[FlowCam]] or haemocytometer to calculate the required volume needed t
- dev_data/protocol_7: gold mix -Acts-on-> Phaeodactylum tricornutum cells; predicted mix -Acts-on-> E. coli cells; mix -Site-> tube; mix -Using-> Phaeodactylum tricornutum cells; Phaeodactylum tricornutum cells -Measure-> 200 μl | he amount of time they spend concentrated. In a 1.5 mL tube [[mix]] 200 μl of E. coli cells with 200 μl of [[Phaeodactylum tricornutum cells]]. Negative control: In a 1.5 mL tube mix 200 μl of SOC med
- dev_data/protocol_7: gold mix -Acts-on-> Phaeodactylum tricornutum cells; predicted mix -Acts-on-> SOC medium; mix -Site-> tube; mix -Using-> Phaeodactylum tricornutum cells; Phaeodactylum tricornutum cells -Measure-> 200 μl | lum tricornutum cells. Negative control: In a 1.5 mL tube [[mix]] 200 μl of SOC medium with 200 μl of [[Phaeodactylum tricornutum cells]]. Note: Incubate and treat the negative control plates ident
- dev_data/protocol_7: gold Collect -Product-> cells; predicted Collect -Acts-on-> cells | t incubator (18°C and 100 μmol photons m-2 s-1) for 2 days. [[Collect]] [[cells]] by adding 1 mL of L1 medium. Use a cell scraper to concentr

### relation/wrong_direction

- dev_data/protocol_36: gold flasks -Meronym-> chlorella; predicted Infect -Acts-on-> flasks; chlorella -Meronym-> flasks | days at 25oC with continuous light and shaking. Infect the [[flasks]] of [[chlorella]] with virus at an moi of 0.01 to 0.001. Incubate the flasks
- dev_data/protocol_102: gold flow cell holder mount -Meronym-> middle; predicted Install -Site-> flow cell holder mount; Install -Site-> middle; middle -Meronym-> flow cell holder mount; middle -Meronym-> camera apparatus | nator.Install flow cell holder (screw pointing up) into the [[flow cell holder mount]] located in the [[middle]] of the camera apparatus. Tighten screw on top of holder to
- dev_data/protocol_116: gold filters -Or-> reagents; predicted ensure -Acts-on-> reagents; ensure -Acts-on-> filters; reagents -Mod-Link-> not contaminated; reagents -Or-> filters; filters -Mod-Link-> not contaminated | tive. Begin by checking the test filters to ensure that the [[reagents]] or [[filters]] were not contaminated and the filtered volumes were appropr
- dev_data/protocol_124: gold protist -Meronym-> bacterized culture; predicted bacterized culture -Meronym-> protist | e agar plates are cooled and set, streak some liquid from a [[bacterized culture]] of the [[protist]] on the agar plates. Incubate the agar plates at the same co
- dev_data/protocol_153: gold MBBM -Meronym-> Chlorella NC64A; predicted Inoculate -Using-> Chlorella NC64A; Chlorella NC64A -Meronym-> MBBM; MBBM -Or-> Micractinium Pbi | Mictractinium Pbi virus Purification Inoculate flasks with [[Chlorella NC64A]] in [[MBBM]] (or Micractinium Pbi in FES) and incubate at 25°C with cont
- dev_data/protocol_237: gold 14,000 rpm -Coreference-Link-> 16,000 x g; predicted Centrifuge -Setting-> 14,000 rpm; Centrifuge -Setting-> 16,000 x g; 16,000 x g -Coreference-Link-> 14,000 rpm | 106 cells, lyse with 100 µlof lysis buffer). Centrifuge at [[14,000 rpm]] ([[16,000 x g]]) for 10 minutes at 4°C. Transfer the supernatant to a new t
- dev_data/protocol_237: gold enhanced chemiluminescence substrate -Coreference-Link-> ECL; predicted Incubate -Using-> ECL; ECL -Coreference-Link-> enhanced chemiluminescence substrate; ECL -Measure-> 10 ml | wash 3/3] Incubate membrane (protein side up) with 10 ml of [[ECL]] ([[enhanced chemiluminescence substrate]]) for 1-2 minutes. The final volume required is 0.125 ml/cm2
- dev_data/protocol_439: gold pipette off -Or-> Decant; predicted Decant -Acts-on-> ethanol wash; Decant -Or-> pipette off; pipette off -Acts-on-> ethanol wash | o wash the DNA pellet. Centrifuge for 1 minute at 14,000xg. [[Decant]] or [[pipette off]] the ethanol wash. Invert the tube on a clean absorbent su

Not classified automatically: normalization errors and unsupported inferences (need human-checked labels).
