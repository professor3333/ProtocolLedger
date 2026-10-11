---
title: ProtocolLedger
emoji: 🧪
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Evidence-linked extraction and review of lab protocols
---

# ProtocolLedger demo

Paste an English wet-lab protocol and get a preparation sheet: actions, materials,
quantities, equipment and conditions, each linked to the exact text that supports it.
Unstated objects are routed to review, never guessed. You can correct the output and
export it as JSON or CSV.

- **Model:** [`__MODEL_REPO__`](https://huggingface.co/__MODEL_REPO__), a fine-tuned
  SciBERT span-relation model. Locked-test end-to-end relation F1 is 0.580; see the
  model card for limitations.
- **Code:** [github.com/professor3333/ProtocolLedger](https://github.com/professor3333/ProtocolLedger)
  at commit `__COMMIT__`.
- **This is a public demo.** Saved reviews are kept only until the Space restarts. Do not
  paste confidential or unpublished protocols. Every row is a suggestion for a person to
  review, not an instruction to execute.
