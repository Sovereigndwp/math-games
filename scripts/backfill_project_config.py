#!/usr/bin/env python3
"""
backfill_project_config.py - Package 13 legacy normalization helper

One-shot helper that creates a valid project_config.real.json for a
slug that already has an operational artifact chain but pre-dates
Package 10. The script derives starter values from the slug's
existing concept_brief.real.json (preferred) or concept_packet.draft
.json (fallback), with optional CLI overrides for fields that cannot
be auto-derived.

The script is strictly additive:
  - writes only the missing project_config.real.json
  - refuses to overwrite an existing project_config.real.json
  - never touches any other file
  - never calls another script
  - never mutates phase beyond choosing current_phase="review" at
    creation time (all legacy slugs are observed as reviewed)

Usage:
  python3 scripts/backfill_project_config.py \\
    --slug <slug> \\
    [--primary-standard "<standard>"] \\
    [--grade-band {pre_k|k_2|3_5|6_8|9_12|cross_band}] \\
    [--created-at 2026-MM-DDTHH:MM:SSZ] \\
    [--dry-run]

Exit codes:
  0  success (file written, or --dry-run with valid derivation)
  1  failure (existing target, unparseable source, missing source,
     derivation failure, self-validation failure, containment
     violation, write I/O error)
  2  setup error (missing jsonschema, missing/unparseable schema
     file, invalid CLI argument)

Design stance:
  This is a normalization helper, not a smart generator. It prefers
  honest derivation from existing data over invention. When data is
  insufficient, the script fails with a clear message and tells the
  operator which CLI override is needed. It does not guess, does not
  hallucinate, does not backfill "unresolved" values where a real
  value is available.
"""

import argparse
import hashlib
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
ISO_Z_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)

GRADE_BANDS = ["pre_k", "k_2", "3_5", "6_8", "9_12", "cross_band"]

DEFAULT_SENSORY_PRIORITIES = ["visual_clarity", "low_distraction"]
DEFAULT_FORBIDDEN_SCOPE = ["no scope changes until backfill is reviewed"]


# ---- helpers -----------------------------------------------------------


def die_setup(msg):
    sys.stderr.write(f"SETUP ERROR: {msg}\n")
    sys.exit(2)


def die_failure(msg):
    sys.stderr.write(f"FAILURE: {msg}\n")
    sys.exit(1)


def load_json_strict(path, context):
    """Load a JSON file; die_failure on parse errors (not die_setup).
    This is used for source files that must be parseable if they exist.
    Returns None if the file does not exist."""
    if not path.exists():
        return None
    try:
        with path.open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        die_failure(f"{path} exists but is not parseable JSON: {e.msg}")
    except OSError as e:
        die_failure(f"{path} could not be read: {e}")


def load_schema(path, context):
    """Load the project_config schema. Missing/unparseable is a setup
    error, not a derivation failure."""
    if not path.exists():
        die_setup(f"required schema missing: {path}")
    try:
        with path.open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        die_setup(f"{context} JSON parse error at {path}: {e.msg}")


def canonical_dump(obj):
    """Deterministic JSON: sorted keys, 2-space indent, trailing newline."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


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
            f"--created-at must be ISO 8601 with Z suffix "
            f"(e.g. 2026-04-11T09:00:00Z), got {value!r}"
        )
    return value


def derive_config_id(slug, created_at):
    date_part = created_at[:10].replace("-", "")  # "20260410"
    h = hashlib.sha256(
        f"{slug}|{created_at}|backfill".encode("utf-8")
    ).hexdigest()[:6]
    return f"pc_{date_part}_{h}"


def sha256_of_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


# ---- derivation ----------------------------------------------------------


def read_sources(slug):
    """Read the 3 possible source files for a slug. Returns a dict with
    keys 'brief', 'draft', 'manifest' each either a parsed dict or None."""
    brief_path = REPO_ROOT / "generated" / "requests" / slug / "concept_brief.real.json"
    draft_path = REPO_ROOT / "generated" / "drafts" / slug / "concept_packet.draft.json"
    manifest_path = REPO_ROOT / "generated" / "drafts" / slug / "concept_packet.manifest.json"
    return {
        "brief": load_json_strict(brief_path, "concept_brief"),
        "draft": load_json_strict(draft_path, "concept_packet.draft"),
        "manifest": load_json_strict(manifest_path, "concept_packet.manifest"),
        "brief_path": brief_path,
        "draft_path": draft_path,
        "manifest_path": manifest_path,
    }


def _get_nested(d, *keys):
    """Safe nested dict get. Returns None on any missing key."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def derive_project_config(slug, sources, cli):
    """Derive a project_config dict from the slug's sources and CLI
    overrides. Tracks derivation sources for the notes field. Fails
    loudly when a required field cannot be derived."""
    brief = sources["brief"]
    draft = sources["draft"]
    manifest = sources["manifest"]

    if brief is None and draft is None:
        die_failure(
            f"slug {slug} has no usable source for backfill "
            f"(no concept_brief.real.json, no concept_packet.draft.json)"
        )

    sources_used = []
    if brief is not None:
        sources_used.append("concept_brief.real.json")
    if draft is not None:
        sources_used.append("concept_packet.draft.json")
    if manifest is not None:
        sources_used.append("concept_packet.manifest.json")
    source_summary = " + ".join(sources_used) if sources_used else "none"

    overrides_used = []

    # --- created_at ---
    if cli["created_at"] is not None:
        created_at = cli["created_at"]
        overrides_used.append("--created-at")
    else:
        brief_ca = _get_nested(brief, "created_at")
        manifest_ga = _get_nested(manifest, "generated_at")
        if isinstance(brief_ca, str) and brief_ca:
            created_at = brief_ca
        elif isinstance(manifest_ga, str) and manifest_ga:
            created_at = manifest_ga
        else:
            die_failure(
                "cannot derive created_at (no brief, no manifest). "
                "Re-run with --created-at 2026-MM-DDTHH:MM:SSZ."
            )

    # --- grade_band ---
    if cli["grade_band"] is not None:
        grade_band = cli["grade_band"]
        overrides_used.append("--grade-band")
    else:
        brief_gb = _get_nested(brief, "target_learners", "grade_band_candidate")
        draft_gb = _get_nested(draft, "target_learners", "grade_band_candidate")
        candidates = [gb for gb in (brief_gb, draft_gb) if gb in GRADE_BANDS]
        if candidates:
            grade_band = candidates[0]
        else:
            die_failure(
                "cannot derive grade_band (all sources say 'unresolved' "
                "or absent). Re-run with --grade-band "
                "{pre_k|k_2|3_5|6_8|9_12|cross_band}."
            )

    # --- primary_standard ---
    if cli["primary_standard"] is not None:
        primary_standard = cli["primary_standard"]
        overrides_used.append("--primary-standard")
    else:
        brief_cc = _get_nested(brief, "target_skill", "ccss_candidate")
        draft_cc = _get_nested(draft, "target_skill", "ccss_candidate")
        picks = []
        if isinstance(brief_cc, list) and brief_cc:
            picks.append(brief_cc[0])
        if isinstance(draft_cc, list) and draft_cc:
            picks.append(draft_cc[0])
        if picks:
            primary_standard = picks[0]
        else:
            die_failure(
                "cannot derive primary_standard (no CCSS label in "
                "sources). Re-run with --primary-standard \"<label>\"."
            )

    # --- target_skill.description ---
    brief_td = _get_nested(brief, "target_skill", "description")
    draft_td = _get_nested(draft, "target_skill", "description")
    if isinstance(brief_td, str) and brief_td:
        target_skill_description = brief_td
    elif isinstance(draft_td, str) and draft_td:
        target_skill_description = draft_td
    else:
        die_failure(
            "cannot derive target_skill.description (no brief "
            "target_skill, no draft target_skill)."
        )

    # --- target_skill.ccss_candidate ---
    brief_cc2 = _get_nested(brief, "target_skill", "ccss_candidate")
    draft_cc2 = _get_nested(draft, "target_skill", "ccss_candidate")
    if isinstance(brief_cc2, list):
        ccss_candidate = list(brief_cc2)
    elif isinstance(draft_cc2, list):
        ccss_candidate = list(draft_cc2)
    else:
        ccss_candidate = [primary_standard]
    # If both sources were empty lists, fall back to [primary_standard].
    if not ccss_candidate:
        ccss_candidate = [primary_standard]

    # --- interaction_type_candidate ---
    brief_it = _get_nested(brief, "interaction_type_candidate")
    draft_it = _get_nested(draft, "interaction_type_candidate")
    if isinstance(brief_it, str) and brief_it:
        interaction_type_candidate = brief_it
    elif isinstance(draft_it, str) and draft_it:
        interaction_type_candidate = draft_it
    else:
        interaction_type_candidate = "unresolved"

    # --- family_candidate ---
    if brief is not None and "family_candidate" in brief:
        family_candidate = brief.get("family_candidate")
    elif draft is not None and "family_candidate" in draft:
        family_candidate = draft.get("family_candidate")
    else:
        family_candidate = None

    # --- core_misconception ---
    def _pick_mc(mc_list):
        if not isinstance(mc_list, list) or not mc_list:
            return None
        first = mc_list[0]
        if not isinstance(first, dict):
            return None
        mc_id = first.get("id")
        mc_desc = first.get("description")
        if not isinstance(mc_id, str) or not isinstance(mc_desc, str):
            return None
        return {"id": mc_id, "description": mc_desc}

    core_misconception = _pick_mc(_get_nested(brief, "misconception_targets"))
    if core_misconception is None:
        core_misconception = _pick_mc(
            _get_nested(draft, "misconception_targets")
        )
    if core_misconception is None:
        die_failure(
            "cannot derive core_misconception. The script refuses to "
            "invent a misconception. Check that the slug's source "
            "files contain at least one misconception target."
        )

    # --- sensory_priorities ---
    # No source field; always use the hard-coded starter default.
    sensory_priorities = list(DEFAULT_SENSORY_PRIORITIES)

    # --- forbidden_scope ---
    brief_cons = _get_nested(brief, "constraints")
    draft_cons = _get_nested(draft, "constraints")
    if isinstance(brief_cons, list) and brief_cons:
        forbidden_scope = list(brief_cons)
    elif isinstance(draft_cons, list) and draft_cons:
        forbidden_scope = list(draft_cons)
    else:
        forbidden_scope = list(DEFAULT_FORBIDDEN_SCOPE)

    # --- current_phase ---
    # Hard-coded "review" per Package 13 J2. All legacy slugs observed
    # by phase_router.py as being in observed_phase=reviewed.
    current_phase = "review"

    # --- success_metric ---
    brief_sc = _get_nested(brief, "success_condition")
    draft_sc = _get_nested(draft, "success_condition")
    if isinstance(brief_sc, str) and brief_sc:
        success_metric = brief_sc
    elif isinstance(draft_sc, str) and draft_sc:
        success_metric = draft_sc
    else:
        die_failure(
            "cannot derive success_metric (no brief success_condition, "
            "no draft success_condition)."
        )

    # --- subject and schema_version ---
    subject = "math"
    schema_version = "0.1.0"

    # --- config_id ---
    config_id = derive_config_id(slug, created_at)

    # --- notes ---
    overrides_str = ", ".join(overrides_used) if overrides_used else "none"
    notes = (
        f"Backfilled by scripts/backfill_project_config.py from legacy "
        f"artifacts for slug {slug}. Source summary: {source_summary}. "
        f"CLI overrides: {overrides_str}. This file was derived from "
        f"existing artifacts that pre-date Package 10; it must be "
        f"reviewed before being treated as authoritative operational "
        f"state."
    )

    # --- assemble config ---
    config = {
        "schema_version": schema_version,
        "config_id": config_id,
        "created_at": created_at,
        "slug": slug,
        "subject": subject,
        "grade_band": grade_band,
        "primary_standard": primary_standard,
        "target_skill": {
            "description": target_skill_description,
            "ccss_candidate": ccss_candidate,
        },
        "interaction_type_candidate": interaction_type_candidate,
        "family_candidate": family_candidate,
        "core_misconception": core_misconception,
        "sensory_priorities": sensory_priorities,
        "forbidden_scope": forbidden_scope,
        "current_phase": current_phase,
        "success_metric": success_metric,
        "notes": notes,
    }

    return config, source_summary, overrides_used


# ---- report -------------------------------------------------------------


def print_derivation_report(config, source_summary, overrides_used, target_path, dry_run, validated):
    print("backfill_project_config.py — " + ("dry-run" if dry_run else "run"))
    print()
    print(f"slug:                         {config['slug']}")
    print(f"source summary:               {source_summary}")
    print(
        f"cli overrides:                "
        f"{', '.join(overrides_used) if overrides_used else 'none'}"
    )
    print()
    print("derivation report:")
    print(f"  config_id:                  {config['config_id']}")
    print(f"  created_at:                 {config['created_at']}")
    print(f"  subject:                    {config['subject']}")
    print(f"  grade_band:                 {config['grade_band']}")
    print(f"  primary_standard:           {config['primary_standard']}")
    ts_desc = config['target_skill']['description']
    print(
        f"  target_skill.description:   "
        f"{ts_desc[:80] + '...' if len(ts_desc) > 80 else ts_desc}"
    )
    print(
        f"  target_skill.ccss_candidate: "
        f"{config['target_skill']['ccss_candidate']}"
    )
    print(
        f"  interaction_type_candidate: "
        f"{config['interaction_type_candidate']}"
    )
    print(f"  family_candidate:           {config['family_candidate']!r}")
    print(f"  core_misconception.id:      {config['core_misconception']['id']}")
    cm_desc = config['core_misconception']['description']
    print(
        f"  core_misconception.desc:    "
        f"{cm_desc[:70] + '...' if len(cm_desc) > 70 else cm_desc}"
    )
    print(f"  sensory_priorities:         {config['sensory_priorities']}")
    print(
        f"  forbidden_scope:            "
        f"{len(config['forbidden_scope'])} items"
    )
    print(f"  current_phase:              {config['current_phase']}")
    sm = config['success_metric']
    print(
        f"  success_metric:             "
        f"{sm[:80] + '...' if len(sm) > 80 else sm}"
    )
    print()
    print(f"target path: {target_path}")
    print(
        f"self-validation against project_config.schema.json: "
        f"{'PASS' if validated else 'FAIL'}"
    )


# ---- main ---------------------------------------------------------------


def main(argv):
    parser = argparse.ArgumentParser(
        prog="backfill_project_config.py",
        description=(
            "Create a project_config.real.json for a legacy slug that "
            "already has an operational artifact chain but pre-dates "
            "Package 10."
        ),
    )
    parser.add_argument(
        "--slug",
        type=validate_slug,
        required=True,
        help="kebab-case slug (pattern ^[a-z0-9]+(-[a-z0-9]+)*$, 2-64 chars)",
    )
    parser.add_argument(
        "--primary-standard",
        type=str,
        default=None,
        help=(
            "Override the auto-derived primary_standard. Required if "
            "the slug's source files have no usable CCSS label."
        ),
    )
    parser.add_argument(
        "--grade-band",
        choices=GRADE_BANDS,
        default=None,
        help=(
            "Override the auto-derived grade_band. Required if the "
            "slug's source files say 'unresolved'."
        ),
    )
    parser.add_argument(
        "--created-at",
        type=parse_iso_z,
        default=None,
        help=(
            "Override the default created_at. Default: the "
            "concept_brief's created_at (if the brief exists), "
            "otherwise the concept_packet manifest's generated_at."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help=(
            "Build, derive, and self-validate the project_config in "
            "memory without writing any file."
        ),
    )

    args = parser.parse_args(argv[1:])

    # --- load schema ---
    schema = load_schema(PROJECT_CONFIG_SCHEMA, "project_config")

    # --- read sources ---
    sources = read_sources(args.slug)

    # --- target path ---
    target_dir = (REPO_ROOT / "generated" / "requests" / args.slug).resolve()
    requests_root = (REPO_ROOT / "generated" / "requests").resolve()
    try:
        target_dir.relative_to(requests_root)
    except ValueError:
        die_failure(
            f"target path must live under generated/requests/, got "
            f"{target_dir}"
        )
    target_path = target_dir / "project_config.real.json"

    # --- refuse to overwrite ---
    if not args.dry_run and target_path.exists():
        die_failure(
            f"project_config.real.json already exists for slug "
            f"{args.slug}: {target_path}. This script refuses to "
            f"overwrite existing configs."
        )

    # --- derive config ---
    cli_overrides = {
        "primary_standard": args.primary_standard,
        "grade_band": args.grade_band,
        "created_at": args.created_at,
    }
    config, source_summary, overrides_used = derive_project_config(
        args.slug, sources, cli_overrides
    )

    # --- self-validate BEFORE any file write ---
    try:
        Draft202012Validator(schema).validate(config)
    except ValidationError as e:
        die_failure(
            f"derived project_config does not validate against schema: "
            f"{e.message}"
        )

    # --- dry-run: print and exit ---
    if args.dry_run:
        print_derivation_report(
            config, source_summary, overrides_used,
            target_path.relative_to(REPO_ROOT), dry_run=True, validated=True
        )
        print("would write: YES")
        return 0

    # --- real write ---
    # Ensure target_dir exists (it should — legacy slugs already have
    # generated/requests/<slug>/). Use exist_ok=True defensively.
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        target_path.write_text(canonical_dump(config), encoding="utf-8")
    except OSError as e:
        die_failure(f"could not write {target_path}: {e}")

    # --- report ---
    print_derivation_report(
        config, source_summary, overrides_used,
        target_path.relative_to(REPO_ROOT), dry_run=False, validated=True
    )
    print()
    print("write status: SUCCESS")
    print(f"  path:   {target_path.relative_to(REPO_ROOT)}")
    print(f"  size:   {target_path.stat().st_size} bytes")
    print(f"  sha256: {sha256_of_file(target_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
