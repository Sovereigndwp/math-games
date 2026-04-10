# Data Schema: Game Concepts Pipeline

**Taskade Project ID:** `LnpYq2qGt5DrXpda`  
**View:** Board (Kanban by Pipeline Stage)  
**Purpose:** Central tracking record for every game concept from raw idea through GO/NO-GO decision.

---

## Custom Fields

| Field ID | Name | Type | Values / Notes |
|---|---|---|---|
| `@gcf04` | Pipeline Stage | select | See options below |
| `@gcf05` | GO/NO-GO Decision | select | See options below |
| `@gcf06` | Delight Gate | select | See options below |
| `@gcf07` | AI Critique | string | Full critique text from Game Design Critic agent (set by Brainstorm → Pipeline Review workflow) |
| `@gcf08` | Closest Existing Game | string | Closest commercial or internal analog; used to assess overlap risk |
| `@gcf09` | Depth Potential | string | Free-text rating and rationale for how far the concept can scale |
| `@gcf10` | Natural Ceiling | string | What the player cannot do beyond this concept's core — where the game stops being itself |
| `@gcf11` | Pause Conditions | string | **Required when GO/NO-GO = Pause.** Specific, verifiable changes required before re-entry. Must not be vague. |
| `@gcf12` | Re-evaluation Trigger | string | **Required when GO/NO-GO = Pause.** Time-based ("90 days") or event-based ("when Routing family reaches P3") trigger that fires re-evaluation. |

### `@gcf04` — Pipeline Stage Options

| Option Value | Label | Meaning |
|---|---|---|
| `stage-intake` | Intake | Concept entered but not yet reviewed |
| `stage-gono` | GO/NO-GO Review | Actively being evaluated by the pipeline |
| `stage-prototype` | In Prototype | Concept has GO decision and is being built |
| `stage-done` | Done | Prototype complete or concept retired |

### `@gcf05` — GO/NO-GO Decision Options

| Option Value | Label | Meaning |
|---|---|---|
| `gono-pending` | Pending | Not yet decided |
| `GO` | GO | Approved — proceed to prototype |
| `NO-GO` | NO-GO | Rejected — do not build |
| `Revise` | Revise | Strong core, specific changes required before prototype |
| `Pause` | Pause | Needs more thinking time |

### `@gcf06` — Delight Gate Options

| Option Value | Label | Meaning |
|---|---|---|
| `dg-pending` | Pending | Not yet evaluated |
| `Pass` | Pass | At least 3/4 delight criteria met |
| `Fail` | Fail | Fewer than 3/4 delight criteria met |

---

## Automated Field Updates

The following workflows write to this project automatically:

| Workflow | Trigger | Fields Written |
|---|---|---|
| Brainstorm → Pipeline Review | New task added | `@gcf04` → `stage-gono`, `@gcf05` → extracted value, `@gcf06` → extracted value, `@gcf07` → full critique |
| Game Design Pipeline Review | Manual (via Critic agent) | `@gcf04` → `stage-gono`, `@gcf05` → `gono-pending`, `@gcf06` → `dg-pending` on concept creation |

---

## Task Structure

Each task (row) in the project represents one game concept:
- **Title:** Concept name (e.g. "Power Grid Operator", "School Trip Fleet")
- **Note:** Additional context, world theme, or design notes
- **Custom fields:** Pipeline Stage, GO/NO-GO, Delight Gate, AI Critique

---

## Current Concepts (as of last session)

Key games known to be in the pipeline with full entries:
- Power Grid Operator — GO, Delight Gate Pass, Prototype Specs seeded
- School Trip Fleet — GO, Delight Gate Pass, Prototype Specs seeded
- Echo Heist — In Prototype (Pass 5 complete, 304 tests passing)
- Bakery Rush — In Prototype / active
- Fire Dispatch — In Prototype / active
- Unit Circle Pizza Lab — In Prototype / active
