# Echo Heist — Repo Audit

**Date:** 2026-04-11  
**Auditor:** Claude (Sonnet 4.6)  
**Files inspected:** index.html (3363L), pass-1.html (1809L), playtest.js (326L), concept_packet_review.json ×2, promotion_record.json ×2, pass-1-record.md through pass-5-record.md

---

## Verified: what is implemented and trustworthy

`index.html` is the canonical Echo Heist game file at Pass 5. All five passes are implemented:

- **Pass 1:** WASD stealth, AABB collision, guard patrol/investigate/chase, vision cones + LOS raycasting, math popup (typed answers, equivalent forms), vault sequence, escape sequence, 3 classes (stats only), scoring, results screen
- **Pass 2:** Class abilities (Space), gadget (Q), Web Audio API, hint system (H), 30 missions across 3 districts, procedural level generator, district difficulty config
- **Pass 3:** Particle system, screen shake, guard wall avoidance (`moveEntityToward`), focus mode (Tab), mastery streaks, per-skill results breakdown, escape alarm audio, vault hint support
- **Pass 4:** D3 curated content (10 missions, 12 templates, authored prompts), scaffold panel (F), objective tracking, auto-hint after 2 wrong, localStorage persistence, 2 echo charges
- **Pass 5:** Class unlock progression, daily contract (D), mission select (S), ability VFX, ambient stealth drone (55 Hz triangle)

`pass-1.html` is correctly frozen at Pass 1 (1809 lines, no Pass 2+ systems).

The concept packet pipeline in `math-game-studio-os` produced valid, schema-versioned, SHA-256-hashed artifacts for `bakery-rush-mini` (v0.1.0) and `snack-line-shuffle-mini` (v0.2.0). The stub generator and draft promoter work. The `generated/` folder structure is consistent and machine-readable.

---

## Found: what is missing, fragile, or inconsistent

### Bug 1 — `checkAnswer` cross-format percent equivalence (in `index.html`)
`normalizeAnswer()` strips `%` from both sides before numeric comparison. This means `checkAnswer('50%', '0.5')` compares numeric 50 vs 0.5 and fails. The game shows `25%` as an accepted answer format in the UI, but prompts with decimal answers (e.g. `answer:'0.3'`) will reject `'30%'` from students who write the equivalent percent. The fix is to divide the user value by 100 when the user input contained `%` but the correct answer did not.

### Bug 2 — `showHint()` score deduction invisible at score = 0 (in `playtest.js`)
The test `assert(G.score < sb, 'H-key hint costs score')` fails because score starts at 0 and `Math.max(0, 0 - 50) = 0`. The deduction is real but clamped. This is a test design bug, not a game bug. Fix: initialize score > 0 before the hint test, or assert `G.totalHintsUsed > 0` instead.

### Naming drift — four conflicting self-identifiers on one file
`index.html` carries: `<title>Echo Heist — Pass 3</title>`, internal comment `Pass 2: Pressure & Progression`, internal comments `Pass 3`, `Pass 4`, `Pass 5` on various blocks. Pass records refer to `current.html`. The canonical name should be `index.html` and the title should reflect Pass 5.

### Broken CI — `playtest.js` reads `current.html`, not `index.html`
`fs.readFileSync(path.join(__dirname,'current.html'),'utf8')` crashes immediately in any checkout that contains only `index.html`. This is a 1-character filename fix.

### Unguarded `HOW_TO_PLAY` state in playtest
`echoHeistHasSeenIntro` reads localStorage on load. Headless tests always start at `HOW_TO_PLAY`, not `MENU`. The test's `simKey('Enter')` twice would advance through HOW_TO_PLAY→MENU→BRIEFING, but `handleBriefingKey` calls `startStealthDrone()` which creates an AudioContext oscillator — crashing headless if not stubbed. The fixed playtest pre-sets `localStorage._store['echoHeistIntroSeen'] = '1'` and uses `jumpTo()` to bypass menu/briefing.

### Pass record test count overclaim
| Pass | Record claims | Actual asserts at that time |
|------|--------------|---------------------------|
| 1 | 71 | 71 (plausible, not verifiable) |
| 2 | 213 | Not verifiable — file not frozen |
| 3 | 213 | Not verifiable — file not frozen |
| 4 | 304 | Not verifiable — file not frozen |
| 5 | 304 | 82 (verified by running playtest.js) |

The fixed playtest runs **310 passing asserts** (with 1 test-design fix). The game code is solid. The test infrastructure was broken.

### No wiring between `math-game-studio-os` pipeline output and `math-games` HTML files
The pipeline produces `generated/review/[slug]/concept_packet.review.json` with `"status": "review_ready"`. Nothing in either repo consumes that signal. The handoff from approved concept packet to built HTML game is entirely manual and untracked.

### No frozen checkpoints for Passes 2–4
`pass-1.html` exists. Nothing for Passes 2, 3, or 4. If a regression surfaces in `index.html`, there is no baseline to diff against.

---

## Smallest improvements that strengthen without creating a second source of truth

**Fix 1 — `index.html` title and comment (2 lines):**  
`<title>Echo Heist — Pass 5</title>` and update line 92 comment to `ECHO HEIST — Pass 5`. No behavior change.

**Fix 2 — `checkAnswer` cross-format percent (6 lines in `index.html`):**  
In `normalizeAnswer`, track whether `%` was present before stripping it. In `checkAnswer`, if user had `%` and correct did not, divide user numeric value by 100 before comparing. This is the only place the equivalence engine lives — no second implementation.

**Fix 3 — `playtest.js` filename + state handling (replace file):**  
Change `current.html` → `index.html`. Add `localStorage._store['echoHeistIntroSeen'] = '1'` before game load. Add `jumpTo(missionIdx, cls)` helper. Add `handleHowToPlayKey` to `simKey` dispatch. Fix hint-cost test to start score > 0. These are the minimum changes that make the 82 original asserts actually run — plus the 3 new sections covering HOW_TO_PLAY, percent equivalence, and the `jumpTo` helper.

**Fix 4 — `PASS_LOG.md` in `math-games` root (new file, no tooling):**  
Documents what is frozen, at what assert count, and what the pass records claimed. Makes the overclaim visible and auditable without invalidating any existing artifact.

**Fix 5 — `scripts/sync_to_games.py` in `math-game-studio-os` (new script, ~40 lines):**  
Reads all `generated/review/*/concept_packet.review.json` files where `status == "review_ready"`. For each, checks whether `math-games/games/[slug]/index.html` exists. Outputs a `STATUS.md` listing approved-but-unbuilt games. Does not generate HTML. Does not touch `math-games` content. Closes the visibility gap between pipeline approval and build status without creating a second gate.

---

## How agent commands map onto the existing pipeline

Do not create new gate logic. The gate engine already lives in `math-game-studio-os/engine/gate_engine.py`.

| Command | Maps to | In which repo |
|---------|---------|--------------|
| `/gate-check` | `gate_engine.py` evaluate on current stage artifact | `math-game-studio-os` |
| `/prototype` | Consumes `prototype_ui_spec` artifact → writes `math-games/games/[slug]/index.html` | `math-games` |
| `/qa-plan` | Writes `playtest-[slug].js` using existing `playtest.js` pattern | `math-games/games/[slug]/` |
| `/smoke-check` | `node playtest-[slug].js` | `math-games/games/[slug]/` |
| `/test-evidence-review` | Reads `playtest-[slug].js` assert count vs pass record claim | `math-games/games/[slug]/` |
| `/retrospective` | Appends to `math-game-studio-os/artifacts/learning_captures/` | `math-game-studio-os` |
| `/dev-story` | Reads `prototype_build_spec` from `math-game-studio-os/generated/` | `math-game-studio-os` |
| `/architecture-decision` | Appends to `math-game-studio-os/docs/` ADR log | `math-game-studio-os` |

The `/team-qa` command should invoke `node playtest-[slug].js` in `math-games`, not create a separate test runner. The existing headless Node + DOM stub pattern is the right infrastructure for all games — each game gets its own playtest file following the same pattern.

