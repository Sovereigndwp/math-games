# Taskade Workflows

This folder documents the Taskade automation layer of the Math Game Studio OS.

The Python pipeline (`pipeline.py`) and the Taskade layer are two distinct systems.
They serve different purposes, run in different contexts, and are not interchangeable.
This document explains how they relate and when to use each one.

---

## What the Taskade Layer Is

The Python pipeline processes a single concept through a fixed sequence of stages.
It is deterministic, gateable, and testable. It runs from a terminal.

The Taskade layer handles everything that happens around and between pipeline runs:

- **Concept intake and routing** — a concept enters as a Taskade task, not a CLI argument
- **GO/NO-GO decisions** — tracked per concept, recorded in a project board, visible at a glance
- **Post-GO orchestration** — misconception mapping, curriculum slot assignment, prototype queue
- **Pass management** — closing a pass, classifying what was learned, promoting reusable rules
- **Question auditing** — batch QA on Echo Heist templates with structured results

None of these are pipeline stages. They happen before, between, and after pipeline runs.

---

## The Two Systems

| Dimension | Python pipeline | Taskade layer |
|---|---|---|
| Entry point | `pipeline.py` CLI | Taskade project board or agent chat |
| Input | `raw_command` string | Task in Game Concepts Pipeline |
| Output | JSON artifacts in `artifacts/` | Updated project fields, new tasks, audit records |
| Trigger | Manual, terminal | Manual agent call or automatic field watch |
| Who runs it | Developer | Designer, orchestrator agent, or Taskade user |
| Gate system | Gate engine with pass/revise/reject | GO/NO-GO and Delight Gate select fields |
| Memory | Job workspaces in `memory/` | Taskade projects: pipeline, library, prototype specs |
| Testable | Yes — 5/5 benchmark suite | No — workflow outputs depend on Claude responses |

The systems share one resource: concepts. A concept that passes the Python pipeline
gate engine is the same concept that gets a GO decision in the Taskade board.
The Taskade layer does not re-run the Python pipeline. It calls agents directly via
Taskade's automation infrastructure.

---

## How a Concept Moves Through Both Systems

```
1. Designer adds concept to Game Concepts Pipeline (Taskade board)
       ↓
2. Brainstorm → Pipeline Review fires automatically
   (agent runs 7-stage design review; GO/NO-GO and Delight Gate written back to task)
       ↓
3. If GO: GO Decision → Curriculum Slot fires automatically
   (Curriculum Architect identifies CCSS slot; concept added to Prototype Specs)
       ↓
4. Pipeline Orchestrator manually runs Misconception Architect
   (misconception map generated; entries written to library as PENDING)
       ↓
5. Developer runs concept through Python pipeline
   (Stages 0–8; prototype_ui_spec produced; artifacts written to artifacts/)
       ↓
6. Pass cycle begins — P1 through P5, governed by docs/pass_rules.md
       ↓
7. After each pass: Pipeline Orchestrator manually runs Pass Closure
   (learning classified; pass record written; OS rules promoted if general)
```

Steps 2 and 3 are automatic. Steps 4 and 7 are manual — the orchestrator agent
triggers them after confirming a GO decision or a completed pass.
Step 5 is entirely in the Python layer.

---

## Workflow Reference

### Brainstorm → Pipeline Review
**File:** `brainstorm_pipeline_review.md`
**Flow ID:** `01KNMNC88WD2TCGE2S8E5F7AF7`
**Trigger:** Automatic — fires when any new task is added to the Game Concepts Pipeline
**Use when:** A new concept has just been added to the board
**Do not use for:** Concepts already reviewed; concepts being re-evaluated after revision

Runs the Game Design Critic agent on every new pipeline task automatically.
Writes GO/NO-GO decision, Delight Gate verdict, and full AI critique back to the task's
custom fields. The designer does not need to trigger anything manually.

---

### Game Design Pipeline Review
**File:** `game_design_pipeline_review.md`
**Flow ID:** `01KNM0B599YCAR5Y2JN47G8XZQ`
**Trigger:** Manual — called by the Game Design Critic agent
**Use when:** A concept needs a fresh review, or Brainstorm workflow did not fire
**Do not use for:** Running a concept through the Python pipeline — that is `pipeline.py`

Full 7-stage design review: Game Experience Spec, Pre-Build Excellence Check, Delight
Gate, Design Checks (all four), Skill & Overlap, GO/NO-GO Decision, and P1–P5 Prototype
Readiness Guide. Identical in scope to what the Brainstorm workflow triggers automatically.
Use this for manual re-runs or one-off reviews.

---

### GO Decision → Curriculum Slot Assignment
**File:** `go_decision_curriculum_slot.md`
**Flow ID:** `01KNMND4MFXZQ73J0GFAMZX452`
**Trigger:** Automatic — fires when the GO/NO-GO field is updated on any pipeline task
**Use when:** A concept has just received a GO decision
**Do not use for:** NO-GO concepts; concepts still in revision

Calls the Curriculum Architect to identify the CCSS/NGSS standard and confirm the grade
band, then adds the approved concept to the Prototype Specs project queue.
Fires on any field update — including NO-GO. The Curriculum Architect handles gracefully
if the decision is not GO.

---

### Misconception Architect
**File:** `misconception_architect.md`
**Flow ID:** `01KNMPE00ZG4RQAW7V4J1MZ1GX`
**Trigger:** Manual — called by the Pipeline Orchestrator after a GO decision
**Use when:** A concept has a GO decision and the Python pipeline is about to begin
**Do not use for:** Concepts still in review; concepts with a NO-GO decision

Run this before starting the Python pipeline. Predicts every misconception class relevant
to the concept, cross-references the seeded library, and generates new entries where gaps
exist. Entries are written to the Misconception Library as `[PENDING REVIEW]` — they must
be manually promoted before becoming active.

Required inputs: `concept_title`, `concept_description`, `target_skill`, `target_age`,
`game_experience_spec` (from Stage 1 of the pipeline review).

---

### Pass Closure — Learning Capture & Promotion
**File:** `pass_closure.md`
**Flow ID:** `01KNMPFZ021BFFKKN66GNKWD34`
**Trigger:** Manual — called by the Pipeline Orchestrator after a pass completes
**Use when:** A prototype pass has been completed and its result is known
**Do not use for:** Passes still in progress; passes abandoned mid-run

Run immediately after a pass closes. Classifies the learning (LOCAL or GENERAL), writes
a pass record to the Playtest Audit, and — if GENERAL — drafts a new OS rule for
promotion to the appropriate design document. The Orchestrator receives a 3-sentence
summary and the recommended next pass.

Required inputs: `game_name`, `pass_number`, `what_changed`, `raw_observations`,
`proof_target_result`, `bottleneck_addressed`, `playtest_question_answer`.

LOCAL = stored in the Playtest Audit only.
GENERAL = promoted as a new design rule to the relevant OS document.

---

### Echo Heist — Question Audit Pipeline
**File:** `echo_heist_question_audit.md`
**Flow ID:** `01KNMYV115D5QC7T5MG7A0J80T`
**Trigger:** Manual — called by the Math Question QA agent
**Use when:** A question template or D3 mission question needs a quality audit
**Do not use for:** Auditing the full template set in a single call — run one template at a time

Checks four dimensions per template: answer correctness, skill alignment, randomization
health, and hint quality. Produces a consolidated `PASS / WARN / FAIL` report and writes
the result to the Question Audit Results tracker.

Priority order: T3, T4, T5, T8, T10 (highest known risk first).
D3 mission questions (M21–M30) skip the randomization stage automatically.

Required inputs: `template_id`, `template_name`, `target_skill`, `target_age`,
`question_batch`, `generator_code` (use `"N/A"` for D3 authored questions).

---

## Related Documents

| Question | Document |
|---|---|
| Which Taskade projects store data? | `docs/taskade_resources.md` |
| What are the custom field IDs for the pipeline board? | `docs/taskade_data/game_concepts_pipeline.md` |
| How is the misconception library structured? | `docs/taskade_data/misconception_library.md` |
| What are all the Taskade agent IDs and public URLs? | `docs/taskade_resources.md` |
| What are the Python pipeline stages? | `README.md` and `RUNBOOK.md` |
| What are the pass rules? | `docs/pass_rules.md` |
| Which OS document governs each task type? | `docs/os_doc_usage.md` |

---

## Rule for Using This Layer

Every task that touches the Taskade layer should state which workflow governs it:

> **Workflow:** `pass_closure.md`
> **Game:** Echo Heist Pass 5
> **Trigger:** Manual — orchestrator calls after pass closes

If a task does not map cleanly to one of the six workflows above, it belongs in the
Python pipeline, in the OS documents, or in a direct agent chat — not in a workflow.
