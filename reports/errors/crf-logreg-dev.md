# Error analysis: crf-logreg (dev)

## Entities (14936 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 11128 | 74.5% |
| wrong type | 768 | 5.1% |
| wrong boundary | 1209 | 8.1% |
| wrong boundary and type | 974 | 6.5% |
| missed | 857 | 5.7% |

## Relations (10065 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 5483 | 54.5% |
| endpoint error | 3460 | 34.4% |
| wrong label | 248 | 2.5% |
| wrong direction | 7 | 0.1% |
| wrong attachment | 301 | 3.0% |
| missed | 566 | 5.6% |

Spurious entities (no overlapping gold): Action 167, Modifier 150, Reagent 79, Measure-Type 27, Method 27, Location 22, Device 19, Mention 16

Spurious relations: 747 between gold entities, 2539 with a spurious endpoint.

## Slices

| Reagent names | Gold | Recall |
|---|---:|---:|
| seen in training | 2419 | 0.873 |
| unseen in training | 1013 | 0.570 |

| Documents | Gold relations | Relation recall |
|---|---:|---:|
| without | 8973 | 0.524 |
| with template sibling | 1092 | 0.719 |

## Examples

### entity/missed

- dev_data/protocol_0: gold Modifier 'High-copy', predicted nothing | SpinSmart Plasmid Purification Protocol: [[High-copy]] plasmid DNA from E. coli Start with 1-5 ml E. coli LB cultu
- dev_data/protocol_0: gold Modifier 'clear', predicted nothing | at room temperature for up to 5 min or until lysate appears [[clear]]. Add 300 µl PB3 Neutralization Buffer. Invert the tube 6-8
- dev_data/protocol_0: gold Modifier 'completely clear', predicted nothing | in at 11,000 x g at room temperature. If precipitate is not [[completely clear]] from the lysate, centrifuge again for 5 min at 11,000 x g a
- dev_data/protocol_0: gold Reagent 'HB101', predicted nothing | For host strains containing high levels of nucleases (e.g. [[HB101]] or strains of the JM series), perform a wash step with 500
- dev_data/protocol_0: gold Action 'proceeding', predicted nothing | e-warmed to 50°C. Centrifuge for 1 min at 11,000 x g before [[proceeding]] with Buffer PB5. Add 600 µl PB5 Wash Buffer (make sure EtOH
- dev_data/protocol_0: gold Action 'added', predicted nothing | er PB5. Add 600 µl PB5 Wash Buffer (make sure EtOH has been [[added]]). Centrifuge for 1 min at 11,000 x g. Discard flow-through
- dev_data/protocol_1: gold Modifier 'minimum', predicted nothing | 00g for 5 minutes. Resuspend with fresh growing medium. Use [[minimum]] volume of medium in order to plate in to the slide immediat
- dev_data/protocol_1: gold Method 'observation', predicted nothing | in to the slide immediately. Mount your slide and ready for [[observation]] under microscope.

### entity/wrong_boundary

- dev_data/protocol_0: gold Reagent 'E. coli LB culture*', predicted Reagent 'E. coli LB culture' | tocol: High-copy plasmid DNA from E. coli Start with 1-5 ml [[E. coli LB culture]][[E. coli LB culture*]], pellet cells in a microcentrifuge for 30 sec at 11,000 x g
- dev_data/protocol_0: gold Reagent 'PB3 Neutralization Buffe', predicted Reagent 'PB3 Neutralization Buffer' | e for up to 5 min or until lysate appears clear. Add 300 µl [[PB3 Neutralization Buffe]][[PB3 Neutralization Buffer]]. Invert the tube 6-8 times to mix completely. Do not vortex
- dev_data/protocol_0: gold Reagent 'strains', predicted Reagent 'host strains' | nding Column into the Collection Tube (2 ml). Optional: For [[host strains]][[strains]] containing high levels of nucleases (e.g. HB101 or strains
- dev_data/protocol_0: gold Reagent 'PB4 Wash Buffer', predicted Reagent 'PB4 Wash Buffer pre-warmed' | strains of the JM series), perform a wash step with 500 µl [[PB4 Wash Buffer]][[PB4 Wash Buffer pre-warmed]] to 50°C. Centrifuge for 1 min at 11,000 x g before proceedi
- dev_data/protocol_1: gold Reagent 'protists', predicted Reagent 'unicellular protists' | Super simple In vivo Hoechst staining of [[unicellular protists]][[protists]] Add 1/1000 Hoechst dye (1 uL into 1 mL volume of cells).Kee
- dev_data/protocol_1: gold Reagent 'dye', predicted Reagent 'dye protected' | oechst dye (1 uL into 1 mL volume of cells).Keep cells with [[dye]][[dye protected]] from light. Incubate at room temperature for 10 minutes.Kee
- dev_data/protocol_1: gold Reagent 'dye', predicted Reagent 'dye protected' | Incubate at room temperature for 10 minutes.Keep cells with [[dye]][[dye protected]] from light. Centrifuge cells at 1000g for 5 minutes. Resusp
- dev_data/protocol_1: gold Modifier 'fresh growing', predicted Modifier 'fresh', Reagent 'growing medium' | ht. Centrifuge cells at 1000g for 5 minutes. Resuspend with [[fresh]][[fresh growing]][[growing medium]]. Use minimum volume of medium in order to plate in to the s

### entity/wrong_type

- dev_data/protocol_0: gold Mention 'liquid', predicted Reagent 'liquid' | ,000 x g. Discard the supernatant and remove as much of the [[liquid]][[liquid]] as possible. Add 250 µl PB1 Resuspension Buffer. Vortex or
- dev_data/protocol_0: gold Location 'SpinSmart Plasmid Binding Column', predicted Device 'SpinSmart Plasmid Binding Column' | again for 5 min at 11,000 x g at room temperature. Place a [[SpinSmart Plasmid Binding Column]][[SpinSmart Plasmid Binding Column]] in a Collection Tube (2 ml) and load a maximum of 750 µl of
- dev_data/protocol_0: gold Location 'SpinSmart Plasmid Binding Column', predicted Device 'SpinSmart Plasmid Binding Column' | for 1 min at 11,000 x g. Discard flow-through and place the [[SpinSmart Plasmid Binding Column]][[SpinSmart Plasmid Binding Column]] into the Collection Tube (2 ml). Optional: For host strains
- dev_data/protocol_0: gold Location 'SpinSmart Plasmid Column', predicted Device 'SpinSmart Plasmid Column' | for 1 min at 11,000 x g. Discard flow-through and place the [[SpinSmart Plasmid Column]][[SpinSmart Plasmid Column]] back into the empty Collection Tube (2 ml). Centrifuge for
- dev_data/protocol_0: gold Location 'SpinSmart Plasmid Binding Column', predicted Device 'SpinSmart Plasmid Binding Column' | 1,000 x g and discard the Collection Tube (2 ml). Place the [[SpinSmart Plasmid Binding Column]][[SpinSmart Plasmid Binding Column]] in a 1.5 ml microcentrifuge tube (not provided) and add 50
- dev_data/protocol_0: gold Size '1.5 ml', predicted Amount '1.5 ml' | ube (2 ml). Place the SpinSmart Plasmid Binding Column in a [[1.5 ml]][[1.5 ml]] microcentrifuge tube (not provided) and add 50 µl PB6 Eluti
- dev_data/protocol_1: gold Action 'In vivo Hoechst staining', predicted Method 'In vivo Hoechst staining' | Super simple [[In vivo Hoechst staining]][[In vivo Hoechst staining]] of unicellular protists Add 1/1000 Hoechst dye (1 uL into 1
- dev_data/protocol_1: gold Concentration '1/1000', predicted Amount '1/1000' | simple In vivo Hoechst staining of unicellular protists Add [[1/1000]][[1/1000]] Hoechst dye (1 uL into 1 mL volume of cells).Keep cells wit

### entity/wrong_boundary_and_type

- dev_data/protocol_0: gold Method 'wash step', predicted Action 'wash' | cleases (e.g. HB101 or strains of the JM series), perform a [[wash]][[wash step]] with 500 µl PB4 Wash Buffer pre-warmed to 50°C. Centrifuge
- dev_data/protocol_0: gold Action 'pre-warmed', predicted Reagent 'PB4 Wash Buffer pre-warmed' | strains of the JM series), perform a wash step with 500 µl [[PB4 Wash Buffer pre-warmed]][[pre-warmed]] to 50°C. Centrifuge for 1 min at 11,000 x g before proceedi
- dev_data/protocol_1: gold Modifier 'unicellular', predicted Reagent 'unicellular protists' | Super simple In vivo Hoechst staining of [[unicellular]][[unicellular protists]] Add 1/1000 Hoechst dye (1 uL into 1 mL volume of cells).Kee
- dev_data/protocol_1: gold Action 'protected', predicted Reagent 'dye protected' | oechst dye (1 uL into 1 mL volume of cells).Keep cells with [[dye protected]][[protected]] from light. Incubate at room temperature for 10 minutes.Kee
- dev_data/protocol_1: gold Action 'protected', predicted Reagent 'dye protected' | Incubate at room temperature for 10 minutes.Keep cells with [[dye protected]][[protected]] from light. Centrifuge cells at 1000g for 5 minutes. Resusp
- dev_data/protocol_7: gold Method 'Full Contact Microbiology', predicted Modifier 'Full', Reagent 'Contact Microbiology' | [[Full]][[Full Contact Microbiology]][[Contact Microbiology]] (a.k.a Diatom Transformation via Bacterial Conjugation) Gro
- dev_data/protocol_7: gold Concentration '8.0E6 cells/ml', predicted Numerical '8.0E6', Reagent 'cells' | al Conjugation) Grow the diatom culture to mid-log phase (≈ [[8.0E6]][[8.0E6 cells/ml]][[cells]]/ml for Phaeodactylum tricornutum grown on F/2 media or 5.0 E7
- dev_data/protocol_7: gold Action 'grown', predicted Reagent 'Phaeodactylum tricornutum grown' | w the diatom culture to mid-log phase (≈ 8.0E6 cells/ml for [[Phaeodactylum tricornutum grown]][[grown]] on F/2 media or 5.0 E7 cell/ml when grown on BG-11). We hav

### relation/wrong_attachment

- dev_data/protocol_0: gold pellet -Setting-> 11,000 x g; predicted pellet -Acts-on-> cells; pellet -Setting-> 30 sec; pellet -Site-> microcentrifuge | mid DNA from E. coli Start with 1-5 ml E. coli LB culture*, [[pellet]] cells in a microcentrifuge for 30 sec at [[11,000 x g]]. Discard the supernatant and remove as much of the liquid a
- dev_data/protocol_0: gold Vortex -Acts-on-> cell pellet; predicted Vortex -Or-> pipet; resuspend -Acts-on-> cell pellet | the liquid as possible. Add 250 µl PB1 Resuspension Buffer. [[Vortex]] or pipet up and down to resuspend the [[cell pellet]] completely. No cell clumps should be visible. Add 250 µl PB
- dev_data/protocol_0: gold pipet -Acts-on-> cell pellet; predicted Vortex -Or-> pipet; pipet -Using-> up and down; resuspend -Acts-on-> cell pellet | as possible. Add 250 µl PB1 Resuspension Buffer. Vortex or [[pipet]] up and down to resuspend the [[cell pellet]] completely. No cell clumps should be visible. Add 250 µl PB
- dev_data/protocol_7: gold centrifuge -Acts-on-> Phaeodactylum tricornutum; predicted centrifuge -Acts-on-> E. coli culture; centrifuge -Setting-> 10 minutes; centrifuge -Setting-> 4°C; Phaeodactylum tricornutum -Mod-Link-> required | 5E8 cells for each transformation. For each transformation, [[centrifuge]] 50 mL of E. coli culture and the required [[Phaeodactylum tricornutum]] volume at 4000 x g for 10 minutes at 4°C. Resuspend E. coli
- dev_data/protocol_7: gold centrifuge -Setting-> 4000 x g; predicted centrifuge -Acts-on-> E. coli culture; centrifuge -Setting-> 10 minutes; centrifuge -Setting-> 4°C | 5E8 cells for each transformation. For each transformation, [[centrifuge]] 50 mL of E. coli culture and the required Phaeodactylum tricornutum volume at [[4000 x g]] for 10 minutes at 4°C. Resuspend E. coli pellet in 500 μL o
- dev_data/protocol_7: gold mix -Acts-on-> Phaeodactylum tricornutum cells; predicted mix -Acts-on-> tube; mix -Acts-on-> E. coli cells; Phaeodactylum tricornutum cells -Measure-> 200 μl | he amount of time they spend concentrated. In a 1.5 mL tube [[mix]] 200 μl of E. coli cells with 200 μl of [[Phaeodactylum tricornutum cells]]. Negative control: In a 1.5 mL tube mix 200 μl of SOC med
- dev_data/protocol_7: gold mix -Acts-on-> Phaeodactylum tricornutum cells; predicted mix -Acts-on-> tube; mix -Acts-on-> SOC medium; Phaeodactylum tricornutum cells -Measure-> 200 μl | lum tricornutum cells. Negative control: In a 1.5 mL tube [[mix]] 200 μl of SOC medium with 200 μl of [[Phaeodactylum tricornutum cells]]. Note: Incubate and treat the negative control plates ident
- dev_data/protocol_7: gold light incubator -Setting-> 18°C; predicted Move -Setting-> 18°C; Move -Site-> light incubator | e plates for 90 minutes at 30°C in the dark. Move plates to [[light incubator]] ([[18°C]] and 100 μmol photons m-2 s-1) for 2 days. Collect cells by

### relation/missed

- dev_data/protocol_0: gold Add -Setting-> 250 µl; predicted Add -Acts-on-> PB1 Resuspension Buffer; PB1 Resuspension Buffer -Measure-> 250 µl | e supernatant and remove as much of the liquid as possible. [[Add]] [[250 µl]] PB1 Resuspension Buffer. Vortex or pipet up and down to res
- dev_data/protocol_0: gold Vortex -Commands-> resuspend; predicted Vortex -Or-> pipet; resuspend -Acts-on-> cell pellet | the liquid as possible. Add 250 µl PB1 Resuspension Buffer. [[Vortex]] or pipet up and down to [[resuspend]] the cell pellet completely. No cell clumps should be visibl
- dev_data/protocol_0: gold pipet -Commands-> resuspend; predicted Vortex -Or-> pipet; pipet -Using-> up and down; resuspend -Acts-on-> cell pellet | as possible. Add 250 µl PB1 Resuspension Buffer. Vortex or [[pipet]] up and down to [[resuspend]] the cell pellet completely. No cell clumps should be visibl
- dev_data/protocol_0: gold resuspend -Mod-Link-> completely; predicted resuspend -Acts-on-> cell pellet | µl PB1 Resuspension Buffer. Vortex or pipet up and down to [[resuspend]] the cell pellet [[completely]]. No cell clumps should be visible. Add 250 µl PB2 Lysis Buf
- dev_data/protocol_0: gold Add -Setting-> 250 µl; predicted Add -Acts-on-> PB2 Lysis Buffer; PB2 Lysis Buffer -Measure-> 250 µl | e cell pellet completely. No cell clumps should be visible. [[Add]] [[250 µl]] PB2 Lysis Buffer. Invert the tube 6-8 times to mix complete
- dev_data/protocol_0: gold Invert -Commands-> mix; predicted Invert -Acts-on-> tube; Invert -Count-> 6-8; mix -Mod-Link-> completely | cell clumps should be visible. Add 250 µl PB2 Lysis Buffer. [[Invert]] the tube 6-8 times to [[mix]] completely. Do not vortex!. Incubate at room temperature fo
- dev_data/protocol_0: gold Add -Setting-> 300 µl; predicted Add -Acts-on-> PB3 Neutralization Buffer; PB3 Neutralization Buffer -Measure-> 300 µl | temperature for up to 5 min or until lysate appears clear. [[Add]] [[300 µl]] PB3 Neutralization Buffer. Invert the tube 6-8 times to mix
- dev_data/protocol_0: gold Invert -Commands-> mix; predicted Invert -Acts-on-> tube; Invert -Count-> 6-8; mix -Mod-Link-> completely | lysate appears clear. Add 300 µl PB3 Neutralization Buffer. [[Invert]] the tube 6-8 times to [[mix]] completely. Do not vortex!. Centrifuge for 5 min at 11,000

### relation/wrong_label

- dev_data/protocol_1: gold Mount -Site-> microscope; predicted Mount -Acts-on-> slide; Mount -Using-> microscope | me of medium in order to plate in to the slide immediately. [[Mount]] your slide and ready for observation under [[microscope]].
- dev_data/protocol_7: gold measure -Site-> FlowCam; predicted measure -Acts-on-> Phaeodactylum tricornutum cell; measure -Measure-Type-Link-> concentration; measure -Using-> FlowCam; FlowCam -Or-> haemocytometer | hours. During the 3-4 hours the E. coli culture is growing, [[measure]] the Phaeodactylum tricornutum cell concentration with a [[FlowCam]] or haemocytometer to calculate the required volume needed t
- dev_data/protocol_7: gold mix -Site-> tube; predicted tube -Measure-> 1.5 mL; mix -Acts-on-> tube; mix -Acts-on-> E. coli cells | ize the amount of time they spend concentrated. In a 1.5 mL [[tube]] [[mix]] 200 μl of E. coli cells with 200 μl of Phaeodactylum tricor
- dev_data/protocol_7: gold mix -Site-> tube; predicted tube -Measure-> 1.5 mL; mix -Acts-on-> tube; mix -Acts-on-> SOC medium | dactylum tricornutum cells. Negative control: In a 1.5 mL [[tube]] [[mix]] 200 μl of SOC medium with 200 μl of Phaeodactylum tricornut
- dev_data/protocol_7: gold Collect -Product-> cells; predicted Collect -Acts-on-> cells | t incubator (18°C and 100 μmol photons m-2 s-1) for 2 days. [[Collect]] [[cells]] by adding 1 mL of L1 medium. Use a cell scraper to concentr
- dev_data/protocol_7: gold Incubate -Product-> colonies; predicted Incubate -Acts-on-> colonies; Incubate -Setting-> 18°C; Incubate -Setting-> 100 μmol photons m-2 s-1 | Spread 200 μl of the cell suspension on a Selection Plate. [[Incubate]] at 18°C and 100 μmol photons m-2 s-1 until [[colonies]] appear. After a minimum of 8-12 days, untransformed Phaeoda
- dev_data/protocol_27: gold Shake -Using-> orbital rotator; predicted Shake -Setting-> 150rpm; Shake -Setting-> 20 mins; Shake -Site-> orbital rotator | os to container with 50:50 4% paraformaldehyde and heptane. [[Shake]] on [[orbital rotator]] at 150rpm for 20 mins. Allow solution to heptane and PFA to
- dev_data/protocol_27: gold trapped -Product-> embryos; predicted remove -Acts-on-> embryos; trapped -Acts-on-> embryos; trapped -Site-> interface | ispose of as required. Be sure to not disturb or remove the [[embryos]] that are [[trapped]] in the interface. Add Methanol in equal volume to the remai

### relation/wrong_direction

- dev_data/protocol_116: gold vial -Meronym-> stock SYBR solution; predicted Thaw -Acts-on-> vial; Thaw -Acts-on-> stock SYBR solution; vial -Measure-> 40-µL; stock SYBR solution -Measure-> 40-µL; stock SYBR solution -Meronym-> vial | 2O on each section of the marked Petri plates. Thaw a 40-µL [[vial]] of the [[stock SYBR solution]] and add 2 µL stock solution to each drop (78 µL) of sterile
- dev_data/protocol_237: gold 14,000 rpm -Coreference-Link-> 16,000 x g; predicted Centrifuge -Setting-> 14,000 rpm; Centrifuge -Setting-> 16,000 x g; 16,000 x g -Coreference-Link-> 14,000 rpm | 106 cells, lyse with 100 µlof lysis buffer). Centrifuge at [[14,000 rpm]] ([[16,000 x g]]) for 10 minutes at 4°C. Transfer the supernatant to a new t
- dev_data/protocol_439: gold pipette off -Or-> Decant; predicted Decant -Acts-on-> ethanol wash; Decant -Or-> pipette off; pipette off -Acts-on-> ethanol wash | o wash the DNA pellet. Centrifuge for 1 minute at 14,000xg. [[Decant]] or [[pipette off]] the ethanol wash. Invert the tube on a clean absorbent su
- dev_data/protocol_439: gold -80°C -Or-> -20°C; predicted store -Setting-> -20°C; -20°C -Or-> -80°C | his stage. Store DNA at 4°C, for long term storage store at [[-20°C]] or [[-80°C]]. Centrifuge for 5 minutes at 14,000xg and pour off the supe
- dev_data/protocol_440: gold 0.1 -Or-> 0.05; predicted 0.05 -Or-> 0.1 | t a 150 mL LB subculture (recommended starting OD600 either [[0.05]] or [[0.1]]). Grow at 37oC until OD600 reaches 0.3-0.4. Centrifuge at 4
- dev_data/protocol_504: gold cryo box -Meronym-> lid; predicted lid -Meronym-> cryo box | holder and put it on Kimwipes to dry. Cover, e.g. with the [[lid]] of a [[cryo box]] or a Petri dish. Allow to air-dry. Label membrane filter wi
- dev_data/protocol_620: gold 1.5 days -Or-> 36 h; predicted 36 h -Mod-Link-> at least; 36 h -Or-> 1.5 days | ture (induced 6 h prior). Co-cultivate for 2 days (at least [[36 h]] or [[1.5 days]]) on a shaker in the tissue culture room (21 ºC, CL 150-200

Not classified automatically: normalization errors and unsupported inferences (need human-checked labels).
