# Workflow: Echo Heist — Question Audit Pipeline

**Taskade Flow ID:** `01KNMYV115D5QC7T5MG7A0J80T`  
**Trigger type:** Manual (`CustomTrigger`)  
**Called by:** Math Question QA agent  
**Purpose:** Run a full 4-dimension quality audit on any Echo Heist question template. Produces a structured report and writes results to the Question Audit Results tracker.

---

## Trigger Inputs

| Field | Type | Required | Description |
|---|---|---|---|
| `template_id` | string | yes | e.g. `T3`, `T10`, `M21` |
| `template_name` | string | yes | e.g. "Percent change", "Rounding" |
| `target_skill` | string | yes | The exact math skill being audited |
| `target_age` | string | yes | e.g. "Grades 6-8, ages 11-13" |
| `question_batch` | string | yes | The questions to audit (as text block) |
| `generator_code` | string | yes | The JS generator function (or "N/A" for D3 authored questions) |

---

## Stages

### Stage 1 — Independent Answer Verification
**Action:** `ai.ask`  
**Input:** template_id, template_name, target_skill, target_age, question_batch  
**Purpose:** For each question, independently compute the answer from scratch. Never trust the stored answer.

For every question:
- Show full computation step by step
- Compare to stored answer
- Rate: **PASS** (matches within 0.01) | **WARN** (numerically correct, format issue) | **FAIL** (answer differs — this is a bug)

Output ends with: `CORRECTNESS SUMMARY: X PASS Y WARN Z FAIL`

---

### Stage 2 — Skill Alignment Analysis
**Action:** `ai.ask`  
**Input:** target_skill, target_age, question_batch  
**Purpose:** Does answering each question genuinely require the target skill, or can a student shortcut?

Rating per question:
- **ON-SKILL** — requires the skill, no viable shortcut, appropriate difficulty
- **SHORTCUT-RISK** — student could answer correctly without using the skill
- **OFF-SKILL** — question doesn't exercise the stated skill
- **TOO-EASY** — numbers so simple the skill is not exercised at grade level
- **TOO-HARD** — exceeds Grades 6-8 expectations

Output ends with: `ALIGNMENT SUMMARY: counts per rating`

---

### Stage 3 — Randomization Health Check
**Action:** `ai.ask`  
**Input:** template_id, generator_code, question_batch  
**Purpose:** Analyze the procedural generator for quality issues. If generator_code is "N/A" (D3 authored question), mark as `N/A` and skip.

Checks:
- **Degenerate cases** — answer = 0 or 1, trivially small numbers, nonsensical parameters
- **Collision risk** — distinct output count: `HIGH` (<20) | `MEDIUM` (20-50) | `LOW` (>50)
- **Answer bias** — for A/B questions, does one answer dominate?
- **Float precision risks** — operations like `0.1 + 0.2` that cause JS float drift
- **Missing guards** — constraints that should prevent degenerate outputs

Output ends with: `RANDOMIZATION HEALTH: PASS | WARN | FAIL` and `FIX REQUIRED: [specific gen function changes or None]`

---

### Stage 4 — Hint Quality Review
**Action:** `ai.ask`  
**Input:** template_id, target_age, question_batch (with hints)  
**Purpose:** Review hint quality for every question.

**hint1 rules:**
- PASS — names the approach without solving (e.g. "Percent decrease", "Two-step equation")
- WARN — too vague (e.g. "Work backwards")
- FAIL — gives the answer directly OR is mathematically wrong

**hint2 rules:**
- PASS — sets up the computation without completing it (e.g. "18 × 0.75")
- WARN — restates the question without advancing the student
- FAIL — completes the calculation (gives the answer) OR is incorrect

Also flag: notation inappropriate for ages 11-13 (sigma, calculus, etc.)

Output ends with: `HINT SUMMARY: X PASS Y WARN Z FAIL`

---

### Stage 5 — Consolidated Audit Report
**Action:** `ai.ask`  
**Input:** template_id, template_name, Stages 1-4 results  
**Purpose:** Synthesize all four reports into a final structured audit.

**Overall status rules:**
- **FAIL** if any single dimension is FAIL
- **WARN** if no FAILs but any WARNs exist
- **PASS** only if all four dimensions pass

**Output format (exact):**
```
OVERALL STATUS: PASS | WARN | FAIL
CORRECTNESS: PASS | WARN | FAIL
SKILL ALIGNMENT: PASS | WARN | FAIL
RANDOMIZATION: PASS | WARN | FAIL | N/A
HINT QUALITY: PASS | WARN | FAIL
AGE BAND FIT: PASS | WARN | FAIL

ISSUES FOUND:
• [CRITICAL] issue description
• [MEDIUM] issue description

FIX REQUIRED:
• [specific actionable fix for each issue, or "None"]
```

---

### Stage 6 — Write Audit Result to Tracker
**Action:** `task.create`  
**Project:** Question Audit Results (`1A7jTuKq9Zqa1sMF`)  
**Position:** `beforeend`  
**Content:** `AUDIT: {template_id} -- {template_name}\n\n{Stage 5 report}`

---

## Template Reference (Echo Heist)

| ID | Skill | Standard | Type |
|---|---|---|---|
| T1 | One-step equations | 6.EE.B.7 | procedural |
| T2 | Two-step equations | 7.EE.B.4 | procedural |
| T3 | Percent change | 7.RP.A.3 | procedural |
| T4 | Decimal-percent | 6.RP.A.3c | procedural |
| T5 | Fraction of quantity | 6.RP.A.1 | procedural |
| T6 | Fraction add/sub | 5.NF.A.1 | procedural |
| T7 | Rate-time-distance | 6.RP.A.3b | procedural |
| T8 | Rate comparison | 6.RP.A.2 | procedural |
| T9 | Integer ops | 7.NS.A.1 | procedural |
| T10 | Rounding | 5.NBT.A.4 | procedural |
| T11 | Angles | 7.G.B.5 | procedural |
| T12 | Expected value | 7.SP.C.5 | procedural |
| M21-M30 | D3 mission questions | various | authored (no generator) |

## Known Highest-Risk Templates (audit these first)
- **T3** — float precision in percent calculations
- **T4** — equivalent form collisions
- **T5** — trivial answers when numerator = denominator
- **T8** — answer bias in rate comparison (one rate often dominates)
- **T10** — JS float rounding drift

---

## Data Flow Summary

```
manual trigger (template submitted for audit)
  → Stage 1: Independent answer verification
  → Stage 2: Skill alignment analysis
  → Stage 3: Randomization health check (or N/A for D3)
  → Stage 4: Hint quality review
  → Stage 5: Consolidated audit report
  → Stage 6: Result written to Question Audit Results tracker
```
