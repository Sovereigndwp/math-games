#!/usr/bin/env python3
"""
validate_schemas.py — math-games schema + fixture validator

Validates:
  1. Every schema file parses as JSON.
  2. Every schema is a valid JSON Schema Draft 2020-12.
  3. Every example fixture parses as JSON.
  4. Every example fixture validates against its corresponding schema.

Exit codes:
  0  all schemas and fixtures pass
  1  validation failure (one or more fixtures do not match their schema,
     or an example fixture has a JSON parse error)
  2  script/setup error (missing jsonschema library, missing schema file,
     schema file JSON parse error, or schema is not a valid JSON Schema)

Dependencies:
  Python 3.8+
  jsonschema >= 4.18 (required for Draft 2020-12 support)

Usage:
  python3 scripts/validate_schemas.py

To add a new schema+fixture pair, append a tuple to PAIRS below.
Package 2 is schema-only validation. Cross-file reference checks
(audit -> repair linkage, release -> audit linkage, release -> repair
eligibility) are the responsibility of Package 3 and are NOT performed
by this script.
"""

import json
import sys
from pathlib import Path

# --- dependency import ---------------------------------------------------
try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError:
    sys.stderr.write(
        "ERROR: jsonschema is not installed.\n"
        "Install it with:\n"
        "  pip install -r requirements.txt\n"
        "or:\n"
        "  pip install 'jsonschema>=4.18'\n"
    )
    sys.exit(2)

# --- explicit pair map ---------------------------------------------------
# (human_name, schema_path, fixture_path)
REPO_ROOT = Path(__file__).resolve().parent.parent

PAIRS = [
    (
        "concept_brief",
        REPO_ROOT / "schemas" / "concept_brief.schema.json",
        REPO_ROOT / "schemas" / "examples" / "concept_brief.example.json",
    ),
    (
        "build_plan",
        REPO_ROOT / "schemas" / "build_plan.schema.json",
        REPO_ROOT / "schemas" / "examples" / "build_plan.example.json",
    ),
    (
        "qa_audit",
        REPO_ROOT / "schemas" / "qa_audit.schema.json",
        REPO_ROOT / "schemas" / "examples" / "qa_audit.example.json",
    ),
    (
        "repair_record",
        REPO_ROOT / "schemas" / "repair_record.schema.json",
        REPO_ROOT / "schemas" / "examples" / "repair_record.example.json",
    ),
    (
        "release_certificate",
        REPO_ROOT / "schemas" / "release_certificate.schema.json",
        REPO_ROOT / "schemas" / "examples" / "release_certificate.example.json",
    ),
    (
        "generation_request",
        REPO_ROOT / "schemas" / "generation_request.schema.json",
        REPO_ROOT / "schemas" / "examples" / "generation_request.example.json",
    ),
    (
        "generation_manifest",
        REPO_ROOT / "schemas" / "generation_manifest.schema.json",
        REPO_ROOT / "schemas" / "examples" / "generation_manifest.example.json",
    ),
]


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


def format_validation_error(err):
    """Format a jsonschema ValidationError as multi-line human-readable output."""
    instance_path = "$"
    for part in err.absolute_path:
        if isinstance(part, int):
            instance_path += f"[{part}]"
        else:
            instance_path += f".{part}"
    rule_path = "/".join(str(p) for p in err.absolute_schema_path) or "(root)"
    lines = [
        f"      at instance path:  {instance_path}",
        f"      violated rule:     {rule_path}",
        f"      error:             {err.message}",
    ]
    return "\n".join(lines)


# --- main ----------------------------------------------------------------
def main():
    print("validate_schemas.py — math-games schema + fixture validator")
    print()

    setup_errors = 0
    validation_errors = 0
    schemas_checked = 0
    fixtures_checked = 0
    loaded_schemas = {}

    # Phase 1: schemas
    print("=== schemas ===")
    for name, schema_path, _ in PAIRS:
        schemas_checked += 1
        schema, err = load_json(schema_path)
        if err:
            print(f"  [FAIL] {schema_path.name:<42} SETUP ERROR")
            print(f"         {err}")
            setup_errors += 1
            continue
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as e:
            print(f"  [FAIL] {schema_path.name:<42} SETUP ERROR")
            print(f"         schema is not a valid Draft 2020-12 schema: {e.message}")
            setup_errors += 1
            continue
        print(f"  [ OK ] {schema_path.name:<42} parsed OK, valid Draft 2020-12")
        loaded_schemas[name] = schema

    if setup_errors > 0:
        print()
        print("=== summary ===")
        print(f"  schemas checked:     {schemas_checked}")
        print(f"  fixtures checked:    0 (aborted; cannot validate against broken schemas)")
        print(f"  setup errors:        {setup_errors}")
        print(f"  validation failures: 0")
        print(f"  exit: 2 (setup error)")
        return 2

    # Phase 2: fixtures
    print()
    print("=== fixtures vs schemas ===")
    for name, _, fixture_path in PAIRS:
        fixtures_checked += 1
        fixture, err = load_json(fixture_path)
        if err:
            print(f"  [FAIL] {name:<42} FIXTURE PARSE FAILED")
            print(f"         {err}")
            validation_errors += 1
            continue

        schema = loaded_schemas[name]
        validator = Draft202012Validator(schema)
        errors = sorted(
            validator.iter_errors(fixture),
            key=lambda e: list(e.absolute_path),
        )

        if not errors:
            print(f"  [ OK ] {name:<42} fixture validates against schema")
        else:
            print(f"  [FAIL] {name:<42} fixture FAILED validation ({len(errors)} error(s))")
            for e in errors:
                print(format_validation_error(e))
            validation_errors += 1

    print()
    print("=== summary ===")
    print(f"  schemas checked:     {schemas_checked}")
    print(f"  fixtures checked:    {fixtures_checked}")
    print(f"  setup errors:        {setup_errors}")
    print(f"  validation failures: {validation_errors}")

    if validation_errors > 0:
        print(f"  exit: 1 (validation failure)")
        return 1

    print(f"  exit: 0 (all pass)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
