# Data Schema: Prototype Specifications

**Taskade Project ID:** `9bfNR2acXuAHiWyC`  
**View:** Table  
**Purpose:** One entry per game concept that has received a GO decision. Each entry holds the full prototype specification needed for a developer to begin building. New entries are automatically added by the Misconception Architect workflow (Stage 5) and the GO Decision → Curriculum Slot workflow (Step 2).

---

## Entry Structure

Each task in this project represents one game and contains:

### Task Title
The canonical game name (e.g. "Power Grid Operator", "Echo Heist")

### Task Note / Body
The full prototype spec, structured as follows:

```
## [Game Name] — Prototype Spec

### Overview
- Target skill: [e.g. Two-step equations, 7.EE.B.4]
- Target age / grade band: [e.g. Grades 6-8, ages 11-13]
- Interaction family: [e.g. Allocation / Network Balancing]
- World theme: [e.g. Managing a power grid under load constraints]

### Core Loop
[Description of the smallest meaningful repeatable action]

### Component Tree
[React component hierarchy — which components exist and their relationships]

### State Machine
States: [list of states]
Transitions: [state → event → new state]
Guards: [conditions that block transitions]

### Data Model
[Shape of data stored during a session]

### Prototype Stages

#### P1 — Core Viability
Success criteria:
- [ ] [testable criterion]
- [ ] [testable criterion]
STOP CONDITION: [single observation that triggers a stop]

#### P2A — Session Payoff
...

#### P2B — Challenge Fairness
...

#### P3 — Personality & World
...

#### P4 — Mastery & Breadth
...

#### P5 — Release Readiness
...

### Edge Cases
- Wrong answer handling
- Timeout / disconnection
- Accessibility triggers (keyboard, screen reader)
- Mobile / low-end device performance

### Animation & Feedback Spec
- Correct answer: [what happens]
- Incorrect answer: [what happens]
- Level complete: [what happens]
```

---

## Games Currently in Prototype Specs

| Game | Family | Grade Band | Status |
|---|---|---|---|
| Power Grid Operator | Allocation / Network Balancing | 6-8 | Spec seeded — awaiting build |
| School Trip Fleet | Capacity Packing | 3-5 | Spec seeded — awaiting build |
| Echo Heist | Stealth-Puzzle / Routing | 6-8 | Pass 5 complete — in active development |
| Bakery Rush | Exact-Sum Composition | K-2 / 1-3 | Active |
| Fire Dispatch | Dispatch | 3-5 | Active |
| Unit Circle Pizza Lab | Precision Placement | 9-12 | Active |

---

## Automated Writes

The following workflows add entries to this project automatically:

| Workflow | When | What is written |
|---|---|---|
| Misconception Architect (`01KNMPE00ZG4RQAW7V4J1MZ1GX`) | Stage 5, after every GO decision | Concept title as a new task |
| GO Decision → Curriculum Slot (`01KNMND4MFXZQ73J0GFAMZX452`) | Step 2, after GO field update | Concept title as a new task |

After auto-creation, the Prototype Engineer agent should be asked to fill in the full spec body.
