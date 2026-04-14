# Lessons Captured from Grocery Dash

**Source:** reading and auditing `grocery_dash_v2.html` (the actual shipping game, not a prior guess)
**Feeds:** `.lessons/grocery-dash/`, `.lessons/patterns-that-work.md`, `.lessons/patterns-that-break.md`, and a proposed update to `.contracts/global-ux.md` and the Stage 0 concept-intake agent prompt.

Each lesson is stated in a form that can be referenced from future games as a concrete rule, not a vibe.

---

## Patterns that worked (for `patterns-that-work.md`)

### L1 · The fantasy-first naming rule

**Observation:** Every level in Grocery Dash is named after a real dinner — *Grilled Cheese, Pancake Breakfast, Taco Night, Mac & Cheese, Pasta Bolognese, Sushi Night.* Not one level is named after its math mechanic.

**Why this matters:** When I (incorrectly) audited the game sight-unseen, I wrote level names like *The Warm-Up, Big Scale, Ceiling Division, The Messy Multiplier.* Those names describe the *math*, which is what I — a pipeline auditor — cared about. They do not describe what the player is doing. A child does not sit down to play "Ceiling Division." A child sits down to play "Taco Night" and then, incidentally, learns ceiling division.

**Rule for future games:** level names are dinner names, mission names, animal names, destination names — whatever the fantasy noun is. Never name a level after its mechanic. If a contributor proposes a level name and you can tell what the math is from the name alone, the name is wrong.

**Apply to:** every educational game in the portfolio. Add to the Stage 0 concept-intake agent as a hard check.

---

### L2 · Pack-size variants are a unique-to-game mechanic

**Observation:** Grocery Dash's core math isn't "scale a recipe and ceiling-divide." It's "scale a recipe, then choose which pack size produces the least waste, possibly mixing variants." The game detects *avoidable overshoot* separately from *total overshoot* and uses that distinction to award stars.

**Why this matters:** Worksheets cannot ask "given these two pack sizes, which wastes less?" You need a game state to present the choice. This is one of the few math mechanics that is *strictly better* in interactive form than on paper. It earns the game's existence.

**Rule for future games:** when designing a math mechanic, explicitly ask "is this better than a worksheet?" If the answer is "the game makes it faster" or "the game makes it more fun," that's insufficient. The answer must be "the game lets the child do something a worksheet literally cannot present." Otherwise the game is an expensive worksheet.

**Apply to:** Stage 2 kill-test. Add as a scored dimension, not just the existing yes/no.

---

### L3 · DOM-based side panels beat canvas-based text

**Observation:** Grocery Dash puts the recipe card in a real DOM element on the right side of the canvas, not inside the canvas itself. It updates in real time via `textContent` assignment. The font is crisp at any zoom level, the text is selectable, and a screen reader can read it.

**What I did wrong in my rebuild:** I put the recipe card inside the canvas as drawn text, rebuilt every frame. That meant the font couldn't be system-ui-rendered, text couldn't be selected, and accessibility tools saw nothing.

**Rule for future games:** anything that is *text-heavy and persistent* — recipe cards, score panels, tutorial cards, settings — should be HTML/CSS, not canvas. Canvas is for the game world. HTML is for the information architecture around it. The existing engine conventions in `echo-heist-final.html` and `orbital-drift_2.html` use canvas for text, and they're wrong about that too — Grocery Dash got this right.

**Apply to:** update `.contracts/global-ux.md` with a rule: *text-heavy UI lives in DOM, not canvas. Canvas is for the world.*

---

### L4 · The "validated door" pattern for checkout/submit

**Observation:** Grocery Dash does not show the checkout receipt if the cart is wrong. Walking onto the checkout tile triggers `isCartReady()`; if the cart fails, the player gets a toast ("Bread: need 10, have 8") and stays in the store. The receipt only appears once the cart is actually plausible.

**Why this matters:** The obvious design is "let the player submit whenever, then show the receipt with errors highlighted." That's what I imagined in my prior audit. The obvious design is worse. It turns the checkout screen into a slot machine — submit, read error, fix, submit again, read error. The validated-door pattern forces the player to *think before submitting*, which is what the game is supposed to teach.

**Rule for future games:** when an action commits the player's work for evaluation, the default should be "refuse to accept obviously-wrong submissions with specific feedback" rather than "accept anything and grade it." The "obviously wrong" threshold depends on the mechanic. For Grocery Dash it's short + distractor + overshoot-beyond-unavoidable.

**Apply to:** any game with a submit/checkout/cast-spell/launch action. Add as a `.contracts/brilliant-rules.md` entry.

---

### L5 · Star ratings with named tiers beat score

**Observation:** Grocery Dash's checkout screen shows `★★★ PERFECT SHOP!` with a named descriptor per tier:
- 3 stars: "⚡ PERFECT — No waste, great time!"
- 2 stars: "Well done! Aim for no waste + 35s+ for 3 stars"
- 1 star: "Completed! Try again with no wasted ingredients for more stars"

Each tier has a *named goal* the player can see. The 2-star tier literally tells you how to reach 3 stars.

**Rule for future games:** progression scoring should be tiered (3 or 4 levels) with explicit improvement hints at each level below max. Pure numeric score is flat — "you got 1,847 points" tells the child nothing about what to do next. "⚡ PERFECT — No waste, great time!" is a target they can aim at.

**Apply to:** every future game's results screen. Add as a rubric check in `/feel-audit`.

---

### L6 · Group color palettes as invisible spatial scaffolding

**Observation:** Grocery Dash defines a `GRP` constant mapping food groups to colors:
```javascript
const GRP = { produce:'#4ade80', grain:'#facc15', dairy:'#60a5fa', protein:'#f87171', condiment:'#fb923c' };
```

Every particle burst, every ingredient card accent, and every shelf tint uses these colors consistently. A child learning "green = produce" across 12 levels has acquired a free spatial search heuristic.

**Rule for future games:** whenever the game has a natural taxonomy (food groups, element types, creature families, mission categories), lock a color palette for it at Stage 7 and use those colors *consistently* across particles, UI accents, and world objects. Consistency is the lesson — not the palette itself.

**Apply to:** Stage 7 multisensory-spec agent. Add a "taxonomy palette check."

---

## Patterns that broke (for `patterns-that-break.md`)

### B1 · Never audit a game you haven't read the source of

**What went wrong:** In the prior turn, I produced a full audit dossier for Grocery Dash based on the itch.io page copy, screenshots, and my model of what the game "probably" was. I then proposed a rewrite based on that audit. When the actual source was uploaded, it turned out I had gotten the core math model wrong (pack-size variants, not ceiling division), invented level names that don't exist, and recommended removing features the game already has.

**The cost:** An entire audit dossier and a reference build had to be retracted. Worse: if that audit had been committed to the repo without a source read, it would have become a durable piece of "truth" that later agents would have trusted. The pipeline's whole point is auditable, versioned knowledge. Fake audits poison the lessons library.

**Rule:** The Stage 0 concept-intake agent must be blocked from producing any artifact until the source file of the current build is loaded into its context. If no source is available, the only valid artifact is a *concept brief for a new game*, not an audit of an existing one. This should be enforced at the gate-engine level — `concept-intake` reads `.games/<slug>/src/` and fails with "source not available" if the directory is empty.

**Add to `.contracts/global-ux.md`:** section "Auditing existing builds":
> An audit of a shipping or in-development game must cite line numbers from the actual source file. An audit without line citations is a concept proposal, not an audit. The Stage 0 agent must refuse to mark an audit as `PASS` or `REVISE` without source evidence.

**Add to Stage 0 agent prompt:** a hard check: "if `source_file` is empty, emit `blocker: source_required` and halt."

---

### B2 · Authored-but-unused content is noise

**What went wrong:** Grocery Dash has a `budget` field on every level and a `price` field on every ingredient and distractor. Zero code reads these fields. The `#spent-info` CSS class exists but no element with that ID is ever created. The economy/budget mechanic was scaffolded and then forgotten. A future contributor reading the source sees `budget: 40.00` and reasonably assumes there's a budget mechanic. There isn't.

**The cost:** Future work is built on a mistaken mental model. Someone writes a blog post saying "Grocery Dash has a budget mechanic" and the company has to quietly correct them. Or worse, someone "optimizes" the levels' budget fields without realizing they change nothing.

**Rule:** Every data field in a game's content bank must be *consumed by at least one code path at runtime*. If a field is reserved for a future feature, it must be marked with a `// RESERVED:` comment pointing to the concept slug that will consume it. Otherwise delete it.

**Add to Stage 8 content-bank agent:** a static check that every field on every level and every ingredient is either consumed by at least one code reference or annotated `RESERVED`. Unannotated dead fields fail the gate.

---

### B3 · The NPC-drain pattern: penalizing the wrong agent

**What went wrong:** Grocery Dash has two paths for player-NPC collision:
- Player walks into NPC: player loses 5s, NPC teleports away (correct)
- NPC walks into player: player loses 5s, NPC stays (bug)

The second path is wrong because the player didn't cause the collision. The NPC did. Penalizing the player for something they didn't do feels arbitrary, and because NPCs re-try moves every ~500ms, a stationary player bleeds time continuously.

**Rule:** When two agents can collide, be explicit about *which agent's action triggered the collision* and penalize only that one. If the collision is "agent A moves into agent B's tile," the penalty is on A, not B. Always. This is a general rule, not a Grocery Dash rule.

**Add to `.contracts/brilliant-rules.md`:** section "Collision attribution":
> When two agents can collide, the penalty applies to the *moving* agent, not the stationary one. A stationary player should never lose resources to an AI-driven agent walking into them.

---

### B4 · Resize handlers with implicit state lists

**What went wrong:** The resize handler in Grocery Dash explicitly lists three screens to rebuild (`menu`, `levelintro`, `checkout`). It omits two others (`gameover`, `win`). The handler works fine until someone adds a new screen state and forgets to update the handler.

**Root cause:** This is a *positive list* where every state that needs rebuilding has to be named. Adding a new state requires remembering to update multiple places. Easy to miss.

**Rule:** Any registration-style code (resize handlers, input handlers, draw dispatchers, state machines) should use a *registry pattern* where states register their own rebuild hooks, not a hard-coded if/else chain. For a small game a 5-line object literal is enough: `const SCREEN_BUILDERS = { menu: makeMenuSc, levelintro: makeLevelIntroSc, checkout: makeCheckoutSc, gameover: makeGoSc, win: makeWinSc };`. Then the resize handler just runs `SCREEN_BUILDERS[gs]?.()`. Adding a state means adding a line to one object.

**Add to `.contracts/brilliant-rules.md`:** section "Positive lists are code smell":
> If adding a new feature requires updating multiple separate if/else chains, refactor to a registry object before adding the feature. Positive lists reliably drift out of sync.

---

### B5 · Side-effecting UI builders

**What went wrong:** `makeGoSc()` in Grocery Dash looks like a pure UI builder that returns a drawable screen object. But its *first two lines* decrement `lives` and update the lives HUD. That means you cannot re-call `makeGoSc()` idempotently — every call eats a life.

**The cost:** The resize handler can't rebuild the gameover screen on window resize without double-penalizing the player. This is why B2 in the QA report needs a two-part fix: move the side effect out, then extend the handler.

**Rule:** Functions named `make*` or `build*` or `render*` should be *pure builders* with no side effects beyond constructing the return value. State changes (decrementing lives, saving scores, updating HUD) belong at the *cause site* — the place where the game decided the state should change — not at the *display site* where the result is rendered.

**Add to `.contracts/brilliant-rules.md`:** section "Builder purity":
> UI builder functions must be idempotent. A UI builder may read game state but must not mutate it. State mutations belong in event handlers and state transitions, not in render functions.

---

## Cross-cutting recommendations for the pipeline itself

Two of these lessons (B1 and B2) suggest changes to how the pipeline *operates*, not just what it produces.

### R1 · Stage 0 agent needs a source-required gate

See B1 above. The gate engine should reject any audit artifact that cannot cite specific line numbers from the source. Concrete spec for the gate:

```yaml
# gate.yml addition
audit_must_cite_source:
  when: stage == 0 || stage == 11 || stage == 12
  requires:
    - source_file_present: true
    - citation_count: ">= 3"
  on_fail: blocker: "audit requires source file evidence"
```

### R2 · Stage 8 content-bank agent needs a dead-field linter

See B2 above. A simple static check: parse the content bank, collect every field name, and for each field verify it appears in at least one non-content code reference. Any field that doesn't, either flag as `RESERVED` in-source or delete.

### R3 · A new skill folder: `.skills/audio/`

The Web Audio tone stack in P-3 of the patch plan is the *third* instance of essentially the same code across this portfolio (`echo-heist-final.html`, `orbital-drift_2.html`, and now Grocery Dash after patching). That's the definition of a reusable skill. Extract to `.skills/audio/tones.js` with a documented API and have future games import it. Saves 60+ lines per game and guarantees consistent audio feel across the portfolio.

### R4 · A new skill folder: `.skills/dom-panels/`

The DOM-based recipe panel pattern in Grocery Dash is worth extracting. A skill for "persistent information panels next to a canvas game" would give future games free accessibility, better fonts, and simpler state management. The skill lives in `.skills/dom-panels/` with a `panel-spec.md` documenting the conventions.

---

## Summary: what the pipeline learned from this game

| Area | Lesson | Priority |
|---|---|---|
| **Auditing discipline** | Never audit without source | P0 |
| **Content governance** | Dead fields are noise; annotate or delete | P0 |
| **Naming** | Levels named after fantasy, not mechanic | P1 |
| **Math design** | Beat the worksheet test, not the fun test | P1 |
| **UI architecture** | DOM for text, canvas for world | P1 |
| **Feedback design** | Validated doors beat submit-and-grade | P2 |
| **Progression** | Named star tiers beat numeric score | P2 |
| **Visual language** | Taxonomy color palettes scaffold search | P2 |
| **Collision design** | Penalize the mover, not the stander | P2 |
| **Code structure** | UI builders must be pure | P3 |
| **Code structure** | Registry objects beat positive lists | P3 |
| **Portfolio tooling** | Extract audio and DOM-panel skills | P3 |

**These are the lessons the next 11 games inherit for free.**
