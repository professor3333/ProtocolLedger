# Error analysis: scibert-uniform-negatives-s21-7dc7a1893e on later-domain (dev, vs. machine labels)

## Entities (1866 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 1522 | 81.6% |
| wrong type | 75 | 4.0% |
| wrong boundary | 90 | 4.8% |
| wrong boundary and type | 50 | 2.7% |
| missed | 129 | 6.9% |

## Relations (1254 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 786 | 62.7% |
| endpoint error | 291 | 23.2% |
| wrong label | 15 | 1.2% |
| wrong attachment | 41 | 3.3% |
| missed | 121 | 9.7% |

Spurious entities (no overlapping gold): Reagent 36, Modifier 35, Method 20, Action 13, Measure-Type 11, Time 6, Numerical 5, Location 5

Spurious relations: 104 between gold entities, 224 with a spurious endpoint.

## Slices

| Reagent names | Gold | Recall |
|---|---:|---:|
| seen in training | 223 | 0.915 |
| unseen in training | 261 | 0.789 |

## Examples

### entity/wrong_type

- later-domain/pio-317105: gold Device 'components', predicted Reagent 'components' | acuum filtration apparatus in a clean workspace. Ensure all [[components]][[components]] are sterile before use. Place a Whatman 0.45 µm filter pape
- later-domain/pio-317813: gold Location 'dry ice', predicted Reagent 'dry ice' | microcentrifuge tube. The tissue sample should be placed on [[dry ice]][[dry ice]] after retrieved from the storage and the weighing step must
- later-domain/pio-317813: gold Speed '25 Hz', predicted Generic-Measure '25 Hz' | ue with TissueLyser II (QIAGEN) Homogenisation for 2 min at [[25 Hz]][[25 Hz]]. Add 1 stainless steel bead to the tube. Aliquot 200 µl dis
- later-domain/pio-317813: gold Amount '1', predicted Numerical '1' | sueLyser II (QIAGEN) Homogenisation for 2 min at 25 Hz. Add [[1]][[1]] stainless steel bead to the tube. Aliquot 200 µl disrupted
- later-domain/pio-317813: gold Action 'pulse-vortexing', predicted Method 'pulse-vortexing' | oteinase K. Add 100 µl Buffer VXL. Close the cap and mix by [[pulse-vortexing]][[pulse-vortexing]]. Thoroughly homogenise the sample and the buffer to ensure
- later-domain/pio-223996: gold Amount 'two', predicted Numerical 'two' | A-GFP ATG2 DKO (RRID:CVCL_F0LE) Seed cells in 15 cm dishes ([[two]][[two]] dishes per condition). Treat cells with: Earle’s Balanced S
- later-domain/pio-226171: gold Device 'flow cell', predicted Reagent 'flow cell' | 3880 After the sequencing run is finished you can wash your [[flow cell]][[flow cell]] to remove the remaining library and either prepare for anot
- later-domain/pio-226171: gold Method 'storage', predicted Action 'storage' | ibrary and either prepare for another sequencing run or for [[storage]][[storage]] at 4°C. The wash uses the reagents supplied in the ONT wash

### entity/missed

- later-domain/pio-317105: gold Modifier 'Whatman', predicted nothing | pace. Ensure all components are sterile before use. Place a [[Whatman]] 0.45 µm filter paper onto the filtration membrane support u
- later-domain/pio-317105: gold Device 'filter paper', predicted nothing | components are sterile before use. Place a Whatman 0.45 µm [[filter paper]] onto the filtration membrane support using sterile forceps.
- later-domain/pio-317813: gold Method 'Pathogen-Agnostic WGS', predicted nothing | [[Pathogen-Agnostic WGS]]: An ONT Workflow (Lyssavirus Rabies Part 1 - RNA Extraction
- later-domain/pio-317813: gold Method 'ONT Workflow', predicted nothing | Pathogen-Agnostic WGS: An [[ONT Workflow]] (Lyssavirus Rabies Part 1 - RNA Extraction) Weigh 50 mg bra
- later-domain/pio-317813: gold Reagent 'Lyssavirus Rabies', predicted nothing | Pathogen-Agnostic WGS: An ONT Workflow ([[Lyssavirus Rabies]] Part 1 - RNA Extraction) Weigh 50 mg brain tissue (straw me
- later-domain/pio-223996: gold Modifier 'per condition', predicted nothing | DKO (RRID:CVCL_F0LE) Seed cells in 15 cm dishes (two dishes [[per condition]]). Treat cells with: Earle’s Balanced Salt Solution (EBSS).
- later-domain/pio-226171: gold Modifier 'consecutive', predicted nothing | rus isolates Pairs of samples (with the same EPID) can have [[consecutive]] barcodes but try not to group samples from the same geograp
- later-domain/pio-226171: gold Reagent 'barcodes', predicted nothing | Pairs of samples (with the same EPID) can have consecutive [[barcodes]] but try not to group samples from the same geographic area

### entity/wrong_boundary_and_type

- later-domain/pio-317105: gold Modifier 'entire', predicted Amount 'entire volume' | ple into the filtration funnel. Apply vacuum and filter the [[entire]][[entire volume]]. Replace filter paper if it becomes clogged. Using sterile
- later-domain/pio-317105: gold Reagent 'volume', predicted Amount 'entire volume' | ple into the filtration funnel. Apply vacuum and filter the [[entire volume]][[volume]]. Replace filter paper if it becomes clogged. Using sterile
- later-domain/pio-317105: gold Modifier 'inward', predicted Action 'Fold inward' | es clogged. Using sterile forceps, remove the filter paper. [[Fold inward]][[inward]] (cell-side in) and place into a sterile 2 mL microcentrifug
- later-domain/pio-317105: gold Amount 'appropriate volume', predicted Modifier 'appropriate', Measure-Type 'volume' | and place into a sterile 2 mL microcentrifuge tube. Add an [[appropriate]][[appropriate volume]][[volume]] of 1X PBS to the tube containing the folded filter paper. V
- later-domain/pio-317105: gold Reagent 'QIAamp® DNA Mini Kit', predicted Method 'QIAamp® DNA Mini Kit manufacturer's instructions' | PBS solution. Proceed with DNA extraction according to the [[QIAamp® DNA Mini Kit]][[QIAamp® DNA Mini Kit manufacturer's instructions]], using the resuspended PBS as the starting material. Elute
- later-domain/pio-317105: gold Modifier 'resuspended', predicted Reagent 'resuspended PBS' | QIAamp® DNA Mini Kit manufacturer's instructions, using the [[resuspended]][[resuspended PBS]] as the starting material. Elute the purified DNA in Buffer
- later-domain/pio-317105: gold Modifier 'as the starting material', predicted Reagent 'starting material' | Kit manufacturer's instructions, using the resuspended PBS [[as the starting material]][[starting material]]. Elute the purified DNA in Buffer AE into a clean 1.5 mL mi
- later-domain/pio-317813: gold Method 'weighing step', predicted Action 'weighing' | placed on dry ice after retrieved from the storage and the [[weighing]][[weighing step]] must be carried out swiftly. Add 600 µl 1X DNA/RNA ShieldTM

### entity/wrong_boundary

- later-domain/pio-317105: gold Action 'Fold', predicted Action 'Fold inward' | es clogged. Using sterile forceps, remove the filter paper. [[Fold]][[Fold inward]] (cell-side in) and place into a sterile 2 mL microcentrifug
- later-domain/pio-317105: gold Method 'manufacturer's instructions', predicted Method 'QIAamp® DNA Mini Kit manufacturer's instructions' | PBS solution. Proceed with DNA extraction according to the [[QIAamp® DNA Mini Kit manufacturer's instructions]][[manufacturer's instructions]], using the resuspended PBS as the starting material. Elute
- later-domain/pio-317105: gold Reagent 'PBS', predicted Reagent 'resuspended PBS' | QIAamp® DNA Mini Kit manufacturer's instructions, using the [[resuspended PBS]][[PBS]] as the starting material. Elute the purified DNA in Buffer
- later-domain/pio-317813: gold Method 'RNA Extraction', predicted Reagent 'RNA', Method 'Extraction' | n-Agnostic WGS: An ONT Workflow (Lyssavirus Rabies Part 1 - [[RNA]][[RNA Extraction]][[Extraction]]) Weigh 50 mg brain tissue (straw method) in a 2 ml microcen
- later-domain/pio-317813: gold Method 'extraction step', predicted Method 'extraction' | l bead to the tube. Aliquot 200 µl disrupted tissue for the [[extraction]][[extraction step]]. Pipette 20 µl Proteinase K into a 1.5 ml Lo-Bind tube. Add
- later-domain/pio-223996: gold Method 'Protection Assay', predicted Method 'Proteinase K Protection Assay' | Isolation of Autophagosomes and [[Proteinase K Protection Assay]][[Protection Assay]] Use the following cell lines: HAP1 ATG9A-GFP (RRID:CVCL_E2T
- later-domain/pio-223996: gold Concentration '100 nanomolar (nM)', predicted Concentration '100 nanomolar' | ). Treat cells with: Earle’s Balanced Salt Solution (EBSS). [[100 nanomolar]][[100 nanomolar (nM)]] Bafilomycin A1 (BafA). Incubate for 02:00:00 prior to harve
- later-domain/pio-226171: gold Reagent 'identical sequences', predicted Reagent 'sequences' | This helps detect any potential cross-contamination because [[identical sequences]][[sequences]] are then unlikely to be detected in samples with consecutiv

### relation/wrong_label

- later-domain/pio-317105: gold Elute -Using-> Buffer AE; predicted Elute -Acts-on-> DNA; Elute -Site-> Buffer AE; Elute -Site-> microcentrifuge tube | ctions, using the resuspended PBS as the starting material. [[Elute]] the purified DNA in [[Buffer AE]] into a clean 1.5 mL microcentrifuge tube.
- later-domain/pio-223996: gold Use -Using-> cell lines; predicted Use -Acts-on-> cell lines; Use -Acts-on-> HAP1 ATG9A-GFP ATG2 DKO | olation of Autophagosomes and Proteinase K Protection Assay [[Use]] the following [[cell lines]]: HAP1 ATG9A-GFP (RRID:CVCL_E2TR) HAP1 ATG9A-GFP ATG2 DKO (R
- later-domain/pio-223996: gold Use -Using-> HAP1 ATG9A-GFP ATG2 DKO; predicted Use -Acts-on-> cell lines; Use -Acts-on-> HAP1 ATG9A-GFP ATG2 DKO | olation of Autophagosomes and Proteinase K Protection Assay [[Use]] the following cell lines: HAP1 ATG9A-GFP (RRID:CVCL_E2TR) [[HAP1 ATG9A-GFP ATG2 DKO]] (RRID:CVCL_F0LE) Seed cells in 15 cm dishes (two dishes per
- later-domain/pio-243070: gold Incubate -Site-> rotator; predicted Incubate -Setting-> 4 °C; Incubate -Setting-> 10 min; Incubate -Setting-> 3 to 5 min; Incubate -Using-> rotator; rotator -Mod-Link-> gentle; rotator -Setting-> 4 °C; rotator -Setting-> 10 min | 100 µL washed anti-HA beads. Avoid disturbing the pellet. [[Incubate]] on a gentle [[rotator]] at 4 °C for 10 min (proteomics workflow). (Metabolomics w
- later-domain/pio-323282: gold Run -Site-> thermocycler; predicted Run -Using-> reverse transcription; Run -Using-> thermocycler | (total = 18 µL). Mix at 1600 rpm for 1 min, then spin down [[Run]] reverse transcription on [[thermocycler]]: Temperature Time 25°C 10 min 55°C 30 min 80°C 10 min 4°C H
- later-domain/pio-321426: gold Sonicate -Site-> water bath sonicator; predicted Sonicate -Acts-on-> PFFs; Sonicate -Using-> water bath sonicator | , removing as much as possible without drying out the cells [[Sonicate]] PFFs (and no PFF control) in a [[water bath sonicator]] with the program: 30 seconds on; 30 seconds off; repeat for
- later-domain/pio-319104: gold incubate -Site-> ice; predicted incubate -Acts-on-> ice; incubate -Setting-> 30 min | uffer containing 50mM IAA + 1X protease inhibitor cocktail; [[incubate]] on [[ice]] for 30 min. The experiment can either be paused at this poi
- later-domain/pio-119518: gold Discard -Acts-on-> Collection Tube; predicted Discard -Acts-on-> flow-through liquid; Discard -Setting-> 1 minute; Discard -Site-> Collection Tube | High Pure Filter Tube. 8000 x g, Room temperature, 1 minute [[Discard]] the flow-through liquid and [[Collection Tube]], and insert the Filter Tube into a new Collection Tube. Add

### relation/missed

- later-domain/pio-223996: gold Use -Using-> HAP1 ATG9A-GFP; predicted Use -Acts-on-> cell lines; Use -Acts-on-> HAP1 ATG9A-GFP ATG2 DKO | olation of Autophagosomes and Proteinase K Protection Assay [[Use]] the following cell lines: [[HAP1 ATG9A-GFP]] (RRID:CVCL_E2TR) HAP1 ATG9A-GFP ATG2 DKO (RRID:CVCL_F0LE) S
- later-domain/pio-223996: gold dishes -Coreference-Link-> dishes; predicted Seed -Site-> dishes; dishes -Measure-> 15 cm; dishes -Measure-> two | AP1 ATG9A-GFP ATG2 DKO (RRID:CVCL_F0LE) Seed cells in 15 cm [[dishes]] (two [[dishes]] per condition). Treat cells with: Earle’s Balanced Salt Sol
- later-domain/pio-223996: gold EBSS -Coreference-Link-> Earle’s Balanced Salt Solution; predicted Treat -Using-> Earle’s Balanced Salt Solution | 15 cm dishes (two dishes per condition). Treat cells with: [[Earle’s Balanced Salt Solution]] ([[EBSS]]). 100 nanomolar (nM) Bafilomycin A1 (BafA). Incubate for 02
- later-domain/pio-223996: gold BafA -Coreference-Link-> Bafilomycin A1; predicted Bafilomycin A1 -Measure-> 100 nanomolar | : Earle’s Balanced Salt Solution (EBSS). 100 nanomolar (nM) [[Bafilomycin A1]] ([[BafA]]). Incubate for 02:00:00 prior to harvesting. Harvest cells
- later-domain/pio-223996: gold VIB -Coreference-Link-> Vesicle Isolation Buffer; predicted Resuspend -Site-> Vesicle Isolation Buffer; Vesicle Isolation Buffer -Measure-> 800 µL | rifugation. Wash once with PBS. Resuspend pellets in 800 µL [[Vesicle Isolation Buffer]] ([[VIB]]): Transfer to LoBind tubes (Eppendorf, Cat# 0030108116).
- later-domain/pio-226171: gold SB -Coreference-Link-> Sequencing buffer; predicted Thaw -Acts-on-> Sequencing buffer; Thaw -Acts-on-> SB | t Oxford Nanopore Technologies Catalog #EXP-WSH004 Thaw the [[Sequencing buffer]] ([[SB]]), Library beads (LIB), Flow Cell Tether (FCT) and one tube
- later-domain/pio-226171: gold LIB -Coreference-Link-> Library beads; predicted Thaw -Acts-on-> Library beads | logies Catalog #EXP-WSH004 Thaw the Sequencing buffer (SB), [[Library beads]] ([[LIB]]), Flow Cell Tether (FCT) and one tube of Flow Cell Flush (F
- later-domain/pio-226171: gold FCT -Coreference-Link-> Flow Cell Tether; predicted Thaw -Acts-on-> Flow Cell Tether | SH004 Thaw the Sequencing buffer (SB), Library beads (LIB), [[Flow Cell Tether]] ([[FCT]]) and one tube of Flow Cell Flush (FCF) at room temperature

### relation/wrong_attachment

- later-domain/pio-223996: gold Treat -Using-> Bafilomycin A1; predicted Treat -Acts-on-> cells; Treat -Using-> Earle’s Balanced Salt Solution; Bafilomycin A1 -Measure-> 100 nanomolar | 0LE) Seed cells in 15 cm dishes (two dishes per condition). [[Treat]] cells with: Earle’s Balanced Salt Solution (EBSS). 100 nanomolar (nM) [[Bafilomycin A1]] (BafA). Incubate for 02:00:00 prior to harvesting. Harvest
- later-domain/pio-226171: gold detected -Site-> samples; predicted detected -Acts-on-> sequences; detected -Site-> 96-well plate; samples -Mod-Link-> adjacent | ination because identical sequences are then unlikely to be [[detected]] in [[samples]] with consecutive barcodes that are adjacent to one another
- later-domain/pio-226171: gold prepare -Setting-> 4°C; predicted storage -Setting-> 4°C | h your flow cell to remove the remaining library and either [[prepare]] for another sequencing run or for storage at [[4°C]]. The wash uses the reagents supplied in the ONT wash kit: O
- later-domain/pio-226171: gold Thaw -Acts-on-> Flow Cell Flush; predicted Thaw -Acts-on-> Sequencing buffer; Thaw -Acts-on-> SB; Thaw -Acts-on-> Library beads; Thaw -Acts-on-> Flow Cell Tether; Thaw -Acts-on-> tube; Thaw -Setting-> room temperature; Flow Cell Flush -Meronym-> tube | l Wash Kit Oxford Nanopore Technologies Catalog #EXP-WSH004 [[Thaw]] the Sequencing buffer (SB), Library beads (LIB), Flow Cell Tether (FCT) and one tube of [[Flow Cell Flush]] (FCF) at room temperature then place on ice. Mix the SQB, F
- later-domain/pio-226171: gold Add -Acts-on-> nuclease free water; predicted Add -Acts-on-> sample RNA; Add -Site-> reaction; nuclease free water -Measure-> 5μL | ll, ensuring you add a different barcode for each reaction. [[Add]] 5μL sample RNA to each reaction, and 5μL of [[nuclease free water]] for negative controls, and pipette 5 times to mix Spin down
- later-domain/pio-226171: gold Add -Site-> negative controls; predicted Add -Acts-on-> sample RNA; Add -Site-> reaction | ll, ensuring you add a different barcode for each reaction. [[Add]] 5μL sample RNA to each reaction, and 5μL of nuclease free water for [[negative controls]], and pipette 5 times to mix Spin down for 5 seconds to make
- later-domain/pio-243070: gold Pre-chill -Acts-on-> magnet; predicted Pre-chill -Acts-on-> buffers; Pre-chill -Acts-on-> tubes; Pre-chill -Setting-> 4 °C | ns for Proteomics, with Options for Lipidomics/Metabolomics [[Pre-chill]] all buffers, tubes, [[magnet]], and centrifuge to 4 °C. ￼ Keep everything on ice and minim
- later-domain/pio-243070: gold Pre-chill -Acts-on-> centrifuge; predicted Pre-chill -Acts-on-> buffers; Pre-chill -Acts-on-> tubes; Pre-chill -Setting-> 4 °C; centrifuge -Setting-> 4 °C | ns for Proteomics, with Options for Lipidomics/Metabolomics [[Pre-chill]] all buffers, tubes, magnet, and [[centrifuge]] to 4 °C. ￼ Keep everything on ice and minimize time from ha

Not classified automatically: normalization errors and unsupported inferences (need human-checked labels).
