# Workflow: Pass Closure — Learning Capture & Promotion

**Taskade Flow ID:** `01KNMPFZ021BFFKKN66GNKWD34`  
**Trigger type:** Manual (`CustomTrigger`)  
**Called by:** Pipeline Orchestrator agent (after every completed prototype pass)  
**Purpose:** After a prototype pass completes, classify the learning, write a pass record to the audit log, and determine whether the learning is general enough to promote to an OS-level rule.

---

## Trigger Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `game_name` | string | yes | Name of the game (e.g. "Echo Heist") |
| `pass_number` | string | yes | Pass label (e.g. "Pass 5") |
| `what_changed` | string | yes | What changed in player feeling from this pass |
| `raw_observations` | string | yes | Full observations from playtesting |
| `proof_target_result` | string | yes | Did this pass prove or disprove its target? |
| `bottleneck_addressed` | string | yes | Which bottleneck was this pass attacking? |
| `playtest_question_answer` | string | yes | Answer to the specific playtest question |

---

## Stages

### Step 1 — Extract & Classify Learning
**Action:** `ai.categorize`  
**Input:** all trigger fields  
**Output schema (structured JSON):**
```json
{
  "learning_summary": "string (one clear sentence)",
  "classification": "viability | motivation | difficulty_tuning | personality_and_feel | replay | release_readiness",
  "failure_mode": "string (if pass revealed a near-failure, describe exactly)",
  "is_local_or_general": "LOCAL | GENERAL",
  "promotion_target": "pass_rules | os_engagement_rules | design_checks | game_families | learning_capture_only",
  "promotion_rationale": "string",
  "applies_to_future_games_when": "string"
}
```

> **LOCAL** = applies only to this game.  
> **GENERAL** = pattern applicable across future games → triggers promotion path.

---

### Step 2 — Write Pass Record to Playtest Audit
**Action:** `task.create`  
**Project:** Playtest Audit (`9a1qJTArrd2EgdUh`)  
**Position:** `beforeend`  
**Content:** `{game_name} {pass_number} — {learning_summary}`

---

### Step 3 — Route: Promote or Hold?
**Branch node** — condition on `is_local_or_general`

#### Branch A — GENERAL → Promote
**Condition:** `is_local_or_general == "GENERAL"`

**Action:** `ai.generate`  
**Input:** learning_summary, classification, promotion_target, applies_to_future_games_when, promotion_rationale  
**Prompt:** Write a new design rule for the Math Game Studio OS. The rule must follow this structure:
```
WHEN: [the condition this rule applies in]
RULE: [what to do]
BECAUSE: [the rationale]
EXAMPLE: [one correct application]
```
Format cleanly, ready to paste into the target design document.

#### Branch B — LOCAL → Hold as Learning Capture
No further action. Record is stored in the Playtest Audit only.

---

### Step 4 — Orchestrator Pass Summary
**Action:** `ai.ask`  
**Input:** game_name, pass_number, learning_summary, promotion_target  
**Prompt:** Write a 3-sentence status note confirming:
1. Which game and pass was completed
2. What changed in player feeling
3. Whether a promotion was triggered and to which OS document

Ends with the recommended next pass for this game.

---

## Learning Classification Definitions

| Classification | Meaning |
|---|---|
| `viability` | Did the core loop prove it works (or not)? |
| `motivation` | Did players care about what they were doing? |
| `difficulty_tuning` | Was the challenge calibration right for the age band? |
| `personality_and_feel` | Did the game feel like something vs. feel like nothing? |
| `replay` | Was there a reason to play again? |
| `release_readiness` | Is the game ready for classroom or public use? |

## Promotion Target Definitions

| Target | Meaning |
|---|---|
| `pass_rules` | Add to the Pass Rules OS document |
| `os_engagement_rules` | Add to engagement/motivation design principles |
| `design_checks` | Add to the design review checklist |
| `game_families` | Refine or expand the Game Family Registry |
| `learning_capture_only` | Keep locally; not generalizable |

---

## Data Flow Summary

```
manual trigger (pass completed)
  → Step 1: Classify learning (JSON) — LOCAL or GENERAL?
  → Step 2: Write pass record to Playtest Audit
  → Step 3: Branch on LOCAL/GENERAL
      [GENERAL] → Generate promotion draft (new OS rule)
      [LOCAL]   → Hold in audit only
  → Step 4: Orchestrator writes 3-sentence pass summary + next pass recommendation
```
