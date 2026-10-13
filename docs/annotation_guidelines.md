# Annotation guidelines

How to write gold labels for the later-domain and challenge sets. The schema is the
WNUT-2020 wet-lab schema: 18 entity types and 14 relation types. Where the original
guidelines leave a choice open, these rules follow what the **cleaned training split**
does most often. Each rule gives its train count, so an inconsistent rule can be seen as
one. Counts come from `train` after deduplication (314 protocols).

## Ground rules

1. **Annotate from scratch.** Use the "Annotate from scratch" mode, which never calls a
   model. Do not open `machine_labels.jsonl`, `machine_specs/`, or any
   `reports/annotation_sets/*-errors.md` for a set you are still annotating: they show
   machine labels, and gold copied from them is not gold.
2. **Label what the text says.** Never add an entity for something that is only implied.
   An Action with no stated object stays without `Acts-on`: 2,990 of 10,472 train
   Actions (29%) have neither `Acts-on` nor `Site`. The interface shows such rows as
   "Not explicitly stated".
3. **Spans are exact character ranges of the raw text.** Do not include surrounding
   spaces or punctuation that is not part of the expression.
4. **Load files with the upload button**, never by pasting. Gold is matched to its source
   by a hash of the exact text, and pasting can change Unicode spaces.
5. **Choose every type, direction and relation label explicitly.** In from-scratch mode
   the interface has no defaults; the line next to "Add relation" shows exactly what
   will be created (`head —label→ tail`).
6. **When a case is not covered here, decide, then record the decision** at the end of
   this file, with an example. Apply it from then on. Earlier documents are not edited;
   the repeat pass measures how stable the rules are.

## Workflow

1. Start the interface (see the README, "New annotation sets").
2. Tick **Annotate from scratch**, upload `data/annotation/<set>/texts/<id>.txt`, and press
   **Start annotating**.
3. Go line by line. For each line, add its entities first, then their relations.
4. Tick **Store the protocol text on the server** and save the review. Saving the same text
   again replaces the earlier annotation in the export (the most recent review wins).
5. To continue later, open **Open a saved review** under the protocol text: reviews saved
   from this browser are listed, and saving after opening adds a new revision. If the
   browser has forgotten a review (cleared storage, another machine), issue a new token
   from the database and paste the printed ID and token:
   `uv run python scripts/reopen_review.py --db data/annotation.db --text-file <the .txt>`
6. Back up the database after each session:
   `uv run python scripts/backup_reviews.py backup data/annotation.db backups/annotation-<date>.db`

## Entities

| Type | What it marks | Train | Most frequent in train |
|---|---|---:|---|
| Action | an operation the protocol tells you to do | 10,472 | add, incubate, mix, remove, centrifuge, place, wash, transfer |
| Reagent | a substance, sample or biological material | 9,625 | cells, supernatant, sample, ethanol, DNA, beads, pellet, PBS |
| Modifier | a word that qualifies another entity | 3,860 | each, gently, carefully, sterile, new, at least, thoroughly |
| Location | a container or place where material is | 3,387 | tube, plate, tubes, ice, well, column, slides |
| Amount | a quantity of material (volume, mass) | 2,955 | 1 ml, 100 µl, 1.5 ml, 5 ml |
| Time | a duration or point in time | 2,032 | 5 minutes, overnight, 30 seconds, 10 min |
| Device | an instrument or piece of equipment | 1,470 | filter, magnetic stand, thermocycler, syringe, pump |
| Temperature | a temperature, including symbolic ones | 1,368 | room temperature, 4°C, 37°C, -20°C, RT |
| Method | a named technique or procedure | 1,360 | up and down, incubation, extraction, centrifugation, pipetting |
| Concentration | a concentration or dilution | 1,200 | 1x, 70%, 10 mM, 2x |
| Measure-Type | the name of a measured property | 713 | volume, concentration, purity, yield, density |
| Numerical | a bare count | 706 | 3, two, one, twice, several |
| Speed | a centrifugation or shaking speed | 518 | 14,000 x g, 10,000 rpm, maximum speed |
| Generic-Measure | any other measurement | 445 | 100 V, 1:2000, 140 bp, several times |
| Size | a physical dimension, pore or mesh size | 232 | 0.2 µm, 12 x 75 mm, 70 µm |
| Mention | a pronoun or reference to an earlier entity | 219 | it, them, this, they, these |
| Seal | something that closes or covers a container | 181 | lid, cap, parafilm, aluminum foil |
| pH | a pH value | 63 | pH 8.0, pH 7.5 |

## Relations

Direction is always **head → tail** as listed. Share = how often train uses that head and
tail pair for the relation.

| Relation | Meaning | Head → tail (train share) | Train example |
|---|---|---|---|
| Acts-on | the thing an Action operates on | Action → Reagent 75%, Location 16%, Device 5%, Mention 2% | Thaw → kit components |
| Measure | a material or container and its quantity | Reagent → Amount 52%, Reagent → Concentration 24%, Location → Amount 7%, Reagent → Numerical 4% | nuclease-free water → 30 μl |
| Setting | a condition of an Action | Action → Time 44%, Temperature 29%, Speed 11%, Generic-Measure 3% | Incubate → 2 hours |
| Mod-Link | an entity and its Modifier | Reagent 36%, Action 30%, Location 16%, Amount 5% → Modifier | Mix → thoroughly |
| Site | where an Action happens or puts things | Action → Location 60%, Reagent 26%, Device 13% | collect → bottoms |
| Using | what an Action is done with | Action → Reagent 40%, Method 29%, Device 22% | grind → blue pestle |
| Meronym | a part and the whole it belongs to | Reagent → Reagent 44%, Reagent → Location 22%, Location → Location 15% | bottoms → tubes |
| Or | two alternatives | same type on both sides, earlier → later | 16°C → room temperature |
| Measure-Type-Link | an Action and the property it measures or sets | Action → Measure-Type 100% | minimize → amount |
| Count | how many times an Action is done | Action → Numerical 100% | pipetting → 10 |
| Product | what an Action produces | Action → Reagent 100% | collect → solutions |
| Coreference-Link | a reference and what it refers to | Mention → Reagent 36%, Reagent → Reagent 18%, Mention → Location 13% | it → tube |
| Commands | an Action that directs another Action | Action → Action 100% | Mix → pipetting |
| Of-Type | a value and the property it is a value of | Generic-Measure 65%, Numerical 35% → Measure-Type | 1% → v/v |

A pair of entities may carry more than one relation when the text supports both.

## Span conventions

| Case | Rule | Train evidence |
|---|---|---|
| Value and unit | One span: `5 mL`, `37 °C`, `14,000 x g` (Speed includes `x g`) | Speed spans with `x g`: 226 |
| Ranges | One span: `5–10 min`, `100-200 mg` | 354 quantity spans contain a range |
| "~", "approximately", "up to", "within", "about" | Outside the quantity span; label `30 min`, not `up to 30 min` | words outside 131, inside 28; `~` outside 64 |
| Adjectives before a material | A separate Modifier linked with `Mod-Link`: `sterile` + `tube` | separate 1,418, inside the name 526 |
| Negation ("not", "do not") | Leave unlabelled; label the Action itself | unlabelled 144 of 198 |
| "it", "them" after an Action | Label as Mention; add `Coreference-Link` only when the referent is in the text | Mention in 90 of 109 |
| "room temperature", "RT" | Temperature | 350 and 41 |
| "overnight" | Time | 104 of 119 |
| Vendor names and catalog numbers | Outside the span: `Proteinase K` in `Proteinase K (NEB, P8107S)` | train is split (51 inside, 57 outside); this guide chooses outside |
| Multi-word Actions | Label the verb alone; in `pipette up and down`, `up and down` is a Method | 614 of 10,472 Actions are multi-word; `up and down` is the most frequent Method |
| Titles | Nouns such as `Preparation`, `Isolation`, `Extraction` are Methods with no relations; "-ing" words such as `Isolating` are Actions | "-tion" title words: 102 Method, 1 Action; "-ing": 45 Action, 11 Method |
| `Or` direction | From the earlier mention to the later one | 341 of 408 |
| Quantity direction | Always from the material to the quantity, whatever the word order | quantity is the tail in 4,453 of 4,459 `Measure` links; it precedes its material in 3,825 |
| Lists written amount first ("250 µL, of the NTP buffer mix") | Link each amount to the material that follows it | |
| Discontinuous expressions | The interface cannot store them; label the contiguous core and record the case | |

## Decisions log

Add one entry per new decision: the date, the rule, and one example (set, id, text).

- *(none yet)*
