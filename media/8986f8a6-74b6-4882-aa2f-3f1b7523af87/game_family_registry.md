# Data Schema: Game Family Registry

**Taskade Project ID:** `N9S2kjQdv3s7tyya`  
**View:** Table  
**Purpose:** Defines all interaction family archetypes for the K-12 Game Design Studio. Every game concept must be placed into a family. Families with no games are tracked as gaps to fill.

---

## What Is a Game Family?

A game family is a cluster of games that share the same **core interaction type** — the mechanical action a player repeats each round. Two games in the same family feel similar to play even if their themes are completely different. The family determines what kind of math is most naturally embedded.

---

## The Eight Families

### 1. Exact-Sum Composition
**Core interaction:** Player combines items to hit an exact target value.  
**Math naturally embedded:** Addition, subtraction, number bonds, mental math  
**Example games:** Bakery Rush  
**Coverage status:** ✅ Has game(s)

---

### 2. Dispatch
**Core interaction:** Player assigns tasks/resources to agents under constraints (capacity, time, priority).  
**Math naturally embedded:** Division, multiplication, resource allocation, rate reasoning  
**Example games:** Fire Dispatch  
**Coverage status:** ✅ Has game(s)

---

### 3. Precision Placement
**Core interaction:** Player places an object, answer, or marker at an exact position on a continuous scale.  
**Math naturally embedded:** Fractions, decimals, unit circle, number line reasoning  
**Example games:** Unit Circle Pizza Lab  
**Coverage status:** ✅ Has game(s)

---

### 4. Allocation / Network Balancing
**Core interaction:** Player distributes a fixed resource across a network to meet multiple constraints simultaneously.  
**Math naturally embedded:** Equations, inverse operations, systems thinking, proportional reasoning  
**Example games:** Power Grid Operator  
**Coverage status:** ✅ Has game(s)

---

### 5. Capacity Packing
**Core interaction:** Player packs items into containers without exceeding capacity limits.  
**Math naturally embedded:** Division (ceiling), multiplication, proportional reasoning, inequalities  
**Example games:** School Trip Fleet  
**Coverage status:** ✅ Has game(s)

---

### 6. Routing / Pathfinding
**Core interaction:** Player finds or optimizes a path through a network or map.  
**Math naturally embedded:** Distance, rate, coordinate geometry, graph reasoning, optimization  
**Example games:** None yet  
**Coverage status:** ⚠️ **GAP — needs a game**

---

### 7. Sequence / Ordering
**Core interaction:** Player arranges items, steps, or values into the correct order or sequence.  
**Math naturally embedded:** Ordering integers/fractions, algorithm sequencing, procedural reasoning, sorting  
**Example games:** None yet  
**Coverage status:** ⚠️ **GAP — needs a game**

---

### 8. Build / Craft
**Core interaction:** Player assembles components into a structure following mathematical rules or constraints.  
**Math naturally embedded:** Geometry, measurement, area/perimeter, proportional scaling, volume  
**Example games:** None yet  
**Coverage status:** ⚠️ **GAP — needs a game**

---

## Gap Priority

All three gaps should be treated as **high priority**. The Pipeline Orchestrator knows this list and actively steers new concept intake toward filling these families.

| Family | Gap Priority | Why |
|---|---|---|
| Routing / Pathfinding | High | Rich math embedding (rate, distance, coordinates); no close competitor in studio |
| Sequence / Ordering | High | Critical for algorithm/procedure fluency; underserved by existing games |
| Build / Craft | Medium | Geometry coverage needed; slightly harder to embed precisely |

---

## Special Note: Echo Heist

Echo Heist (Stealth-Puzzle / Routing) was discovered in the repo at `previews/echo-heist/` and imported to the pipeline at Pass 5 (304 tests, 0 failures). It partially fills the **Routing** gap via a new family designation: **Stealth-Puzzle / Routing**. This has been logged in the Game Concepts Pipeline. A pure Routing/Pathfinding game is still needed for full family coverage.
