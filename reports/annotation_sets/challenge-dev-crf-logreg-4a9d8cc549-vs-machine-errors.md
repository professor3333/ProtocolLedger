# Error analysis: crf-logreg-4a9d8cc549 on challenge (dev, vs. machine labels)

## Entities (218 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 134 | 61.5% |
| wrong type | 21 | 9.6% |
| wrong boundary | 23 | 10.5% |
| wrong boundary and type | 18 | 8.3% |
| missed | 22 | 10.1% |

## Relations (145 gold)

| Category | Count | Share |
|---|---:|---:|
| correct | 52 | 35.9% |
| endpoint error | 79 | 54.5% |
| wrong label | 1 | 0.7% |
| wrong attachment | 1 | 0.7% |
| missed | 12 | 8.3% |

Spurious entities (no overlapping gold): Reagent 23, Action 18, Modifier 9, Location 7, Method 6, Numerical 3, Measure-Type 1, Mention 1

Spurious relations: 9 between gold entities, 61 with a spurious endpoint.

## Slices

| Reagent names | Gold | Recall |
|---|---:|---:|
| seen in training | 22 | 0.773 |
| unseen in training | 28 | 0.607 |

## Examples

### entity/wrong_type

- challenge/pio-241749: gold Method 'MPLEx', predicted Reagent 'MPLEx' | Preparation of Lung Tissue Blocks for [[MPLEx]][[MPLEx]] Place the sample in the cryostat (allow to thermally equili
- challenge/pio-241749: gold Numerical '2x', predicted Concentration '2x' | n the cryostat (allow to thermally equilibrate ~20 min) Cut [[2x]][[2x]] sections (50 μm) and place sections in pre-weighed 2 mL Sor
- challenge/pio-241749: gold Reagent 'punches', predicted Location 'punches' | punch 2 tissue cores from each tissue section and place the [[punches]][[punches]] in pre-weighed 2 mL Sorenson MµlTI™ SafeSeal™ Microcentrifu
- challenge/pio-126304: gold Method 'Immunofluorescence staining', predicted Action 'Immunofluorescence staining' | [[Immunofluorescence staining]][[Immunofluorescence staining]] Incubate 00:20:00 at Room temperature . For cells expressin
- challenge/pio-126304: gold Time '00:20:00', predicted Generic-Measure '00:20:00' | Immunofluorescence staining Incubate [[00:20:00]][[00:20:00]] at Room temperature . For cells expressing light sensitive
- challenge/pio-126304: gold Location 'coverslips', predicted Seal 'coverslips' | light. Perform the following washes with 1× PBS: Remove the [[coverslips]][[coverslips]] from the plate and gently put it upside-down on the antibod
- challenge/pio-126304: gold Modifier 'upside-down', predicted Method 'upside-down' | PBS: Remove the coverslips from the plate and gently put it [[upside-down]][[upside-down]] on the antibody drop.
- challenge/pio-321801: gold Method 'PCR', predicted Reagent 'PCR' | Preparation of Encoding Probes SOP005.v1.7 ([[PCR]][[PCR]], In-vitro Transcription, Reverse Transcription Alkaline Hyd

### entity/missed

- challenge/pio-241749: gold Action 'allow', predicted nothing | g Tissue Blocks for MPLEx Place the sample in the cryostat ([[allow]] to thermally equilibrate ~20 min) Cut 2x sections (50 μm) a
- challenge/pio-241749: gold Modifier 'thermally', predicted nothing | Blocks for MPLEx Place the sample in the cryostat (allow to [[thermally]] equilibrate ~20 min) Cut 2x sections (50 μm) and place sect
- challenge/pio-241749: gold Action 'equilibrate', predicted nothing | MPLEx Place the sample in the cryostat (allow to thermally [[equilibrate]] ~20 min) Cut 2x sections (50 μm) and place sections in pre-
- challenge/pio-241749: gold Action 'Use', predicted nothing | centrifuge Tubes VWR International (Avantor) Catalog #53550 [[Use]] a Rapid-Core Sampling Punch - 4 mm Ted Pella Inc. Catalog #
- challenge/pio-321801: gold Method 'cycle steps 2 through 5', predicted nothing | nscription Alkaline Hydrolysis & Probe Concentration Repeat [[cycle steps 2 through 5]] from step 3 until the rate at which the sample amplificatio
- challenge/pio-229673: gold Modifier 'optional', predicted nothing | , add Hoechst 33342 to 1 µg/mL. Add phenol-red-free medium ([[optional]]) for imaging. Find Cytoplasm around each nucleus using 568
- challenge/pio-241598: gold Reagent '12S', predicted nothing | OceanOmics Centre: [[12S]], 16S and COI Metabarcoding of Marine Vertebrates In the att
- challenge/pio-241598: gold Action 'enter', predicted nothing | oding of Marine Vertebrates In the attached Input_Template, [[enter]] all required samples in the Metadata tab and assign each on

### entity/wrong_boundary

- challenge/pio-241749: gold Location 'Sorenson MµlTI™ SafeSeal™ Microcentrifuge Tubes', predicted Location 'Sorenson MµlTI™ SafeSeal™ Microcentrifuge Tubes VWR International' | 2x sections (50 μm) and place sections in pre-weighed 2 mL [[Sorenson MµlTI™ SafeSeal™ Microcentrifuge Tubes]][[Sorenson MµlTI™ SafeSeal™ Microcentrifuge Tubes VWR International]] (Avantor) Catalog #53550 Use a Rapid-Core Sampling Punch -
- challenge/pio-241749: gold Location 'Sorenson MµlTI™ SafeSeal™ Microcentrifuge Tubes', predicted Location 'Sorenson MµlTI™ SafeSeal™ Microcentrifuge Tubes VWR International' | ch tissue section and place the punches in pre-weighed 2 mL [[Sorenson MµlTI™ SafeSeal™ Microcentrifuge Tubes]][[Sorenson MµlTI™ SafeSeal™ Microcentrifuge Tubes VWR International]] (Avantor) Catalog #53550 *Note: When punching the tissue co
- challenge/pio-241749: gold Action 'avoid', predicted Action 'avoid regions' | ntor) Catalog #53550 *Note: When punching the tissue cores, [[avoid]][[avoid regions]] with OCT, as this can be difficult to remove from the sampl
- challenge/pio-321801: gold Reagent 'Encoding Probes', predicted Reagent 'Encoding Probes SOP005.v1.7' | Preparation of [[Encoding Probes]][[Encoding Probes SOP005.v1.7]] (PCR, In-vitro Transcription, Reverse Transcription Alkalin
- challenge/pio-321801: gold Method 'Reverse Transcription', predicted Method 'Reverse Transcription Alkaline Hydrolysis & Probe Concentration' | f Encoding Probes SOP005.v1.7 (PCR, In-vitro Transcription, [[Reverse Transcription]][[Reverse Transcription Alkaline Hydrolysis & Probe Concentration]] Repeat cycle steps 2 through 5 from step 3 until the rate a
- challenge/pio-321801: gold Method 'Alkaline Hydrolysis', predicted Method 'Reverse Transcription Alkaline Hydrolysis & Probe Concentration' | f Encoding Probes SOP005.v1.7 (PCR, In-vitro Transcription, [[Reverse Transcription Alkaline Hydrolysis & Probe Concentration]][[Alkaline Hydrolysis]] & Probe Concentration Repeat cycle steps 2 through 5 from step 3 until the rate a
- challenge/pio-321801: gold Method 'Probe Concentration', predicted Method 'Reverse Transcription Alkaline Hydrolysis & Probe Concentration' | f Encoding Probes SOP005.v1.7 (PCR, In-vitro Transcription, [[Reverse Transcription Alkaline Hydrolysis & Probe Concentration]][[Probe Concentration]] Repeat cycle steps 2 through 5 from step 3 until the rate a
- challenge/pio-321801: gold Reagent 'RNasin Plus', predicted Reagent 'RNasin' | rovided with the Quick HiScribe T7 polymerase kit 25 µL, of [[RNasin]][[RNasin Plus]] 25 µL, T7 polymerase (from the same HiScribe kit) If vacuum

### entity/wrong_boundary_and_type

- challenge/pio-241749: gold Device 'Rapid-Core Sampling Punch', predicted Modifier 'Rapid-Core', Method 'Sampling Punch - 4 mm Ted Pella Inc' | fuge Tubes VWR International (Avantor) Catalog #53550 Use a [[Rapid-Core]][[Rapid-Core Sampling Punch]][[Sampling Punch - 4 mm Ted Pella Inc]]. Catalog #15115-10 to punch 2 tissue cores from each tissue
- challenge/pio-241749: gold Size '4 mm', predicted Method 'Sampling Punch - 4 mm Ted Pella Inc' | VWR International (Avantor) Catalog #53550 Use a Rapid-Core [[Sampling Punch - 4 mm Ted Pella Inc]][[4 mm]] Ted Pella Inc. Catalog #15115-10 to punch 2 tissue cores from each tissue
- challenge/pio-241749: gold Location 'regions', predicted Action 'avoid regions' | ntor) Catalog #53550 *Note: When punching the tissue cores, [[avoid regions]][[regions]] with OCT, as this can be difficult to remove from the sampl
- challenge/pio-126304: gold Modifier 'light sensitive', predicted Method 'expressing light sensitive fluorescent proteins' | staining Incubate 00:20:00 at Room temperature . For cells [[expressing light sensitive fluorescent proteins]][[light sensitive]] fluorescent proteins, cover the 24 well plate with aluminum foil to block out am
- challenge/pio-126304: gold Reagent 'fluorescent proteins', predicted Method 'expressing light sensitive fluorescent proteins' | staining Incubate 00:20:00 at Room temperature . For cells [[expressing light sensitive fluorescent proteins]][[fluorescent proteins]], cover the 24 well plate with aluminum foil to block out am
- challenge/pio-321801: gold Reagent 'in vitro template', predicted Method 'in vitro template created in Part 1.' | sh 1.7 mL Eppendorf tube, mix the following: 160 µL, of the [[in vitro template]][[in vitro template created in Part 1.]] 176 µL, of nuclease free water 250 µL, of the NTP buffer mi
- challenge/pio-321801: gold Reagent 'HiScribe kit', predicted Device 'same HiScribe kit' | se kit 25 µL, of RNasin Plus 25 µL, T7 polymerase (from the [[same HiScribe kit]][[HiScribe kit]]) If vacuum concentrator isn’t available, concentrate probe
- challenge/pio-229673: gold Reagent 'LysoTracker® Red DND-99', predicted Method 'LysoTracker® Red DND-99 Live-Cell Staining  26 HCS Analysis' | Protocol — [[LysoTracker® Red DND-99]][[LysoTracker® Red DND-99 Live-Cell Staining  26 HCS Analysis]] During the final 10 min, add Hoechst 33342 to 1 µg/mL. Add

### relation/wrong_attachment

- challenge/pio-241749: gold sections -Measure-> 50 μm; predicted Cut -Acts-on-> sections; sections -Measure-> 2x | he cryostat (allow to thermally equilibrate ~20 min) Cut 2x [[sections]] ([[50 μm]]) and place sections in pre-weighed 2 mL Sorenson MµlTI™ Saf

### relation/missed

- challenge/pio-321801: gold mix -Acts-on-> nuclease free water; predicted nuclease free water -Measure-> 176 µL; nuclease free water -Measure-> 250 µL | (generally 15-20 cycles). In a fresh 1.7 mL Eppendorf tube, [[mix]] the following: 160 µL, of the in vitro template created in Part 1. 176 µL, of [[nuclease free water]] 250 µL, of the NTP buffer mix provided with the Quick HiScr
- challenge/pio-321801: gold mix -Acts-on-> NTP buffer mix; predicted NTP buffer mix -Measure-> 250 µL | (generally 15-20 cycles). In a fresh 1.7 mL Eppendorf tube, [[mix]] the following: 160 µL, of the in vitro template created in Part 1. 176 µL, of nuclease free water 250 µL, of the [[NTP buffer mix]] provided with the Quick HiScribe T7 polymerase kit 25 µL, o
- challenge/pio-321801: gold mix -Acts-on-> T7 polymerase; predicted T7 polymerase -Measure-> 25 µL | (generally 15-20 cycles). In a fresh 1.7 mL Eppendorf tube, [[mix]] the following: 160 µL, of the in vitro template created in Part 1. 176 µL, of nuclease free water 250 µL, of the NTP buffer mix provided with the Quick HiScribe T7 polymerase kit 25 µL, of RNasin Plus 25 µL, [[T7 polymerase]] (from the same HiScribe kit) If vacuum concentrator isn’t a
- challenge/pio-321801: gold mix -Site-> Eppendorf tube; predicted Eppendorf tube -Measure-> 1.7 mL; Eppendorf tube -Mod-Link-> fresh | reach a plateau (generally 15-20 cycles). In a fresh 1.7 mL [[Eppendorf tube]], [[mix]] the following: 160 µL, of the in vitro template created in
- challenge/pio-229673: gold add -Setting-> 10 min; predicted 10 min -Mod-Link-> final; add -Acts-on-> Hoechst 33342 | DND-99 Live-Cell Staining  26 HCS Analysis During the final [[10 min]], [[add]] Hoechst 33342 to 1 µg/mL. Add phenol-red-free medium (optio
- challenge/pio-229673: gold Hoechst 33342 -Measure-> 1 µg/mL; predicted add -Acts-on-> Hoechst 33342 | Cell Staining  26 HCS Analysis During the final 10 min, add [[Hoechst 33342]] to [[1 µg/mL]]. Add phenol-red-free medium (optional) for imaging. Find Cy
- challenge/pio-241598: gold well -Measure-> 12 µL; predicted nothing | ftware, survey the plates, ensuring that the volume in each [[well]] is between [[12 µL]] and 65 µL. If the value is too low, prepare a new plate, if
- challenge/pio-241598: gold well -Measure-> 65 µL; predicted nothing | ftware, survey the plates, ensuring that the volume in each [[well]] is between 12 µL and [[65 µL]]. If the value is too low, prepare a new plate, if the value

### relation/wrong_label

- challenge/pio-228894: gold Lay -Site-> Kimwipe; predicted Lay -Acts-on-> it; Lay -Using-> Kimwipe | emove the incubation frame cover and clean it with ethanol. [[Lay]] it on a [[Kimwipe]] until ready for use. Flick probes and use a mini centrifuge

Not classified automatically: normalization errors and unsupported inferences (need human-checked labels).
