# Agent Tool Definitions

This file documents every tool binding for every agent in the Math Game Studio OS.
Two tool types exist:
- **AutomationPieceActionTool** — a built-in Taskade action (AI, search, etc.)
- **AutomationCallManualCustomTriggerWorkflowTool** — calls a workflow that has a manual CustomTrigger; the agent passes structured inputs and receives the workflow's output

---

## Pipeline Orchestrator (`01KNMNAPBV02J41TQPV2W5XV51`)

| Tool | Type | ID / Action |
|---|---|---|
| Ask AI | AutomationPieceActionTool | `@taskade/automade-internalpiece-openai/ai.ask` |
| Search Web | AutomationPieceActionTool | `@taskade/automade-internalpiece-media/web.search` |
| Misconception Architect | AutomationCallManualCustomTriggerWorkflowTool | `01KNMPE00ZG4RQAW7V4J1MZ1GX` |
| Pass Closure | AutomationCallManualCustomTriggerWorkflowTool | `01KNMPFZ021BFFKKN66GNKWD34` |

**When to use each:**
- `ai.ask` — reasoning, synthesis, summarising pipeline state
- `web.search` — researching game families, standards, educational research
- Misconception Architect — immediately after a GO decision; inputs: `concept_title`, `concept_description`, `target_skill`, `target_age`, `game_experience_spec`
- Pass Closure — after every completed prototype pass; inputs: `game_name`, `pass_number`, `what_changed`, `raw_observations`, `proof_target_result`, `bottleneck_addressed`, `playtest_question_answer`

---

## Game Design Critic (`01KNM0ECMQFA8EYBP45WTV587M`)

| Tool | Type | ID / Action |
|---|---|---|
| Game Design Pipeline Review | AutomationCallManualCustomTriggerWorkflowTool | `01KNM0B599YCAR5Y2JN47G8XZQ` |

**When to use:**
- For any concept submitted for review; inputs: `concept_title`, `concept_description`, `target_skill`, `target_age`
- Returns a full 7-stage report ending with GO/NO-GO decision and P1-P5 prototype guide

---

## Math Question QA (`01KNMYTFPEHNWARKW3EBMPSXPQ`)

| Tool | Type | ID / Action |
|---|---|---|
| Ask AI | AutomationPieceActionTool | `@taskade/automade-internalpiece-openai/ai.ask` |
| Search Web | AutomationPieceActionTool | `@taskade/automade-internalpiece-media/web.search` |
| Echo Heist Question Audit Pipeline | AutomationCallManualCustomTriggerWorkflowTool | `01KNMYV115D5QC7T5MG7A0J80T` |

**When to use each:**
- `ai.ask` — inline answer verification and reasoning during conversation
- `web.search` — look up math references, rounding rules, standards edge cases
- Audit Pipeline — for batch audits; inputs: `template_id`, `template_name`, `target_skill`, `target_age`, `question_batch`, `generator_code`

---

## Player Clarity Auditor (`01KNN06QC17WFGVCFNGJ5FJRA4`)

| Tool | Type | ID / Action |
|---|---|---|
| Search Web | AutomationPieceActionTool | `@taskade/automade-internalpiece-media/web.search` |
| Scrape Webpage | AutomationPieceActionTool | `@taskade/automade-internalpiece-media/website.extract` |

**When to use each:**
- `website.extract` — fetch prototype HTML from GitHub: `https://raw.githubusercontent.com/Sovereigndwp/math-game-studio-os/main/previews/[game-name]/current.html`
- `web.search` — research UX patterns, onboarding standards, age-appropriate clarity benchmarks

---

## Curriculum Architect (`01KNMN97E63DVSZFE50AW67BN6`)

| Tool | Type | ID / Action |
|---|---|---|
| Search Web | AutomationPieceActionTool | `@taskade/automade-internalpiece-media/web.search` |
| Ask AI | AutomationPieceActionTool | `@taskade/automade-internalpiece-openai/ai.ask` |

**When to use each:**
- `web.search` — look up CCSS/NGSS standards, research existing curricula
- `ai.ask` — reason about gap analysis, grade band fit, slot availability

---

## Prototype Engineer (`01KNMN9NTZ9R9SVMEPPB2RPQ57`)

| Tool | Type | ID / Action |
|---|---|---|
| Generate with AI | AutomationPieceActionTool | `@taskade/automade-internalpiece-openai/ai.generate` |
| Search Web | AutomationPieceActionTool | `@taskade/automade-internalpiece-media/web.search` |

**When to use each:**
- `ai.generate` — produce component trees, state machine definitions, acceptance criteria docs
- `web.search` — research React patterns, WCAG standards, performance benchmarks for low-end devices

---

## Brainstorming Specialist (`01KNM59YXXTZ9XVS17KJ2JPV1M`)

| Tool | Type | ID / Action |
|---|---|---|
| Search Web | AutomationPieceActionTool | `@taskade/automade-internalpiece-media/web.search` |
| Scrape Webpage | AutomationPieceActionTool | `@taskade/automade-internalpiece-media/website.extract` |

**When to use each:**
- `web.search` — research educational game examples, age-band skill frameworks
- `website.extract` — scrape specific game pages or research papers for reference

---

## Subject Expansion Scout (`01KNMNA5N5S9TDB6XV9VV79YH0`)

| Tool | Type | ID / Action |
|---|---|---|
| Search Web | AutomationPieceActionTool | `@taskade/automade-internalpiece-media/web.search` |
| Ask AI | AutomationPieceActionTool | `@taskade/automade-internalpiece-openai/ai.ask` |

**When to use each:**
- `web.search` — find educational research on misconception rates, existing game market, emerging pedagogy
- `ai.ask` — evaluate expansion viability, structure proposals, reason about gamification fit
