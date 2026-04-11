#!/usr/bin/env python3
"""
phase_router.py - Package 12 advisory read-only phase inspector

Given a slug, report the operational artifact chain state for that slug
in math-games:

  - which of 8 per-slug files exist
  - what project_config.real.json says the current phase is (if present)
  - what phase the file chain appears to be in (derived from file presence)
  - the single most logical next artifact to create (or "hold")
  - any broken-chain or configured/observed mismatch warnings

The router is strictly advisory and strictly read-only. It does not
write, modify, promote, generate, or mutate anything. It does not call
any other script. It is safe to run on any slug at any time, including
on the legacy slugs currently in the repo.

The router uses stdlib only. No jsonschema dependency. Schema
validation is validate_schemas.py's job, not this script's.

Usage:
  python3 scripts/phase_router.py --slug <slug> [--json]

Exit codes:
  0  router ran and reported (even with warnings)
  2  argparse error (missing --slug, bad slug format)

The router never exits non-zero because of what it found in the chain.
Warnings are information, not failures.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# ---- file codes --------------------------------------------------------

# (code, key, dir_segment, filename)
FILE_SPECS = [
    ("PC", "project_config",         "requests", "project_config.real.json"),
    ("CB", "concept_brief",          "requests", "concept_brief.real.json"),
    ("GR", "generation_request",     "requests", "generation_request.real.json"),
    ("PR", "promotion_request",      "requests", "promotion_request.real.json"),
    ("D",  "concept_packet_draft",   "drafts",   "concept_packet.draft.json"),
    ("M",  "concept_packet_manifest","drafts",   "concept_packet.manifest.json"),
    ("RV", "concept_packet_review",  "review",   "concept_packet.review.json"),
    ("RC", "promotion_record",       "review",   "promotion_record.json"),
]

# ---- helpers -----------------------------------------------------------


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


def build_file_report(slug):
    """Return a dict keyed by FILE_SPEC key, with code, present, path."""
    report = {}
    for code, key, dir_segment, filename in FILE_SPECS:
        rel = f"generated/{dir_segment}/{slug}/{filename}"
        abspath = REPO_ROOT / rel
        report[key] = {
            "code": code,
            "present": abspath.exists() and abspath.is_file(),
            "path": rel,
        }
    return report


def read_project_config_phase(slug):
    """Best-effort read of project_config.current_phase.

    Returns (configured_phase, source) where source is one of:
      "from_project_config" - value extracted successfully
      "absent"              - PC file does not exist
      "unparseable"         - PC file exists but is not parseable JSON
      "no_current_phase_field" - PC parseable but no usable current_phase
    """
    pc_path = REPO_ROOT / "generated" / "requests" / slug / "project_config.real.json"
    if not pc_path.exists():
        return None, "absent"
    try:
        with pc_path.open() as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return None, "unparseable"
    except OSError:
        return None, "unparseable"
    phase = data.get("current_phase")
    if not isinstance(phase, str) or not phase:
        return None, "no_current_phase_field"
    return phase, "from_project_config"


def derive_observed_phase(files):
    """Evaluate routing rules in order from most advanced to least.
    First match wins. Returns a phase name."""
    pc = files["project_config"]["present"]
    cb = files["concept_brief"]["present"]
    gr = files["generation_request"]["present"]
    pr = files["promotion_request"]["present"]
    d  = files["concept_packet_draft"]["present"]
    m  = files["concept_packet_manifest"]["present"]
    rv = files["concept_packet_review"]["present"]
    rc = files["promotion_record"]["present"]

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


def next_action_for(observed_phase, slug, files):
    """Return (next_artifact, next_action) for a given observed phase.

    next_artifact is a repo-relative path string to the file the operator
    should create next, or None if the next action is to run a script or
    to hold.
    """
    if observed_phase == "empty":
        return (
            None,
            f"run scripts/new_game_init.py --slug {slug} ... "
            f"to initialize this slug",
        )
    if observed_phase == "initialized":
        return (
            files["generation_request"]["path"],
            "create the generation_request.real.json manually "
            "(author-authored for now)",
        )
    if observed_phase == "generation_requested":
        return (
            None,
            f"run scripts/generate_concept_packet_stub.py "
            f"{files['generation_request']['path']}",
        )
    if observed_phase == "drafted":
        return (
            files["promotion_request"]["path"],
            "create the promotion_request.real.json manually "
            "(author-authored for now)",
        )
    if observed_phase == "promotion_requested":
        return (
            None,
            f"run scripts/promote_draft_stub.py "
            f"{files['promotion_request']['path']}",
        )
    if observed_phase == "reviewed":
        return (
            None,
            "hold - no next artifact inside Package 12 scope "
            "(future QA/repair/release phases are not yet implemented)",
        )
    # observed_phase == "partial"
    return (None, "broken chain; inspect warnings")


def compute_warnings(files, configured_phase, configured_source, observed_phase):
    """Return list of {code, message} dicts."""
    warnings = []
    pc = files["project_config"]["present"]
    cb = files["concept_brief"]["present"]
    gr = files["generation_request"]["present"]
    pr = files["promotion_request"]["present"]
    d  = files["concept_packet_draft"]["present"]
    m  = files["concept_packet_manifest"]["present"]
    rv = files["concept_packet_review"]["present"]
    rc = files["promotion_record"]["present"]
    any_non_pc = any([cb, gr, pr, d, m, rv, rc])

    # --- broken-chain warnings (always evaluated) ---
    if any_non_pc and not pc:
        warnings.append({
            "code": "W1",
            "message": (
                "project_config.real.json absent; legacy slug "
                "pre-dates Package 10. Consider creating one manually "
                "to enable future phase tracking."
            ),
        })
    if configured_source == "unparseable":
        warnings.append({
            "code": "W2",
            "message": (
                "project_config.real.json exists but is not parseable "
                "JSON; configured_phase cannot be read."
            ),
        })
    if configured_source == "no_current_phase_field":
        warnings.append({
            "code": "W3",
            "message": (
                "project_config.real.json exists but has no usable "
                "current_phase field."
            ),
        })
    if d and not m:
        warnings.append({
            "code": "W4",
            "message": (
                "concept_packet.draft.json exists but "
                "concept_packet.manifest.json is missing; generator "
                "output is broken."
            ),
        })
    if m and not d:
        warnings.append({
            "code": "W5",
            "message": (
                "concept_packet.manifest.json exists but "
                "concept_packet.draft.json is missing; generator "
                "output is broken."
            ),
        })
    if rv and not rc:
        warnings.append({
            "code": "W6",
            "message": (
                "concept_packet.review.json exists but "
                "promotion_record.json is missing; promoter output "
                "is broken."
            ),
        })
    if rc and not rv:
        warnings.append({
            "code": "W7",
            "message": (
                "promotion_record.json exists but "
                "concept_packet.review.json is missing; promoter "
                "output is broken."
            ),
        })
    if (d or m) and not gr:
        warnings.append({
            "code": "W8",
            "message": (
                "draft or manifest exists without a "
                "generation_request.real.json; chain is backward-skipped."
            ),
        })
    if pr and not (d and m):
        warnings.append({
            "code": "W9",
            "message": (
                "promotion_request.real.json exists but the draft or "
                "manifest it would promote is missing."
            ),
        })
    if (rv or rc) and not pr:
        warnings.append({
            "code": "W10",
            "message": (
                "review or promotion_record exists without a "
                "promotion_request.real.json; chain is backward-skipped."
            ),
        })
    if (not cb) and any([gr, pr, d, m, rv, rc]):
        warnings.append({
            "code": "W11",
            "message": (
                "concept_brief.real.json absent but downstream artifacts "
                "exist; legacy or fixture-runtime chain."
            ),
        })

    # --- mismatch warnings (only when configured_phase is readable) ---
    if configured_source == "from_project_config" and configured_phase is not None:
        if configured_phase == "concept" and observed_phase in (
            "drafted", "promotion_requested", "reviewed"
        ):
            warnings.append({
                "code": "M1",
                "message": (
                    f"configured phase is 'concept' but observed phase is "
                    f"'{observed_phase}'. Consider updating "
                    f"project_config.current_phase."
                ),
            })
        if configured_phase == "packet" and observed_phase in (
            "initialized", "generation_requested"
        ):
            warnings.append({
                "code": "M2",
                "message": (
                    "configured phase is 'packet' but no draft/manifest "
                    "exists yet. Either the draft chain has not been run, "
                    "or configured phase is ahead of observed state."
                ),
            })
        if configured_phase == "packet" and observed_phase == "reviewed":
            warnings.append({
                "code": "M3",
                "message": (
                    "configured phase is 'packet' but observed phase is "
                    "'reviewed'. Consider updating "
                    "project_config.current_phase."
                ),
            })
        if configured_phase == "review" and observed_phase != "reviewed":
            warnings.append({
                "code": "M4",
                "message": (
                    f"configured phase is 'review' but observed phase is "
                    f"'{observed_phase}'. Review and/or promotion_record "
                    f"are missing."
                ),
            })
        if configured_phase in ("prototype", "qa", "repair", "release_ready"):
            warnings.append({
                "code": "M5",
                "message": (
                    f"configured phase is '{configured_phase}', which v0.1 "
                    f"of phase_router cannot detect from file presence. "
                    f"The router has no opinion for these phases."
                ),
            })

    return warnings


def build_report(slug):
    files = build_file_report(slug)
    configured_phase, configured_source = read_project_config_phase(slug)
    observed_phase = derive_observed_phase(files)
    next_artifact, next_action = next_action_for(observed_phase, slug, files)
    warnings = compute_warnings(
        files, configured_phase, configured_source, observed_phase
    )
    files_present = sum(1 for v in files.values() if v["present"])
    return {
        "slug": slug,
        "observed_files": files,
        "configured_phase": configured_phase,
        "configured_phase_source": configured_source,
        "observed_phase": observed_phase,
        "next_artifact": next_artifact,
        "next_action": next_action,
        "warnings": warnings,
        "summary": {
            "files_present": files_present,
            "files_total": len(files),
            "phase": observed_phase,
            "warning_count": len(warnings),
        },
    }


# ---- presentation ------------------------------------------------------


def print_human_report(report):
    """Compact, operator-friendly human output.

    Prints:
      slug
      configured phase
      observed phase
      next artifact
      next action
      warnings count (and one-line-per-warning if any)
      compact file matrix
    """
    r = report
    configured = r["configured_phase"]
    if configured is None:
        if r["configured_phase_source"] == "absent":
            configured_display = "n/a (project_config.real.json absent)"
        elif r["configured_phase_source"] == "unparseable":
            configured_display = "unparseable"
        elif r["configured_phase_source"] == "no_current_phase_field":
            configured_display = "missing current_phase field"
        else:
            configured_display = "n/a"
    else:
        configured_display = configured

    next_artifact_display = r["next_artifact"] if r["next_artifact"] else "-"

    print(f"slug:             {r['slug']}")
    print(f"configured phase: {configured_display}")
    print(f"observed phase:   {r['observed_phase']}")
    print(f"next artifact:    {next_artifact_display}")
    print(f"next action:      {r['next_action']}")
    print(
        f"warnings:         {r['summary']['warning_count']} "
        f"({r['summary']['files_present']}/{r['summary']['files_total']} "
        f"files present)"
    )
    if r["warnings"]:
        for w in r["warnings"]:
            print(f"  {w['code']}: {w['message']}")

    # Compact file matrix: one line per file with code and marker
    print("files:")
    for _code, key, _dir_segment, _filename in FILE_SPECS:
        entry = r["observed_files"][key]
        marker = "[X]" if entry["present"] else "[ ]"
        print(f"  {marker} {entry['code']:<2}  {entry['path']}")


def main(argv):
    parser = argparse.ArgumentParser(
        prog="phase_router.py",
        description=(
            "Inspect the operational artifact chain for a slug in "
            "math-games and report the observed phase, configured "
            "phase, next valid artifact, and any warnings. "
            "Read-only and advisory."
        ),
    )
    parser.add_argument(
        "--slug",
        type=validate_slug,
        required=True,
        help="kebab-case slug (pattern ^[a-z0-9]+(-[a-z0-9]+)*$, 2-64 chars)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help=(
            "Emit a machine-readable JSON report instead of "
            "human-readable text. All fields in both modes carry the "
            "same information; only the presentation differs."
        ),
    )
    args = parser.parse_args(argv[1:])

    report = build_report(args.slug)

    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
