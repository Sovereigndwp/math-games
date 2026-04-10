# Data Schema: P0 Pass Plan (Stage 8.5)

**File path:** `artifacts/{game-slug}/p0_pass_plan.md`
**Format:** Markdown — one file per game, written after GREEN gate, before Developer handoff
**Written by:** Prototype Engineer (mandatory output of Stage 8.5)
**Read by:** Software Developer, Pipeline Orchestrator, any session that opens P0 for a game

---

## What This Is

The P0 Pass Plan is a single page produced by the Prototype Engineer immediately after a concept clears the Build Standards Gate (GREEN). It is not part of the pipeline stages. It is not optional.

**Problem it solves:** The pipeline ends at Stage 8 with a `prototype_ui_spec`. The pass system starts at P0. Without this bridge, developers begin P0 without a named bottleneck, a proof target, or a stop rule. Passes sprawl. Work continues past the point of useful signal.

**This document defines the exact conditions under which P0 is done.**

---

## When to Produce It

The Prototype Engineer produces this document immediately after:
1. The Build Standards Agent returns GREEN on the `prototype_ui_spec`, AND
2. Before the first Developer session begins

It is produced once per game. It is not regenerated unless a major redesign resets the concept to P0 (in which case, the old file is archived, not overwritten).

---

## Required Sections

Every P0 Pass Plan must contain exactly these five sections and nothing else. Keep each section to one or two sentences. This document is a boundary, not a design brief.

---

### 1. Primary Bottleneck

State the single biggest unknown that P0 must resolve. One sentence. This should be about player experience, not technical implementation.

**Format:**
```
The primary bottleneck for P0 is [one-line statement of what is not yet proven].
```

**Examples:**
- "The primary bottleneck for P0 is whether a player understands what action to take within the first 30 seconds without reading instructions."
- "The primary bottleneck for P0 is whether the core loop can sustain interest for more than one full run."
- "The primary bottleneck for P0 is whether the math is genuinely the action or becomes a side interrupt to an otherwise playable game."

**Anti-examples (too vague — not allowed):**
- "The bottleneck is whether it's fun."
- "We need to see if the concept works."

---

### 2. Proof Target

State one observable outcome that would prove the bottleneck is resolved. Must be something a person can observe during or immediately after a session — not a metric requiring instrumentation.

**Format:**
```
P0 is proven when: [one-line observable outcome].
```

**Examples:**
- "P0 is proven when: a new player reaches level 3 without asking what they're supposed to do."
- "P0 is proven when: the player voluntarily starts a second run immediately after the first ends."
- "P0 is proven when: the player describes their action using the game's math language, not as 'clicking buttons'."

---

### 3. Playtest Question

State the single question that a playtest session for P0 should answer. This is the question the developer and designer carry into the room.

**Format:**
```
Playtest question: [one direct question]
```

**Examples:**
- "Playtest question: Does the player understand what 'success' looks like before the first failure?"
- "Playtest question: Does the pressure feel unfair, or does it feel like a fair challenge?"
- "Playtest question: Does the world react in a way the player notices?"

---

### 4. Stop Rule

State what "done enough for P0" looks like, and what is explicitly out of scope. This prevents the pass from absorbing P1 or P2 concerns.

**Format:**
```
P0 is complete when: [condition].
Out of scope for P0: [one or two things explicitly excluded].
```

**Examples:**
- "P0 is complete when: a player who has never seen the game can reach the end of level 2 and articulate what they did wrong on a failed run. Out of scope for P0: scoring, difficulty tuning, progression beyond level 2."
- "P0 is complete when: the core loop runs end-to-end without a crash and the player can describe the goal in one sentence. Out of scope for P0: audio, visual polish, hint systems."

---

### 5. Next Pass

Name the next pass type that should begin once P0 is closed. This keeps the session from reopening P0 concerns after it is declared done.

**Format:**
```
Next pass: [P1 / P2A / P2B] — [one sentence on what it will address].
```

**Examples:**
- "Next pass: P1 — prove the core loop is understandable, playable, and produces a clear fail state for understandable reasons."
- "Next pass: P2A — give the run a reason to matter; add end-of-session payoff and replay motivation."

---

## Full Example

```markdown
# Bakery Rush — P0 Pass Plan

**Game:** Bakery Rush
**Produced by:** Prototype Engineer
**Date:** 2025-11-05
**Build Standards Gate:** GREEN
**Pipeline artifact:** artifacts/bakery-rush/prototype_ui_spec.json

---

## 1. Primary Bottleneck

The primary bottleneck for P0 is whether the player understands that they are composing orders from parts — not just clicking the right-looking item.

## 2. Proof Target

P0 is proven when: a player who has failed an order can explain which ingredient combination was wrong, not just that they got it wrong.

## 3. Playtest Question

Playtest question: Does the player understand the composition mechanic, or are they guessing by visual appearance?

## 4. Stop Rule

P0 is complete when: three consecutive new players can complete level 1 and describe the order-filling mechanic in their own words without prompting. Out of scope for P0: difficulty scaling, speed tuning, audio, any mechanic beyond the core drag-and-fill loop.

## 5. Next Pass

Next pass: P1 — prove the loop is understandable under real pressure, controls work cleanly, and the player can fail for understandable reasons.
```

---

## Where This File Lives

```
artifacts/
  bakery-rush/
    prototype_ui_spec.json
    p0_pass_plan.md          ← produced at Stage 8.5
  fire-dispatch/
    prototype_ui_spec.json
    p0_pass_plan.md
  echo-heist/
    prototype_ui_spec.json
    p0_pass_plan.md          ← backfill: reconstruct from pass record history
```

The ledger entry for each concept references this file at `p0_pass_plan` once it exists.

---

## Relationship to Other Documents

| Document | Relationship |
|---|---|
| `prototype_ui_spec.json` | Precedes the pass plan — must reach GREEN gate first |
| `pipeline_ledger.json` | References the pass plan path at `p0_pass_plan` field |
| `pass_rules.md` | Governs all passes including P0 — the pass plan specifies the P0 application |
| Pass records in `artifacts/learning_captures/` | Written after P0 closes, reference the pass plan's proof target and playtest question |
