# Grocery Dash — Design Review

**Slug:** `grocery-dash`
**Source audited:** `grocery_dash_v2.html` (1,768 lines) — the actual shipping build
**Date:** 2026-04-13
**Pipeline:** `edu-game-os` v2, Stages 0–5
**Verdict:** **PASS WITH MINOR REVISIONS**

---

## Correction notice

A prior audit of this game was written without access to the source file. It was grounded in itch.io page copy and assumptions, and it got the core math model wrong. **That prior audit is retracted.** This document is the authoritative review.

The retraction itself is logged as a `.lessons/patterns-that-break.md` entry: *never audit a game whose source you haven't read.*

---

## Stage 0 — Concept intake

**One-line loop:** *Scale a recipe for a dinner party of M people, pick the right pack sizes from the shelves, avoid the manager and shoppers, and reach checkout before time runs out.*

**Career tie-in:** Home cook / caterer. Lower aspirational ceiling than "pilot" or "marine biologist" but exceptional **fantasy integrity** — every child has watched an adult scale a recipe in a real store, so the math feels load-bearing in a way rare for edu-games.

**Target skills verified against real content bank:**
- Multi-step multiplicative word problems (translate recipe + guest count → units needed)
- Pack-size choice as a decision problem — *which* pack size minimizes overshoot
- Working memory under time pressure
- Attention discrimination (distinguish recipe items from distractors)

**Standards this actually hits:**
- CCSS.MATH.CONTENT.4.OA.A.2 (multiplicative comparison)
- 4.OA.A.3 (multi-step word problems, interpreting remainders)
- 5.NF.B.6 (real-world fraction multiplication — levels 9, 11, 12 use non-integer scales)
- 6.RP.A.3 (ratio reasoning)

**Grade band:** 3–6 primary.

---

## Stage 1 — Learner fit

| Dimension | Finding | Score |
|---|---|---|
| Reading load in core loop | Moderate. Recipe panel requires short reads. Not K–2 without scaffolding. | 6/10 |
| Math cognitive load | Well calibrated. L1 small whole numbers; L12 multi-variant with ×7 scale. | 9/10 |
| Motor load | Low. Grid-step movement, single action key. | 9/10 |
| Session shape | 12 levels × ~90–130s ≈ 18 min full run. | 9/10 |
| Progression | Stars + best times. Real replay motivation. | 9/10 |

**Learner-fit score: 8.4/10.** Only gap: no K–2 on-ramp (no narration, no picture-only recipe mode). Tracked as future concept `grocery-dash-jr`.

---

## Stage 2 — Kill test

1. **Can a child guess through this?** No. `tryMove` gates checkout via `isCartReady()` and refuses entry if the cart is wrong, showing a toast and requiring a fix first. The checkout receipt is only revealed once the cart is actually plausible. **PASS.**
2. **Better than a worksheet?** Yes. The variant mechanic — choosing between a 20-slice loaf and a 10-slice mini-loaf — is a decision worksheets cannot ask. **PASS.**
3. **Does the fantasy require the math?** Yes. Cannot reach checkout without correct scaling. **PASS.**
4. **Would a teacher use this?** Yes, with caveats — no teacher mode, no data export, no way to lock diner counts. Feature, not blocker.
5. **Respects the child's time?** Yes. 3-lives structure with preserved stars on retry.

**Verdict: PASS.** Not archived to `kill-log.md`.

---

## Stage 3 — Fantasy integrity

| Question | Answer |
|---|---|
| Would a real home cook do this math? | Yes, verbatim, weekly |
| Does failure break the world? | Yes — "The dinner guests went home hungry! 😢" |
| Is the signature moment named? | Informally — the **3-star checkout receipt** is the beat |
| Would a child describe this with math or theme? | Theme ("shop for dinner") — correct |
| Is the world-break authored, not generic? | Yes |

**Score: 9/10.** Recommendation: explicitly name the signature beat in docs as **"the perfect receipt"** so future contributors know what to protect during revisions.

---

## Stage 4 — Interaction map

The real system has four interactive surfaces, each authored well:

1. **Grid movement** with 120ms debounce. Arrow/WASD + D-pad on touch.
2. **Space to grab/return.** Tile-aware: first Space on a visited shelf returns a pack, re-entering a shelf and pressing Space grabs another. Clever and elegant.
3. **Live DOM recipe panel** on the right, rebuilt per level, with real-time "In cart: 0 slices" updates.
4. **Checkout zone** as a *validated door* — walking onto it runs a cart-correctness check and either opens the receipt or bounces with a toast.

### Observed issues — design warts (not bugs; those go in QA)

| # | Severity | Issue |
|---|---|---|
| W-1 | MEDIUM | **No pause.** `P`/`Escape` do nothing. Global UX contract violation. |
| W-2 | MEDIUM | **No mute.** Currently moot (no audio), becomes critical when audio lands. |
| W-3 | LOW | Movement debounce (120ms) feels sluggish to keyboard players. Drop to 90ms. |
| W-4 | HIGH | **No audio at all.** No grab sound, error tone, ambient hum, or tick. Juice-floor violation — scoring 0/6 audio criteria. |
| W-5 | MEDIUM | No hint key. Stuck players have no recovery path except restart. |
| W-6 | LOW | Recipe panel doesn't highlight the ingredient the player is currently standing next to. A "you're here" glow would reduce context-switching cost. |

All W-items are additive — they don't require rewriting anything, just adding.

---

## Stage 5 — Core loop

**Current loop sentence:** *Read recipe → scale in head → navigate → grab packs → head to checkout → get stars.*

**Observed payoff moments:**
1. Toast + particle burst on grab (every grab)
2. Blocked checkout with specific toast ("Bread: need 10, have 8")
3. Checkout receipt with star rating
4. Level-up unlock pulse on the menu

**Rhythm:** four payoff moments per level, with the star receipt as the climax. Good rhythm.

**Luck vs skill ratio:** ~15/85. The 15% luck comes from random diner count per play (`dinersOptions[random]`), which is actually a *feature* — different replays exercise different scale factors. Lower than most arcade games.

**Signature moment:** I'm designating the **3-star receipt with the `PERFECT — No waste, great time!` line** as the signature beat. Protect it: every future change to Grocery Dash must preserve or enhance that moment, never dilute it.

**Session shape:**
- L1–3: tutorial + scaling warm-up (0 NPCs)
- L4–5: NPC introduction (1 NPC)
- L6–8: NPC + chaser escalation
- L9–12: full chaos with variants

This curve is correct. Don't touch it.

---

## Review summary

**Ready for release with a minor-revision patch.** No structural changes needed. The game is well-designed, faithful to its math fantasy, and gates guess-through attempts effectively. The patch list (see `qa-report.md` and `patch-plan.md`) fixes the two real bugs and adds the three missing global-UX-contract features (pause, mute, audio floor). None of these require a rewrite.

**Next pipeline stages:** feel-audit, misconception-map, then `/team-audit` followed by `/release-checklist`.
