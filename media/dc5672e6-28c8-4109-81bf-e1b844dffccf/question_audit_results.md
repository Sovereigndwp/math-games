# Data Schema: Echo Heist — Question Audit Results

**Taskade Project ID:** `1A7jTuKq9Zqa1sMF`  
**View:** Table  
**Purpose:** Tracks the audit status and full results for every Echo Heist question template and D3 mission question. New audit results are written automatically by the Question Audit Pipeline workflow.

---

## Row Types

There are three types of rows in this project:

### 1. Template Rows (T1–T12)
One row per procedural question template. These templates generate randomized questions at runtime.

| Row ID | Template | Skill | Standard | Known Risks |
|---|---|---|---|---|
| T1 | One-step equations | Solve for x | 6.EE.B.7 | Trial-and-error bypass |
| T2 | Two-step equations | Multi-step solve | 7.EE.B.4 | Same |
| T3 | Percent change | % increase/decrease | 7.RP.A.3 | Float precision |
| T4 | Decimal-percent | % ↔ decimal | 6.RP.A.3c | Equivalent form collisions |
| T5 | Fraction of quantity | Fraction × whole | 6.RP.A.1 | Trivial answers (num = denom) |
| T6 | Fraction add/sub | Add/subtract fractions | 5.NF.A.1 | — |
| T7 | Rate-time-distance | d = r × t | 6.RP.A.3b | — |
| T8 | Rate comparison | Compare two rates | 6.RP.A.2 | Answer bias (one rate dominates) |
| T9 | Integer ops | Signed number operations | 7.NS.A.1 | — |
| T10 | Rounding | Round to specified place | 5.NBT.A.4 | JS float drift |
| T11 | Angles | Complementary/supplementary | 7.G.B.5 | — |
| T12 | Expected value | Probability × outcome | 7.SP.C.5 | — |

### 2. D3 Mission Rows (M21–M30)
One row per authored (non-procedural) question from the D3 mission set. These questions are hand-authored and have no generator code.

| Row ID | Mission | Notes |
|---|---|---|
| M21–M30 | D3 mission questions | Authored; randomization stage is N/A |

### 3. Cross-Cutting Issue Rows
Rows tracking issues that affect multiple templates (e.g. float precision across T3, T4, T10).

---

## Audit Result Fields

Each row contains the full output of the Question Audit Pipeline workflow for that template, written as a task note. The structured summary follows this format:

```
OVERALL STATUS: PASS | WARN | FAIL
CORRECTNESS: PASS | WARN | FAIL
SKILL ALIGNMENT: PASS | WARN | FAIL
RANDOMIZATION: PASS | WARN | FAIL | N/A
HINT QUALITY: PASS | WARN | FAIL
AGE BAND FIT: PASS | WARN | FAIL

ISSUES FOUND:
• [CRITICAL] ...
• [MEDIUM] ...

FIX REQUIRED:
• ...
```

---

## Audit Priority Order

Run audits in this order (highest risk first):

1. **T3** — float precision in percent calculations
2. **T4** — equivalent form collisions (many possible valid forms)
3. **T5** — trivial answers when numerator equals denominator
4. **T8** — answer bias in rate comparison
5. **T10** — JS float rounding drift near .5 boundaries
6. **T1, T2** — trial-and-error bypass risk (skill alignment)
7. **T6, T7, T9, T11, T12** — lower known risk
8. **M21–M30** — D3 mission questions (no randomization to check)

---

## Workflow Integration

New audit results are written to this project by:
- **Echo Heist Question Audit Pipeline** (`01KNMYV115D5QC7T5MG7A0J80T`) — Stage 6 creates a new task with the full audit report
- **Math Question QA agent** (`01KNMYTFPEHNWARKW3EBMPSXPQ`) — can trigger the pipeline or write inline notes

---

## Answer Acceptance Rules (Reference)

These rules are implemented in the Echo Heist game engine itself. Auditors should be aware of them:

| Rule | Detail |
|---|---|
| Trailing % stripped | `50%` normalizes to `50` before comparison |
| Fractions parsed | `1/2` → `0.5` via regex |
| Numeric tolerance | `abs(student_answer - correct_answer) < 0.01` |
| Known gap | Fraction-decimal equivalence works both directions via `parseFloat` |
