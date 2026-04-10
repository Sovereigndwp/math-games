# Workflow: GO Decision → Curriculum Slot Assignment

**Taskade Flow ID:** `01KNMND4MFXZQ73J0GFAMZX452`  
**Trigger type:** Automatic — fires when custom field `@gcf05` (GO/NO-GO Decision) is updated on any task in the Game Concepts Pipeline  
**Purpose:** When a concept receives a GO decision, automatically route it to the Curriculum Architect to assign a standards slot and prototype priority, then add it to the Prototype Specs queue.

---

## Trigger

**Type:** `task.custom_attribute_updated`  
**Project:** Game Concepts Pipeline (`LnpYq2qGt5DrXpda`)  
**Field watched:** `@gcf05` (GO/NO-GO Decision)  
**Available from trigger:** `nodeText` (concept text), `nodeNote` (notes), `nodeId`

> **Note:** This flow fires on ANY update to `@gcf05` — including NO-GO decisions. The Curriculum Architect prompt should handle gracefully if the decision is not GO.

---

## Steps

### Step 1 — Generate Curriculum Slot & Prototype Entry via Curriculum Architect
**Action:** `agent.ask`  
**Agent:** Curriculum Architect (`01KNMN97E63DVSZFE50AW67BN6`)  
**Input prompt:**
```
A game concept has just received a GO decision in our pipeline. Please:
1. Identify the exact CCSS or NGSS standard this covers
2. Confirm the grade band (K-2, 3-5, 6-8, or 9-12)
3. Check if this slot is open in our curriculum map
4. Recommend the prototype priority (P1-P5 entry point)

Concept: {{ trigger.nodeText }}
Note: {{ trigger.nodeNote }}
```

---

### Step 2 — Add Approved Concept to Prototype Specs
**Action:** `task.create`  
**Project:** Prototype Specifications (`9bfNR2acXuAHiWyC`)  
**Position:** `beforeend`  
**Content:** `{{ trigger.nodeText }}`

---

## Data Flow Summary

```
@gcf05 field updated on any Game Concepts Pipeline task
  → Step 1: Curriculum Architect identifies CCSS/NGSS standard, grade band, open slot, prototype priority
  → Step 2: Concept added to Prototype Specifications project queue
```

---

## Related Projects

| Project | ID | Role |
|---|---|---|
| Game Concepts Pipeline | `LnpYq2qGt5DrXpda` | Source — watches this project |
| Prototype Specifications | `9bfNR2acXuAHiWyC` | Destination — adds approved concepts here |
| K-12 Curriculum Map | `fQKsxPJWgG2kPRoQ` | Agent knowledge — checked for open slots |
