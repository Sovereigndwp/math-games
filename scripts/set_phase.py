#!/usr/bin/env python3
"""
set_phase.py - Package 15 controlled phase mutation helper

Change the current_phase field of a slug's project_config.real.json
with safety checks. Read-only for every other field. Refuses unsafe
transitions. Preserves deterministic formatting.

This is the only sanctioned v0.1 way to mutate current_phase after
a slug has been initialized or backfilled. Hand-editing the JSON
remains an option for rollbacks or other edge cases, and git history
remains the audit trail for every phase change.

Scope:
  - Changes exactly one JSON field: project_config.real.json.current_phase
  - Everything else in the PC file is preserved byte-equivalent
    (values equal; textual form stable because the backfill and
    initializer scripts write canonical JSON with sorted keys)
  - Refuses unsafe transitions before any write happens
  - Self-validates the derived PC against project_config.schema.json
    before writing

CLI:
  --slug SLUG              (required; kebab-case)
  --to-phase {concept,packet,review}
                            (required; v0.1 accepts only these 3)
  --dry-run                 (optional; no write)

Why only 3 target phases in v0.1:
  concept, packet, and review are the only phases whose observed
  state can be derived from file presence today. prototype, qa,
  repair, and release_ready have no file-chain artifacts yet. They
  will be added to --to-phase in a later package when the
  corresponding artifacts exist. Until then, keeping the CLI
  narrow is more honest than accepting those values and refusing
  them at runtime.

Refusal rules (evaluated in order, first match wins):
  R1  bad CLI arg                        -> argparse exit 2
  R2  jsonschema not installed           -> exit 2
  R3  schema file missing/unparseable    -> exit 2
  R4  project_config.real.json absent    -> exit 1
  R5  project_config.real.json bad JSON  -> exit 1
  R6  PC has no usable current_phase     -> exit 1
  R9  target phase == current phase      -> exit 1 ("already")
  R10 backward transition                 -> exit 1
  R11 observed phase doesn't match        -> exit 1
      the target's requirement
  R12 derived PC fails self-validation   -> exit 1
  R13 write I/O error                    -> exit 1

Phase -> observed-phase mapping (same as phase_router, duplicated
inline per Package 15 L7):
  concept  <-> initialized | generation_requested
  packet   <-> drafted | promotion_requested
  review   <-> reviewed

Backward transitions (v0.1 refused):
  packet -> concept
  review -> concept
  review -> packet

If an operator genuinely needs a backward transition, they
hand-edit the JSON and commit with a clear reason.

Audit trail:
  Every successful set_phase.py invocation produces a commit whose
  diff shows exactly which slug changed, from what phase to what
  phase. No in-file history field exists in v0.1; git log is the
  complete audit trail.
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError
except ImportError:
    sys.stderr.write(
        "ERROR: jsonschema is not installed.\n"
        "Install it with: pip install -r requirements.txt\n"
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent

PROJECT_CONFIG_SCHEMA = REPO_ROOT / "schemas" / "project_config.schema.json"

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Only the 3 v0.1-supported target phases are offered by the CLI.
# argparse rejects anything else before the refusal rules run.
ALLOWED_TARGET_PHASES = ["concept", "packet", "review"]

# Phase -> required observed phases (for the transition to be allowed)
PHASE_OBSERVED_REQUIREMENTS = {
    "concept": ("initialized", "generation_requested"),
    "packet": ("drafted", "promotion_requested"),
    "review": ("reviewed",),
}

# Backward transitions explicitly refused in v0.1.
BACKWARD_TRANSITIONS = {
    ("packet", "concept"),
    ("review", "concept"),
    ("review", "packet"),
}


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


def load_schema(path, context):
    if not path.exists():
        die_setup(f"required schema missing: {path}")
    try:
        with path.open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        die_setup(f"{context} schema JSON parse error at {path}: {e.msg}")


def canonical_dump(obj):
    """Deterministic JSON: sorted keys, 2-space indent, trailing newline."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# ---- observed phase derivation (duplicated inline from phase_router) ---


# Per-slug file spec: (key, directory segment, filename)
FILE_SPECS = [
    ("project_config",         "requests", "project_config.real.json"),
    ("concept_brief",          "requests", "concept_brief.real.json"),
    ("generation_request",     "requests", "generation_request.real.json"),
    ("promotion_request",      "requests", "promotion_request.real.json"),
    ("concept_packet_draft",   "drafts",   "concept_packet.draft.json"),
    ("concept_packet_manifest","drafts",   "concept_packet.manifest.json"),
    ("concept_packet_review",  "review",   "concept_packet.review.json"),
    ("promotion_record",       "review",   "promotion_record.json"),
]


def build_file_presence(slug):
    """Return a dict keyed by file key with 'present' and 'path'."""
    report = {}
    for key, dir_segment, filename in FILE_SPECS:
        abspath = REPO_ROOT / "generated" / dir_segment / slug / filename
        report[key] = {
            "present": abspath.exists() and abspath.is_file(),
            "path": str(abspath.relative_to(REPO_ROOT)),
        }
    return report


def derive_observed_phase(files):
    """Inline duplicate of phase_router.py observed_phase logic.
    Evaluated from most-advanced to least-advanced. First match wins."""
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


# ---- main --------------------------------------------------------------


def main(argv):
    parser = argparse.ArgumentParser(
        prog="set_phase.py",
        description=(
            "Change the current_phase field of a slug's "
            "project_config.real.json with safety checks. Read-only "
            "for every other field. Refuses unsafe transitions."
        ),
    )
    parser.add_argument(
        "--slug",
        type=validate_slug,
        required=True,
        help="kebab-case slug (pattern ^[a-z0-9]+(-[a-z0-9]+)*$, 2-64 chars)",
    )
    parser.add_argument(
        "--to-phase",
        choices=ALLOWED_TARGET_PHASES,
        required=True,
        dest="to_phase",
        help=(
            "Target phase. v0.1 accepts only concept, packet, or "
            "review because these are the only phases with a "
            "file-presence signal the script can verify. Later "
            "packages will add prototype, qa, repair, and "
            "release_ready when their file-chain artifacts exist."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help=(
            "Load PC, derive new PC in memory, self-validate, print "
            "what would be written. No file write."
        ),
    )
    args = parser.parse_args(argv[1:])

    slug = args.slug
    target_phase = args.to_phase

    # --- R2/R3: load schema ---
    schema = load_schema(PROJECT_CONFIG_SCHEMA, "project_config")

    # --- R4: PC must exist ---
    pc_path = REPO_ROOT / "generated" / "requests" / slug / "project_config.real.json"
    if not pc_path.exists():
        die_failure(
            f"no project_config.real.json for slug {slug}. Create "
            f"one with scripts/new_game_init.py or "
            f"scripts/backfill_project_config.py first."
        )

    # --- R5: PC must be parseable ---
    try:
        with pc_path.open() as f:
            pc_data = json.load(f)
    except json.JSONDecodeError as e:
        die_failure(
            f"project_config.real.json for slug {slug} is not "
            f"parseable JSON: {e.msg}. Fix the file before re-running."
        )
    except OSError as e:
        die_failure(
            f"project_config.real.json for slug {slug} could not be "
            f"read: {e}"
        )

    # --- R6: PC must have a usable current_phase ---
    if not isinstance(pc_data, dict):
        die_failure(
            f"project_config.real.json for slug {slug} is not a JSON "
            f"object."
        )
    current_phase = pc_data.get("current_phase")
    if not isinstance(current_phase, str) or not current_phase:
        die_failure(
            f"project_config.real.json for slug {slug} has no usable "
            f"current_phase field."
        )

    # --- R9: target != current ---
    if target_phase == current_phase:
        die_failure(
            f"slug {slug} is already in phase {current_phase!r}. No "
            f"change needed."
        )

    # --- R10: backward transitions refused ---
    if (current_phase, target_phase) in BACKWARD_TRANSITIONS:
        die_failure(
            f"backward transition {current_phase!r} -> {target_phase!r} "
            f"is not supported in v0.1 of set_phase.py. Rollbacks must "
            f"be performed by hand-editing the JSON and committing "
            f"with a clear reason."
        )

    # --- R11: observed phase must match target's requirement ---
    files = build_file_presence(slug)
    observed_phase = derive_observed_phase(files)
    required = PHASE_OBSERVED_REQUIREMENTS[target_phase]
    if observed_phase not in required:
        die_failure(
            f"target phase {target_phase!r} requires observed phase "
            f"in {set(required)} but slug {slug} has observed phase "
            f"{observed_phase!r}. The artifact chain is not ready for "
            f"this transition. Run scripts/phase_router.py --slug "
            f"{slug} to see the current file state."
        )

    # --- derive new PC (change exactly one field) ---
    new_pc = dict(pc_data)
    new_pc["current_phase"] = target_phase

    # --- R12: self-validate derived PC against schema ---
    try:
        Draft202012Validator(schema).validate(new_pc)
    except ValidationError as e:
        die_failure(
            f"derived project_config does not validate against "
            f"schema after setting current_phase: {e.message}. No "
            f"write performed."
        )

    # --- report what would be written ---
    print("set_phase.py —", "dry-run" if args.dry_run else "run")
    print()
    print(f"slug:            {slug}")
    print(f"observed phase:  {observed_phase}")
    print(f"current phase:   {current_phase}")
    print(f"target phase:    {target_phase}")
    print(f"transition:      {current_phase} -> {target_phase}")
    print(f"target path:     {pc_path.relative_to(REPO_ROOT)}")
    print()

    if args.dry_run:
        print("self-validation against project_config.schema.json: PASS")
        print("would write: YES (current_phase only; all other fields unchanged)")
        return 0

    # --- R13: write ---
    try:
        pc_path.write_text(canonical_dump(new_pc), encoding="utf-8")
    except OSError as e:
        die_failure(f"could not write {pc_path}: {e}")

    print("self-validation against project_config.schema.json: PASS")
    print(f"write status: SUCCESS")
    print(
        f"  path:     {pc_path.relative_to(REPO_ROOT)}"
    )
    print(f"  changed:  current_phase: {current_phase} -> {target_phase}")
    print(f"  other fields: unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
