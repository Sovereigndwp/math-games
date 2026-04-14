# Grocery Dash — QA Report

**Source:** `grocery_dash_v2.html` (1,768 lines)
**Method:** static source read + Playwright runtime stress test across all 12 levels
**Runtime errors found in stress test:** **0** (excluding a Google Fonts CDN 407 that does not affect gameplay)

The game is functionally sound. The issues below are real and verified against the source, but none are ship-blockers on their own.

---

## Bugs verified in source

### B-1 · HIGH · Stationary-player NPC drain

**Location:** game loop, NPC movement block, the `tryDir` inner function:

```javascript
if(nc===player.c&&nr===player.r){
  timeLeft=Math.max(0,timeLeft-5);
  addToast('Excuse me! -5 seconds 🛒','#f87171');
  spawnParts(player.px+T/2,player.py+T/2,'#ef4444');
  updateUI(); return false;
}
```

**Symptom:** When an NPC's random-walk code tries to enter the player's tile, the code applies `-5s` and returns false. The NPC will keep re-attempting every `NPC_DELAY + random*200` ≈ 420–620ms. A player who stops next to an NPC to read the recipe panel gets drained repeatedly with no recovery.

**Why this is inconsistent:** the player-into-NPC path (in `tryMove`) correctly teleports the NPC to a far tile as a one-time penalty. The NPC-into-player path penalizes without relocating, producing an infinite drain.

**Fix (1 line):** remove the penalty from this branch. NPC walking into player becomes a blocked move with no cost; only player walking into NPC costs time. Correct game-design reading is that the player is responsible for collisions, not the NPC.

```javascript
if(nc===player.c&&nr===player.r) return false;  // blocked, no penalty
```

Alternatively, cap the penalty to once every 3 seconds with a shared `lastBumpAt` timestamp. Either works; the one-line fix is cleaner.

---

### B-2 · MEDIUM · Resize handler misses gameover/win screens

**Location:** lines 99–108:

```javascript
window.addEventListener('resize', () => {
  CX.setTransform(1,0,0,1,0,0); sizeCanvas();
  if(typeof gs !== 'undefined'){
    if(gs==='menu') enterMenu();
    else if(gs==='levelintro' && screen) screen=makeLevelIntroSc();
    else if(gs==='checkout' && screen) screen=makeCheckoutSc();
  }
});
```

**Symptom:** If the player resizes the window while on `gameover` or `win`, the PLAY AGAIN button's click hit-box stays at the old coordinates. Clicks land on empty canvas and do nothing. Only escape path is a full reload.

**Why it's non-trivial:** `makeGoSc()` decrements `lives` as a side effect. A naive rebuild on resize would double-decrement.

**Fix (2 parts):**

1. Move `lives--` out of `makeGoSc()` into the places that *cause* game over — the timer expiry path in `startLevelTimer` and any future life-loss event.
2. Add two branches to the resize handler:

```javascript
else if(gs==='gameover' && screen) screen=makeGoSc();
else if(gs==='win' && screen) screen=makeWinSc();
```

Both `makeGoSc` and `makeWinSc` then become pure view builders that can be re-called safely.

---

### B-3 · LOW · Dead code: `packsNeeded` and `unitsNeeded`

**Location:** lines 487–493.

```javascript
function packsNeeded(ing){
  return Math.ceil(ing.recipeAmt * getScale() / ing.packSize);
}
function unitsNeeded(ing){
  return ing.recipeAmt * getScale();
}
```

**Symptom:** Both defined, neither called anywhere in the file. Verified by grep — zero references.

**Impact:** None at runtime. Bloats maintenance surface and creates confusion about whether there's a central "how many packs do I need" source of truth. There isn't; the logic is inlined in `isCartReady`, `buildRecipePanel`, and the checkout screen, which is why these helpers went stale.

**Fix:** Delete them, **or** repurpose them as public helpers if you add a hint key (W-5 in the design review). My recommendation: **keep them** and wire them into a new hint system — the code is correct and useful, it's just missing its caller.

---

### B-4 · LOW · Dead data: `budget` and `price`

**Location:** every `LEVELS[].budget` field and every ingredient/distractor `price` field. Plus the CSS class `#spent-info` at line 37.

**Symptom:** Zero code references "budget", "price", "spent", or "cost" outside the `LEVELS` array declaration and one comment block. The `#spent-info` element with that CSS class is never created in HTML. The entire economy/budget mechanic was scaffolded and never wired up.

**Impact:** Authored-but-unused content noise. Signals a feature that was designed and abandoned or deferred, without a tracking artifact.

**Options:**

- **A — Delete.** Strip `budget` and `price` fields from every level, remove the `#spent-info` CSS, and note in the kill log that the economy mechanic is deferred. Cleanest short-term move.
- **B — Wire it up.** Add a price tracker, make checkout enforce the budget, change the star rubric to include "came in under budget." This is a real design decision that changes the difficulty curve and requires a full pipeline pass on its own concept slug (`grocery-dash-budget`).
- **C — Park it with a TODO comment.** Explicitly mark the fields as `// RESERVED — budget mechanic deferred to grocery-dash-budget` so future contributors don't delete them thinking they're dead.

**Recommendation: C.** It preserves the design intent without shipping unused code paths.

---

### B-5 · LOW · Chaser gets stuck on shelves

**Location:** game loop, chaser movement block, lines approximately 1710–1740.

**Symptom:** The chaser uses greedy Manhattan-distance pathfinding with no obstacle awareness. When a shelf column is directly between chaser and player, the chaser picks the direction that reduces Manhattan distance, hits a shelf, and in the next tick picks the same blocked direction again. The chaser wiggles in place or oscillates without making progress. On some levels the chaser never reaches the player at all.

**Is it a bug?** Technically no — the chaser "works" in that it moves. But it undermines the intended tension on levels with active chasers (L4+).

**Cheap fix (3 lines):** when all direction preferences are blocked, pick a random unblocked direction instead. The chaser wanders productively until it has a clear line.

**Full fix (~40 lines):** replace greedy with BFS over the tile grid, recomputed once per chaser-move tick. BFS on 21×17 = 357 cells is negligible cost. This is the right fix for release.

---

### B-6 · LOW · Dev cheat noise

**Location:** lines approximately 1622–1631, the `_devBuf` buffer.

**Symptom:** `_devBuf` accumulates every keyboard `e.key.toUpperCase()`. Arrow keys contribute `'ARROWUP'`, `'ARROWDOWN'`, etc., which is noise. The `slice(-6)` trim prevents unbounded growth, and the chance of accidentally spelling "UNLOCK" via arrow noise is effectively zero. Not exploitable.

**Fix:** gate the buffer on `e.key.length === 1` so only single-character keys contribute. Or delete the cheat before release. I'd keep the cheat for QA but clean the buffer.

---

## Stress test summary

**Method:** Playwright-driven browser, 12 levels × 20 random inputs per level, followed by a full checkout flow on Level 1 with an artificially filled valid cart.

**Results:**
- 0 runtime errors
- 0 console warnings (ignoring a Google Fonts CDN 407 that doesn't affect gameplay)
- All 12 levels render correctly
- All screens (menu, level-intro, tutorial, playing, checkout, gameover, win) draw without exception
- Timer cleanup is over-instrumented — 2 `setInterval` calls, 6 `clearInterval` calls, no leaks observed
- dt is clamped to 50ms on tab switch (good)
- localStorage access is wrapped in try/catch (good)

**Verdict:** The game is shippable as-is. The patch plan below is optional polish for release candidate, not a blocker.
