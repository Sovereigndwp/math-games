# Workflow: Game Design Pipeline Review

**Taskade Flow ID:** `01KNM0B599YCAR5Y2JN47G8XZQ`  
**Trigger type:** Manual (`CustomTrigger`)  
**Called by:** Game Design Critic agent

---

## Trigger Inputs

| Field | Type | Required |
|---|---|---|
| `concept_title` | string | yes |
| `concept_description` | string | yes |
| `target_skill` | string | yes |
| `target_age` | string | yes |

---

## Stages

### Stage 1 — Game Experience Spec
**Action:** `ai.generate`  
**Input:** concept_title, concept_description, target_skill, target_age  
**Prompt covers:**
1. CORE FANTASY — What does the player imagine they are doing?
2. CORE ACTION — Single repeatable mechanical action per turn
3. WHY IT IS NOT A WORKSHEET IN COSTUME — what would be lost without the theme?
4. DEPTH POTENTIAL — how does challenge scale with player skill?
5. BREADTH POTENTIAL — what variations or modes could extend the game?
6. NATURAL CEILING — when does a skilled player have nothing left to learn?
7. SKILL DISTINCTNESS — exact cognitive/math operation exercised

---

### Stage 2 — Pre-Build Excellence Check
**Action:** `ai.ask`  
**Input:** concept + Stage 1 result  
**Prompt covers:**
1. WHY WOULD THE PLAYER CARE? — intrinsic motivation hooks
2. WHAT 3 MOMENTS COULD BE MEMORABLE?
3. WHAT IS THE FIRST MASTERY LAYER BEYOND CORRECTNESS?
4. ARE THE DECISIONS REAL OR FAKE?
5. WHAT ACCIDENTAL FRICTION COULD MAKE THIS FEEL BAD?
6. WHAT WOULD PROVE THE CONCEPT IS WEAK ENOUGH TO STOP EARLY?

Ends with one-paragraph overall assessment.

---

### Stage 3 — Delight Gate
**Action:** `ai.categorize`  
**Input:** concept + Stage 1 + Stage 2  
**Output schema (structured JSON):**
```json
{
  "has_delight": boolean,
  "has_tension": boolean,
  "theme_carries_math": boolean,
  "reason_to_replay": boolean,
  "gate_verdict": "PASS | FAIL",
  "gate_reasoning": "string"
}
```
> PASS requires at least 3/4 criteria true.

---

### Stage 4 — Design Checks (All Four)
**Action:** `ai.ask`  
**Input:** concept + Stage 1 + Stage 3 reasoning  
**Scores each STRONG / WEAK / NEEDS WORK:**
1. FANTASY INTEGRITY — does felt experience match mechanical experience?
2. SATISFACTION LOOP — is there a clear rewarding feedback loop?
3. CONSEQUENCE QUALITY — do mistakes and successes have real weight?
4. REPLAY VARIATION — does a second session feel different from the first?

Ends with Design Health Rating: STRONG / MIXED / WEAK.

---

### Stage 5 — Skill & Overlap Review
**Action:** `ai.categorize`  
**Input:** concept + Stage 1  
**Output schema (structured JSON):**
```json
{
  "exact_math_skill": "string",
  "closest_existing_game": "string",
  "cognitive_similarity_risk": "HIGH | MEDIUM | LOW",
  "borrowed_vs_new": "string",
  "overlap_resolution": "KEEP_BOTH | KEEP_THIS | KEEP_OTHER | NEEDS_DIFFERENTIATION",
  "overlap_reasoning": "string"
}
```

---

### Stage 6 — GO / NO-GO Decision
**Action:** `ai.categorize`  
**Input:** all prior stage results  
**Output schema (structured JSON):**
```json
{
  "decision": "GO | REVISE | PAUSE | STOP",
  "confidence": "HIGH | MEDIUM | LOW",
  "primary_strengths": ["string", "string", "string"],
  "primary_risks": ["string", "string", "string"],
  "prototype_entry_point": "string",
  "if_revise_what_exactly": "string",
  "executive_summary": "string"
}
```

---

### Stage 7 — Prototype Readiness Guide (P1–P5)
**Action:** `ai.generate`  
**Input:** concept + Stage 6 decision + Stage 1 spec  
**Produces 3-5 testable bullet points for each phase, plus a STOP CONDITION:**
- **P1 — CORE VIABILITY:** core loop clarity, world legibility before pressure, reachable win, understandable failure
- **P2A — SESSION PAYOFF:** run payoff, grading, actionable takeaway, clean session close
- **P2B — CHALLENGE FAIRNESS:** fairness, no shortcut skills, near/far differences, one new complexity layer
- **P3 — PERSONALITY & WORLD:** game personality, world reaction, one memorable moment
- **P4 — MASTERY & BREADTH:** reason to return, content breadth, mastery beyond correctness
- **P5 — RELEASE READINESS:** final polish criteria specific to this concept

---

### Stage 8 — Save Concept to Game Concepts Pipeline
**Action:** `task.create`  
**Project:** Game Concepts Pipeline (`LnpYq2qGt5DrXpda`)  
**Position:** `beforeend`  
**Fields set:**

| Field ID | Field Name | Value |
|---|---|---|
| `@gcf04` | Pipeline Stage | `stage-gono` |
| `@gcf05` | GO/NO-GO Decision | `gono-pending` |
| `@gcf06` | Delight Gate | `dg-pending` |

---

## Data Flow Summary

```
trigger inputs
  → Stage 1: Game Experience Spec
  → Stage 2: Pre-Build Excellence Check
  → Stage 3: Delight Gate (JSON)
  → Stage 4: Design Checks
  → Stage 5: Skill & Overlap (JSON)
  → Stage 6: GO/NO-GO Decision (JSON)
  → Stage 7: P1-P5 Prototype Readiness Guide
  → Stage 8: Task written to Game Concepts Pipeline
```
