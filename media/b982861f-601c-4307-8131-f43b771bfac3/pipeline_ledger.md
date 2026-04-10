# Data Schema: Pipeline Ledger

**File path:** `artifacts/pipeline_ledger.json`
**Format:** JSON — single array of ledger entries, one entry per concept per pipeline run
**Written by:** Pipeline Orchestrator (manually, at session close)
**Read by:** Pipeline Orchestrator, Build Standards Agent, Prototype Engineer, any session that needs pipeline status

---

## Purpose

`pipeline_ledger.json` is the repo-native source of truth for every gate decision, revision cycle, and pass status across all concepts. It exists because pipeline state otherwise lives only in conversation history and Taskade project fields — neither of which survives a context reset or is queryable across concepts.

**This file is committed to the repo after every session that produces a gate decision, RED flag, or pass status change.**

It does not replace Taskade. It is the durable record Taskade is not designed to be.

---

## Schema

```json
[
  {
    "concept": "Echo Heist",
    "run_id": "2025-01-echo-heist-v1",
    "pipeline_completed": "2025-01-15",
    "current_pass": "P5",
    "current_pass_status": "complete",
    "go_decision": "GO",
    "go_decision_date": "2024-11-01",
    "curriculum_slot": "6.EE, 7.RP, 7.NS — Grades 6–8",
    "interaction_family": "Stealth-Gated Precision Solve",
    "stages": {
      "stage_1": { "status": "pass", "artifact": "artifacts/echo-heist/intake_brief.json", "revisions": 0 },
      "stage_2": { "status": "pass", "artifact": "artifacts/echo-heist/kill_report.json", "revisions": 0 },
      "stage_3": { "status": "pass", "artifact": "artifacts/echo-heist/interaction_decision_memo.json", "revisions": 0 },
      "stage_4": { "status": "pass", "artifact": "artifacts/echo-heist/family_architecture_brief.json", "revisions": 0 },
      "stage_5": { "status": "pass", "artifact": "artifacts/echo-heist/lowest_viable_loop_brief.json", "revisions": 0 },
      "stage_6": { "status": "pass", "artifact": "artifacts/echo-heist/prototype_spec.json", "revisions": 1 },
      "stage_7": { "status": "pass", "artifact": "artifacts/echo-heist/prototype_build_spec.json", "revisions": 0 },
      "stage_8": { "status": "pass", "artifact": "artifacts/echo-heist/prototype_ui_spec.json", "revisions": 0 }
    },
    "build_standards_gate": {
      "overall": "GREEN",
      "co_items": {
        "CO-1": "RESOLVED",
        "CO-2": "RESOLVED",
        "CO-3": "RESOLVED",
        "CO-4": "RESOLVED",
        "CO-5": "RESOLVED",
        "CO-6": "RESOLVED"
      },
      "mg_items": {
        "MG-1": "RESOLVED",
        "MG-2": "RESOLVED",
        "MG-3": "RESOLVED",
        "MG-4": "RESOLVED",
        "MG-5": "RESOLVED",
        "MG-6": "RESOLVED"
      },
      "red_flag_count": 0,
      "second_red_flags": []
    },
    "p0_pass_plan": "artifacts/echo-heist/p0_pass_plan.md",
    "pass_records": [
      { "pass": "P1", "status": "complete", "date": "2024-11-10", "bottleneck": "loop clarity and first-use confusion", "proof_target_met": true },
      { "pass": "P2A", "status": "complete", "date": "2024-11-20", "bottleneck": "end-of-run payoff and replay reason", "proof_target_met": true },
      { "pass": "P2B", "status": "complete", "date": "2024-12-01", "bottleneck": "speed and difficulty tuning", "proof_target_met": true },
      { "pass": "P3", "status": "complete", "date": "2024-12-15", "bottleneck": "game feel and world reaction", "proof_target_met": true },
      { "pass": "P5", "status": "complete", "date": "2025-01-15", "bottleneck": "release readiness and meta systems", "proof_target_met": true }
    ],
    "notes": "Gold-standard reference for Stealth-Gated Precision Solve family. 304 tests, 0 failures."
  }
]
```

---

## Field Reference

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `concept` | string | yes | Canonical concept name — must match Game Concepts Pipeline task title exactly |
| `run_id` | string | yes | Unique identifier for this pipeline run. Format: `YYYY-MM-{concept-slug}-v{n}` |
| `pipeline_completed` | date | yes | ISO date the Stage 8 artifact was produced (or `null` if pipeline did not complete) |
| `current_pass` | string | yes | Current pass label: `"none"`, `"P0"`, `"P1"`, `"P2A"`, `"P2B"`, `"P3"`, `"P4"`, `"P5"`, `"complete"` |
| `current_pass_status` | string | yes | Status within the current pass: `"not_started"`, `"in_progress"`, `"complete"`, `"blocked"` |
| `go_decision` | string | yes | `"GO"`, `"NO-GO"`, `"Revise"`, `"Pause"`, `"Pending"` — matches `@gcf05` in Game Concepts Pipeline |
| `go_decision_date` | date | no | ISO date the GO decision was recorded |
| `curriculum_slot` | string | yes | CCSS/NGSS standards and grade band (e.g. `"6.EE, 7.RP — Grades 6–8"`) |
| `interaction_family` | string | yes | Family name from Game Family Registry |
| `stages` | object | yes | Per-stage status — see Stage Record below |
| `build_standards_gate` | object | yes | Gate result from Build Standards Agent — see Gate Record below |
| `p0_pass_plan` | string | no | Path to the P0 Pass Plan produced by Prototype Engineer at Stage 8.5. `null` if not yet produced |
| `pass_records` | array | yes | One entry per completed pass — see Pass Record below |
| `notes` | string | no | Free-text notes on special status, known gaps, or backfill context |

### Stage Record (one per stage, keyed `stage_1` through `stage_8`)

| Field | Type | Description |
|---|---|---|
| `status` | string | `"pass"`, `"revise"`, `"reject"`, `"not_run"` |
| `artifact` | string | Path to the produced artifact JSON, relative to repo root. `null` if stage did not complete |
| `revisions` | integer | Number of revision cycles before the stage reached `"pass"` |

### Gate Record (`build_standards_gate`)

| Field | Type | Description |
|---|---|---|
| `overall` | string | `"GREEN"`, `"AMBER"`, `"RED"` |
| `co_items` | object | One key per CO item (CO-1 through CO-6). Value: `"RESOLVED"`, `"UNRESOLVED"`, `"UNRESOLVED [SECOND FLAG]"`, `"N/A"` |
| `mg_items` | object | One key per MG item (MG-1 through MG-6). Same value set as CO items |
| `red_flag_count` | integer | Total number of RED flags raised on this concept across all revision cycles |
| `second_red_flags` | array | List of CO/MG item IDs that reached SECOND FLAG status. Empty array if none |

### Pass Record (one per completed pass)

| Field | Type | Description |
|---|---|---|
| `pass` | string | Pass label: `"P0"`, `"P1"`, `"P2A"`, `"P2B"`, `"P3"`, `"P4"`, `"P5"` |
| `status` | string | `"complete"`, `"in_progress"`, `"abandoned"` |
| `date` | date | ISO date the pass was closed |
| `bottleneck` | string | One-line statement of the primary bottleneck this pass targeted |
| `proof_target_met` | boolean | Whether the proof target defined at pass start was met |

---

## Write Rules

These rules are enforced by the Pipeline Orchestrator. An entry must be committed to the ledger before the session closes whenever any of the following occur:

1. **Any gate decision is issued** — stage pass, revise, or reject
2. **A RED flag is raised** — whether first or second
3. **A GO or NO-GO decision is recorded** — for any concept
4. **A pass is opened or closed** — including abandoned passes
5. **A concept's pause status changes** — pause set, pause conditions updated, or re-evaluation triggered

If no gate decision, pass event, or status change occurs in a session, the ledger does not need to be updated.

---

## Backfill

The three approved concepts (Bakery Rush, Fire Dispatch, Unit Circle Pizza Lab) and Echo Heist should be backfilled as the first commit. Use the `"notes"` field to indicate `"backfilled — pre-ledger concept; stage artifact paths may be incomplete"` for any fields that cannot be precisely reconstructed.

Power Grid Operator, School Trip Fleet, Metro Minute, and all other pipeline concepts should be added with `pipeline_completed: null` and `current_pass: "none"` until their pipeline runs complete.

---

## Querying the Ledger

To get current status of all concepts:
```
cat artifacts/pipeline_ledger.json | jq '[.[] | {concept, current_pass, current_pass_status, go_decision, interaction_family}]'
```

To find all concepts with active RED flags:
```
cat artifacts/pipeline_ledger.json | jq '[.[] | select(.build_standards_gate.red_flag_count > 0)]'
```

To find all concepts with no P0 pass plan yet:
```
cat artifacts/pipeline_ledger.json | jq '[.[] | select(.go_decision == "GO" and .p0_pass_plan == null)]'
```
