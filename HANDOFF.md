# HANDOFF — STARK HEIR (cold-start brief)

## 1. WHAT THIS IS
Chronological MCU fanfiction. Mark Howard Stark — Tony's public son, hidden Adaptation-Talent holder with a stabilized X-gene and a growing psychic core. Canon is the spine; the OC braids around it with absolute canon ownership.

## 2. THE LIVE EDGE
**V1 epoch retired by user order (2026-10-24). Zero live chapters in `chapters/`.** V2 rebuild pending: Chapter One under N-law. The canon trove (receipts/coverage for IM1 beats 1–23), continuity ledger, and style autopsy are preserved in records — build from those, never from archived prose.

## 3. STATE OWNERS (single sources, never duplicate)
- Live state: `foundation/STATUS_PANEL.md` (§0 LIVE)
- Machine mirror: `foundation/CURRENT_STATE_MANIFEST.json`
- Canon coverage/receipts per chapter: `canon_coverage/`
- Full head-card apparatus: archived in those coverage files
- Event ledger: `foundation/SERIAL_LOG.md`

## 4. THE LAWS
`foundation/CROSS_PROJECT_LAW.md` — P1–P15 + P12-AMENDMENT. `foundation/STYLE_GUIDE_NATURAL.md` — N-law (binding 2026-10-24): plain short sentences; Mark writes like a real twelve-year-old; butterflies grow as plot behavior, never announced; banned craft-words in prose. Bible §2 canon words; §16 map authority. Desk protocol (AGENTS.md → the-authors-desk): base revision + baseline gate before edits; small authorized changes; push without force.

## 5. THE GATES
`python3 tools/mcu_verify.py` — must exit PASS. Hard style law effective 2026-10-12: sentences ≤60 words; zero digits in prose (card content inside the status fence is exempt); zero CJK; each chapter opens with a COMPACT 4-line ◆ STATUS card (status / CANON SOURCE / NEW+butterflies+NEXT / FULL CARD pointer). CI runs the same verifier on every push (`.github/workflows/style-gate.yml`).

## 6. CONVENTIONS
- "Next" from the user → compose the next chapter: receipts → coverage entry → predraft audit → draft → self-check + garble scan → gates → records → push.
- No force-push. Fetch remote before composing (upstream audits may land).
- Composition caps: ≤60-word sentences; digits may appear only inside the fenced card; CJK nowhere.
