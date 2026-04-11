#!/usr/bin/env python3
"""
new_game_init.py — Package 11 per-slug initializer

Create the starter operational state for a new game slug in math-games.

For a new slug, this script creates exactly:
  - generated/requests/<slug>/
  - generated/requests/<slug>/project_config.real.json
  - generated/requests/<slug>/concept_brief.real.json

It intentionally does NOT create generated/drafts/<slug>/ or
generated/review/<slug>/. Those later-phase directories are created by
the generator and promoter only when their phases actually begin; the
initializer's job is to produce the first valid operational state, not
to pretend later phases already exist.

The script is strictly additive:
  - fails with exit 1 if generated/requests/<slug>/ or either target
    file already exists
  - never writes outside generated/
  - never calls another script
  - never touches schemas, fixtures, README, taxonomy, taskade_exports,
    requirements.txt, or .gitignore

Both output files are self-validated against their respective schemas
in memory BEFORE any file is written. If template drift ever breaks
the schema match, the script exits 1 with the exact validation error
and writes nothing.

Usage:
  python3 scripts/new_game_init.py \\
    --slug place-value-pop-mini \\
    --title "Place Value Pop Mini" \\
    --subject math \\
    --grade-band k_2 \\
    --primary-standard "CCSS.MATH.CONTENT.1.NBT.B.2" \\
    [--created-at 2026-04-11T09:00:00Z] \\
    [--dry-run]

Exit codes:
  0  success (files written, or --dry-run with valid templates)
  1  failure (slug already exists, containment violation, target file
     already exists, template self-validation failure)
  2  setup error (missing jsonschema, missing/unparseable schema file,
     invalid CLI argument)

Determinism:
  IDs are derived from SHA-256(slug + created_at) so two runs with the
  same slug and --created-at produce byte-identical output. Without
  --created-at, the default created_at is datetime.now(timezone.utc)
  truncated to seconds, so normal operator runs get real wall-clock
  timestamps without friction.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
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

CONCEPT_BRIEF_SCHEMA = REPO_ROOT / "schemas" / "concept_brief.schema.json"
PROJECT_CONFIG_SCHEMA = REPO_ROOT / "schemas" / "project_config.schema.json"

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ISO_Z_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)

SUBJECTS = ["math"]
GRADE_BANDS = ["pre_k", "k_2", "3_5", "6_8", "9_12", "cross_band"]


# --- helpers -------------------------------------------------------------


def die_setup(msg):
    sys.stderr.write(f"SETUP ERROR: {msg}\n")
    sys.exit(2)


def die_failure(msg):
    sys.stderr.write(f"FAILURE: {msg}\n")
    sys.exit(1)


def load_schema(path, context):
    if not path.exists():
        die_setup(f"required schema missing: {path}")
    try:
        with path.open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        die_setup(f"{context} schema JSON parse error at {path}: {e.msg}")


def sha256_of_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def canonical_dump(obj):
    # Deterministic JSON: sorted keys, 2-space indent, trailing newline.
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def parse_iso_z(value):
    """Parse an ISO 8601 date-time with Z suffix. Returns the original
    string on success. Raises argparse.ArgumentTypeError on failure."""
    if not ISO_Z_PATTERN.match(value):
        raise argparse.ArgumentTypeError(
            f"--created-at must be ISO 8601 with Z suffix "
            f"(e.g. 2026-04-11T09:00:00Z), got {value!r}"
        )
    # Additional sanity: actually parse to confirm the date-time is real.
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"--created-at {value!r} is not a valid ISO 8601 date-time: {e}"
        )
    return value


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


def validate_bounded_string(name, min_len, max_len):
    def _validator(value):
        if not (min_len <= len(value) <= max_len):
            raise argparse.ArgumentTypeError(
                f"--{name} must be {min_len}-{max_len} chars, got {len(value)}"
            )
        return value
    return _validator


def now_iso_z():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def derive_ids(slug, created_at):
    date_part = created_at[:10].replace("-", "")  # "20260411"
    config_hash = hashlib.sha256(
        f"{slug}|{created_at}".encode("utf-8")
    ).hexdigest()[:6]
    brief_hash = hashlib.sha256(
        f"{slug}|{created_at}|brief".encode("utf-8")
    ).hexdigest()[:6]
    return (
        f"pc_{date_part}_{config_hash}",
        f"cb_{date_part}_{brief_hash}",
    )


# --- template builders ---------------------------------------------------


PLACEHOLDER_PREFIX = "[INITIALIZER PLACEHOLDER]"


def build_project_config(
    *, slug, subject, grade_band, primary_standard, created_at, config_id
):
    return {
        "schema_version": "0.1.0",
        "config_id": config_id,
        "created_at": created_at,
        "slug": slug,
        "subject": subject,
        "grade_band": grade_band,
        "primary_standard": primary_standard,
        "target_skill": {
            "description": (
                f"{PLACEHOLDER_PREFIX} Describe the specific skill this "
                f"game develops. Rewrite before advancing current_phase "
                f"from 'concept'."
            ),
            "ccss_candidate": [primary_standard],
        },
        "interaction_type_candidate": "unresolved",
        "family_candidate": None,
        "core_misconception": {
            "id": "M1",
            "description": (
                f"{PLACEHOLDER_PREFIX} Describe the core misconception "
                f"this game is designed to expose. Rewrite before "
                f"advancing current_phase from 'concept'."
            ),
        },
        "sensory_priorities": [
            "visual_clarity",
            "low_distraction",
        ],
        "forbidden_scope": [
            "no timer pressure in P1",
            "no scoring layer in P1",
            "no multi-scene flow in P1",
        ],
        "current_phase": "concept",
        "success_metric": (
            f"{PLACEHOLDER_PREFIX} One-sentence description of what counts "
            f"as success at the concept phase. Rewrite as the game advances "
            f"phases."
        ),
        "notes": None,
    }


def build_concept_brief(
    *, slug, title, grade_band, primary_standard, created_at, brief_id
):
    return {
        "schema_version": "0.1.0",
        "brief_id": brief_id,
        "created_at": created_at,
        "title": title,
        "proposed_slug": slug,
        "source": {
            "origin": "human_direct",
            "captured_by": "initializer",
            "taskade_project_id": None,
            "external_url": None,
            "notes": (
                "Created by scripts/new_game_init.py. All placeholder "
                "fields must be rewritten by a human author before status "
                "advances from 'draft'."
            ),
        },
        "concept_summary": (
            f"{PLACEHOLDER_PREFIX} This brief was created by "
            f"scripts/new_game_init.py with starter placeholder content. "
            f"Rewrite this concept_summary with a real one-paragraph "
            f"description of what the player does, in what world, toward "
            f"what goal, before advancing status from 'draft'. The "
            f"placeholder exists only to satisfy schema minLength "
            f"requirements and is not valid design content."
        ),
        "core_mechanic": {
            "player_action": (
                f"{PLACEHOLDER_PREFIX} Describe what the player physically "
                f"does every turn. Rewrite before advancing status from "
                f"'draft'."
            ),
            "feedback_loop": (
                f"{PLACEHOLDER_PREFIX} Describe what the game shows in "
                f"response to the player action and how correctness is "
                f"signaled. Rewrite before advancing status from 'draft'."
            ),
            "math_as_lockpick_statement": None,
        },
        "target_learners": {
            "grade_band_candidate": grade_band,
            "age_range_candidate": None,
            "prerequisites_candidate": [],
        },
        "math_domain": "unresolved",
        "target_skill": {
            "description": (
                f"{PLACEHOLDER_PREFIX} Describe the specific skill this "
                f"game develops. Rewrite before advancing status from "
                f"'draft'."
            ),
            "ccss_candidate": [primary_standard],
        },
        "interaction_type_candidate": "unresolved",
        "family_candidate": None,
        "misconception_targets": [
            {
                "id": "M1",
                "description": (
                    f"{PLACEHOLDER_PREFIX} Describe the core misconception "
                    f"this game is designed to expose. Rewrite before "
                    f"advancing status from 'draft'."
                ),
                "existing_library_match": None,
            }
        ],
        "success_condition": (
            f"{PLACEHOLDER_PREFIX} One-sentence human-legible description "
            f"of a successful play session. Rewrite before advancing "
            f"status from 'draft'."
        ),
        "constraints": [
            (
                f"{PLACEHOLDER_PREFIX} Add real design constraints before "
                f"advancing status from 'draft'."
            )
        ],
        "dependencies": [],
        "closest_existing_game": None,
        "portfolio_fit": {
            "why_now": (
                f"{PLACEHOLDER_PREFIX} Describe why this concept is worth "
                f"considering now and what gap it fills. Rewrite before "
                f"advancing status from 'draft'."
            ),
            "overlap_risk": "unresolved",
            "replacement_or_extension_of": None,
        },
        "status": "draft",
        "next_action": {
            "type": "request_revision",
            "owner": "human_author",
            "reason": (
                "Starter brief created by new_game_init.py. All fields "
                "are placeholders that need human refinement before "
                "status advances from 'draft'."
            ),
        },
        "unresolved_items": [
            {
                "field": "concept_summary",
                "reason": (
                    "Initializer placeholder; needs a real one-paragraph "
                    "concept description."
                ),
                "blocking": True,
                "raised_at": created_at,
            },
            {
                "field": "core_mechanic.player_action",
                "reason": (
                    "Initializer placeholder; needs a real description of "
                    "the per-turn player action."
                ),
                "blocking": True,
                "raised_at": created_at,
            },
            {
                "field": "core_mechanic.feedback_loop",
                "reason": (
                    "Initializer placeholder; needs a real description of "
                    "what the game shows in response."
                ),
                "blocking": True,
                "raised_at": created_at,
            },
            {
                "field": "math_domain",
                "reason": (
                    "Initializer defaulted to 'unresolved'. Author must "
                    "choose a real math domain from the schema enum "
                    "before advancing status."
                ),
                "blocking": True,
                "raised_at": created_at,
            },
            {
                "field": "target_skill.description",
                "reason": (
                    "Initializer placeholder; needs a real skill "
                    "description."
                ),
                "blocking": True,
                "raised_at": created_at,
            },
            {
                "field": "interaction_type_candidate",
                "reason": (
                    "Initializer defaulted to 'unresolved'. Runner should "
                    "resolve against taxonomy/interaction_types.yaml."
                ),
                "blocking": True,
                "raised_at": created_at,
            },
            {
                "field": "misconception_targets",
                "reason": (
                    "Initializer placeholder M1; needs a real misconception "
                    "the game is designed to expose."
                ),
                "blocking": True,
                "raised_at": created_at,
            },
            {
                "field": "success_condition",
                "reason": (
                    "Initializer placeholder; needs a real one-sentence "
                    "successful play session description."
                ),
                "blocking": True,
                "raised_at": created_at,
            },
            {
                "field": "constraints",
                "reason": (
                    "Initializer placeholder; needs real design "
                    "constraints."
                ),
                "blocking": True,
                "raised_at": created_at,
            },
            {
                "field": "portfolio_fit.why_now",
                "reason": (
                    "Initializer placeholder; needs a real portfolio "
                    "rationale."
                ),
                "blocking": True,
                "raised_at": created_at,
            },
        ],
        "review_notes": [],
        "author_notes": [
            (
                "This brief was created by scripts/new_game_init.py with "
                "placeholder content."
            ),
            (
                "All fields marked [INITIALIZER PLACEHOLDER] must be "
                "rewritten by a human author before advancing status from "
                "'draft'."
            ),
            (
                "The 10 unresolved_items entries list the specific fields "
                "needing rewrite."
            ),
        ],
    }


# --- main ----------------------------------------------------------------


def main(argv):
    parser = argparse.ArgumentParser(
        prog="new_game_init.py",
        description=(
            "Create the starter structure and starter files for a new "
            "game slug."
        ),
    )
    parser.add_argument(
        "--slug",
        type=validate_slug,
        required=True,
        help="kebab-case slug (pattern ^[a-z0-9]+(-[a-z0-9]+)*$, 2-64 chars)",
    )
    parser.add_argument(
        "--title",
        type=validate_bounded_string("title", 1, 120),
        required=True,
        help="Working title (1-120 chars)",
    )
    parser.add_argument(
        "--subject",
        choices=SUBJECTS,
        required=True,
        help="Subject area. Only 'math' is supported in v0.1.0.",
    )
    parser.add_argument(
        "--grade-band",
        choices=GRADE_BANDS,
        required=True,
        help=(
            "Target grade band. Must be a committed value ('unresolved' "
            "is NOT offered here because project_config requires "
            "committed state)."
        ),
    )
    parser.add_argument(
        "--primary-standard",
        type=validate_bounded_string("primary-standard", 1, 120),
        required=True,
        help=(
            "Primary standards label (1-120 chars, plain string, no format "
            "validation — math-games treats this as a label)."
        ),
    )
    parser.add_argument(
        "--created-at",
        type=parse_iso_z,
        default=None,
        help=(
            "ISO 8601 date-time with Z suffix (e.g. 2026-04-11T09:00:00Z). "
            "Default: current UTC time at script invocation."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Build and self-validate the templates in memory without "
            "writing any files or creating any directories. Skips the "
            "slug-exists check. Exits 0 if templates validate, 1 if "
            "they don't."
        ),
    )

    args = parser.parse_args(argv[1:])

    # --- load schemas (exit 2 on any setup error) ---
    concept_brief_schema = load_schema(CONCEPT_BRIEF_SCHEMA, "concept_brief")
    project_config_schema = load_schema(PROJECT_CONFIG_SCHEMA, "project_config")

    # --- compute timestamp and IDs ---
    created_at = args.created_at if args.created_at is not None else now_iso_z()
    config_id, brief_id = derive_ids(args.slug, created_at)

    # --- build templates ---
    project_config = build_project_config(
        slug=args.slug,
        subject=args.subject,
        grade_band=args.grade_band,
        primary_standard=args.primary_standard,
        created_at=created_at,
        config_id=config_id,
    )
    concept_brief = build_concept_brief(
        slug=args.slug,
        title=args.title,
        grade_band=args.grade_band,
        primary_standard=args.primary_standard,
        created_at=created_at,
        brief_id=brief_id,
    )

    # --- self-validate templates BEFORE any file is written ---
    try:
        Draft202012Validator(project_config_schema).validate(project_config)
    except ValidationError as e:
        die_failure(
            f"generated project_config does not validate against schema: "
            f"{e.message}"
        )
    try:
        Draft202012Validator(concept_brief_schema).validate(concept_brief)
    except ValidationError as e:
        die_failure(
            f"generated concept_brief does not validate against schema: "
            f"{e.message}"
        )

    if args.dry_run:
        print(f"DRY-RUN: templates valid for slug={args.slug}")
        print(f"  project_config.real.json: would write {config_id}")
        print(f"  concept_brief.real.json:  would write {brief_id}")
        return 0

    # --- containment check ---
    requests_root = (REPO_ROOT / "generated" / "requests").resolve()
    target_dir = (REPO_ROOT / "generated" / "requests" / args.slug).resolve()
    try:
        target_dir.relative_to(requests_root)
    except ValueError:
        die_failure(
            f"target path must live under generated/requests/, got "
            f"{target_dir}"
        )

    project_config_path = target_dir / "project_config.real.json"
    concept_brief_path = target_dir / "concept_brief.real.json"

    # --- existence check (slug directory AND both target files) ---
    if target_dir.exists():
        die_failure(f"slug already exists: {target_dir}")
    if project_config_path.exists():
        die_failure(f"target file already exists: {project_config_path}")
    if concept_brief_path.exists():
        die_failure(f"target file already exists: {concept_brief_path}")

    # --- create directory (exactly one, narrow scope) ---
    # Only generated/requests/<slug>/ is created. generated/drafts/<slug>/
    # and generated/review/<slug>/ are intentionally NOT created here —
    # later-phase directories are created by the generator and promoter
    # only when their phases actually begin.
    target_dir.mkdir(parents=False, exist_ok=False)

    # --- write files ---
    project_config_path.write_text(
        canonical_dump(project_config), encoding="utf-8"
    )
    concept_brief_path.write_text(
        canonical_dump(concept_brief), encoding="utf-8"
    )

    # --- report ---
    print("new_game_init.py — success")
    print(f"  slug:           {args.slug}")
    print(f"  title:          {args.title}")
    print(f"  created_at:     {created_at}")
    print(f"  slug dir:       {target_dir.relative_to(REPO_ROOT)}")
    print(
        f"  project_config: {project_config_path.relative_to(REPO_ROOT)}"
    )
    print(f"    config_id:    {config_id}")
    print(f"    sha256:       {sha256_of_file(project_config_path)}")
    print(
        f"  concept_brief:  {concept_brief_path.relative_to(REPO_ROOT)}"
    )
    print(f"    brief_id:     {brief_id}")
    print(f"    sha256:       {sha256_of_file(concept_brief_path)}")
    print("  status:         success")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
