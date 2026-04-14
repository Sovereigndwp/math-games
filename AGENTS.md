# AGENTS.md — math-games

This repo is the **production layer** of the math-games studio. It owns the operational pipeline that moves a game from raw concept to release-ready artifact.

The companion repo `math-game-studio-os` owns standards and rules. When the two conflict, `math-game-studio-os` wins.

---

## What this repo owns

- Agent and workflow definitions (normalized from Taskade exports)
- Per-slug artifact chains under `generated/`
- JSON Schema 2020-12 definitions under `schemas/`
- Taxonomy files under `taxonomy/`
- Validation and pipeline scripts under `scripts/`
- Built game files under `games/<slug>/` (one folder per game slug)
- QA and feel audit documents under `reviews/<slug>/`
- Reference documentation and design standards under `docs/`

---

## The artifact chain

Each game slug has up to 8 artifacts, in this order:

```
generated/requests/<slug>/project_config.real.json     (PC)
generated/requests/<slug>/concept_brief.real.json      (CB)
generated/requests/<slug>/generation_request.real.json (GR)
generated/requests/<slug>/promotion_request.real.json  (PR)
generated/drafts/<slug>/concept_packet.draft.json      (D)
generated/drafts/<slug>/concept_packet.manifest.json   (M)
generated/review/<slug>/concept_packet.review.json     (RV)
generated/review/<slug>/promotion_record.json          (RC)
```

Phases map to presence of files:

| Observed phase         | Files present         |
|------------------------|-----------------------|
| `empty`                | none                  |
| `initialized`          | PC + CB               |
| `generation_requested` | + GR                  |
| `drafted`              | + D + M               |
| `promotion_requested`  | + PR                  |
| `reviewed`             | + RV + RC             |

**Do not skip steps.** Each phase creates the foundation for the next. A broken chain produces a `partial` phase with warnings.

---

## Scripts reference

All scripts live in `scripts/`. Run from the repo root with `python3 scripts/<script>.py`.

| Script | What it does | Writes to |
|--------|-------------|-----------|
| `new_game_init.py` | Create PC + CB for a new slug | `generated/requests/<slug>/` |
| `phase_router.py` | Read-only phase inspector. Always run this first. | nothing |
| `validate_schemas.py` | Validate all schemas are valid Draft 2020-12 and examples validate | nothing |
| `check_crossrefs.py` | Check 12 cross-reference invariants across example fixtures | nothing |
| `build_generation_request.py` | Build a generation_request file | `generated/requests/<slug>/` |
| `generate_concept_packet_stub.py` | Generate draft + manifest from a generation_request | `generated/drafts/<slug>/` |
| `build_promotion_request.py` | Build a promotion_request file | `generated/requests/<slug>/` |
| `promote_draft_stub.py` | Promote a draft to review (creates RV + RC) | `generated/review/<slug>/` |
| `advance_to_packet.py` | Advance project_config.current_phase to packet | `generated/requests/<slug>/` |
| `advance_to_review.py` | Advance project_config.current_phase to review | `generated/requests/<slug>/` |
| `set_phase.py` | Manually set project_config.current_phase | `generated/requests/<slug>/` |
| `check_project_config.py` | Validate a specific project_config file | nothing |
| `backfill_project_config.py` | Create a PC for a legacy slug missing one | `generated/requests/<slug>/` |

---

## Agent rules

### Before doing anything with a slug

Run `phase_router.py` first:

```bash
python3 scripts/phase_router.py --slug <slug>
```

This tells you the observed phase, configured phase, next action, and any chain warnings. Do not guess the current state — read it.

### Writing files

- **Only write inside `generated/`**. Never touch `schemas/`, `taxonomy/`, `README.md`, `requirements.txt`, `.gitignore`, or `taskade_exports/`.
- All JSON output must use canonical format: sorted keys, 2-space indent, trailing newline.
- Always self-validate against the schema in memory before writing. If validation fails, exit without writing.
- Scripts are strictly additive. They exit 1 if the target file or directory already exists.
- Use `--dry-run` when a script supports it before committing to a write.

### Slug conventions

Slugs must match `^[a-z0-9]+(-[a-z0-9]+)*$`, 2–64 characters. Examples: `place-value-pop-mini`, `snack-line-shuffle`. The slug is not locked until packetization.

### Schema and taxonomy rules

- Schemas are in `schemas/` as Draft 2020-12 JSON files. Do not edit schemas without understanding the downstream impact on every existing `generated/` artifact.
- `taxonomy/interaction_types.yaml` and `taxonomy/families.yaml` are the only authoritative taxonomy sources in this repo.
- `interaction_type_candidate` on a brief must match an `id` in `taxonomy/interaction_types.yaml` or be the literal string `"unresolved"`.
- `family_candidate` is free-form until a family is formally registered. Do not promote a family into `taxonomy/families.yaml` without a formal concept packet as evidence.

### Placeholder fields

`new_game_init.py` creates briefs with `[INITIALIZER PLACEHOLDER]` in all fields that require human authorship. These are intentional and schema-valid. Do not mistake them for real content. All placeholder fields must be rewritten by a human author before `status` advances from `"draft"`.

### What agents must not do

- Do not skip chain steps (e.g., create a draft before a generation_request exists).
- Do not create a `generated/drafts/<slug>/` or `generated/review/<slug>/` directory manually — those are created by the generator and promoter scripts only.
- Do not promote Taskade-authored family names or concept descriptions as canonical without repo-native evidence.
- Do not infer phase state from file names — always use `phase_router.py`.
- Do not write outside `generated/` for any reason.

---

## Running validation

After any write, run both checks to confirm chain integrity:

```bash
python3 scripts/validate_schemas.py
python3 scripts/check_crossrefs.py
```

Exit codes: `0` = pass, `1` = validation failure, `2` = setup/environment error.

---

## Dependency

The only external dependency is `jsonschema>=4.18`:

```bash
pip install -r requirements.txt
```

`check_crossrefs.py` and `phase_router.py` use stdlib only.
