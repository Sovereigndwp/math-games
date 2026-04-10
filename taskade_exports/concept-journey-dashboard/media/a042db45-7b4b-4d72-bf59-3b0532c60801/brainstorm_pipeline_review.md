# Workflow: Brainstorm → Pipeline Review

**Taskade Flow ID:** `01KNMNC88WD2TCGE2S8E5F7AF7`  
**Trigger type:** Automatic — fires when a new task is added to the Game Concepts Pipeline project  
**Purpose:** Every new concept added to the pipeline is immediately routed through the Game Design Critic for a full automated review. Results are written back to the pipeline record's custom fields.

---

## Trigger

**Type:** `task.added`  
**Project:** Game Concepts Pipeline (`LnpYq2qGt5DrXpda`)  
**Fires on:** Any new task created in that project  
**Available from trigger:** `nodeText` (concept text), `nodeId` (task ID for write-back)

---

## Stages

### Step 1 — Run Full Pipeline Review via Game Design Critic Agent
**Action:** `agent.ask`  
**Agent:** Game Design Critic (`01KNM0ECMQFA8EYBP45WTV587M`)  
**Input prompt:**
```
Run the full game design pipeline review for this concept:

CONCEPT: {{ trigger.nodeText }}

Provide:
1. Game Experience Spec (core fantasy, core action, natural ceiling)
2. Pre-Build Excellence Check
3. Delight Gate verdict: PASS or FAIL with reason
4. GO / NO-GO Decision with rationale
5. If GO: Prototype entry point (P1 success criteria)
6. AI Critique Summary (2-3 sentences)
7. Closest Existing Game
8. Depth Potential score 1-10
```

---

### Step 2 — Extract GO/NO-GO Decision
**Action:** `ai.ask`  
**Input:** Step 1 full result  
**Prompt:** Extract the GO/NO-GO decision. Respond with ONLY one of: `GO`, `NO-GO`, `Revise`, `Pause`, `Pending`

---

### Step 3 — Extract Delight Gate Status
**Action:** `ai.ask`  
**Input:** Step 1 full result  
**Prompt:** Extract the Delight Gate verdict. Respond with ONLY one of: `Pass`, `Fail`, `Pending`

---

### Step 4 — Update Pipeline Stage Field
**Action:** `updateCustomFields`  
**Project:** `LnpYq2qGt5DrXpda`  
**Node:** `{{ trigger.nodeId }}`  
**Fields written:**

| Field ID | Field Name | Value |
|---|---|---|
| `@gcf04` | Pipeline Stage | `stage-gono` |
| `@gcf07` | AI Critique | Full Step 1 result text |

---

### Step 5 — Write GO/NO-GO + Delight Gate Back to Pipeline
**Action:** `updateCustomFields`  
**Project:** `LnpYq2qGt5DrXpda`  
**Node:** `{{ trigger.nodeId }}`  
**Fields written:**

| Field ID | Field Name | Value |
|---|---|---|
| `@gcf05` | GO/NO-GO Decision | Step 2 extracted value |
| `@gcf06` | Delight Gate | Step 3 extracted value |

---

## Pipeline Custom Fields Reference

| Field ID | Name | Type | Values |
|---|---|---|---|
| `@gcf04` | Pipeline Stage | select | `stage-intake`, `stage-gono`, `stage-prototype`, `stage-done` |
| `@gcf05` | GO/NO-GO Decision | select | `GO`, `NO-GO`, `Revise`, `Pause`, `Pending`, `gono-pending` |
| `@gcf06` | Delight Gate | select | `Pass`, `Fail`, `Pending`, `dg-pending` |
| `@gcf07` | AI Critique | string | Full critique text |

---

## Data Flow Summary

```
New task added to Game Concepts Pipeline
  → Step 1: Agent runs full 7-stage pipeline review
  → Step 2: Extract GO/NO-GO (text → select value)
  → Step 3: Extract Delight Gate (text → select value)
  → Step 4: Write stage + AI critique to pipeline record
  → Step 5: Write GO/NO-GO + Delight Gate to pipeline record
```
