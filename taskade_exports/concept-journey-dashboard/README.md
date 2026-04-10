# Concept Journey Dashboard — Raw Taskade Export

This folder holds **raw, unprocessed export material** from the Taskade space `Concept Journey Dashboard` (space ID `63ifx7l9wtgfvsop`), captured from the `production` environment on `2026-04-10T14:51:53.528Z`.

It is preserved **for provenance only**.

## What this folder is

- A verbatim snapshot of one specific Taskade space, captured at one specific moment.
- The source material from which this repo's normalized, canonical systems (`agents/`, `workflows/`, `pipeline/`, `concepts/`, `reviews/`, `releases/`, `apps/`) will be derived as normalization work is performed.
- The evidence trail that any normalized artifact can be traced back to.

## What this folder is NOT

- It is **not** the canonical normalized system of this repo.
- It is **not** a source of truth for durable operating rules, agent definitions, workflow definitions, or game state.
- It is **not** authoritative for any governance claim (ownership, standards alignment, release readiness, shipped status) unless that claim has been independently promoted into a durable repo-native location.
- It is **not** exhaustive — it is one snapshot at one timestamp, and the live Taskade space may already have diverged.

## Rules for files in this folder

1. **Do not edit files here in place** except during explicit export-normalization work. If a file here is wrong, the fix belongs in the normalized repo-native location, not here.
2. **Do not delete files here** without also recording why in the commit message.
3. **When refreshing** with a new Taskade export of the same space, replace the contents of this folder wholesale — do not patch files in place.
4. **Treat every CCSS claim, grade-band claim, family placement, and ownership claim** found inside these files as Taskade-side claims only, not repo-validated facts, until they are explicitly promoted into a durable repo-native location.

## Where normalized repo-native content lives

The durable repo-native structure is described in this repo's top-level `README.md` under "Planned repo structure". As normalization work progresses, durable content derived from this export will land in those directories — not here.

## Architecture split

This repo (`math-games`) is the **operational production repo**. It owns raw Taskade export material, normalized agent and workflow rosters, extracted app code, the concept inbox and packetization pipeline, audits, release candidates, and shipped games.

The separate `math-game-studio-os` repo is the **standards and policy repo**. It owns game design policies, gate definitions, release rules, concept packet discipline, educational constraints, and evaluation logic.

Raw export material in this folder must not make policy claims. Policy claims live in `math-game-studio-os`. When in doubt, err toward preserving the material here verbatim and promoting it through the right channel elsewhere.

## Snapshot metadata

| Field | Value |
|---|---|
| **Taskade space name** | `Concept Journey Dashboard` |
| **Taskade space ID** | `63ifx7l9wtgfvsop` |
| **Taskade space emoji** | 🔥 |
| **Taskade space visibility** | `collaborator` |
| **Source environment** | `production` |
| **Exported at** | `2026-04-10T14:51:53.528Z` |
| **Export format version** | `1.0` |
| **Original publish location** | `github.com/Sovereigndwp/math-games` (repo root) |

## Contents overview

| Path | Kind | Role |
|---|---|---|
| `manifest.json` | file | Authoritative space metadata from the Taskade export |
| `projects/` | 24 project JSON files | Each file is one Taskade project (Quill delta tree format) |
| `agents/` | 17 agent JSON files | Taskade agent definitions by Taskade agent ID (14 active + 3 deprecated) |
| `automations/` | 15 workflow JSON files | Taskade automation / flow definitions |
| `apps/` | 1 file (`default.json`, 1.1 MB) | Embedded Taskade App virtual filesystem — contains source code of the parallel "Studio OS" React application that was running inside Taskade at export time |
| `media/` | 74 files | Media references and sidecar metadata from the export |
