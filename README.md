# Math Games

GitHub-first operating repo for building educational games from concept to fully functional release.

This repo is the migration path away from Taskade as the main operating system. It is designed to become the durable home for game concepts, agent definitions, workflow logic, embedded app code, review artifacts, release candidates, and governance.

The long-term goal is simple:

**take a game from idea → concept packet → prototype → review → release-ready product**  
using a process that is structured, auditable, increasingly autonomous, and able to learn from mistakes, gaps, wins, and iteration history.

## Why this repo exists

A large amount of operational logic, agent structure, workflow orchestration, and app code was living inside Taskade exports. That created five problems:

1. durable knowledge was mixed with temporary operating state
2. code and process were trapped inside export blobs
3. ownership and release governance were unclear
4. automation was harder to validate and version-control
5. Taskade risked becoming a second source of truth

This repo exists to fix that.

It is the place where the system gets normalized, clarified, versioned, and made portable.

## Relationship to `math-game-studio-os`

This repo is not meant to replace `math-game-studio-os`.

The two repos should work together:

### `math-game-studio-os`
Owns the **standards and rules**:
- game design policies
- release rules
- gate definitions
- concept packet discipline
- review/release architecture
- durable educational and quality constraints

### `math-games`
Owns the **operational production layer**:
- Taskade export normalization
- agent roster
- workflow roster
- embedded app extraction
- concept intake
- active game production
- QA audits
- learning captures
- release candidates
- future autonomous game pipeline

A simple way to think about it:

- `math-game-studio-os` defines **how the studio should work**
- `math-games` becomes the place where the studio **actually produces games**

## Current state

This repo currently contains the full exported content from Taskade, including:

- project JSONs
- agent JSONs
- automation JSONs
- manifest metadata
- markdown renderings
- an embedded app/codebase inside `apps/default.json`

That export is preserved as raw evidence and source material. It should not be treated as already-normalized structure.

The migration is still in progress.

## Core principle

**Raw export is not the same thing as canonical structure.**

Just because something exists in a Taskade export does not mean it should become durable truth in this repo.

Everything brought over from Taskade must be classified first.

## What belongs here

This repo is meant to become the durable home for:

- normalized agent definitions
- normalized workflow definitions
- concept inbox and packetization
- review artifacts and audits
- embedded app code extracted into real files
- release candidates and shipped builds
- governance records
- operational queue state
- lessons learned from passes, audits, and failures

## What does not belong here as canonical truth

These may still be stored for provenance, but not promoted blindly:

- raw Taskade exports
- temporary discussion logs
- transient daily task state
- unverified standards claims
- unverified family assignments
- duplicate concept descriptions
- UI chrome or scrape noise from exports
- code trapped in export blobs without extraction and normalization

## Planned repo structure

This is the target structure for the repo as Taskade is phased out:

```text
math-games/
├── README.md
├── docs/
│   ├── system_overview.md
│   ├── operating_model.md
│   ├── release_contract.md
│   ├── migration_plan.md
│   └── governance.md
├── taskade_exports/
│   └── concept-journey-dashboard/
│       ├── manifest.json
│       ├── projects/
│       ├── agents/
│       ├── automations/
│       ├── apps/
│       └── media/
├── agents/
│   ├── registry.json
│   ├── active/
│   ├── deprecated/
│   └── specs/
├── workflows/
│   ├── registry.json
│   ├── active/
│   ├── deprecated/
│   └── contracts/
├── pipeline/
│   ├── stages/
│   ├── gates/
│   ├── schemas/
│   └── templates/
├── concepts/
│   ├── inbox/
│   ├── packetized/
│   └── archived/
├── reviews/
│   ├── active/
│   └── audits/
├── releases/
│   ├── candidates/
│   └── shipped/
├── apps/
│   ├── studio-os/
│   └── extracted/
├── ops/
│   ├── queue.json
│   ├── release_candidates.json
│   ├── governance.json
│   └── decisions.md
└── scripts/
    ├── extract_taskade_export.py
    ├── normalize_agents.py
    ├── normalize_automations.py
    ├── extract_embedded_app.py
    └── validate_release.py
