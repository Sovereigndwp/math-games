# Math Game Studio — Design Standards
## Graphic Bible · UX/UI Rules · Pipeline Gates

*Mandatory reading before any game enters Stage 7 (Multisensory Spec).*
*Every rule here becomes a pipeline gate. Violation = REVISE, not a suggestion.*

---

## Part 1 — The Graphic Bible

A Graphic Bible defines the visual contract for every game this studio ships. It prevents visual drift across builds, enables multiple contributors to work on the same asset simultaneously, and gives the Feel Audit Agent a concrete standard to check against.

Every game in production must have a Graphic Bible completed before any art or UI is produced. It is a living document — locked before build starts, updated only through a formal revision logged in `.governance/decisions.md`.

---

### 1.1 Color System

Every game declares exactly one color system. No ad-hoc hex values in code — only named tokens from the system.

**Required token categories:**

```
BACKGROUND   — deep, mid, surface (3 values)
PRIMARY      — the world's dominant accent
SUCCESS      — correct answer, world healed, door opened
DANGER       — wrong answer, guard alerted, heat rising
WARNING      — near-correct, timer urgent, noise rising
NEUTRAL      — HUD chrome, disabled states, muted text
TEXT         — primary, secondary, tertiary
```

**Naming convention:** `GAME_TOKEN_NAME` — e.g. `ECHO_SUCCESS`, `STAR_DANGER`

**Color derivation rule:** Success and Danger must be distinguishable by shape or intensity alone, not color alone. Every game is colorblind-safe by default. Test by converting to grayscale — all states must remain distinct.

**Pantone alignment:** For each game, the primary color maps to its closest Pantone equivalent. This is the anchor — all other colors derive from it using consistent relationships (complement, triad, analogous).

| Game | Primary | Pantone | HEX |
|---|---|---|---|
| Echo Heist | Phosphor green | Pantone 802 C | `#00FF6E` |
| Star Courier | Cosmic gold | Pantone 7405 C | `#F0B400` |
| (new game) | — | — | — |

---

### 1.2 Typography System

Two fonts maximum per game. Selected from Google Fonts. Never Arial, Inter, Roboto, or system-ui.

**Roles:**
- **Display font** — titles, scores, countdowns. Always has personality. Monospace for tech/heist games, rounded-slab for K-2 worlds.
- **Body font** — prompts, labels, hints. Legible at 11px. Never decorative.

**Size scale (no other sizes permitted):**
```
48px — titles, major states (DETECTED, MISSION COMPLETE)
28–36px — score, timer, key numbers
16–18px — math prompt text
13–14px — HUD labels, stat values
10–11px — micro labels, keyboard hints
```

**Weight rule:** Two weights only — regular (400) and bold (600–700). No intermediate weights.

**Current approved pairs:**
| Game | Display | Body |
|---|---|---|
| Echo Heist | Share Tech Mono | Rajdhani |
| Star Courier | Boogaloo | Nunito |
| K-2 default | Fredoka One | Quicksand |
| 3-5 default | Righteous | Jost |

---

### 1.3 Character & World Style Sheets

For every game, before production, the following must be drawn or described in the Graphic Bible:

**Player character:**
- 4 states minimum: idle, moving, crouching/interacting, caught/failed
- Color: always matches the selected class or role — never generic gray
- Size relationship to tile: documented as a ratio (e.g. `0.6 × TILE`)
- Animation principle: which of the 12 Disney principles apply (squash/stretch, anticipation, follow-through)

**Antagonists / obstacles:**
- Visual state machine: patrol color, alert color, chase color — documented as hex
- Vision cone: opacity, color, and how it changes per state
- Alert icon: what symbol, what color, what size — standardized across all games

**Interactive objects:**
- Terminal: must pulse at a documented frequency (e.g. `sin(t/500) × 0.2 + 0.8`)
- Door (locked): color `#8b4513`, keypad glow `#ffcc00`
- Door (open): always visually distinct — darker, receded
- Loot / target object: gold diamond, size `24px tall`, pulse documented
- Exit: `#00ff44` at 53% opacity with "EXIT" label, `20px monospace` — consistent across all games

**Feedback overlays (floating world-space text):**
- Correct: `#22c55e`, 14px bold, rises 2 tiles over 2.2 seconds
- Wrong: `#ef4444`, 14px bold, stays static for 1.5 seconds
- Escape gate open: `#22c55e`, emoji + text
- Blocked exit: `#ef4444`, emoji + text, maximum 1.8 seconds

---

### 1.4 Environment Style

**Tile color palette (consistent across all heist/stealth games):**
```
Floor:       #1a1f2e
Wall:        #2a2d3a  (never pure black — must have warmth)
Carpet:      #1a2a1e  (noise-reducing — visually softer)
Metal:       #2a2a2e  (noise-generating — visually colder, crosshatch pattern)
Door locked: #8b4513
Door open:   #3a2a1a
Terminal:    #0d2137  (with cyan glow)
Exit:        #0f3d1a  (green tint — safety signal)
Loot:        #2a2a1a  (gold accent on top)
```

**Grid lines:** Always `rgba(255,255,255,0.03)` — present but never dominant.

**Background:** Dark (`#0a0a0f`) with subtle ambient — never pure black, never gradients as decoration. Only canvas-drawn atmosphere.

---

### 1.5 HUD Layout Standard

The HUD is a fixed contract. Every game follows this layout:

```
┌─────────────────────────────────────────────────────────────┐
│ TOP BAR (38px)                                              │
│ [Class chip + name]  [Mission ID + name]  [Objective]  [$Score] [Timer] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                  GAME WORLD CANVAS                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ BOTTOM BAR (40px)                                           │
│ HEAT ████░ NOISE ████░ │ MATH n/n │ ABILITY │ GADGET │ ECHO │ STATUS │
└─────────────────────────────────────────────────────────────┘
```

**Top bar rules:**
- Background: `rgba(5,8,16,0.96)` — frosted, not opaque
- Accent underline: horizontal gradient fade `rgba(primary,0.3)` — never solid line
- Class chip: colored background `primary + "22"` (8% alpha), matching text

**Bottom bar rules:**
- Each instrument has a 2-line layout: label (9px, muted) above, value (11–13px bold) below
- Meter bars: `roundRect` with track background `rgba(255,255,255,0.05)`, colored fill
- Status (loot/escape) always right-aligned
- Controls hint: `9px monospace`, `rgba(71,85,105,0.4)` — barely visible, always present

---

## Part 2 — UX/UI Non-Negotiables

These are hard rules enforced at Stage 9 (UX Continuity Agent) and Stage 11 (Feel Audit). No exceptions.

---

### 2.1 Prompt Randomization (NEW HARD RULE — Priority 1)

> **Prompts are functions, not strings. Numbers are generated at runtime, not authored. No player sees the same problem twice on any retry of any level. Ever.**

**Implementation rule:**
- All `mission.prompts`, `mission.vaultPrompts`, and `mission.escapePrompts` must be populated inside `loadLevel()`, never at module initialization time
- Every template must be a function calling `Math.random()` at invocation
- Curriculum alignment (which skill type a prompt tests) is fixed. The numbers are not.
- The answer must be computed from the generated inputs — never hardcoded alongside hardcoded inputs

**Pipeline gate:** Stage 8 build agent checks that `mission.prompts` is an empty array in MISSIONS data and populated only inside `loadLevel()`. Any game where prompts are pre-populated at parse time FAILS this gate.

---

### 2.2 Exit / Gate Logic (Bug Class: Escape Bypass)

> **No mission-critical path may be bypassed. If a gate exists, the gate must be solved before the destination is reachable.**

**Implementation rule:**
- Exit tile (`T.EXIT`) must not trigger `finishMission()` unless all escape gates for the current phase are solved
- Track `escapeGatesTotal` (set at `startEscape()`) and `escapeGatesSolved` (incremented per gate solution)
- If player reaches EXIT with unsolved gates: push player back, show feedback overlay, do not finish
- HUD must always show gate status during escape phase — never leave player guessing why exit doesn't work

**Pattern to follow:**
```javascript
if (escapeGatesTotal === 0 || escapeGatesSolved >= escapeGatesTotal) {
  finishMission();
} else {
  const gatesLeft = escapeGatesTotal - escapeGatesSolved;
  // Show feedback + push player back
}
```

**Applies to:** Any game with a gated exit, locked door on critical path, or sequence-dependent unlock.

---

### 2.3 Responsiveness

- Every tap or keypress must produce a visual response within 100ms
- Canvas renders at 60fps via `requestAnimationFrame` — never `setInterval`
- Math popup appears with an entry animation (`popupIn`, `0.16s ease-out`) — never instant
- Feedback text appears immediately on answer submission — no delay before the player sees the result

---

### 2.4 Multisensory Completeness

Every meaningful game event must have all three channels:

| Event | Visual | Audio | Haptic |
|---|---|---|---|
| Correct answer | Particle burst + feedback text | Ascending tone sequence | Short pulse |
| Wrong answer | Screen shake + red particles + feedback | Sawtooth buzz | Double pulse |
| Critical success (vault cracked, planet lit) | World-state change + big particles | Multi-note chord | Sustained |
| Session end | Full celebration (confetti/constellation) | Fanfare | Long pattern |
| Blocked action | Feedback overlay | None (silence is sharp) | None |

Missing any channel on a primary event = **Feel Audit deduction**.

---

### 2.5 No Reading Required for K-2

For any game targeting grades K-2:
- Core loop interaction requires zero reading (tap, drag, visual matching)
- Reflection prompts use emoji/icon faces — no multiple choice text
- Error feedback is visual and emotional (creature sad, overflow animation) — never just red text
- The only text that may appear: numbers, which are the learning target

---

### 2.6 Font Rules

- Never use: Arial, Helvetica, system-ui, -apple-system, Inter, Roboto
- Always load from Google Fonts via `@import` or `<link>`
- Font must be loaded before first render — use `document.fonts.ready` in self-gate check
- Math prompt text: minimum 16px, font-weight 600, high contrast on dark background

---

### 2.7 Touch Targets

- All interactive elements: minimum 48×48px tap area
- Fragment/answer buttons: 58–64px
- HUD instruments: display only, not interactive (no accidental taps during gameplay)
- Math input: full-width, minimum 44px tall, large font (18–20px)

---

## Part 3 — Open Source Tools & Engine Standards

This studio builds HTML5 Canvas games — self-contained, no build step, no server. The following tools and references inform our technical decisions.

---

### 3.1 Rendering Philosophy

We use **Canvas 2D** as the primary rendering system. Every animated world element is drawn in the game loop — no CSS animations for gameplay elements.

**Why Canvas over CSS:**
- Shake, particles, world-state changes all need frame-accurate control
- CSS animations don't compose with game state (you can't pause them on focus-mode activation)
- Canvas gives us pixel-level control for the feel layer

**Canvas patterns we enforce:**
```javascript
// Shake via translate — affects world, not HUD
ctx.save(); ctx.translate(shakeX, shakeY);
// ... draw world ...
ctx.restore();
// HUD drawn after restore — unaffected by shake

// Easing via lerp — nothing moves linearly
jarDisplayLevel += (target - jarDisplayLevel) * 0.15;

// Particles via physics — gravity, drag, rotation
p.vy += p.gravity; p.vx *= p.drag; p.vy *= p.drag;
```

---

### 3.2 Audio Philosophy

**Web Audio API only** — no external audio files, no libraries.

Every sound is synthesized procedurally:
- Correct: sine wave, ascending frequency sequence
- Wrong: sawtooth wave (intentionally harsh — feels wrong by design)
- Ambient tension: triangle oscillator, very low frequency (55Hz), barely audible
- Fanfare: multiple oscillators, staggered start times

**Why procedural audio:**
- Zero load time, zero network requests
- Pitch variation (±8%) prevents monotony on repeated sounds
- Audio unlocks on first user gesture — always initialize `AudioContext` on first keypress/tap

**Haptic standard:**
```javascript
navigator.vibrate && navigator.vibrate([pattern]);
// Correct: [15, 10, 60]  — tap, pause, sustain
// Wrong:   [80, 20, 80]  — double thud
// Success: [20, 10, 50, 10, 100] — celebration pattern
```

---

### 3.3 Godot Reference Standards

When designing mechanics, reference Godot's approach as a quality benchmark — even though we build in Canvas:

**Godot's node-based scene system** → our equivalent: each game state has a clean entry/exit (`loadLevel`, `startEscape`, `finishVault`). State changes never leave orphaned event listeners or running timers.

**Godot's signal system** → our equivalent: explicit function calls on state transitions. Never modify game state inside draw functions.

**Godot's Area2D detection** → our equivalent: AABB collision with separate X and Y axis resolution. Player slides along walls rather than stopping.

**Godot's AnimationPlayer** → our equivalent: decaying lerp values updated in the game loop. `jarDisplayLevel`, `softstepFlashTimer`, `shakeAmp` decay each frame — same principle as keyframe interpolation.

---

### 3.4 Useful Open Source References

| Resource | What to learn from it |
|---|---|
| **Godot Engine** (godotengine.org) | Scene organization, node architecture, physics principles |
| **Phaser 3** (phaser.io) | Game state machine patterns, input system design |
| **LittleJS** (github.com/KilledByAPixel/LittleJS) | Minimal Canvas game loop, particle system architecture |
| **Kaboom.js** (kaboomjs.com) | Scene/object lifecycle, component patterns |
| **GDC Vault** (gdcvault.com) | Game feel talks — "The Art of Screenshake" (Vlambeer) is required viewing |
| **gamedesignskills.com** | Mechanics reference, stealth design principles |
| **Kavex/GameDev-Resources** (GitHub) | Curated tool list — Material Maker, Aseprite, open asset pipelines |

---

## Part 4 — The Screenplay Standard

Every game with narrative context (character, mission, world consequence) requires a non-linear interaction script before build. This is not optional flavor text — it is the spec for every piece of text a player reads.

**Required documents:**

**1. World Context Brief (1 page)**
- Who is the player character and what is their role?
- What does the world look like before the player succeeds?
- What does the world look like after?
- What does failure feel like — emotionally, visually, in the world?

**2. Interaction Script**
For every prompt type in the game, one authored example showing:
- The narrative frame (who is speaking, what is the situation)
- The math action (what the player is literally solving)
- The world consequence (what happens when correct / wrong)

Example from Echo Heist:
> *Frame:* Security node blocks corridor. Guard patrol approaches in 45 seconds.
> *Action:* Solve `3x + 8 = 35` to spoof the node signature.
> *Correct:* Node blinks green. Path clears. Guard passes without triggering alert.
> *Wrong:* Heat +5. Node flashes red. 3 seconds of guard alertness.

**3. Feedback Library**
All floating feedback text, HUD messages, and state labels — written once, used consistently. No improvised strings in code.

| State | Text | Color | Duration |
|---|---|---|---|
| Door unlocked | 🔓 DOOR UNLOCKED | `#22c55e` | 2.2s |
| Camera disabled | 📷 CAMERA DISABLED | `#22c55e` | 2.2s |
| Gate open | 🚪 GATE OPEN | `#22c55e` | 2.2s |
| Vault cracked | 🔐 LOCK CRACKED! | `#ffd700` | 2.0s |
| Exit blocked | ⛔ N GATE(S) — SOLVE FIRST | `#ef4444` | 1.8s |
| Heat warning | ⚠ HEAT CRITICAL | `#ef4444` | 1.5s |

---

## Part 5 — Pipeline Gate Summary

| Gate | Stage | Rule | Result of failure |
|---|---|---|---|
| Prompt randomization | Stage 8 Build | `mission.prompts` populated in `loadLevel()`, not at parse time | REJECT build |
| Exit bypass prevention | Stage 8 Build | Exit checks `escapeGatesSolved >= escapeGatesTotal` | REJECT build |
| Font compliance | Stage 11 Feel Audit | No Arial/Inter/Roboto in font stack | Feel Audit deduction |
| Touch targets | Stage 11 Feel Audit | All interactive elements ≥48px | Feel Audit deduction |
| K-2 no-reading | Stage 9 UX Contract | Reflection prompts emoji-only | REJECT build |
| Graphic Bible complete | Stage 7 Multisensory Spec | Color tokens named, font pair declared, HUD layout documented | Gate blocked |
| Audio on all primary events | Stage 11 Feel Audit | Correct/wrong/vault/session each have audio | Feel Audit deduction |
| Haptic on primary events | Stage 11 Feel Audit | Correct/wrong/critical each have vibrate() | Feel Audit deduction (mobile) |
| Canvas 2D rendering | Stage 10 Build | Animated elements drawn in RAF loop, not CSS animation | REVISE |
| Feedback library used | Stage 10 Build | All floating text drawn from approved feedback strings | REVISE |

---

*Last updated: April 2026*
*Owner: Studio pipeline. Changes require ADR entry in `.governance/decisions.md`.*
