# Error analysis: rules (dev)

## Entities (14936 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 10068 | 67.4% |
| wrong type | 730 | 4.9% |
| wrong boundary | 1371 | 9.2% |
| wrong boundary and type | 722 | 4.8% |
| missed | 2045 | 13.7% |

## Relations (10065 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 3413 | 33.9% |
| endpoint error | 4803 | 47.7% |
| wrong label | 606 | 6.0% |
| wrong attachment | 679 | 6.8% |
| missed | 564 | 5.6% |

Spurious entities (no overlapping gold): Action 281, Modifier 248, Reagent 47, Mention 35, Measure-Type 31, Method 28, Numerical 22, Location 22

Spurious relations: 2034 between gold entities, 3692 with a spurious endpoint.

## Slices

| Reagent names | Gold | Recall |
|---|---:|---:|
| seen in training | 2419 | 0.844 |
| unseen in training | 1013 | 0.008 |

| Documents | Gold relations | Relation recall |
|---|---:|---:|
| without | 8973 | 0.321 |
| with template sibling | 1092 | 0.487 |

## Examples

### entity/wrong_boundary

- dev_data/protocol_0: gold Method 'SpinSmart Plasmid Purification', predicted Method 'Purification' | [[SpinSmart Plasmid Purification]][[Purification]] Protocol: High-copy plasmid DNA from E. coli Start with 1-5
- dev_data/protocol_0: gold Reagent 'E. coli LB culture*', predicted Reagent 'culture' | tocol: High-copy plasmid DNA from E. coli Start with 1-5 ml [[E. coli LB culture*]][[culture]]*, pellet cells in a microcentrifuge for 30 sec at 11,000 x g
- dev_data/protocol_0: gold Reagent 'PB1 Resuspension Buffer', predicted Reagent 'Resuspension Buffer' | nt and remove as much of the liquid as possible. Add 250 µl [[PB1 Resuspension Buffer]][[Resuspension Buffer]]. Vortex or pipet up and down to resuspend the cell pellet c
- dev_data/protocol_0: gold Reagent 'PB2 Lysis Buffer', predicted Reagent 'Lysis Buffer' | et completely. No cell clumps should be visible. Add 250 µl [[PB2 Lysis Buffer]][[Lysis Buffer]]. Invert the tube 6-8 times to mix completely. Do not vortex
- dev_data/protocol_0: gold Modifier 'completely clear', predicted Modifier 'completely', Modifier 'clear' | in at 11,000 x g at room temperature. If precipitate is not [[completely]][[completely clear]][[clear]] from the lysate, centrifuge again for 5 min at 11,000 x g a
- dev_data/protocol_0: gold Location 'SpinSmart Plasmid Binding Column', predicted Location 'Column' | again for 5 min at 11,000 x g at room temperature. Place a [[SpinSmart Plasmid Binding Column]][[Column]] in a Collection Tube (2 ml) and load a maximum of 750 µl of
- dev_data/protocol_0: gold Modifier 'maximum', predicted Modifier 'maximum of' | asmid Binding Column in a Collection Tube (2 ml) and load a [[maximum]][[maximum of]] 750 µl of the supernatant (from the "Lysate Clarification"
- dev_data/protocol_0: gold Location 'SpinSmart Plasmid Binding Column', predicted Location 'Column' | for 1 min at 11,000 x g. Discard flow-through and place the [[SpinSmart Plasmid Binding Column]][[Column]] into the Collection Tube (2 ml). Optional: For host strains

### entity/missed

- dev_data/protocol_0: gold Modifier 'High-copy', predicted nothing | SpinSmart Plasmid Purification Protocol: [[High-copy]] plasmid DNA from E. coli Start with 1-5 ml E. coli LB cultu
- dev_data/protocol_0: gold Reagent 'E. coli', predicted nothing | t Plasmid Purification Protocol: High-copy plasmid DNA from [[E. coli]] Start with 1-5 ml E. coli LB culture*, pellet cells in a mi
- dev_data/protocol_0: gold Action 'Start', predicted nothing | d Purification Protocol: High-copy plasmid DNA from E. coli [[Start]] with 1-5 ml E. coli LB culture*, pellet cells in a microcen
- dev_data/protocol_0: gold Device 'microcentrifuge', predicted nothing | li Start with 1-5 ml E. coli LB culture*, pellet cells in a [[microcentrifuge]] for 30 sec at 11,000 x g. Discard the supernatant and remov
- dev_data/protocol_0: gold Reagent 'PB3 Neutralization Buffe', predicted nothing | e for up to 5 min or until lysate appears clear. Add 300 µl [[PB3 Neutralization Buffe]]r. Invert the tube 6-8 times to mix completely. Do not vorte
- dev_data/protocol_0: gold Method 'Clarification', predicted nothing | ad a maximum of 750 µl of the supernatant (from the "Lysate [[Clarification]]" section above) onto the column. Centrifuge for 1 min at 11
- dev_data/protocol_0: gold Reagent 'HB101', predicted nothing | For host strains containing high levels of nucleases (e.g. [[HB101]] or strains of the JM series), perform a wash step with 500
- dev_data/protocol_0: gold Reagent 'JM series', predicted nothing | ning high levels of nucleases (e.g. HB101 or strains of the [[JM series]]), perform a wash step with 500 µl PB4 Wash Buffer pre-warme

### entity/wrong_type

- dev_data/protocol_0: gold Action 'pellet', predicted Reagent 'pellet' | mid DNA from E. coli Start with 1-5 ml E. coli LB culture*, [[pellet]][[pellet]] cells in a microcentrifuge for 30 sec at 11,000 x g. Discar
- dev_data/protocol_0: gold Mention 'liquid', predicted Reagent 'liquid' | ,000 x g. Discard the supernatant and remove as much of the [[liquid]][[liquid]] as possible. Add 250 µl PB1 Resuspension Buffer. Vortex or
- dev_data/protocol_0: gold Numerical '6-8', predicted Amount '6-8' | ld be visible. Add 250 µl PB2 Lysis Buffer. Invert the tube [[6-8]][[6-8]] times to mix completely. Do not vortex!. Incubate at room t
- dev_data/protocol_0: gold Numerical '6-8', predicted Amount '6-8' | lear. Add 300 µl PB3 Neutralization Buffer. Invert the tube [[6-8]][[6-8]] times to mix completely. Do not vortex!. Centrifuge for 5 m
- dev_data/protocol_0: gold Reagent 'precipitate', predicted Action 'precipitate' | Centrifuge for 5 min at 11,000 x g at room temperature. If [[precipitate]][[precipitate]] is not completely clear from the lysate, centrifuge again f
- dev_data/protocol_0: gold Action 'pre-warmed', predicted Modifier 'pre-warmed' | JM series), perform a wash step with 500 µl PB4 Wash Buffer [[pre-warmed]][[pre-warmed]] to 50°C. Centrifuge for 1 min at 11,000 x g before proceedi
- dev_data/protocol_0: gold Modifier 'empty', predicted Action 'empty' | hrough and place the SpinSmart Plasmid Column back into the [[empty]][[empty]] Collection Tube (2 ml). Centrifuge for 2 min at 11,000 x g
- dev_data/protocol_0: gold Size '1.5 ml', predicted Amount '1.5 ml' | ube (2 ml). Place the SpinSmart Plasmid Binding Column in a [[1.5 ml]][[1.5 ml]] microcentrifuge tube (not provided) and add 50 µl PB6 Eluti

### entity/wrong_boundary_and_type

- dev_data/protocol_0: gold Method 'wash step', predicted Action 'wash' | cleases (e.g. HB101 or strains of the JM series), perform a [[wash]][[wash step]] with 500 µl PB4 Wash Buffer pre-warmed to 50°C. Centrifuge
- dev_data/protocol_1: gold Modifier 'unicellular', predicted Reagent 'unicellular protists' | Super simple In vivo Hoechst staining of [[unicellular]][[unicellular protists]] Add 1/1000 Hoechst dye (1 uL into 1 mL volume of cells).Kee
- dev_data/protocol_1: gold Action 'protected', predicted Location 'protected from light' | st dye (1 uL into 1 mL volume of cells).Keep cells with dye [[protected]][[protected from light]]. Incubate at room temperature for 10 minutes.Keep cells wit
- dev_data/protocol_1: gold Action 'protected', predicted Location 'protected from light' | bate at room temperature for 10 minutes.Keep cells with dye [[protected]][[protected from light]]. Centrifuge cells at 1000g for 5 minutes. Resuspend with fr
- dev_data/protocol_1: gold Action 'plate in', predicted Location 'plate' | sh growing medium. Use minimum volume of medium in order to [[plate]][[plate in]] to the slide immediately. Mount your slide and ready for ob
- dev_data/protocol_7: gold Concentration '8.0E6 cells/ml', predicted Reagent 'cells' | al Conjugation) Grow the diatom culture to mid-log phase (≈ [[8.0E6 cells/ml]][[cells]]/ml for Phaeodactylum tricornutum grown on F/2 media or 5.0 E7
- dev_data/protocol_7: gold Measure-Type 'transformation efficiency', predicted Method 'transformation' | r 5.0 E7 cell/ml when grown on BG-11). We have investigated [[transformation]][[transformation efficiency]] throughout the growth curve and found this to be the sweets
- dev_data/protocol_7: gold Time 'On the day of transformation', predicted Method 'transformation' | (We grow them at 37°C at 270 rpm in a shaking incubator.). [[On the day of transformation]][[transformation]], use the overnight culture to inoculate 50 mL of fresh LB+a

### relation/missed

- dev_data/protocol_0: gold Add -Setting-> 250 µl; predicted Add -Acts-on-> Resuspension Buffer; Resuspension Buffer -Measure-> 250 µl | e supernatant and remove as much of the liquid as possible. [[Add]] [[250 µl]] PB1 Resuspension Buffer. Vortex or pipet up and down to res
- dev_data/protocol_0: gold Vortex -Commands-> resuspend; predicted resuspend -Acts-on-> cell pellet | the liquid as possible. Add 250 µl PB1 Resuspension Buffer. [[Vortex]] or pipet up and down to [[resuspend]] the cell pellet completely. No cell clumps should be visibl
- dev_data/protocol_0: gold Vortex -Or-> pipet; predicted nothing | the liquid as possible. Add 250 µl PB1 Resuspension Buffer. [[Vortex]] or [[pipet]] up and down to resuspend the cell pellet completely. No cel
- dev_data/protocol_0: gold pipet -Commands-> resuspend; predicted resuspend -Acts-on-> cell pellet | as possible. Add 250 µl PB1 Resuspension Buffer. Vortex or [[pipet]] up and down to [[resuspend]] the cell pellet completely. No cell clumps should be visibl
- dev_data/protocol_0: gold pipet -Using-> up and down; predicted nothing | as possible. Add 250 µl PB1 Resuspension Buffer. Vortex or [[pipet]] [[up and down]] to resuspend the cell pellet completely. No cell clumps sho
- dev_data/protocol_0: gold Add -Setting-> 250 µl; predicted Add -Acts-on-> Lysis Buffer; Lysis Buffer -Measure-> 250 µl | e cell pellet completely. No cell clumps should be visible. [[Add]] [[250 µl]] PB2 Lysis Buffer. Invert the tube 6-8 times to mix complete
- dev_data/protocol_0: gold Invert -Commands-> mix; predicted Invert -Site-> tube; mix -Mod-Link-> completely | cell clumps should be visible. Add 250 µl PB2 Lysis Buffer. [[Invert]] the tube 6-8 times to [[mix]] completely. Do not vortex!. Incubate at room temperature fo
- dev_data/protocol_0: gold Add -Setting-> 300 µl; predicted nothing | temperature for up to 5 min or until lysate appears clear. [[Add]] [[300 µl]] PB3 Neutralization Buffer. Invert the tube 6-8 times to mix

### relation/wrong_attachment

- dev_data/protocol_0: gold Vortex -Acts-on-> cell pellet; predicted resuspend -Acts-on-> cell pellet; cell pellet -Mod-Link-> completely | the liquid as possible. Add 250 µl PB1 Resuspension Buffer. [[Vortex]] or pipet up and down to resuspend the [[cell pellet]] completely. No cell clumps should be visible. Add 250 µl PB
- dev_data/protocol_0: gold pipet -Acts-on-> cell pellet; predicted resuspend -Acts-on-> cell pellet; cell pellet -Mod-Link-> completely | as possible. Add 250 µl PB1 Resuspension Buffer. Vortex or [[pipet]] up and down to resuspend the [[cell pellet]] completely. No cell clumps should be visible. Add 250 µl PB
- dev_data/protocol_0: gold resuspend -Mod-Link-> completely; predicted resuspend -Acts-on-> cell pellet; cell pellet -Mod-Link-> completely | µl PB1 Resuspension Buffer. Vortex or pipet up and down to [[resuspend]] the cell pellet [[completely]]. No cell clumps should be visible. Add 250 µl PB2 Lysis Buf
- dev_data/protocol_0: gold Place -Site-> Collection Tube; predicted Place -Site-> Column; Collection Tube -Measure-> 2 ml; load -Site-> Collection Tube | ntrifuge again for 5 min at 11,000 x g at room temperature. [[Place]] a SpinSmart Plasmid Binding Column in a [[Collection Tube]] (2 ml) and load a maximum of 750 µl of the supernatant (fro
- dev_data/protocol_0: gold added -Acts-on-> EtOH; predicted make sure -Acts-on-> EtOH | ding with Buffer PB5. Add 600 µl PB5 Wash Buffer (make sure [[EtOH]] has been [[added]]). Centrifuge for 1 min at 11,000 x g. Discard flow-through
- dev_data/protocol_0: gold place -Site-> Collection Tube; predicted empty -Site-> Collection Tube; Collection Tube -Measure-> 2 ml | entrifuge for 1 min at 11,000 x g. Discard flow-through and [[place]] the SpinSmart Plasmid Column back into the empty [[Collection Tube]] (2 ml). Centrifuge for 2 min at 11,000 x g and discard the
- dev_data/protocol_0: gold Centrifuge -Setting-> 11,000 x g; predicted Centrifuge -Setting-> 2 min; discard -Setting-> 11,000 x g | Plasmid Column back into the empty Collection Tube (2 ml). [[Centrifuge]] for 2 min at [[11,000 x g]] and discard the Collection Tube (2 ml). Place the SpinSmart
- dev_data/protocol_0: gold Place -Site-> microcentrifuge tube; predicted Place -Site-> Column; microcentrifuge tube -Measure-> 1.5 ml; add -Site-> microcentrifuge tube | 2 min at 11,000 x g and discard the Collection Tube (2 ml). [[Place]] the SpinSmart Plasmid Binding Column in a 1.5 ml [[microcentrifuge tube]] (not provided) and add 50 µl PB6 Elution Buffer. Incubate f

### relation/wrong_label

- dev_data/protocol_0: gold Invert -Acts-on-> tube; predicted Invert -Site-> tube; tube -Measure-> 6-8 | cell clumps should be visible. Add 250 µl PB2 Lysis Buffer. [[Invert]] the [[tube]] 6-8 times to mix completely. Do not vortex!. Incubate at ro
- dev_data/protocol_0: gold Invert -Acts-on-> tube; predicted Invert -Site-> tube; tube -Measure-> 6-8 | lysate appears clear. Add 300 µl PB3 Neutralization Buffer. [[Invert]] the [[tube]] 6-8 times to mix completely. Do not vortex!. Centrifuge for
- dev_data/protocol_0: gold discard -Acts-on-> Collection Tube; predicted discard -Setting-> 11,000 x g; discard -Site-> Collection Tube; Collection Tube -Measure-> 2 ml | lection Tube (2 ml). Centrifuge for 2 min at 11,000 x g and [[discard]] the [[Collection Tube]] (2 ml). Place the SpinSmart Plasmid Binding Column in a 1.5
- dev_data/protocol_1: gold Add -Site-> cells; predicted Add -Acts-on-> cells; Add -Measure-Type-Link-> volume; cells -Measure-> 1/1000; cells -Measure-> 1 uL; cells -Measure-> 1 mL | per simple In vivo Hoechst staining of unicellular protists [[Add]] 1/1000 Hoechst dye (1 uL into 1 mL volume of [[cells]]).Keep cells with dye protected from light. Incubate at room
- dev_data/protocol_1: gold Mount -Acts-on-> slide; predicted Mount -Site-> slide | me of medium in order to plate in to the slide immediately. [[Mount]] your [[slide]] and ready for observation under microscope.
- dev_data/protocol_7: gold grow -Site-> shaking incubator; predicted grow -Acts-on-> them; grow -Setting-> 37°C; grow -Setting-> 270 rpm; grow -Using-> shaking incubator | rs) in LB+antibiotics, for each planned transformation. (We [[grow]] them at 37°C at 270 rpm in a [[shaking incubator]].). On the day of transformation, use the overnight culture
- dev_data/protocol_7: gold inoculate -Using-> overnight culture; predicted inoculate -Acts-on-> overnight culture; inoculate -Acts-on-> antibiotic; inoculate -Acts-on-> dilution | shaking incubator.). On the day of transformation, use the [[overnight culture]] to [[inoculate]] 50 mL of fresh LB+antibiotic, 1:50 dilution, for each plann
- dev_data/protocol_7: gold mix -Product-> Negative control; predicted mix -Acts-on-> Negative control; mix -Acts-on-> SOC medium; mix -Acts-on-> cells; mix -Site-> tube | coli cells with 200 μl of Phaeodactylum tricornutum cells. [[Negative control]]: In a 1.5 mL tube [[mix]] 200 μl of SOC medium with 200 μl of Phaeodactylum tricornut

Not classified automatically: normalization errors and unsupported inferences (need human-checked labels).
