#!/usr/bin/env python3
"""
advance_to_review.py - Package 20 second composition wrapper

Advance a slug from the clean 'packet' state to the 'review' state
by running three already-approved write tools in sequence:

  [1/3] scripts/build_promotion_request.py --slug <slug>
  [2/3] scripts/promote_draft_stub.py <promotion-request-path>
  [3/3] scripts/set_phase.py --slug <slug> --to-phase review

Design stance:
  - Pure composition wrapper. Never writes any file directly. Every
    file that appears on disk as a result of this script running is
    written by one of the three existing subcommands.
  - All prechecks run BEFORE any subcommand is invoked. If any
    precheck fails, zero subcommands run.
  - Subprocess stdout and stderr inherit the wrapper's stdout and
    stderr. The operator sees each subcommand's output verbatim.
  - Stop on first failure. Partial state is left on disk for the
    operator to inspect and decide.
  - No --force, no --skip-precheck, no hidden defaults.

Scope:
  v0.1 supports exactly one starting state: clean 'drafted'
  (PC + CB + GR + D + M exist, current_phase='packet', no
  promotion_request, no review, no promotion_record). Any other
  starting state is refused with a clear diagnostic.

Usage:
  python3 scripts/advance_to_review.py --slug <slug>
                                       [--created-at-request <iso>]
                                       [--dry-run]

Exit codes:
  0  success (all 3 subcommands completed) or successful dry-run
  1  precheck failure or subcommand failure
  2  argparse error or setup error

Precheck order (first match wins):
  R1    bad CLI arg                             -> argparse exit 2
  R4    project_config.real.json absent,
        unparseable, not an object, or has no
        usable current_phase                     -> exit 1
  R5    current_phase != 'packet'                -> exit 1
  R6    required files (PC, CB, GR, D, M) not
        all present, OR forbidden files (PR, RV,
        RC) any present                          -> exit 1
  R7    observed_phase != 'drafted'              -> exit 1
  R8a   placeholder content still present in any
        of the 11 tracked creative fields        -> exit 1
  R8b   check_project_config.py --json fails any
        of the four gate conditions:
          - stdout is not parseable JSON
          - summary.has_project_config != true
          - summary.comparable != true
          - summary.checks_fail != 0             -> exit 1
  R9    [1/3] build_promotion_request.py failed  -> exit 1
  R10   [2/3] promote_draft_stub.py failed       -> exit 1
  R11   [3/3] set_phase.py failed                -> exit 1

R8a (placeholder refusal):
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

  Package 20 enforces the same creative-rewrite boundary as
  Package 19. A packet-phase slug that still contains initializer
  placeholder text has not been creatively rewritten, and the
  wrapper refuses to promote it to review.

R8b (consistency gate):
  check_project_config.py exits 0 even when it finds FAILs, so
  exit-code-only gating is unsafe. This wrapper invokes it with
  --json, parses stdout, and refuses separately on:
    - unparseable JSON (the checker itself is broken)
    - summary.has_project_config not exactly True
    - summary.comparable not exactly True
    - summary.checks_fail not exactly 0
  On pass, prints a one-line summary including checks_pass so the
  operator log stays informative.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

BUILD_PROMOTION_REQUEST = REPO_ROOT / "scripts" / "build_promotion_request.py"
PROMOTE_DRAFT_STUB = REPO_ROOT / "scripts" / "promote_draft_stub.py"
SET_PHASE = REPO_ROOT / "scripts" / "set_phase.py"
CHECK_PROJECT_CONFIG = REPO_ROOT / "scripts" / "check_project_config.py"

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
            f"(e.g. 2026-04-11T15:00:00Z), got {value!r}"
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


# ---- placeholder detection (R8a) ---------------------------------------


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
    is still present. Empty list means R8a passes."""
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


# ---- R8b: check_project_config.py --json gate --------------------------


def run_consistency_gate(slug):
    """Invoke scripts/check_project_config.py --slug <slug> --json and
    parse its stdout. Returns (checks_pass, checks_fail) on success.
    Calls die_failure on any of the four R8b refusals."""
    argv = [
        sys.executable,
        str(CHECK_PROJECT_CONFIG.relative_to(REPO_ROOT)),
        "--slug", slug,
        "--json",
    ]
    try:
        result = subprocess.run(
            argv,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
    except OSError as e:
        die_failure(
            f"R8b: could not invoke check_project_config.py: {e}"
        )

    # R8b.1: stdout must be parseable JSON.
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        die_failure(
            f"R8b: check_project_config.py --json did not return "
            f"parseable JSON: {e.msg}. stderr was:\n{result.stderr}"
        )

    if not isinstance(report, dict):
        die_failure(
            f"R8b: check_project_config.py --json output is not a "
            f"JSON object."
        )

    summary = report.get("summary")
    if not isinstance(summary, dict):
        die_failure(
            f"R8b: check_project_config.py --json output has no "
            f"'summary' object."
        )

    # R8b.2: has_project_config must be exactly True.
    if summary.get("has_project_config") is not True:
        die_failure(
            f"R8b: check_project_config reports has_project_config="
            f"{summary.get('has_project_config')!r} (expected True). "
            f"The slug's project_config.real.json is missing or the "
            f"checker could not read it."
        )

    # R8b.3: comparable must be exactly True.
    if summary.get("comparable") is not True:
        die_failure(
            f"R8b: check_project_config reports comparable="
            f"{summary.get('comparable')!r} (expected True). "
            f"PC and its comparable sources cannot be cross-checked; "
            f"run scripts/check_project_config.py --slug {slug} for "
            f"details."
        )

    # R8b.4: checks_fail must be exactly 0.
    checks_fail = summary.get("checks_fail")
    if checks_fail != 0:
        die_failure(
            f"R8b: check_project_config reports checks_fail="
            f"{checks_fail!r} (expected 0). Resolve the PC/source "
            f"inconsistencies before advancing to review. Run "
            f"scripts/check_project_config.py --slug {slug} for "
            f"field-level details."
        )

    checks_pass = summary.get("checks_pass", 0)
    return checks_pass, checks_fail


# ---- subprocess runner -------------------------------------------------


def run_step(step_marker, argv):
    """Run a subcommand with inherited stdout/stderr. Returns exit code.

    Flush wrapper stdout before and after the subprocess call so the
    wrapper's buffered output and the subprocess's direct-to-fd output
    interleave in the correct chronological order.
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
        prog="advance_to_review.py",
        description=(
            "Advance a slug from clean 'drafted' state to 'review' "
            "state by running build_promotion_request.py, "
            "promote_draft_stub.py, and set_phase.py in sequence. "
            "Read-only prechecks first (including a check_project_config "
            "--json consistency gate). Stop on first failure."
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
            "build_promotion_request.py as its --created-at value. "
            "Default: build_promotion_request.py's default (now UTC)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help=(
            "Run all read-only prechecks (including the "
            "check_project_config --json gate) and print the exact "
            "subcommands that would be invoked, without invoking any "
            "of them."
        ),
    )
    args = parser.parse_args(argv[1:])

    slug = args.slug

    # --- Precheck R4: project_config must exist, parse, have current_phase ---
    pc_path = REPO_ROOT / "generated" / "requests" / slug / "project_config.real.json"
    if not pc_path.exists():
        die_failure(
            f"R4: no project_config.real.json for slug {slug}. Run "
            f"scripts/new_game_init.py first, then advance through "
            f"concept and packet phases."
        )
    pc_data = load_json(pc_path, "project_config")
    if not isinstance(pc_data, dict):
        die_failure(
            f"R4: project_config.real.json for slug {slug} is not a "
            f"JSON object."
        )
    current_phase = pc_data.get("current_phase")
    if not isinstance(current_phase, str) or not current_phase:
        die_failure(
            f"R4: project_config.real.json for slug {slug} has no "
            f"usable current_phase field."
        )

    # --- Precheck R5: current_phase must be 'packet' ---
    if current_phase != "packet":
        die_failure(
            f"R5: project_config.real.json.current_phase is "
            f"{current_phase!r}; advance_to_review.py only handles the "
            f"'packet' starting state. Use scripts/advance_to_packet.py "
            f"if you are coming from 'concept', or scripts/set_phase.py "
            f"manually for other transitions."
        )

    # --- Precheck R6: required files present, forbidden files absent ---
    files = build_file_presence(slug)
    required_keys = [
        "project_config",
        "concept_brief",
        "generation_request",
        "concept_packet_draft",
        "concept_packet_manifest",
    ]
    forbidden_keys = [
        "promotion_request",
        "concept_packet_review",
        "promotion_record",
    ]
    missing = [k for k in required_keys if not files[k]["present"]]
    extra = [k for k in forbidden_keys if files[k]["present"]]
    if missing:
        die_failure(
            f"R6: slug {slug} is missing required files for the "
            f"'drafted' starting state: {', '.join(missing)}. Run "
            f"scripts/phase_router.py --slug {slug} to see the current "
            f"file state, then run the appropriate earlier wrapper or "
            f"primitive to create the missing files."
        )
    if extra:
        die_failure(
            f"R6: slug {slug} already has downstream files that must "
            f"be absent for the 'drafted' starting state: "
            f"{', '.join(extra)}. advance_to_review.py refuses to "
            f"overwrite. Inspect generated/requests/{slug}/ and "
            f"generated/review/{slug}/ and decide manually how to "
            f"proceed."
        )

    # --- Precheck R7: observed_phase must be 'drafted' ---
    observed_phase = derive_observed_phase(files)
    if observed_phase != "drafted":
        die_failure(
            f"R7: slug {slug} has observed_phase {observed_phase!r}. "
            f"advance_to_review.py only handles the clean 'drafted' "
            f"starting state. Inspect with scripts/phase_router.py "
            f"--slug {slug} and run the missing subcommand manually."
        )

    # --- Precheck R8a: placeholder content refusal ---
    cb_path = REPO_ROOT / "generated" / "requests" / slug / "concept_brief.real.json"
    cb_data = load_json(cb_path, "concept_brief")
    if not isinstance(cb_data, dict):
        die_failure(
            f"R8a: concept_brief.real.json for slug {slug} is not a "
            f"JSON object."
        )
    offenders = check_placeholders(cb_data, pc_data)
    if offenders:
        die_failure(
            f"R8a: slug {slug} still contains initializer placeholder "
            f"content in: {', '.join(offenders)}. Rewrite the creative "
            f"content in concept_brief.real.json and "
            f"project_config.real.json before running advance_to_review.py."
        )

    # --- Precheck R8b: check_project_config.py --json consistency gate ---
    checks_pass, checks_fail = run_consistency_gate(slug)

    # --- All prechecks passed. Build subcommand invocations. ---
    python = sys.executable
    step1_argv = [
        python, str(BUILD_PROMOTION_REQUEST.relative_to(REPO_ROOT)),
        "--slug", slug,
    ]
    if args.created_at_request is not None:
        step1_argv.extend(["--created-at", args.created_at_request])

    promotion_request_path = (
        REPO_ROOT / "generated" / "requests" / slug / "promotion_request.real.json"
    )
    step2_argv = [
        python, str(PROMOTE_DRAFT_STUB.relative_to(REPO_ROOT)),
        str(promotion_request_path.relative_to(REPO_ROOT)),
    ]

    step3_argv = [
        python, str(SET_PHASE.relative_to(REPO_ROOT)),
        "--slug", slug,
        "--to-phase", "review",
    ]

    # --- Report header ---
    print(
        "advance_to_review.py — "
        + ("dry-run" if args.dry_run else "run")
    )
    print()
    print(f"slug:             {slug}")
    print(f"current_phase:    {current_phase}")
    print(f"observed_phase:   {observed_phase}")
    print()
    print("prechecks:")
    print(f"  [OK] R4  project_config.real.json present, parseable, has current_phase")
    print(f"  [OK] R5  project_config.current_phase == 'packet'")
    print(f"  [OK] R6  required files present (PC, CB, GR, D, M); forbidden files absent (PR, RV, RC)")
    print(f"  [OK] R7  observed_phase == 'drafted'")
    print(f"  [OK] R8a no initializer placeholder content in 11 tracked fields")
    print(
        f"  [OK] R8b consistency check: PASS "
        f"(checks_pass={checks_pass}, checks_fail={checks_fail})"
    )
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
            f"R9: [1/3] build_promotion_request.py exited with code "
            f"{rc}. See its output above for details. Nothing further "
            f"was invoked."
        )

    rc = run_step("2/3", step2_argv)
    if rc != 0:
        die_failure(
            f"R10: [2/3] promote_draft_stub.py exited with code {rc}. "
            f"See its output above for details. "
            f"promotion_request.real.json exists on disk from step 1; "
            f"inspect generated/requests/{slug}/ and "
            f"generated/review/{slug}/ and decide whether to retry "
            f"manually."
        )

    rc = run_step("3/3", step3_argv)
    if rc != 0:
        die_failure(
            f"R11: [3/3] set_phase.py exited with code {rc}. See its "
            f"output above for details. promotion_request + review + "
            f"promotion_record all exist on disk from steps 1 and 2; "
            f"run set_phase.py --slug {slug} --to-phase review manually "
            f"to complete the transition."
        )

    # --- Final success report ---
    print()
    print("=" * 72)
    print(f"advance_to_review.py — success")
    print(f"  slug:             {slug}")
    print(f"  transition:       packet -> review")
    print(f"  subcommands run:  3 of 3")
    print(f"  status:           SUCCESS")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
