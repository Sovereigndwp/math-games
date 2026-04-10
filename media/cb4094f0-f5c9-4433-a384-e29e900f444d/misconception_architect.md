# Workflow: Misconception Architect — Post-Pipeline Analysis

**Taskade Flow ID:** `01KNMPE00ZG4RQAW7V4J1MZ1GX`  
**Trigger type:** Manual (`CustomTrigger`)  
**Called by:** Pipeline Orchestrator agent (after every GO decision)  
**Purpose:** After a concept receives a GO decision, predict every way a learner could misunderstand or fail — and generate a structured misconception map for the Misconception Library.

---

## Trigger Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `concept_title` | string | yes | Name of the game concept |
| `concept_description` | string | yes | Full description |
| `target_skill` | string | yes | The exact math/cognitive skill |
| `target_age` | string | yes | Learner age band (e.g. "grades 3-5") |
| `game_experience_spec` | string | yes | The full GE Spec from Stage 1 of pipeline review |

---

## Stages

### Stage 1 — Check Library for Known Game
**Action:** `ai.ask`  
**Input:** concept_title, concept_description, target_skill, target_age  
**Purpose:** Check if this concept overlaps with any seeded game in the Misconception Library, and extract all applicable existing entries.

Known games with seeded entries:
- **Bakery Rush** — counting-up, carry/regrouping errors, visual-shape matching
- **Fire Dispatch** — repeated-addition, division-as-subtraction
- **Unit Circle Pizza Lab** — radian/degree confusion, sin/cos axis flip
- **Power Grid Operator** — equals-as-command, inverse-operation confusion
- **School Trip Fleet** — ceiling division truncation, per-vehicle vs total capacity confusion

Output classifies each seeded entry as: **DIRECTLY RELEVANT** (transfer unchanged) | **NEEDS REVISION** | **NEW ENTRY REQUIRED**

---

### Stage 2 — Semantic Risk Routing
**Action:** `ai.categorize`  
**Input:** concept info + Stage 1 library check result  
**Output schema (structured JSON):**
```json
{
  "library_coverage": "FULL | PARTIAL | NONE",
  "misconception_risks": [
    {
      "risk": "string",
      "category": "procedural_error | representation_mismatch | conceptual_gap | overgeneralization | shortcut_skill | cognitive_overload",
      "severity": "HIGH | MEDIUM | LOW",
      "library_action": "KEEP | REVISE | NEW"
    }
  ],
  "categories_needing_new_entries": ["string"]
}
```

---

### Stage 3 — Generate Full Misconception Map
**Action:** `ai.generate`  
**Input:** concept info + Stage 2 risks and new entry categories  
**Prompt:** Generates a structured library entry for every identified risk in this format.

Coverage rule: all six error categories must be represented in the output.
If a category does not apply to this game, include an entry for it anyway and
set `DESCRIPTION` to a one-sentence explanation of why it does not apply.
Entries that only describe a behavior without naming the underlying misunderstanding
are invalid and must be rewritten before this stage is considered complete.

```
---
MISCONCEPTION: [plain-language name]
CATEGORY: [procedural_error | representation_mismatch | conceptual_gap | overgeneralization | shortcut_skill | cognitive_overload]
DESCRIPTION: [What exactly does the player do wrong?]
FAILURE SIGNAL: [Observable behavior in the game that reveals this misconception]
DESIGN RESPONSE: [Specific mechanic, feedback, or constraint that addresses this]
APPLIES TO FUTURE GAMES WHEN: [Conditions under which a future game would trigger this entry]
LIBRARY ACTION: [KEEP | REVISE | NEW]
SEVERITY: [HIGH | MEDIUM | LOW]
---
```

Every entry must be grounded in the specific mechanics, age band, and skill — no generic entries.

---

### Stage 3.5 — Gate Check
**Action:** `ai.categorize`  
**Input:** Stage 3 misconception map output  
**Purpose:** Verify the map clears the minimum threshold before any write occurs.  
**Output schema (structured JSON):**
```json
{
  "valid_misconception_count": <integer>,
  "invalid_entries": [
    {
      "misconception": "<MISCONCEPTION field value>",
      "reason": "<why this entry is invalid>"
    }
  ],
  "gate_result": "PASS | FAIL",
  "gate_notes": "<one sentence summary>"
}
```

**Gate rule:** `valid_misconception_count >= 3` and `gate_result == "PASS"` required
to proceed. If the gate fails, return to Stage 3 with the `invalid_entries` list
and regenerate only the failing entries. Do not advance to Stage 4 on a FAIL result.

---

### Stage 4 — Write Misconception Map to Library (Pending Review)
**Action:** `task.create`  
**Project:** Misconception Library (`cyt3zvpjf32D1Ddt`)  
**Position:** `beforeend`  
**Content:** `[PENDING REVIEW] {concept_title} — Misconception Map`

> Entries are written as PENDING so a human can review before promoting to active library status.

---

### Stage 5 — Add Concept to Prototype Specs
**Action:** `task.create`  
**Project:** Prototype Specifications (`9bfNR2acXuAHiWyC`)  
**Position:** `beforeend`  
**Content:** `{concept_title}`

---

### Stage 6 — Notify Pipeline Orchestrator
**Action:** `ai.ask`  
**Input:** concept_title, Stage 2 library_coverage, Stage 3 misconception map  
**Prompt:** Write a 3-5 sentence status update confirming:
1. Concept name and that it passed GO
2. KEEP / REVISE / NEW entry count breakdown
3. Highest-severity risk and its design response
4. Recommended next action (which prototype phase to enter and what to prove first)

---

## Misconception Category Definitions

| Category | Meaning |
|---|---|
| `procedural_error` | Player applies the right procedure incorrectly (e.g. forgets to carry) |
| `representation_mismatch` | Player confuses one representation for another (e.g. fraction vs decimal) |
| `conceptual_gap` | Player lacks the underlying concept (e.g. doesn't understand what division means) |
| `overgeneralization` | Player applies a rule beyond where it works (e.g. "multiplication always makes bigger") |
| `shortcut_skill` | Player finds a workaround that bypasses the target skill |
| `cognitive_overload` | Too many things tracked simultaneously; player abandons reasoning |

---

## Data Flow Summary

```
manual trigger (GO decision received)
  → Stage 1: Library check — which seeded entries transfer?
  → Stage 2: Semantic routing — structured risk classification (JSON)
  → Stage 3: Full misconception map generation
  → Stage 3.5: Gate check — valid_misconception_count >= 3 (FAIL loops back to Stage 3)
  → Stage 4: Write to Misconception Library as PENDING
  → Stage 5: Add concept to Prototype Specs
  → Stage 6: Orchestrator status update
```
