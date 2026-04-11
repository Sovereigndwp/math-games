#!/usr/bin/env python3
"""
advance_to_packet.py - Package 19 first composition wrapper

Advance a slug from the clean 'initialized' state to the 'packet'
state by running three already-approved write tools in sequence:

  [1/3] scripts/build_generation_request.py --slug <slug>
  [2/3] scripts/generate_concept_packet_stub.py <request-path>
  [3/3] scripts/set_phase.py --slug <slug> --to-phase packet

Design stance:
  - This is a pure composition wrapper. It never writes any file
    directly. Every file that appears on disk as a result of this
    script running is written by one of the three existing
    subcommands.
  - All prechecks run BEFORE any subcommand is invoked. If any
    precheck fails, zero subcommands run.
  - Subprocess stdout and stderr inherit the wrapper's stdout and
    stderr. The operator sees each subcommand's output verbatim.
  - Stop on first failure. Partial state is left on disk for the
    operator to inspect and decide.
  - No --force, no --skip-precheck, no hidden defaults.

Scope:
  v0.1 supports exactly one starting state: clean 'initialized'
  (PC + CB exist, current_phase='concept', no generation_request,
  no draft, no manifest, no downstream artifacts). Any other
  starting state is refused with a clear diagnostic.

Usage:
  python3 scripts/advance_to_packet.py --slug <slug>
                                       [--created-at-request <iso>]
                                       [--dry-run]

Exit codes:
  0  success (all 3 subcommands completed) or successful dry-run
  1  precheck failure or subcommand failure
  2  argparse error or setup error

Precheck order (first match wins):
  R1   bad CLI arg                             -> argparse exit 2
  R2   project_config.real.json absent         -> exit 1
  R3   concept_brief.real.json absent          -> exit 1
  R3b  placeholder content still present       -> exit 1
       in any checked creative field
  R4   project_config.current_phase != 'concept' OR
       project_config unparseable                -> exit 1
  R6   generation_request.real.json already     -> exit 1
       exists for slug
  R5   observed_phase != 'initialized'         -> exit 1
  R7   [1/3] build_generation_request.py failed -> exit 1
  R8   [2/3] generate_concept_packet_stub.py
       failed                                   -> exit 1
  R9   [3/3] set_phase.py failed                -> exit 1

R3b (placeholder refusal):
  Refuses if any of these fields still starts with
  "[INITIALIZER PLACEHOLDER]":

    concept_brief.real.json:
      concept_summary
      core_mechanic.player_action
      core_mechanic.feedback_loop
      target_skill.description
      misconception_targets[0].description
      success_condition
      constraints[0]
      portfolio_fit.why_now

    project_config.real.json:
      target_skill.description
      core_misconception.description
      success_metric

  This enforces the human creative-rewrite boundary between
  new_game_init and advance_to_packet. The wrapper refuses to
  mass-produce placeholder drafts.

R6 is checked BEFORE R5 so that a re-run after a partial advance
reports "generation_request already exists" (more specific) rather
than "observed_phase drafted" (more generic).
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

BUILD_GENERATION_REQUEST = REPO_ROOT / "scripts" / "build_generation_request.py"
GENERATE_CONCEPT_PACKET_STUB = REPO_ROOT / "scripts" / "generate_concept_packet_stub.py"
SET_PHASE = REPO_ROOT / "scripts" / "set_phase.py"

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ISO_Z_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)

PLACEHOLDER_PREFIX = "[INITIALIZER PLACEHOLDER]"


# ---- helpers -----------------------------------------------------------


def die_setup(msg):
    sys.stderr.write(f"SETUP ERROR: {msg}\n")
    sys.exit(2)


def die_failure(msg):
    sys.stderr.write(f"FAILURE: {msg}\n")
    sys.exit(1)


def validate_slug(value):
    if not SLUG_PATTERN.match(value):
        raise argparse.ArgumentTypeError(
            f"--slug {value!r} must be kebab-case matching "
            f"^[a-z0-9]+(-[a-z0-9]+)*$"
        )
    if not (2 <= len(value) <= 64):
        raise argparse.ArgumentTypeError(
            f"--slug must be 2-64 chars, got {len(value)}"
        )
    return value


def parse_iso_z(value):
    if not ISO_Z_PATTERN.match(value):
        raise argparse.ArgumentTypeError(
            f"--created-at-request must be ISO 8601 with Z suffix "
            f"(e.g. 2026-04-11T14:00:00Z), got {value!r}"
        )
    return value


def load_json(path, context):
    try:
        with path.open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        die_failure(
            f"{context} at {path.relative_to(REPO_ROOT)} is not "
            f"parseable JSON: {e.msg}"
        )
    except OSError as e:
        die_failure(
            f"{context} at {path.relative_to(REPO_ROOT)} could not "
            f"be read: {e}"
        )


# ---- placeholder detection (R3b) ---------------------------------------


def _starts_with_placeholder(value):
    """Return True if value is a string that starts with the literal
    [INITIALIZER PLACEHOLDER] prefix."""
    return isinstance(value, str) and value.startswith(PLACEHOLDER_PREFIX)


def _field_at_path(data, path):
    """Walk a dotted path into a dict, supporting list indices. Returns
    None if any segment is missing. path is a list of (key, type) tuples
    where type is 'dict_key' or an int list index."""
    cur = data
    for step in path:
        if isinstance(step, str):
            if not isinstance(cur, dict) or step not in cur:
                return None
            cur = cur[step]
        elif isinstance(step, int):
            if not isinstance(cur, list) or step >= len(cur):
                return None
            cur = cur[step]
    return cur


def check_placeholders(brief_data, pc_data):
    """Return list of field path strings where [INITIALIZER PLACEHOLDER]
    is still present. Empty list means R3b passes."""
    offenders = []

    # concept_brief checked fields
    brief_paths = [
        ("concept_brief.concept_summary", ["concept_summary"]),
        ("concept_brief.core_mechanic.player_action",
         ["core_mechanic", "player_action"]),
        ("concept_brief.core_mechanic.feedback_loop",
         ["core_mechanic", "feedback_loop"]),
        ("concept_brief.target_skill.description",
         ["target_skill", "description"]),
        ("concept_brief.misconception_targets[0].description",
         ["misconception_targets", 0, "description"]),
        ("concept_brief.success_condition", ["success_condition"]),
        ("concept_brief.constraints[0]", ["constraints", 0]),
        ("concept_brief.portfolio_fit.why_now",
         ["portfolio_fit", "why_now"]),
    ]
    for label, path in brief_paths:
        value = _field_at_path(brief_data, path)
        if _starts_with_placeholder(value):
            offenders.append(label)

    # project_config checked fields
    pc_paths = [
        ("project_config.target_skill.description",
         ["target_skill", "description"]),
        ("project_config.core_misconception.description",
         ["core_misconception", "description"]),
        ("project_config.success_metric", ["success_metric"]),
    ]
    for label, path in pc_paths:
        value = _field_at_path(pc_data, path)
        if _starts_with_placeholder(value):
            offenders.append(label)

    return offenders


# ---- observed phase derivation (duplicated inline from phase_router) ---


def build_file_presence(slug):
    base = REPO_ROOT / "generated"
    paths = {
        "project_config":         base / "requests" / slug / "project_config.real.json",
        "concept_brief":          base / "requests" / slug / "concept_brief.real.json",
        "generation_request":     base / "requests" / slug / "generation_request.real.json",
        "promotion_request":      base / "requests" / slug / "promotion_request.real.json",
        "concept_packet_draft":   base / "drafts"   / slug / "concept_packet.draft.json",
        "concept_packet_manifest":base / "drafts"   / slug / "concept_packet.manifest.json",
        "concept_packet_review":  base / "review"   / slug / "concept_packet.review.json",
        "promotion_record":       base / "review"   / slug / "promotion_record.json",
    }
    return {
        key: {"present": p.exists() and p.is_file(), "path": p}
        for key, p in paths.items()
    }


def derive_observed_phase(files):
    def p(key):
        return files.get(key, {}).get("present", False)
    pc = p("project_config")
    cb = p("concept_brief")
    gr = p("generation_request")
    pr = p("promotion_request")
    d = p("concept_packet_draft")
    m = p("concept_packet_manifest")
    rv = p("concept_packet_review")
    rc = p("promotion_record")

    any_file = any([pc, cb, gr, pr, d, m, rv, rc])
    if not any_file:
        return "empty"
    if rv and rc:
        return "reviewed"
    if pr:
        return "promotion_requested"
    if d and m:
        return "drafted"
    if gr:
        return "generation_requested"
    if cb:
        return "initialized"
    return "partial"


# ---- subprocess runner -------------------------------------------------


def run_step(step_marker, argv):
    """Run a subcommand with inherited stdout/stderr. Returns exit code.

    Flush wrapper stdout before and after the subprocess call so the
    wrapper's buffered output and the subprocess's direct-to-fd output
    interleave in the correct chronological order. Without the flushes,
    Python's block-buffered stdout delays wrapper prints until the
    wrapper exits, producing subprocess-then-wrapper output ordering.
    """
    print(f"\n[{step_marker}] " + " ".join(argv))
    print("-" * 72)
    sys.stdout.flush()
    result = subprocess.run(argv, cwd=str(REPO_ROOT))
    sys.stdout.flush()
    print("-" * 72)
    print(f"[{step_marker}] exit={result.returncode}")
    sys.stdout.flush()
    return result.returncode


# ---- main --------------------------------------------------------------


def main(argv):
    parser = argparse.ArgumentParser(
        prog="advance_to_packet.py",
        description=(
            "Advance a slug from clean 'initialized' state to 'packet' "
            "state by running build_generation_request.py, "
            "generate_concept_packet_stub.py, and set_phase.py in "
            "sequence. Read-only prechecks first. Stop on first failure."
        ),
    )
    parser.add_argument(
        "--slug",
        type=validate_slug,
        required=True,
        help="kebab-case slug (pattern ^[a-z0-9]+(-[a-z0-9]+)*$, 2-64 chars)",
    )
    parser.add_argument(
        "--created-at-request",
        type=parse_iso_z,
        default=None,
        dest="created_at_request",
        help=(
            "ISO 8601 date-time with Z suffix, passed to "
            "build_generation_request.py as its --created-at value. "
            "Default: build_generation_request.py's default (now UTC)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help=(
            "Run all read-only prechecks and print the exact "
            "subcommands that would be invoked, without invoking any "
            "of them."
        ),
    )
    args = parser.parse_args(argv[1:])

    slug = args.slug

    # --- Precheck R2: project_config must exist ---
    pc_path = REPO_ROOT / "generated" / "requests" / slug / "project_config.real.json"
    if not pc_path.exists():
        die_failure(
            f"no project_config.real.json for slug {slug}. Run "
            f"scripts/new_game_init.py first."
        )

    # --- Precheck R3: concept_brief must exist ---
    cb_path = REPO_ROOT / "generated" / "requests" / slug / "concept_brief.real.json"
    if not cb_path.exists():
        die_failure(
            f"no concept_brief.real.json for slug {slug}. Run "
            f"scripts/new_game_init.py first."
        )

    # Both files exist, load them for subsequent prechecks.
    pc_data = load_json(pc_path, "project_config")
    cb_data = load_json(cb_path, "concept_brief")

    if not isinstance(pc_data, dict):
        die_failure(
            f"project_config.real.json for slug {slug} is not a JSON object."
        )
    if not isinstance(cb_data, dict):
        die_failure(
            f"concept_brief.real.json for slug {slug} is not a JSON object."
        )

    # --- Precheck R3b: placeholder content refusal ---
    offenders = check_placeholders(cb_data, pc_data)
    if offenders:
        die_failure(
            f"slug {slug} still contains initializer placeholder "
            f"content in: {', '.join(offenders)}. Rewrite the creative "
            f"content in concept_brief.real.json and "
            f"project_config.real.json before running advance_to_packet.py."
        )

    # --- Precheck R4: current_phase must be 'concept' ---
    current_phase = pc_data.get("current_phase")
    if not isinstance(current_phase, str) or current_phase != "concept":
        die_failure(
            f"project_config.real.json.current_phase is "
            f"{current_phase!r}; advance_to_packet.py only handles the "
            f"'concept' starting state. Use scripts/set_phase.py "
            f"manually if you need a different transition."
        )

    # --- Precheck R6: generation_request must NOT exist (checked BEFORE R5) ---
    gr_path = REPO_ROOT / "generated" / "requests" / slug / "generation_request.real.json"
    if gr_path.exists():
        die_failure(
            f"generation_request.real.json already exists for slug "
            f"{slug}: {gr_path.relative_to(REPO_ROOT)}. "
            f"advance_to_packet.py refuses to overwrite. Run "
            f"scripts/generate_concept_packet_stub.py + "
            f"scripts/set_phase.py manually if you want to continue "
            f"from here."
        )

    # --- Precheck R5: observed_phase must be 'initialized' ---
    files = build_file_presence(slug)
    observed_phase = derive_observed_phase(files)
    if observed_phase != "initialized":
        die_failure(
            f"slug {slug} has observed_phase {observed_phase!r}. "
            f"advance_to_packet.py only handles the clean 'initialized' "
            f"starting state. Inspect with scripts/phase_router.py "
            f"--slug {slug} and run the missing subcommand manually."
        )

    # --- All prechecks passed. Build subcommand invocations. ---
    python = sys.executable
    step1_argv = [
        python, str(BUILD_GENERATION_REQUEST.relative_to(REPO_ROOT)),
        "--slug", slug,
    ]
    if args.created_at_request is not None:
        step1_argv.extend(["--created-at", args.created_at_request])

    step2_argv = [
        python, str(GENERATE_CONCEPT_PACKET_STUB.relative_to(REPO_ROOT)),
        str(gr_path.relative_to(REPO_ROOT)),
    ]

    step3_argv = [
        python, str(SET_PHASE.relative_to(REPO_ROOT)),
        "--slug", slug,
        "--to-phase", "packet",
    ]

    # --- Report header ---
    print(
        "advance_to_packet.py — "
        + ("dry-run" if args.dry_run else "run")
    )
    print()
    print(f"slug:             {slug}")
    print(f"current_phase:    {current_phase}")
    print(f"observed_phase:   {observed_phase}")
    print()
    print("prechecks:")
    print(f"  [OK] R2  project_config.real.json present")
    print(f"  [OK] R3  concept_brief.real.json present")
    print(f"  [OK] R3b no initializer placeholder content in creative fields")
    print(f"  [OK] R4  project_config.current_phase == 'concept'")
    print(f"  [OK] R6  generation_request.real.json absent")
    print(f"  [OK] R5  observed_phase == 'initialized'")
    print()

    if args.dry_run:
        print("would run, in order:")
        print(f"  [1/3] {' '.join(step1_argv)}")
        print(f"  [2/3] {' '.join(step2_argv)}")
        print(f"  [3/3] {' '.join(step3_argv)}")
        print()
        print("exit: 0 (dry-run, no subcommand invoked)")
        return 0

    # --- Real run: invoke all three subcommands in sequence ---
    print("invoking subcommands:")

    rc = run_step("1/3", step1_argv)
    if rc != 0:
        die_failure(
            f"[1/3] build_generation_request.py exited with code {rc}. "
            f"See its output above for details. Nothing further was invoked."
        )

    rc = run_step("2/3", step2_argv)
    if rc != 0:
        die_failure(
            f"[2/3] generate_concept_packet_stub.py exited with code "
            f"{rc}. See its output above for details. "
            f"generation_request.real.json exists on disk from step 1; "
            f"inspect and decide whether to retry manually."
        )

    rc = run_step("3/3", step3_argv)
    if rc != 0:
        die_failure(
            f"[3/3] set_phase.py exited with code {rc}. See its output "
            f"above for details. generation_request.real.json + draft + "
            f"manifest exist on disk from steps 1 and 2; run set_phase.py "
            f"manually to complete the transition."
        )

    # --- Final success report ---
    print()
    print("=" * 72)
    print(f"advance_to_packet.py — success")
    print(f"  slug:             {slug}")
    print(f"  transition:       concept -> packet")
    print(f"  subcommands run:  3 of 3")
    print(f"  status:           SUCCESS")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
