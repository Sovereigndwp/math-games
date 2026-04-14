# Grocery Dash — Misconception Map

**Stage 12 artifact.** The top errors a 3rd–6th grader will make, predicted from the actual math model in the shipping game (multi-step scaling with pack-size variants), ranked by likely frequency.

Each entry includes the misconception, an expected frequency, the telemetry event name to emit, and teacher-voice copy for the checkout receipt when this error is detected.

---

## M1 — Forgets to scale (grabs recipe-as-written amounts)

**Frequency prediction:** ~30% on first attempt, dropping to ~5% after L3
**Telemetry event:** `gd_missed_scale`
**Detection signal:** `gotUnits === recipeAmt` but `needUnits > recipeAmt`
**Teacher copy:** *"The recipe serves {serves}, but you're feeding {diners}. You bought enough for {serves} — try multiplying everything by {scale}× first."*

---

## M2 — Scales correctly but forgets to ceiling-round packs

**Frequency prediction:** ~25%
**Telemetry event:** `gd_under_by_one_pack`
**Detection signal:** `gotUnits < needUnits` AND `gotUnits + packSize >= needUnits` (one more pack would have worked)
**Teacher copy:** *"You needed {needUnits} {unit} and one pack is {packSize}. You got {gotPacks} packs = {gotUnits}. Always round UP — better too much than not enough."*

---

## M3 — Picks the wrong pack-size variant (leaves waste)

**Frequency prediction:** ~15% — this is unique to this game's variant mechanic
**Telemetry event:** `gd_wasteful_variant_choice`
**Detection signal:** `avoidableExtra > 0` in the checkout results (the game already computes this)
**Teacher copy:** *"You got enough {ingredient}, but you could have wasted less by picking a different pack size. The {smallerPackLabel} is {smallerPackSize} per pack — try that next time for no waste."*

This is the signature misconception of Grocery Dash. Most edu-games can't even ask this question. Every telemetry hit here is a learning opportunity that wouldn't exist on a worksheet.

---

## M4 — Multiplies by diners instead of by scale factor

**Frequency prediction:** ~12%
**Telemetry event:** `gd_scaled_by_diners`
**Detection signal:** `gotUnits === recipeAmt × diners` (not `recipeAmt × diners/serves`)
**Teacher copy:** *"Recipe serves {serves}, diners are {diners} — you multiplied by {diners} instead of {diners}÷{serves}={scale}. The multiplier is diners ÷ servings, not just diners."*

This happens most often when `serves = 1` and diners is small, because the two answers coincide and the child gets the right answer for the wrong reason. First appearance of a `serves > 1` level (L2: Pancake Breakfast, serves 4) is where this misconception surfaces.

---

## M5 — Grabs a distractor thinking it's a recipe item

**Frequency prediction:** ~8%
**Telemetry event:** `gd_grabbed_distractor`
**Detection signal:** any distractor with `packsInCart > 0` at checkout gate
**Teacher copy:** *"You put {distractorName} in the cart, but it's not on the recipe. Check the recipe card carefully and put it back before heading to checkout."*

The game already blocks checkout in this case with a toast, which is good — the misconception becomes a self-correcting loop. Teacher copy is for the retrospective, not the mid-level toast.

---

## M6 — Correct math but runs out of time

**Frequency prediction:** ~6%
**Telemetry event:** `gd_timeout_with_correct_math`
**Detection signal:** gameover triggered AND final cart would have passed checkout
**Teacher copy:** *"Your math was right — you just ran out of time. Try planning your aisle route before you start moving. Tip: press H to see the recipe card while playing."*

This is a different *kind* of error — the child has the skill, they lack the pacing. Deserves a different scaffold (route planning) rather than a math scaffold.

---

## M7 — Stuck on ingredient with two variants, doesn't realize they can mix

**Frequency prediction:** ~4%
**Telemetry event:** `gd_single_variant_lock`
**Detection signal:** the player grabbed from only one variant shelf on an ingredient where mixing variants would have produced less waste
**Teacher copy:** *"For {ingredient}, you used only the {usedPack}. You could have used some {otherPack} too — mixing pack sizes is allowed, and sometimes it wastes less."*

This is advanced. It won't appear until L5+ where multiple variants exist per ingredient. Worth detecting as a hint that the child has mastered scaling but not yet optimization.

---

## Other — uncategorized

**Frequency prediction:** ~3%
**Telemetry event:** `gd_other`
**Teacher copy:** generic retry encouragement

---

## Telemetry bus stub

The current game emits nothing. To make this misconception map actionable, add a `emit(event, payload)` function that logs to `console.log` in the shape `[TELEMETRY] {event} {payload}`. A future backend can capture these events without code changes. Total cost: ~15 lines in the checkout screen.

```javascript
function emit(event, payload) {
  if (typeof console !== 'undefined') {
    console.log(`[TELEMETRY] ${event}`, JSON.stringify(payload));
  }
}
```

Then in the checkout result calculation, detect each misconception and call `emit` once per error class. The game doesn't need to visibly change — this is a silent observability layer that makes the next iteration's A/B tests possible.

---

## How this feeds the pipeline

Every telemetry hit becomes a row in the game's `.reviews/grocery-dash/telemetry-review.md`. After N sessions, the retrospective can show actual frequency numbers against these predictions and adjust level tuning accordingly. That's the learning loop the pipeline exists to enable.

**Prediction accuracy target:** after the first 100 sessions, predicted and actual frequencies should agree within ±10 percentage points. If they don't, the misconception map gets revised and the lesson goes into `.lessons/grocery-dash/`.
