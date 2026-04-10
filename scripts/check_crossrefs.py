#!/usr/bin/env python3
"""
check_crossrefs.py — math-games cross-reference checker

Verifies structural links ACROSS artifact files:
  - audits point to real findings (internal to each qa_audit)
  - repairs point to real audits and findings
  - release certificates only cite eligible repairs and eligible audits

This is NOT schema validation. For schema validation, use validate_schemas.py
(Package 2). This script assumes its inputs are already schema-valid and
checks only cross-file linkage.

Checks implemented:
  Group A — qa_audit internal consistency
    XR-01  recommended_fixes[*].target_finding_ids[*] exist as finding_ids
    XR-02  findings[*].fix_refs[*] exist as fix_ids
  Group B — qa_audit resolved_by references -> repair_record
    XR-03  findings[*].resolved_by_repair_ids[*] exist as repair_ids
    XR-04  recommended_fixes[*].resolved_by_repair_id exists as repair_id
  Group C — repair_record -> qa_audit
    XR-05  source_audit_ref.audit_id exists as audit_id
    XR-06  target_finding_ids[*] exist in the referenced audit
    XR-07  target_fix_ids[*] exist in the referenced audit
  Group D — release_certificate -> qa_audit
    XR-08  evidence.*.audit_refs[*] resolve to known audits (by path)
    XR-09  referenced audits have audit_applies_to_release_evidence = true
  Group E — release_certificate -> repair_record
    XR-10  repair_history[*] resolves to known repair_records (by path)
    XR-11  referenced repairs have release_evidence_eligible = true
    XR-12  referenced repairs have outcome.status = verified_fix

Exit codes:
  0  all cross-reference checks pass
  1  one or more cross-reference failures
  2  script/setup error (missing fixture file, JSON parse error, missing
     required primary ID field)

Dependencies:
  Python 3.8+
  (stdlib only — no external packages)

Usage:
  python3 scripts/check_crossrefs.py

This script operates on an in-memory collection built from the fixture
registry below. To add a new artifact, append to FIXTURE_REGISTRY.

Resolution strategies:
  - Direct ID lookup: most cross-references carry an explicit ID field
    (audit_id, repair_id, finding_id, fix_id).
  - Path-basename heuristic: release_certificate.audit_refs and
    release_certificate.repair_history use artifactRef which carries
    only path and hash, not an explicit ID. This script extracts the
    last path segment without .json extension and looks it up as the
    target ID. This is a documented convention. A future schema bump
    could add an explicit id field to artifactRef to eliminate the
    heuristic.

What this script does NOT check:
  - File existence of paths inside artifacts (fixture paths are
    placeholders; real operational path-existence checks are deferred).
  - SHA-256 hash matching (fixtures use placeholder hashes; hash
    verification is deferred to a later package).
  - Schema validation (use validate_schemas.py).
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# (type_name, fixture_path)
FIXTURE_REGISTRY = [
    ("concept_brief",       REPO_ROOT / "schemas" / "examples" / "concept_brief.example.json"),
    ("build_plan",          REPO_ROOT / "schemas" / "examples" / "build_plan.example.json"),
    ("qa_audit",            REPO_ROOT / "schemas" / "examples" / "qa_audit.example.json"),
    ("repair_record",       REPO_ROOT / "schemas" / "examples" / "repair_record.example.json"),
    ("release_certificate", REPO_ROOT / "schemas" / "examples" / "release_certificate.example.json"),
]

PRIMARY_ID_FIELD = {
    "concept_brief":       "brief_id",
    "build_plan":          "plan_id",
    "qa_audit":            "audit_id",
    "repair_record":       "repair_id",
    "release_certificate": "certificate_id",
}


# --- helpers -------------------------------------------------------------

def load_json(path):
    """Load a JSON file. Returns (data, error_msg). Exactly one will be None."""
    if not path.exists():
        return None, f"file does not exist: {path}"
    try:
        with path.open() as f:
            return json.load(f), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error at line {e.lineno} col {e.colno}: {e.msg}"
    except OSError as e:
        return None, f"file read error: {e}"


def load_collection():
    """
    Load all registered fixtures into a nested dict keyed by type and
    primary ID. Returns (collection, setup_errors). collection is:
        {type_name: {primary_id: fixture_data}}
    """
    collection = {t: {} for t, _ in FIXTURE_REGISTRY}
    setup_errors = []

    for type_name, path in FIXTURE_REGISTRY:
        data, err = load_json(path)
        if err:
            setup_errors.append(f"{type_name} at {path}: {err}")
            continue
        id_field = PRIMARY_ID_FIELD[type_name]
        if id_field not in data:
            setup_errors.append(
                f"{type_name} at {path}: missing required primary ID field '{id_field}'"
            )
            continue
        primary_id = data[id_field]
        collection[type_name][primary_id] = data

    return collection, setup_errors


def all_findings_in_audit(audit):
    """Return concatenated list of findings across all 5 findings arrays."""
    return (
        audit.get('template_findings', [])
        + audit.get('mission_findings', [])
        + audit.get('cross_cutting_findings', [])
        + audit.get('clarity_findings', [])
        + audit.get('anxiety_findings', [])
    )


def path_basename_id(path_str):
    """Extract the last path segment without .json extension."""
    return Path(path_str).stem


# --- individual checks ---------------------------------------------------
# Each check returns a list of error message strings. Empty list = PASS.

def xr01_audit_fix_targets_existing_findings(collection):
    """XR-01: recommended_fixes[*].target_finding_ids[*] must exist as finding_ids."""
    errors = []
    for audit_id, audit in collection['qa_audit'].items():
        finding_ids = {f['finding_id'] for f in all_findings_in_audit(audit)}
        for fix in audit.get('recommended_fixes', []):
            for tfid in fix.get('target_finding_ids', []):
                if tfid not in finding_ids:
                    errors.append(
                        f"audit '{audit_id}': fix '{fix['fix_id']}' targets "
                        f"finding '{tfid}' which does not exist in this audit"
                    )
    return errors


def xr02_finding_fix_refs_exist_in_fixes(collection):
    """XR-02: findings[*].fix_refs[*] must exist as fix_ids."""
    errors = []
    for audit_id, audit in collection['qa_audit'].items():
        fix_ids = {fx['fix_id'] for fx in audit.get('recommended_fixes', [])}
        for f in all_findings_in_audit(audit):
            for fref in f.get('fix_refs', []):
                if fref not in fix_ids:
                    errors.append(
                        f"audit '{audit_id}': finding '{f['finding_id']}' "
                        f"references fix '{fref}' which does not exist in "
                        f"recommended_fixes"
                    )
    return errors


def xr03_finding_resolved_by_repair_exists(collection):
    """XR-03: findings[*].resolved_by_repair_ids[*] must match a repair_id."""
    errors = []
    known_repair_ids = set(collection['repair_record'].keys())
    for audit_id, audit in collection['qa_audit'].items():
        for f in all_findings_in_audit(audit):
            for rid in f.get('resolved_by_repair_ids', []):
                if rid not in known_repair_ids:
                    errors.append(
                        f"audit '{audit_id}': finding '{f['finding_id']}' "
                        f"claims resolved_by_repair_ids contains '{rid}' "
                        f"which is not a known repair_record"
                    )
    return errors


def xr04_fix_resolved_by_repair_exists(collection):
    """XR-04: recommended_fixes[*].resolved_by_repair_id must match a repair_id."""
    errors = []
    known_repair_ids = set(collection['repair_record'].keys())
    for audit_id, audit in collection['qa_audit'].items():
        for fix in audit.get('recommended_fixes', []):
            rid = fix.get('resolved_by_repair_id')
            if rid is None:
                continue
            if rid not in known_repair_ids:
                errors.append(
                    f"audit '{audit_id}': fix '{fix['fix_id']}' "
                    f"claims resolved_by_repair_id='{rid}' "
                    f"which is not a known repair_record"
                )
    return errors


def xr05_repair_source_audit_exists(collection):
    """XR-05: repair_record.source_audit_ref.audit_id must match an audit_id."""
    errors = []
    known_audit_ids = set(collection['qa_audit'].keys())
    for repair_id, repair in collection['repair_record'].items():
        src = repair.get('source_audit_ref', {})
        aid = src.get('audit_id')
        if aid not in known_audit_ids:
            errors.append(
                f"repair '{repair_id}': source_audit_ref.audit_id='{aid}' "
                f"is not a known qa_audit"
            )
    return errors


def xr06_repair_finding_ids_exist_in_source_audit(collection):
    """XR-06: repair.target_finding_ids[*] must exist in the source audit."""
    errors = []
    for repair_id, repair in collection['repair_record'].items():
        src_aid = repair.get('source_audit_ref', {}).get('audit_id')
        audit = collection['qa_audit'].get(src_aid)
        if audit is None:
            # XR-05 will have already reported this; skip to avoid double error
            continue
        audit_finding_ids = {f['finding_id'] for f in all_findings_in_audit(audit)}
        for tfid in repair.get('target_finding_ids', []):
            if tfid not in audit_finding_ids:
                errors.append(
                    f"repair '{repair_id}': target_finding_ids contains '{tfid}' "
                    f"which does not exist in referenced audit '{src_aid}'"
                )
    return errors


def xr07_repair_fix_ids_exist_in_source_audit(collection):
    """XR-07: repair.target_fix_ids[*] must exist in the source audit."""
    errors = []
    for repair_id, repair in collection['repair_record'].items():
        src_aid = repair.get('source_audit_ref', {}).get('audit_id')
        audit = collection['qa_audit'].get(src_aid)
        if audit is None:
            continue
        audit_fix_ids = {fx['fix_id'] for fx in audit.get('recommended_fixes', [])}
        for tfxid in repair.get('target_fix_ids', []):
            if tfxid not in audit_fix_ids:
                errors.append(
                    f"repair '{repair_id}': target_fix_ids contains '{tfxid}' "
                    f"which does not exist in referenced audit '{src_aid}'"
                )
    return errors


def _release_audit_refs(cert):
    """Collect all audit_refs from a release_certificate's 5 evidence domains."""
    refs = []
    evidence = cert.get('evidence', {})
    for domain in ('build_standards', 'player_clarity', 'math_qa'):
        dom = evidence.get(domain, {})
        for ref in dom.get('audit_refs', []):
            refs.append((domain, ref))
    return refs


def xr08_release_audit_refs_resolve(collection):
    """XR-08: release.evidence.*.audit_refs[*] must resolve to known audits."""
    errors = []
    known_audit_ids = set(collection['qa_audit'].keys())
    for cert_id, cert in collection['release_certificate'].items():
        for domain, ref in _release_audit_refs(cert):
            inferred_id = path_basename_id(ref.get('path', ''))
            if inferred_id not in known_audit_ids:
                errors.append(
                    f"certificate '{cert_id}': evidence.{domain}.audit_refs "
                    f"path '{ref.get('path')}' resolves (by path-basename "
                    f"heuristic) to '{inferred_id}' which is not a known qa_audit"
                )
    return errors


def xr09_release_audits_release_evidence_eligible(collection):
    """XR-09: referenced audits must have audit_applies_to_release_evidence = true."""
    errors = []
    for cert_id, cert in collection['release_certificate'].items():
        for domain, ref in _release_audit_refs(cert):
            inferred_id = path_basename_id(ref.get('path', ''))
            audit = collection['qa_audit'].get(inferred_id)
            if audit is None:
                continue  # XR-08 already reported
            if not audit.get('audit_applies_to_release_evidence', False):
                errors.append(
                    f"certificate '{cert_id}': evidence.{domain} cites audit "
                    f"'{inferred_id}' which has "
                    f"audit_applies_to_release_evidence=false"
                )
    return errors


def xr10_release_repair_history_resolves(collection):
    """XR-10: release.repair_history[*] must resolve to known repair_records."""
    errors = []
    known_repair_ids = set(collection['repair_record'].keys())
    for cert_id, cert in collection['release_certificate'].items():
        for ref in cert.get('repair_history', []):
            inferred_id = path_basename_id(ref.get('path', ''))
            if inferred_id not in known_repair_ids:
                errors.append(
                    f"certificate '{cert_id}': repair_history path "
                    f"'{ref.get('path')}' resolves (by path-basename heuristic) "
                    f"to '{inferred_id}' which is not a known repair_record"
                )
    return errors


def xr11_release_repairs_release_evidence_eligible(collection):
    """XR-11: referenced repairs must have release_evidence_eligible = true."""
    errors = []
    for cert_id, cert in collection['release_certificate'].items():
        for ref in cert.get('repair_history', []):
            inferred_id = path_basename_id(ref.get('path', ''))
            repair = collection['repair_record'].get(inferred_id)
            if repair is None:
                continue  # XR-10 already reported
            if not repair.get('release_evidence_eligible', False):
                errors.append(
                    f"certificate '{cert_id}': repair_history cites repair "
                    f"'{inferred_id}' which has release_evidence_eligible=false"
                )
    return errors


def xr12_release_repairs_verified_fix_status(collection):
    """XR-12: referenced repairs must have outcome.status = verified_fix."""
    errors = []
    for cert_id, cert in collection['release_certificate'].items():
        for ref in cert.get('repair_history', []):
            inferred_id = path_basename_id(ref.get('path', ''))
            repair = collection['repair_record'].get(inferred_id)
            if repair is None:
                continue  # XR-10 already reported
            status = repair.get('outcome', {}).get('status')
            if status != 'verified_fix':
                errors.append(
                    f"certificate '{cert_id}': repair_history cites repair "
                    f"'{inferred_id}' whose outcome.status='{status}' "
                    f"(expected 'verified_fix')"
                )
    return errors


# --- check registry ------------------------------------------------------

CHECKS = [
    ("Group A: qa_audit internal consistency", [
        ("XR-01", "audit fix.target_finding_ids -> existing findings", xr01_audit_fix_targets_existing_findings),
        ("XR-02", "audit finding.fix_refs -> existing fixes", xr02_finding_fix_refs_exist_in_fixes),
    ]),
    ("Group B: qa_audit resolved_by -> repair_record", [
        ("XR-03", "finding.resolved_by_repair_ids -> known repair_records", xr03_finding_resolved_by_repair_exists),
        ("XR-04", "fix.resolved_by_repair_id -> known repair_record", xr04_fix_resolved_by_repair_exists),
    ]),
    ("Group C: repair_record -> qa_audit", [
        ("XR-05", "repair.source_audit_ref.audit_id -> known audit", xr05_repair_source_audit_exists),
        ("XR-06", "repair.target_finding_ids -> findings in source audit", xr06_repair_finding_ids_exist_in_source_audit),
        ("XR-07", "repair.target_fix_ids -> fixes in source audit", xr07_repair_fix_ids_exist_in_source_audit),
    ]),
    ("Group D: release_certificate -> qa_audit", [
        ("XR-08", "release.evidence.*.audit_refs -> known audits (by path)", xr08_release_audit_refs_resolve),
        ("XR-09", "referenced audits have audit_applies_to_release_evidence=true", xr09_release_audits_release_evidence_eligible),
    ]),
    ("Group E: release_certificate -> repair_record", [
        ("XR-10", "release.repair_history -> known repair_records (by path)", xr10_release_repair_history_resolves),
        ("XR-11", "referenced repairs have release_evidence_eligible=true", xr11_release_repairs_release_evidence_eligible),
        ("XR-12", "referenced repairs have outcome.status=verified_fix", xr12_release_repairs_verified_fix_status),
    ]),
]


# --- main ----------------------------------------------------------------

def main():
    print("check_crossrefs.py — math-games cross-reference checker")
    print("(resolves release_certificate -> audit/repair references by")
    print(" path-basename heuristic; see script header for details)")
    print()

    collection, setup_errors = load_collection()

    if setup_errors:
        print("=== setup errors ===")
        for e in setup_errors:
            print(f"  [FAIL] {e}")
        print()
        print("=== summary ===")
        print(f"  setup errors: {len(setup_errors)}")
        print(f"  exit: 2 (setup error)")
        return 2

    print("=== loaded artifacts ===")
    for type_name, _ in FIXTURE_REGISTRY:
        artifacts = collection[type_name]
        ids = ", ".join(sorted(artifacts.keys())) if artifacts else "(none)"
        print(f"  {type_name+':':<22} {len(artifacts):>2}  ({ids})")
    print()

    total = 0
    failed = 0

    for group_name, checks in CHECKS:
        print(f"=== {group_name} ===")
        for check_id, desc, fn in checks:
            total += 1
            errors = fn(collection)
            if not errors:
                print(f"  [ OK ] {check_id}  {desc}")
            else:
                failed += 1
                print(f"  [FAIL] {check_id}  {desc}  ({len(errors)} error(s))")
                for e in errors:
                    print(f"         {e}")
        print()

    print("=== summary ===")
    print(f"  total checks:  {total}")
    print(f"  passed:        {total - failed}")
    print(f"  failed:        {failed}")
    if failed > 0:
        print(f"  exit: 1 (cross-reference failure)")
        return 1
    print(f"  exit: 0 (all pass)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
