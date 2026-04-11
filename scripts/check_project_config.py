#!/usr/bin/env python3
"""
check_project_config.py - Package 14 advisory read-only consistency checker

Given a slug, compare the slug's project_config.real.json against its
concept_brief, concept_packet.draft, concept_packet.review, and the
phase inferred from file presence. Report mismatches only. Read-only
and advisory.

Purpose:
  Detect drift between a slug's control state (project_config) and
  its actual on-disk artifact chain. This is a safety layer that
  should run BEFORE any future script is allowed to mutate phase.

Scope:
  - 8 check categories (C1..C8) covering slug, grade_band,
    primary_standard, target_skill.description,
    interaction_type_candidate, family_candidate,
    core_misconception.id, and current_phase vs observed_phase.
  - Each check may produce up to 3 sub-comparisons (PC vs
    concept_brief, PC vs concept_packet.draft, PC vs
    concept_packet.review).
  - upgrade_from_unresolved: if a source field is "unresolved" and
    PC holds a committed value, treat as MISMATCH with sub-code
    upgrade_from_unresolved. The checker surfaces this because it
    represents a control-state claim stronger than the upstream
    artifact chain.

Design constraints:
  - stdlib only (no jsonschema; the checker does not validate
    schemas — that is validate_schemas.py's job).
  - Observed-phase derivation is DUPLICATED inline from
    phase_router.py. No cross-script imports. Tighter boundaries
    are better than clever reuse at this stage.
  - Read-only. No file writes. No phase mutation. No auto-fix.
  - Compact human-readable output by default; --json for tests.

Usage:
  python3 scripts/check_project_config.py --slug <slug> [--json]

Exit codes:
  0  checker ran and reported (even with FAIL or SKIP results)
  2  argparse error (missing --slug or bad slug format)

The checker never exits non-zero because of what it found in the
chain. Exit code indicates "did the tool run", not "what it found."
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

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

# Sources the checker reads and parses.
COMPARABLE_SOURCE_KEYS = [
    "concept_brief",
    "concept_packet_draft",
    "concept_packet_review",
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


def per_slug_path(slug, dir_segment, filename):
    return REPO_ROOT / "generated" / dir_segment / slug / filename


def build_file_presence(slug):
    """Return dict keyed by file key -> {present, path (relative),
    parseable, data}.

    parseable and data are None unless present=True and the file
    was successfully parsed."""
    report = {}
    for key, dir_segment, filename in FILE_SPECS:
        abspath = per_slug_path(slug, dir_segment, filename)
        entry = {
            "present": abspath.exists() and abspath.is_file(),
            "path": str(abspath.relative_to(REPO_ROOT)),
            "parseable": None,
            "data": None,
        }
        if entry["present"]:
            try:
                with abspath.open() as f:
                    entry["data"] = json.load(f)
                entry["parseable"] = True
            except (json.JSONDecodeError, OSError):
                entry["parseable"] = False
        report[key] = entry
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


# ---- check engine ------------------------------------------------------


SOURCE_LABEL = {
    "concept_brief": "CB",
    "concept_packet_draft": "draft",
    "concept_packet_review": "review",
}


# Sentinel used to distinguish "key is missing from dict" from
# "key is present with value None". This matters for nullable fields
# like family_candidate, where None is a legitimate value and must
# compare equal to another None from a source file (MATCH), not be
# treated as "PC missing field" (SKIP).
_MISSING = object()


def _get(d, *keys):
    """Walk a nested dict by keys. Returns _MISSING if any key is
    absent along the path or if a non-dict is encountered. Returns the
    actual value otherwise (which may be None for nullable fields)."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return _MISSING
        if k not in cur:
            return _MISSING
        cur = cur[k]
    return cur


def run_simple_check(pc_data, files, code, field_label, pc_path, source_paths,
                     allow_upgrade_from_unresolved=False):
    """A "simple" check: compare a single PC value against a single
    value in each of the 3 comparable sources.

    pc_path: tuple of keys into PC (e.g. ("slug",) or
             ("target_skill", "description"))
    source_paths: dict mapping source_key -> tuple of keys into that
                  source's JSON
    allow_upgrade_from_unresolved: if True, a source value of
                                   "unresolved" against a non-unresolved
                                   PC value is MISMATCH with sub-code
                                   upgrade_from_unresolved.
    """
    pc_value = _get(pc_data, *pc_path) if pc_data is not None else _MISSING
    sub_comparisons = []

    if pc_value is _MISSING:
        result = "SKIP"
        note = "PC missing field"
        return {
            "code": code,
            "field": field_label,
            "result": result,
            "note": note,
            "pc_value": None,
            "sub_comparisons": [],
        }

    for source_key in COMPARABLE_SOURCE_KEYS:
        source_entry = files[source_key]
        label = SOURCE_LABEL[source_key]
        if not source_entry["present"]:
            sub_comparisons.append({
                "source": source_key,
                "source_label": label,
                "source_value": None,
                "result": "SKIP",
                "note": "source missing",
            })
            continue
        if source_entry["parseable"] is not True:
            sub_comparisons.append({
                "source": source_key,
                "source_label": label,
                "source_value": None,
                "result": "SKIP",
                "note": "source unparseable",
            })
            continue
        source_value = _get(source_entry["data"], *source_paths[source_key])
        if source_value is _MISSING:
            sub_comparisons.append({
                "source": source_key,
                "source_label": label,
                "source_value": None,
                "result": "SKIP",
                "note": "source missing field",
            })
            continue
        if source_value == pc_value:
            sub_comparisons.append({
                "source": source_key,
                "source_label": label,
                "source_value": source_value,
                "result": "MATCH",
                "note": None,
            })
        else:
            # Check for upgrade_from_unresolved pattern
            if (allow_upgrade_from_unresolved
                    and source_value == "unresolved"
                    and pc_value != "unresolved"):
                sub_comparisons.append({
                    "source": source_key,
                    "source_label": label,
                    "source_value": source_value,
                    "result": "MISMATCH",
                    "note": "upgrade_from_unresolved",
                })
            else:
                sub_comparisons.append({
                    "source": source_key,
                    "source_label": label,
                    "source_value": source_value,
                    "result": "MISMATCH",
                    "note": None,
                })

    # Roll up check result
    performed = [sc for sc in sub_comparisons if sc["result"] != "SKIP"]
    if not performed:
        result = "SKIP"
        note = "no comparable source"
    elif all(sc["result"] == "MATCH" for sc in performed):
        result = "PASS"
        note = None
    else:
        result = "FAIL"
        note = None

    return {
        "code": code,
        "field": field_label,
        "result": result,
        "note": note,
        "pc_value": pc_value,
        "sub_comparisons": sub_comparisons,
    }


def run_first_item_check(pc_data, files, code, field_label, pc_path,
                         source_list_paths, source_item_key):
    """For fields like primary_standard (PC = string; source =
    source_list[0]) and core_misconception.id (PC = object.id; source =
    source_list[0].id).

    pc_path: tuple of keys into PC yielding the value to compare
    source_list_paths: dict source_key -> tuple of keys into that
                       source yielding a list (e.g. ccss_candidate,
                       misconception_targets)
    source_item_key: key to extract from source_list[0] for comparison;
                     None means use the list[0] itself (for
                     primary_standard vs ccss_candidate[0])
    """
    pc_value = _get(pc_data, *pc_path) if pc_data is not None else _MISSING
    sub_comparisons = []

    if pc_value is _MISSING:
        return {
            "code": code,
            "field": field_label,
            "result": "SKIP",
            "note": "PC missing field",
            "pc_value": None,
            "sub_comparisons": [],
        }

    for source_key in COMPARABLE_SOURCE_KEYS:
        source_entry = files[source_key]
        label = SOURCE_LABEL[source_key]
        if not source_entry["present"]:
            sub_comparisons.append({
                "source": source_key,
                "source_label": label,
                "source_value": None,
                "result": "SKIP",
                "note": "source missing",
            })
            continue
        if source_entry["parseable"] is not True:
            sub_comparisons.append({
                "source": source_key,
                "source_label": label,
                "source_value": None,
                "result": "SKIP",
                "note": "source unparseable",
            })
            continue
        source_list = _get(source_entry["data"], *source_list_paths[source_key])
        if source_list is _MISSING or not isinstance(source_list, list) or not source_list:
            sub_comparisons.append({
                "source": source_key,
                "source_label": label,
                "source_value": None,
                "result": "SKIP",
                "note": "source missing field or empty",
            })
            continue
        first_item = source_list[0]
        if source_item_key is None:
            source_value = first_item
        else:
            source_value = (
                first_item.get(source_item_key)
                if isinstance(first_item, dict)
                else None
            )
        if source_value is None:
            sub_comparisons.append({
                "source": source_key,
                "source_label": label,
                "source_value": None,
                "result": "SKIP",
                "note": "source missing field",
            })
            continue
        if source_value == pc_value:
            sub_comparisons.append({
                "source": source_key,
                "source_label": label,
                "source_value": source_value,
                "result": "MATCH",
                "note": None,
            })
        else:
            sub_comparisons.append({
                "source": source_key,
                "source_label": label,
                "source_value": source_value,
                "result": "MISMATCH",
                "note": None,
            })

    performed = [sc for sc in sub_comparisons if sc["result"] != "SKIP"]
    if not performed:
        result = "SKIP"
        note = "no comparable source"
    elif all(sc["result"] == "MATCH" for sc in performed):
        result = "PASS"
        note = None
    else:
        result = "FAIL"
        note = None

    return {
        "code": code,
        "field": field_label,
        "result": result,
        "note": note,
        "pc_value": pc_value,
        "sub_comparisons": sub_comparisons,
    }


def run_phase_check(pc_data, observed_phase):
    """C8: project_config.current_phase vs observed_phase.

    Mapping rules:
      concept  <-> initialized | generation_requested
      packet   <-> drafted | promotion_requested
      review   <-> reviewed
      anything else (prototype, qa, repair, release_ready) -> SKIP
    """
    pc_value = _get(pc_data, "current_phase") if pc_data is not None else _MISSING
    if pc_value is _MISSING or pc_value is None:
        return {
            "code": "C8",
            "field": "current_phase vs observed_phase",
            "result": "SKIP",
            "note": "PC missing current_phase",
            "pc_value": None,
            "observed_phase": observed_phase,
            "sub_comparisons": [],
        }

    compatible = {
        "concept": ("initialized", "generation_requested"),
        "packet": ("drafted", "promotion_requested"),
        "review": ("reviewed",),
    }

    if pc_value in compatible:
        expected = compatible[pc_value]
        if observed_phase in expected:
            result = "PASS"
            note = None
        else:
            result = "FAIL"
            note = None
    elif pc_value in ("prototype", "qa", "repair", "release_ready"):
        result = "SKIP"
        note = (
            f"v0.1 has no file-presence signal for configured_phase "
            f"{pc_value!r}"
        )
    else:
        # Unknown phase string in PC — shouldn't happen if PC validates,
        # but we handle it gracefully.
        result = "SKIP"
        note = f"unrecognized configured_phase {pc_value!r}"

    return {
        "code": "C8",
        "field": "current_phase vs observed_phase",
        "result": result,
        "note": note,
        "pc_value": pc_value,
        "observed_phase": observed_phase,
        "sub_comparisons": [],
    }


# ---- main report -------------------------------------------------------


def build_report(slug):
    files = build_file_presence(slug)
    observed_phase = derive_observed_phase(files)

    pc_entry = files["project_config"]
    comparable_source_present = any(
        files[k]["present"] for k in COMPARABLE_SOURCE_KEYS
    )
    any_file_present = any(files[k]["present"] for k in files)

    # --- early exits: nothing to check ---
    if not pc_entry["present"]:
        if any_file_present:
            comparable_mode = "no_pc_has_artifacts"
        else:
            comparable_mode = "no_artifacts_at_all"
        return {
            "slug": slug,
            "sources": files,
            "comparable_mode": comparable_mode,
            "observed_phase": observed_phase,
            "checks": [],
            "summary": {
                "checks_total": 0,
                "checks_pass": 0,
                "checks_fail": 0,
                "checks_skip": 0,
                "has_project_config": False,
                "comparable": False,
            },
        }

    if pc_entry["parseable"] is not True:
        # PC exists but is unparseable. All checks will SKIP.
        comparable_mode = "pc_unparseable"
        checks = _all_skip_checks("PC unparseable")
        return {
            "slug": slug,
            "sources": files,
            "comparable_mode": comparable_mode,
            "observed_phase": observed_phase,
            "checks": checks,
            "summary": _summary_from(checks, has_pc=True, comparable=False),
        }

    pc_data = pc_entry["data"]

    # --- run 8 checks ---
    checks = [
        run_simple_check(
            pc_data, files,
            code="C1",
            field_label="slug",
            pc_path=("slug",),
            source_paths={
                "concept_brief": ("proposed_slug",),
                "concept_packet_draft": ("slug",),
                "concept_packet_review": ("slug",),
            },
        ),
        run_simple_check(
            pc_data, files,
            code="C2",
            field_label="grade_band",
            pc_path=("grade_band",),
            source_paths={
                "concept_brief": ("target_learners", "grade_band_candidate"),
                "concept_packet_draft": ("target_learners", "grade_band_candidate"),
                "concept_packet_review": ("target_learners", "grade_band_candidate"),
            },
            allow_upgrade_from_unresolved=True,
        ),
        run_first_item_check(
            pc_data, files,
            code="C3",
            field_label="primary_standard",
            pc_path=("primary_standard",),
            source_list_paths={
                "concept_brief": ("target_skill", "ccss_candidate"),
                "concept_packet_draft": ("target_skill", "ccss_candidate"),
                "concept_packet_review": ("target_skill", "ccss_candidate"),
            },
            source_item_key=None,
        ),
        run_simple_check(
            pc_data, files,
            code="C4",
            field_label="target_skill.description",
            pc_path=("target_skill", "description"),
            source_paths={
                "concept_brief": ("target_skill", "description"),
                "concept_packet_draft": ("target_skill", "description"),
                "concept_packet_review": ("target_skill", "description"),
            },
        ),
        run_simple_check(
            pc_data, files,
            code="C5",
            field_label="interaction_type_candidate",
            pc_path=("interaction_type_candidate",),
            source_paths={
                "concept_brief": ("interaction_type_candidate",),
                "concept_packet_draft": ("interaction_type_candidate",),
                "concept_packet_review": ("interaction_type_candidate",),
            },
            allow_upgrade_from_unresolved=True,
        ),
        run_simple_check(
            pc_data, files,
            code="C6",
            field_label="family_candidate",
            pc_path=("family_candidate",),
            source_paths={
                "concept_brief": ("family_candidate",),
                "concept_packet_draft": ("family_candidate",),
                "concept_packet_review": ("family_candidate",),
            },
        ),
        run_first_item_check(
            pc_data, files,
            code="C7",
            field_label="core_misconception.id",
            pc_path=("core_misconception", "id"),
            source_list_paths={
                "concept_brief": ("misconception_targets",),
                "concept_packet_draft": ("misconception_targets",),
                "concept_packet_review": ("misconception_targets",),
            },
            source_item_key="id",
        ),
        run_phase_check(pc_data, observed_phase),
    ]

    return {
        "slug": slug,
        "sources": files,
        "comparable_mode": "comparable",
        "observed_phase": observed_phase,
        "checks": checks,
        "summary": _summary_from(checks, has_pc=True, comparable=True),
    }


def _all_skip_checks(note):
    labels = [
        ("C1", "slug"),
        ("C2", "grade_band"),
        ("C3", "primary_standard"),
        ("C4", "target_skill.description"),
        ("C5", "interaction_type_candidate"),
        ("C6", "family_candidate"),
        ("C7", "core_misconception.id"),
        ("C8", "current_phase vs observed_phase"),
    ]
    return [
        {
            "code": code,
            "field": field,
            "result": "SKIP",
            "note": note,
            "pc_value": None,
            "sub_comparisons": [],
        }
        for code, field in labels
    ]


def _summary_from(checks, *, has_pc, comparable):
    passes = sum(1 for c in checks if c["result"] == "PASS")
    fails = sum(1 for c in checks if c["result"] == "FAIL")
    skips = sum(1 for c in checks if c["result"] == "SKIP")
    return {
        "checks_total": len(checks),
        "checks_pass": passes,
        "checks_fail": fails,
        "checks_skip": skips,
        "has_project_config": has_pc,
        "comparable": comparable,
    }


# ---- presentation ------------------------------------------------------


def _fmt_value(v, max_len=60):
    """Render a value for compact display."""
    if v is None:
        return "null"
    if isinstance(v, str):
        if len(v) > max_len:
            return f'"{v[:max_len]}..."'
        return f'"{v}"'
    return repr(v)


def print_human_report(report):
    slug = report["slug"]
    comparable_mode = report["comparable_mode"]
    print(f"check_project_config.py — slug: {slug}")
    print()

    # Sources block
    print("sources:")
    label_map = [
        ("project_config",        "project_config      "),
        ("concept_brief",         "concept_brief       "),
        ("concept_packet_draft",  "concept_packet.draft"),
        ("concept_packet_review", "concept_packet.review"),
    ]
    for key, label in label_map:
        entry = report["sources"][key]
        if entry["present"]:
            if entry["parseable"] is False:
                marker = "[unparseable]"
            else:
                marker = "[found]      "
        else:
            marker = "[missing]    "
        print(f"  {marker} {label}  {entry['path']}")
    print()

    # Early-exit nothing-to-check cases
    if comparable_mode == "no_artifacts_at_all":
        print(
            f"no artifacts at all on disk for slug {slug!r}. "
            f"Either the slug does not exist, or it has not been "
            f"initialized."
        )
        print(
            f"Use scripts/new_game_init.py --slug {slug} ... to "
            f"initialize this slug."
        )
        print()
        print("summary: 0 checks run")
        return

    if comparable_mode == "no_pc_has_artifacts":
        print(
            f"slug {slug!r} has artifact files on disk but no "
            f"project_config.real.json. The checker has nothing to "
            f"compare against."
        )
        print(
            f"Use scripts/backfill_project_config.py --slug {slug} "
            f"[--primary-standard ...] to create one, or "
            f"scripts/new_game_init.py for a fresh slug."
        )
        print()
        print("summary: 0 checks run")
        return

    if comparable_mode == "pc_unparseable":
        print(
            f"project_config.real.json for slug {slug!r} exists but "
            f"is not parseable JSON. All checks SKIP. Fix the file "
            f"before re-running."
        )
        print()
        _print_check_lines_and_summary(report)
        return

    # Normal comparable mode
    _print_check_lines_and_summary(report)


def _print_check_lines_and_summary(report):
    print("checks:")
    for check in report["checks"]:
        _print_check_line(check)
    s = report["summary"]
    print()
    print(
        f"summary: {s['checks_total']} checks, "
        f"{s['checks_pass']} pass, "
        f"{s['checks_fail']} fail, "
        f"{s['checks_skip']} skip"
    )


def _print_check_line(check):
    code = check["code"]
    field = check["field"]
    result = check["result"]
    if result == "PASS":
        performed = len([
            sc for sc in check["sub_comparisons"] if sc["result"] != "SKIP"
        ])
        print(
            f"  [PASS] {code}  {field} "
            f"({performed} comparison{'s' if performed != 1 else ''})"
        )
        return
    if result == "SKIP":
        note = check.get("note") or "no comparable source"
        print(f"  [SKIP] {code}  {field} — {note}")
        return
    # FAIL: show full detail
    print(f"  [FAIL] {code}  {field}")
    pc_value = check.get("pc_value")
    if code == "C8":
        observed = check.get("observed_phase")
        print(f"    PC:       {_fmt_value(pc_value)}")
        print(
            f"    observed: {_fmt_value(observed)}              MISMATCH"
        )
        return
    print(f"    PC:     {_fmt_value(pc_value)}")
    for sc in check["sub_comparisons"]:
        label = sc["source_label"]
        source_value = sc["source_value"]
        result = sc["result"]
        note = sc.get("note")
        if result == "MATCH":
            print(
                f"    {label}:{' ' * (7 - len(label))}{_fmt_value(source_value)}"
                f"    MATCH"
            )
        elif result == "MISMATCH":
            suffix = f" ({note})" if note else ""
            print(
                f"    {label}:{' ' * (7 - len(label))}{_fmt_value(source_value)}"
                f"    MISMATCH{suffix}"
            )
        else:
            print(
                f"    {label}:{' ' * (7 - len(label))}skipped ({note})"
            )


# ---- main --------------------------------------------------------------


def main(argv):
    parser = argparse.ArgumentParser(
        prog="check_project_config.py",
        description=(
            "Compare project_config.real.json against the slug's "
            "concept_brief, concept_packet.draft, concept_packet.review, "
            "and observed file state. Report mismatches only. "
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
        # Strip non-serializable data: entries' "data" field contains
        # parsed source JSON which may be large. Keep only presence
        # and path info for the JSON report.
        json_report = {
            "slug": report["slug"],
            "sources": {
                k: {
                    "present": v["present"],
                    "path": v["path"],
                    "parseable": v["parseable"],
                }
                for k, v in report["sources"].items()
            },
            "comparable_mode": report["comparable_mode"],
            "observed_phase": report["observed_phase"],
            "checks": report["checks"],
            "summary": report["summary"],
        }
        print(json.dumps(json_report, indent=2, sort_keys=True))
    else:
        print_human_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
