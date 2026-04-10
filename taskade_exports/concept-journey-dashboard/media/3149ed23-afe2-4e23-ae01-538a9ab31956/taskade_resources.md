# Taskade Resource IDs — Math Game Studio OS

Source of truth for all Taskade space resource IDs.
Keep this file updated whenever agents, workflows, or projects are created or renamed.

**Space ID:** `63ifx7l9wtgfvsop`

---

## Agents

| Key | ID | Visibility | Public URL |
|---|---|---|---|
| pipeline_orchestrator | `01KNMNAPBV02J41TQPV2W5XV51` | public | https://www.taskade.com/a/01KNMNAPC3JRJF8XH1EBFQ24K6 |
| game_design_critic | `01KNM0ECMQFA8EYBP45WTV587M` | public | https://www.taskade.com/a/01KNM0ECMYJNW9RCB8RTVGTTWN |
| brainstorming_specialist | `01KNM59YXXTZ9XVS17KJ2JPV1M` | public | https://www.taskade.com/a/01KNMNB4NR0Q22B6F219PV0Z24 |
| curriculum_architect | `01KNMN97E63DVSZFE50AW67BN6` | public | https://www.taskade.com/a/01KNMN97EEH6YME9NDT04HVVAR |
| prototype_engineer | `01KNMN9NTZ9R9SVMEPPB2RPQ57` | public | https://www.taskade.com/a/01KNMN9NVKSNX3M78XW9FZB3T8 |
| subject_expansion_scout | `01KNMNA5N5S9TDB6XV9VV79YH0` | public | https://www.taskade.com/a/01KNMNA5NEZ0664W0PHCPMR8BY |
| math_question_qa | `01KNMYTFPEHNWARKW3EBMPSXPQ` | public | https://www.taskade.com/a/01KNMYTFPQ3EWY0X6HJ2CZ6ME1 |
| player_clarity_auditor | `01KNN06QC17WFGVCFNGJ5FJRA4` | public | https://www.taskade.com/a/01KNN06QEVQXFENX99NPXAHH8M |

---

## Workflows

| Key | ID | Trigger Type | Called By |
|---|---|---|---|
| game_design_pipeline_review | `01KNM0B599YCAR5Y2JN47G8XZQ` | manual | game_design_critic |
| brainstorm_pipeline_review | `01KNMNC88WD2TCGE2S8E5F7AF7` | automatic (task.added on LnpYq2qGt5DrXpda) | — |
| misconception_architect | `01KNMPE00ZG4RQAW7V4J1MZ1GX` | manual | pipeline_orchestrator |
| pass_closure | `01KNMPFZ021BFFKKN66GNKWD34` | manual | pipeline_orchestrator |
| go_decision_curriculum_slot | `01KNMND4MFXZQ73J0GFAMZX452` | automatic (@gcf05 update on LnpYq2qGt5DrXpda) | — |
| echo_heist_question_audit | `01KNMYV115D5QC7T5MG7A0J80T` | manual | math_question_qa |

---

## Projects

| Key | ID | View | Notes |
|---|---|---|---|
| game_concepts_pipeline | `LnpYq2qGt5DrXpda` | board | Custom fields: @gcf04, @gcf05, @gcf06, @gcf07 |
| misconception_library | `cyt3zvpjf32D1Ddt` | list | — |
| game_family_registry | `N9S2kjQdv3s7tyya` | table | 8 families; 3 gaps (Routing, Sequence, Build) |
| prototype_specs | `9bfNR2acXuAHiWyC` | table | — |
| k12_curriculum_map | `fQKsxPJWgG2kPRoQ` | table | — |
| k12_subject_registry | `kVuJPKGWsBcgeGcH` | table | — |
| execution_handoff | `YP3v6uyRFV38x3mR` | list | — |
| playtest_audit | `9a1qJTArrd2EgdUh` | list | — |
| pass_rules | `AhQEf6x9M4aL3vKS` | list | — |
| question_audit_results | `1A7jTuKq9Zqa1sMF` | table | T1-T12 + M21-M30 rows |

---

## Pipeline Custom Field Reference

| Field ID | Project | Name | Type | Options |
|---|---|---|---|---|
| `@gcf04` | game_concepts_pipeline | Pipeline Stage | select | stage-intake, stage-gono, stage-prototype, stage-done |
| `@gcf05` | game_concepts_pipeline | GO/NO-GO Decision | select | gono-pending, GO, NO-GO, Revise, Pause |
| `@gcf06` | game_concepts_pipeline | Delight Gate | select | dg-pending, Pass, Fail |
| `@gcf07` | game_concepts_pipeline | AI Critique | string | Full critique text |

---

## Repo File Map

| Resource | Repo File |
|---|---|
| All agent system prompts | `agents/{agent_key}/system_prompt.md` |
| All agent tool bindings | `agents/agent_tools.md` |
| Workflow configs | `workflows/{workflow_key}.md` |
| Project schemas | `data/schemas/{project_key}.md` |
| This file | `taskade_resources.md` |
