# Error analysis: crf-logreg-4a9d8cc549 on later-domain (dev, vs. machine labels)

## Entities (1866 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 1353 | 72.5% |
| wrong type | 110 | 5.9% |
| wrong boundary | 140 | 7.5% |
| wrong boundary and type | 123 | 6.6% |
| missed | 140 | 7.5% |

## Relations (1254 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 630 | 50.2% |
| endpoint error | 432 | 34.4% |
| wrong label | 21 | 1.7% |
| wrong attachment | 53 | 4.2% |
| missed | 118 | 9.4% |

Spurious entities (no overlapping gold): Reagent 37, Modifier 22, Action 18, Measure-Type 10, Method 8, Numerical 5, Device 4, Time 4

Spurious relations: 68 between gold entities, 269 with a spurious endpoint.

## Slices

| Reagent names | Gold | Recall |
|---|---:|---:|
| seen in training | 223 | 0.874 |
| unseen in training | 261 | 0.667 |

## Examples

### entity/wrong_boundary

- later-domain/pio-317105: gold Method 'Vacuum Filtration', predicted Method 'Vacuum Filtration and DNA Extraction' | [[Vacuum Filtration]][[Vacuum Filtration and DNA Extraction]] from Environmental Water Samples Assemble vacuum filtration
- later-domain/pio-317105: gold Method 'DNA Extraction', predicted Method 'Vacuum Filtration and DNA Extraction' | [[Vacuum Filtration and DNA Extraction]][[DNA Extraction]] from Environmental Water Samples Assemble vacuum filtration
- later-domain/pio-317105: gold Modifier 'folded', predicted Modifier 'containing the folded' | ifuge tube. Add an appropriate volume of 1X PBS to the tube [[containing the folded]][[folded]] filter paper. Vortex for 30–60 seconds to resuspend microbi
- later-domain/pio-317105: gold Reagent 'QIAamp® DNA Mini Kit', predicted Reagent 'QIAamp® DNA Mini Kit manufacturer's instructions' | PBS solution. Proceed with DNA extraction according to the [[QIAamp® DNA Mini Kit]][[QIAamp® DNA Mini Kit manufacturer's instructions]], using the resuspended PBS as the starting material. Elute
- later-domain/pio-317813: gold Reagent 'Lyssavirus Rabies', predicted Reagent 'Lyssavirus Rabies Part 1 - RNA' | Pathogen-Agnostic WGS: An ONT Workflow ([[Lyssavirus Rabies]][[Lyssavirus Rabies Part 1 - RNA]] Extraction) Weigh 50 mg brain tissue (straw method) in a 2
- later-domain/pio-317813: gold Method 'RNA Extraction', predicted Reagent 'Lyssavirus Rabies Part 1 - RNA', Method 'Extraction' | Pathogen-Agnostic WGS: An ONT Workflow ([[Lyssavirus Rabies Part 1 - RNA]][[RNA Extraction]][[Extraction]]) Weigh 50 mg brain tissue (straw method) in a 2 ml microcen
- later-domain/pio-317813: gold Method 'straw method', predicted Method '(straw method' | us Rabies Part 1 - RNA Extraction) Weigh 50 mg brain tissue [[(straw method]][[straw method]]) in a 2 ml microcentrifuge tube. The tissue sample should b
- later-domain/pio-317813: gold Method 'extraction step', predicted Method 'extraction' | l bead to the tube. Aliquot 200 µl disrupted tissue for the [[extraction]][[extraction step]]. Pipette 20 µl Proteinase K into a 1.5 ml Lo-Bind tube. Add

### entity/wrong_type

- later-domain/pio-317105: gold Device 'components', predicted Reagent 'components' | acuum filtration apparatus in a clean workspace. Ensure all [[components]][[components]] are sterile before use. Place a Whatman 0.45 µm filter pape
- later-domain/pio-317105: gold Reagent 'volume', predicted Measure-Type 'volume' | o the filtration funnel. Apply vacuum and filter the entire [[volume]][[volume]]. Replace filter paper if it becomes clogged. Using sterile
- later-domain/pio-317105: gold Amount 'appropriate volume', predicted Generic-Measure 'appropriate volume' | and place into a sterile 2 mL microcentrifuge tube. Add an [[appropriate volume]][[appropriate volume]] of 1X PBS to the tube containing the folded filter paper. V
- later-domain/pio-317105: gold Device 'filter paper', predicted Location 'filter paper' | tex for 30–60 seconds to resuspend microbial cells from the [[filter paper]][[filter paper]] into the PBS solution. Proceed with DNA extraction accordin
- later-domain/pio-317813: gold Method 'Pathogen-Agnostic WGS', predicted Reagent 'Pathogen-Agnostic WGS' | [[Pathogen-Agnostic WGS]][[Pathogen-Agnostic WGS]]: An ONT Workflow (Lyssavirus Rabies Part 1 - RNA Extraction
- later-domain/pio-317813: gold Location 'dry ice', predicted Reagent 'dry ice' | microcentrifuge tube. The tissue sample should be placed on [[dry ice]][[dry ice]] after retrieved from the storage and the weighing step must
- later-domain/pio-317813: gold Method 'Homogenisation', predicted Reagent 'Homogenisation' | emperature. Disrupt the tissue with TissueLyser II (QIAGEN) [[Homogenisation]][[Homogenisation]] for 2 min at 25 Hz. Add 1 stainless steel bead to the tube.
- later-domain/pio-317813: gold Speed '25 Hz', predicted Generic-Measure '25 Hz' | ue with TissueLyser II (QIAGEN) Homogenisation for 2 min at [[25 Hz]][[25 Hz]]. Add 1 stainless steel bead to the tube. Aliquot 200 µl dis

### entity/missed

- later-domain/pio-317105: gold Modifier 'Whatman', predicted nothing | pace. Ensure all components are sterile before use. Place a [[Whatman]] 0.45 µm filter paper onto the filtration membrane support u
- later-domain/pio-317105: gold Modifier 'entire', predicted nothing | ple into the filtration funnel. Apply vacuum and filter the [[entire]] volume. Replace filter paper if it becomes clogged. Using s
- later-domain/pio-317105: gold Mention 'it', predicted nothing | acuum and filter the entire volume. Replace filter paper if [[it]] becomes clogged. Using sterile forceps, remove the filter p
- later-domain/pio-317105: gold Modifier 'clogged', predicted nothing | ilter the entire volume. Replace filter paper if it becomes [[clogged]]. Using sterile forceps, remove the filter paper. Fold inwar
- later-domain/pio-317105: gold Action 'Fold', predicted nothing | es clogged. Using sterile forceps, remove the filter paper. [[Fold]] inward (cell-side in) and place into a sterile 2 mL microce
- later-domain/pio-317105: gold Modifier 'inward', predicted nothing | ogged. Using sterile forceps, remove the filter paper. Fold [[inward]] (cell-side in) and place into a sterile 2 mL microcentrifug
- later-domain/pio-317813: gold Method 'ONT Workflow', predicted nothing | Pathogen-Agnostic WGS: An [[ONT Workflow]] (Lyssavirus Rabies Part 1 - RNA Extraction) Weigh 50 mg bra
- later-domain/pio-317813: gold Method 'weighing step', predicted nothing | placed on dry ice after retrieved from the storage and the [[weighing step]] must be carried out swiftly. Add 600 µl 1X DNA/RNA ShieldTM

### entity/wrong_boundary_and_type

- later-domain/pio-317105: gold Modifier 'cell-side in', predicted Method 'cell-side' | sing sterile forceps, remove the filter paper. Fold inward ([[cell-side]][[cell-side in]]) and place into a sterile 2 mL microcentrifuge tube. Add an
- later-domain/pio-317105: gold Method 'manufacturer's instructions', predicted Reagent 'QIAamp® DNA Mini Kit manufacturer's instructions' | PBS solution. Proceed with DNA extraction according to the [[QIAamp® DNA Mini Kit manufacturer's instructions]][[manufacturer's instructions]], using the resuspended PBS as the starting material. Elute
- later-domain/pio-317105: gold Modifier 'as the starting material', predicted Reagent 'material' | Kit manufacturer's instructions, using the resuspended PBS [[as the starting material]][[material]]. Elute the purified DNA in Buffer AE into a clean 1.5 mL mi
- later-domain/pio-223996: gold Reagent 'Autophagosomes', predicted Method 'Isolation of Autophagosomes and Proteinase K Protection Assay' | [[Isolation of Autophagosomes and Proteinase K Protection Assay]][[Autophagosomes]] and Proteinase K Protection Assay Use the following cell lines: HAP1 ATG9A-GFP (RRID:CVCL_E2T
- later-domain/pio-223996: gold Reagent 'Proteinase K', predicted Method 'Isolation of Autophagosomes and Proteinase K Protection Assay' | [[Isolation of Autophagosomes and Proteinase K Protection Assay]][[Proteinase K]] Protection Assay Use the following cell lines: HAP1 ATG9A-GFP (RRID:CVCL_E2T
- later-domain/pio-223996: gold Modifier 'per condition', predicted Method 'condition' | DKO (RRID:CVCL_F0LE) Seed cells in 15 cm dishes (two dishes [[per condition]][[condition]]). Treat cells with: Earle’s Balanced Salt Solution (EBSS).
- later-domain/pio-223996: gold Concentration '100 nanomolar (nM)', predicted Numerical '100', Reagent 'nanomolar', Measure-Type 'nM' | ). Treat cells with: Earle’s Balanced Salt Solution (EBSS). [[100]][[100 nanomolar (nM)]][[nanomolar]] ([[nM]]) Bafilomycin A1 (BafA). Incubate for 02:00:00 prior to harve
- later-domain/pio-223996: gold Time '02:00:00', predicted Generic-Measure '02:00' | SS). 100 nanomolar (nM) Bafilomycin A1 (BafA). Incubate for [[02:00]][[02:00:00]] prior to harvesting. Harvest cells by trypsinization and pe

### relation/missed

- later-domain/pio-317105: gold Place -Using-> forceps; predicted Place -Acts-on-> filter paper; Place -Site-> filtration membrane support; forceps -Mod-Link-> sterile | an workspace. Ensure all components are sterile before use. [[Place]] a Whatman 0.45 µm filter paper onto the filtration membrane support using sterile [[forceps]]. Pour the 1.5 L water sample into the filtration funnel. Ap
- later-domain/pio-317105: gold remove -Using-> forceps; predicted forceps -Mod-Link-> sterile; remove -Acts-on-> filter paper | . Replace filter paper if it becomes clogged. Using sterile [[forceps]], [[remove]] the filter paper. Fold inward (cell-side in) and place into
- later-domain/pio-317105: gold filter paper -Meronym-> tube; predicted Add -Site-> tube; tube -Mod-Link-> containing the folded; filter paper -Mod-Link-> containing the folded; filter paper -Setting-> appropriate volume | centrifuge tube. Add an appropriate volume of 1X PBS to the [[tube]] containing the folded [[filter paper]]. Vortex for 30–60 seconds to resuspend microbial cells from
- later-domain/pio-317813: gold mix -Commands-> pulse-vortexing; predicted pulse-vortexing -Mod-Link-> Thoroughly | the Proteinase K. Add 100 µl Buffer VXL. Close the cap and [[mix]] by [[pulse-vortexing]]. Thoroughly homogenise the sample and the buffer to ensure
- later-domain/pio-223996: gold Use -Using-> HAP1 ATG9A-GFP ATG2 DKO; predicted Use -Acts-on-> cell lines; Use -Acts-on-> HAP1 ATG9A-GFP | olation of Autophagosomes and Proteinase K Protection Assay [[Use]] the following cell lines: HAP1 ATG9A-GFP (RRID:CVCL_E2TR) [[HAP1 ATG9A-GFP ATG2 DKO]] (RRID:CVCL_F0LE) Seed cells in 15 cm dishes (two dishes per
- later-domain/pio-223996: gold dishes -Coreference-Link-> dishes; predicted Seed -Site-> dishes; Seed -Site-> dishes; dishes -Measure-> 15 cm; dishes -Measure-> two | AP1 ATG9A-GFP ATG2 DKO (RRID:CVCL_F0LE) Seed cells in 15 cm [[dishes]] (two [[dishes]] per condition). Treat cells with: Earle’s Balanced Salt Sol
- later-domain/pio-223996: gold Treat -Using-> Earle’s Balanced Salt Solution; predicted Treat -Acts-on-> cells | 0LE) Seed cells in 15 cm dishes (two dishes per condition). [[Treat]] cells with: [[Earle’s Balanced Salt Solution]] (EBSS). 100 nanomolar (nM) Bafilomycin A1 (BafA). Incubate
- later-domain/pio-223996: gold Treat -Using-> Bafilomycin A1; predicted Treat -Acts-on-> cells | 0LE) Seed cells in 15 cm dishes (two dishes per condition). [[Treat]] cells with: Earle’s Balanced Salt Solution (EBSS). 100 nanomolar (nM) [[Bafilomycin A1]] (BafA). Incubate for 02:00:00 prior to harvesting. Harvest

### relation/wrong_attachment

- later-domain/pio-317105: gold Proceed -Using-> PBS; predicted Proceed -Using-> DNA extraction; Proceed -Using-> QIAamp® DNA Mini Kit manufacturer's instructions; PBS -Mod-Link-> resuspended | icrobial cells from the filter paper into the PBS solution. [[Proceed]] with DNA extraction according to the QIAamp® DNA Mini Kit manufacturer's instructions, using the resuspended [[PBS]] as the starting material. Elute the purified DNA in Buffer
- later-domain/pio-317813: gold homogenise -Acts-on-> buffer; predicted homogenise -Acts-on-> sample; homogenise -Mod-Link-> Thoroughly | r VXL. Close the cap and mix by pulse-vortexing. Thoroughly [[homogenise]] the sample and the [[buffer]] to ensure sufficient lysis.
- later-domain/pio-226171: gold prepare -Setting-> 4°C; predicted storage -Setting-> 4°C | h your flow cell to remove the remaining library and either [[prepare]] for another sequencing run or for storage at [[4°C]]. The wash uses the reagents supplied in the ONT wash kit: O
- later-domain/pio-226171: gold Thaw -Acts-on-> Library beads; predicted Thaw -Acts-on-> Sequencing buffer; Thaw -Setting-> room temperature | l Wash Kit Oxford Nanopore Technologies Catalog #EXP-WSH004 [[Thaw]] the Sequencing buffer (SB), [[Library beads]] (LIB), Flow Cell Tether (FCT) and one tube of Flow Cell Flu
- later-domain/pio-226171: gold Thaw -Acts-on-> Flow Cell Tether; predicted Thaw -Acts-on-> Sequencing buffer; Thaw -Setting-> room temperature | l Wash Kit Oxford Nanopore Technologies Catalog #EXP-WSH004 [[Thaw]] the Sequencing buffer (SB), Library beads (LIB), [[Flow Cell Tether]] (FCT) and one tube of Flow Cell Flush (FCF) at room tempera
- later-domain/pio-226171: gold Thaw -Acts-on-> Flow Cell Flush; predicted Thaw -Acts-on-> Sequencing buffer; Thaw -Setting-> room temperature | l Wash Kit Oxford Nanopore Technologies Catalog #EXP-WSH004 [[Thaw]] the Sequencing buffer (SB), Library beads (LIB), Flow Cell Tether (FCT) and one tube of [[Flow Cell Flush]] (FCF) at room temperature then place on ice. Mix the SQB, F
- later-domain/pio-226171: gold Add -Acts-on-> nuclease free water; predicted Add -Acts-on-> sample RNA; Add -Site-> reaction; nuclease free water -Measure-> 5μL | ll, ensuring you add a different barcode for each reaction. [[Add]] 5μL sample RNA to each reaction, and 5μL of [[nuclease free water]] for negative controls, and pipette 5 times to mix Spin down
- later-domain/pio-226171: gold Add -Site-> negative controls; predicted Add -Acts-on-> sample RNA; Add -Site-> reaction | ll, ensuring you add a different barcode for each reaction. [[Add]] 5μL sample RNA to each reaction, and 5μL of nuclease free water for [[negative controls]], and pipette 5 times to mix Spin down for 5 seconds to make

### relation/wrong_label

- later-domain/pio-317105: gold Elute -Using-> Buffer AE; predicted Elute -Acts-on-> DNA; Elute -Site-> Buffer AE; Elute -Site-> microcentrifuge tube | ctions, using the resuspended PBS as the starting material. [[Elute]] the purified DNA in [[Buffer AE]] into a clean 1.5 mL microcentrifuge tube.
- later-domain/pio-223996: gold Use -Using-> cell lines; predicted Use -Acts-on-> cell lines; Use -Acts-on-> HAP1 ATG9A-GFP | olation of Autophagosomes and Proteinase K Protection Assay [[Use]] the following [[cell lines]]: HAP1 ATG9A-GFP (RRID:CVCL_E2TR) HAP1 ATG9A-GFP ATG2 DKO (R
- later-domain/pio-223996: gold Use -Using-> HAP1 ATG9A-GFP; predicted Use -Acts-on-> cell lines; Use -Acts-on-> HAP1 ATG9A-GFP | olation of Autophagosomes and Proteinase K Protection Assay [[Use]] the following cell lines: [[HAP1 ATG9A-GFP]] (RRID:CVCL_E2TR) HAP1 ATG9A-GFP ATG2 DKO (RRID:CVCL_F0LE) S
- later-domain/pio-226171: gold detected -Site-> samples; predicted detected -Acts-on-> sequences; detected -Acts-on-> samples | ination because identical sequences are then unlikely to be [[detected]] in [[samples]] with consecutive barcodes that are adjacent to one another
- later-domain/pio-243070: gold Wash -Using-> PBS; predicted Wash -Acts-on-> PBS; PBS -Mod-Link-> ice-cold | for each sample. Place the plate on ice. Aspirate media. [[Wash]] 2× with ice-cold [[PBS]] (gentle). Add ~950 µL ice-cold PBS+PI (proteomics) or KPB
- later-domain/pio-243070: gold Incubate -Site-> rotator; predicted Incubate -Acts-on-> rotator; Incubate -Setting-> 4 °C; Incubate -Setting-> 10 min; Incubate -Setting-> 3 to 5 min; rotator -Mod-Link-> gentle | 100 µL washed anti-HA beads. Avoid disturbing the pellet. [[Incubate]] on a gentle [[rotator]] at 4 °C for 10 min (proteomics workflow). (Metabolomics w
- later-domain/pio-223979: gold flash-freeze -Site-> liquid nitrogen; predicted flash-freeze -Acts-on-> liquid nitrogen | Wash the pellet once with ice-cold 1× PBS (optional), then [[flash-freeze]] in [[liquid nitrogen]] and store at -80 °C until purification. Resuspend cell pell
- later-domain/pio-223980: gold Flash-freeze -Site-> liquid nitrogen; predicted Flash-freeze -Acts-on-> cell pellets; Flash-freeze -Using-> liquid nitrogen | ells by centrifugation ( 4000 x g, °C, , 00:20:00 , 4 °C ). [[Flash-freeze]] cell pellets in [[liquid nitrogen]] and store at -80 °C . Resuspend cell pellets in ice-cold ly

Not classified automatically: normalization errors and unsupported inferences (need human-checked labels).
