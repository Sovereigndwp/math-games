#!/usr/bin/env python3
"""
build_promotion_request.py - Package 18 promotion_request builder

Given a slug that already has both concept_packet.draft.json and
concept_packet.manifest.json under generated/drafts/<slug>/, produce
a validated promotion_request.real.json under
generated/requests/<slug>/. The script:

  1. reads the slug's concept_packet.draft.json and
     concept_packet.manifest.json
  2. computes both SHA-256 hashes at runtime from the on-disk files
  3. derives a deterministic request_id from slug + created_at
  4. fills other required fields from hard-coded defaults aligned
     with the post-Package-8 promoter
  5. self-validates the derived request against
     promotion_request.schema.json
  6. writes exactly one file and stops

Scope:
  This script writes exactly one file:
    generated/requests/<slug>/promotion_request.real.json
  It never touches the draft or manifest. It never invokes the
  promoter or any other script. It never mutates project_config
  .current_phase. It never writes a review or record artifact.

Usage:
  python3 scripts/build_promotion_request.py \\
    --slug <slug> \\
    [--created-at 2026-MM-DDTHH:MM:SSZ] \\
    [--dry-run]

Exit codes:
  0  success (file written) or successful dry-run
  1  failure (missing/unparseable draft or manifest, containment
     violation, target file already exists, derived request fails
     self-validation, write I/O error)
  2  setup error (missing jsonschema, missing/unparseable schema
     file, invalid CLI argument)

Design stance:
  Each write should be reviewable before the next write happens.
  This builder creates the promotion_request and stops. The
  operator then runs promote_draft_stub.py on the produced file
  as a separate, auditable step. Chained side effects would mask
  promoter failures and merge two distinct intent points. The
  promoter's output is where the "review_ready" gate is crossed,
  and the operator should explicitly choose when that happens.
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

PROMOTION_REQUEST_SCHEMA = (
    REPO_ROOT / "schemas" / "promotion_request.schema.json"
)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ISO_Z_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)

# Hard-coded values per Package 18 N3/N4/N6.
ARTIFACT_TYPE = "concept_packet_draft"
PROMOTER_VERSION = "draft-promoter-stub-v0.1.0"
MODE = "review"
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
            f"(e.g. 2026-04-11T13:00:00Z), got {value!r}"
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
        f"{slug}|{created_at}|promotion_request".encode("utf-8")
    ).hexdigest()[:6]
    return f"pr_{date_part}_{h}"


# ---- main --------------------------------------------------------------


def main(argv):
    parser = argparse.ArgumentParser(
        prog="build_promotion_request.py",
        description=(
            "Build generated/requests/<slug>/promotion_request.real.json "
            "from the slug's existing concept_packet.draft.json and "
            "concept_packet.manifest.json. Automatically computes both "
            "SHA-256 hashes and fills other required fields from "
            "defaults."
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
            "Build and self-validate the derived promotion_request "
            "in memory without writing any file."
        ),
    )
    args = parser.parse_args(argv[1:])

    slug = args.slug

    # --- R2/R3: load schema ---
    schema = load_schema(PROMOTION_REQUEST_SCHEMA, "promotion_request")

    # --- Compute upstream paths ---
    draft_path = (
        REPO_ROOT / "generated" / "drafts" / slug / "concept_packet.draft.json"
    )
    manifest_path = (
        REPO_ROOT / "generated" / "drafts" / slug / "concept_packet.manifest.json"
    )

    # --- R4: draft must exist ---
    # Use explicit per-file messages so the operator sees exactly
    # which file is absent. Package 18 treats "draft missing" and
    # "manifest missing" as the same broken-state class but with
    # distinct diagnostics.
    if not draft_path.exists():
        die_failure(
            f"no concept_packet.draft.json for slug {slug}. "
            f"Expected at {draft_path.relative_to(REPO_ROOT)}. "
            f"Run scripts/generate_concept_packet_stub.py on a valid "
            f"generation_request first."
        )

    # --- R5: draft must be parseable ---
    try:
        with draft_path.open() as f:
            json.load(f)
    except json.JSONDecodeError as e:
        die_failure(
            f"concept_packet.draft.json for slug {slug} is not "
            f"parseable JSON: {e.msg}. Fix the file before re-running."
        )
    except OSError as e:
        die_failure(
            f"concept_packet.draft.json for slug {slug} could not be "
            f"read: {e}"
        )

    # --- R6: manifest must exist ---
    if not manifest_path.exists():
        die_failure(
            f"no concept_packet.manifest.json for slug {slug}. "
            f"Expected at {manifest_path.relative_to(REPO_ROOT)}. "
            f"The draft exists but the manifest is missing - this is "
            f"a broken generator output state. Inspect "
            f"generated/drafts/{slug}/ and re-run the generator if "
            f"needed."
        )

    # --- R7: manifest must be parseable ---
    try:
        with manifest_path.open() as f:
            json.load(f)
    except json.JSONDecodeError as e:
        die_failure(
            f"concept_packet.manifest.json for slug {slug} is not "
            f"parseable JSON: {e.msg}. Fix the file before re-running."
        )
    except OSError as e:
        die_failure(
            f"concept_packet.manifest.json for slug {slug} could not "
            f"be read: {e}"
        )

    # --- compute both hashes ---
    draft_hash = sha256_of_file(draft_path)
    manifest_hash = sha256_of_file(manifest_path)

    # --- R8: target path containment ---
    requests_root = (REPO_ROOT / "generated" / "requests").resolve()
    target_dir = (REPO_ROOT / "generated" / "requests" / slug).resolve()
    try:
        target_dir.relative_to(requests_root)
    except ValueError:
        die_failure(
            f"target path must live under generated/requests/, got "
            f"{target_dir}"
        )
    target_path = target_dir / "promotion_request.real.json"

    # --- R9: refuse to overwrite (skipped in dry-run) ---
    if not args.dry_run and target_path.exists():
        die_failure(
            f"promotion_request.real.json already exists for slug "
            f"{slug}: {target_path}. This script refuses to overwrite "
            f"existing requests."
        )

    # --- compute timestamp and request_id ---
    created_at = args.created_at if args.created_at is not None else now_iso_z()
    request_id = derive_request_id(slug, created_at)

    # --- build the promotion_request dict ---
    request = {
        "schema_version": "0.1.0",
        "request_id": request_id,
        "created_at": created_at,
        "artifact_type": ARTIFACT_TYPE,
        "source_draft_ref": {
            "path": f"generated/drafts/{slug}/concept_packet.draft.json",
            "hash": draft_hash,
        },
        "source_manifest_ref": {
            "path": f"generated/drafts/{slug}/concept_packet.manifest.json",
            "hash": manifest_hash,
        },
        "target_path": f"generated/review/{slug}/",
        "promoter_version": PROMOTER_VERSION,
        "mode": MODE,
        "status": STATUS,
    }

    # --- R10: self-validate BEFORE any write ---
    try:
        Draft202012Validator(schema).validate(request)
    except ValidationError as e:
        die_failure(
            f"derived promotion_request does not validate against "
            f"schema: {e.message}. No write performed."
        )

    # --- report derivation ---
    print(
        "build_promotion_request.py — "
        + ("dry-run" if args.dry_run else "run")
    )
    print()
    print(f"slug:                       {slug}")
    print(f"source draft:               {draft_path.relative_to(REPO_ROOT)}")
    print(f"source draft hash:          {draft_hash}")
    print(f"source manifest:            {manifest_path.relative_to(REPO_ROOT)}")
    print(f"source manifest hash:       {manifest_hash}")
    print()
    print("derivation:")
    print(f"  schema_version:           {request['schema_version']}")
    print(f"  request_id:               {request['request_id']}")
    print(f"  created_at:               {request['created_at']}")
    print(f"  artifact_type:            {request['artifact_type']}")
    print(
        f"  source_draft_ref.path:    {request['source_draft_ref']['path']}"
    )
    print(
        f"  source_draft_ref.hash:    {request['source_draft_ref']['hash']}"
    )
    print(
        f"  source_manifest_ref.path: {request['source_manifest_ref']['path']}"
    )
    print(
        f"  source_manifest_ref.hash: {request['source_manifest_ref']['hash']}"
    )
    print(f"  target_path:              {request['target_path']}")
    print(f"  promoter_version:         {request['promoter_version']}")
    print(f"  mode:                     {request['mode']}")
    print(f"  status:                   {request['status']}")
    print()
    print(f"target path: {target_path.relative_to(REPO_ROOT)}")
    print("self-validation against promotion_request.schema.json: PASS")

    if args.dry_run:
        print("would write: YES")
        return 0

    # --- R11: write ---
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
