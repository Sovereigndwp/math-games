#!/usr/bin/env python3
"""
build_generation_request.py - Package 17 generation_request builder

Given a slug that already has a concept_brief.real.json, produce a
validated generation_request.real.json alongside it. The script:

  1. reads the slug's concept_brief.real.json
  2. computes its SHA-256 at runtime
  3. reads the brief's own brief_id field for source_ref.id
  4. derives a deterministic request_id from slug + created_at
  5. fills other required fields from hard-coded defaults
  6. self-validates the derived request against
     generation_request.schema.json
  7. writes exactly one file and stops

Scope:
  This script writes exactly one file:
    generated/requests/<slug>/generation_request.real.json
  It never touches the brief. It never invokes the generator or any
  other script. It never mutates project_config.current_phase. It
  never writes a promotion_request. Package 18 (or later) will build
  promotion_request files.

Usage:
  python3 scripts/build_generation_request.py \\
    --slug <slug> \\
    [--created-at 2026-MM-DDTHH:MM:SSZ] \\
    [--dry-run]

Exit codes:
  0  success (file written) or successful dry-run
  1  failure (no brief, unparseable brief, missing brief_id,
     containment violation, target file already exists, derived
     request fails self-validation, write I/O error)
  2  setup error (missing jsonschema, missing/unparseable schema
     file, invalid CLI argument)

Design stance:
  Each write should be reviewable before the next write happens.
  This builder creates the generation_request and stops. The
  operator then runs generate_concept_packet_stub.py on the
  produced file as a separate, auditable step. Chained side
  effects would mask generator failures and merge two distinct
  intent points.
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

GENERATION_REQUEST_SCHEMA = (
    REPO_ROOT / "schemas" / "generation_request.schema.json"
)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ISO_Z_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
BRIEF_ID_PATTERN = re.compile(r"^cb_[0-9]{8}_[a-z0-9]{6}$")

# Hard-coded values per M3/M4/M6 from the Package 17 proposal.
SOURCE_TYPE = "concept_brief"
ARTIFACT_TYPE = "concept_packet_draft"
GENERATOR_VERSION = "concept-packet-stub-v0.2.0"
MODE = "draft"
STATUS = "pending"


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
            f"--created-at must be ISO 8601 with Z suffix "
            f"(e.g. 2026-04-11T12:00:00Z), got {value!r}"
        )
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            f"--created-at {value!r} is not a valid ISO 8601 date-time: {e}"
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


def now_iso_z():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def sha256_of_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def derive_request_id(slug, created_at):
    date_part = created_at[:10].replace("-", "")  # "20260411"
    h = hashlib.sha256(
        f"{slug}|{created_at}|generation_request".encode("utf-8")
    ).hexdigest()[:6]
    return f"gr_{date_part}_{h}"


# ---- main --------------------------------------------------------------


def main(argv):
    parser = argparse.ArgumentParser(
        prog="build_generation_request.py",
        description=(
            "Build generated/requests/<slug>/generation_request.real.json "
            "from the slug's existing concept_brief.real.json. "
            "Automatically computes the brief's SHA-256 and fills other "
            "required fields from defaults."
        ),
    )
    parser.add_argument(
        "--slug",
        type=validate_slug,
        required=True,
        help="kebab-case slug (pattern ^[a-z0-9]+(-[a-z0-9]+)*$, 2-64 chars)",
    )
    parser.add_argument(
        "--created-at",
        type=parse_iso_z,
        default=None,
        help=(
            "ISO 8601 date-time with Z suffix. Default: current UTC "
            "time at script invocation. Affects the deterministic "
            "request_id derivation."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help=(
            "Build and self-validate the derived generation_request "
            "in memory without writing any file."
        ),
    )
    args = parser.parse_args(argv[1:])

    slug = args.slug

    # --- R2/R3: load schema ---
    schema = load_schema(GENERATION_REQUEST_SCHEMA, "generation_request")

    # --- R4: brief must exist ---
    brief_path = (
        REPO_ROOT / "generated" / "requests" / slug / "concept_brief.real.json"
    )
    if not brief_path.exists():
        die_failure(
            f"no concept_brief.real.json for slug {slug}. Create one "
            f"with scripts/new_game_init.py first."
        )

    # --- R5: brief must be parseable ---
    try:
        with brief_path.open() as f:
            brief_data = json.load(f)
    except json.JSONDecodeError as e:
        die_failure(
            f"concept_brief.real.json for slug {slug} is not parseable "
            f"JSON: {e.msg}. Fix the file before re-running."
        )
    except OSError as e:
        die_failure(
            f"concept_brief.real.json for slug {slug} could not be "
            f"read: {e}"
        )

    # --- R6: brief must have a usable brief_id ---
    if not isinstance(brief_data, dict):
        die_failure(
            f"concept_brief.real.json for slug {slug} is not a JSON object."
        )
    brief_id = brief_data.get("brief_id")
    if not isinstance(brief_id, str) or not BRIEF_ID_PATTERN.match(brief_id):
        die_failure(
            f"concept_brief.real.json for slug {slug} has no usable "
            f"brief_id field (expected pattern ^cb_[0-9]{{8}}_[a-z0-9]"
            f"{{6}}$)."
        )

    # --- compute hash of the brief ---
    brief_hash = sha256_of_file(brief_path)

    # --- R7: target path containment ---
    requests_root = (REPO_ROOT / "generated" / "requests").resolve()
    target_dir = (REPO_ROOT / "generated" / "requests" / slug).resolve()
    try:
        target_dir.relative_to(requests_root)
    except ValueError:
        die_failure(
            f"target path must live under generated/requests/, got "
            f"{target_dir}"
        )
    target_path = target_dir / "generation_request.real.json"

    # --- R8: refuse to overwrite (skipped in dry-run) ---
    if not args.dry_run and target_path.exists():
        die_failure(
            f"generation_request.real.json already exists for slug "
            f"{slug}: {target_path}. This script refuses to overwrite "
            f"existing requests."
        )

    # --- compute timestamp and request_id ---
    created_at = args.created_at if args.created_at is not None else now_iso_z()
    request_id = derive_request_id(slug, created_at)

    # --- build the generation_request dict ---
    request = {
        "schema_version": "0.1.0",
        "request_id": request_id,
        "created_at": created_at,
        "source_type": SOURCE_TYPE,
        "source_ref": {
            "path": f"generated/requests/{slug}/concept_brief.real.json",
            "hash": brief_hash,
            "id": brief_id,
        },
        "artifact_type": ARTIFACT_TYPE,
        "target_path": f"generated/drafts/{slug}/",
        "generator_version": GENERATOR_VERSION,
        "mode": MODE,
        "status": STATUS,
    }

    # --- R9: self-validate BEFORE any write ---
    try:
        Draft202012Validator(schema).validate(request)
    except ValidationError as e:
        die_failure(
            f"derived generation_request does not validate against "
            f"schema: {e.message}. No write performed."
        )

    # --- report derivation ---
    print(
        "build_generation_request.py — "
        + ("dry-run" if args.dry_run else "run")
    )
    print()
    print(f"slug:                   {slug}")
    print(f"source brief:           {brief_path.relative_to(REPO_ROOT)}")
    print(f"source brief hash:      {brief_hash}")
    print(f"brief_id (from brief):  {brief_id}")
    print()
    print("derivation:")
    print(f"  schema_version:       {request['schema_version']}")
    print(f"  request_id:           {request['request_id']}")
    print(f"  created_at:           {request['created_at']}")
    print(f"  source_type:          {request['source_type']}")
    print(f"  source_ref.path:      {request['source_ref']['path']}")
    print(f"  source_ref.hash:      {request['source_ref']['hash']}")
    print(f"  source_ref.id:        {request['source_ref']['id']}")
    print(f"  artifact_type:        {request['artifact_type']}")
    print(f"  target_path:          {request['target_path']}")
    print(f"  generator_version:    {request['generator_version']}")
    print(f"  mode:                 {request['mode']}")
    print(f"  status:               {request['status']}")
    print()
    print(f"target path: {target_path.relative_to(REPO_ROOT)}")
    print("self-validation against generation_request.schema.json: PASS")

    if args.dry_run:
        print("would write: YES")
        return 0

    # --- R10: write ---
    try:
        target_path.write_text(canonical_dump(request), encoding="utf-8")
    except OSError as e:
        die_failure(f"could not write {target_path}: {e}")

    # --- report ---
    written_hash = sha256_of_file(target_path)
    print()
    print("write status: SUCCESS")
    print(f"  path:   {target_path.relative_to(REPO_ROOT)}")
    print(f"  size:   {target_path.stat().st_size} bytes")
    print(f"  sha256: {written_hash}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
