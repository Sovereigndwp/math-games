#!/usr/bin/env python3
"""
promote_draft_stub.py — Package 6 draft-to-review promotion stub

Deterministic, no-AI promotion script that reads a promotion_request and
writes:

  1. <target>/concept_packet.review.json
  2. <target>/promotion_record.json

It verifies:
  - the promotion_request validates against schema
  - the source draft and source generation manifest both exist
  - both source hashes match the actual files
  - source paths live under generated/drafts/
  - target path lives under generated/review/
  - target files do not already exist (fail on existing; no overwrite)

Usage:
  python3 scripts/promote_draft_stub.py [request.json]

If no request path is given, defaults to:
  generated/requests/example-game/promotion_request.runtime.json

Exit codes:
  0  promotion succeeded, record written and self-validated
  1  promotion failure (bad input, schema mismatch, hash mismatch,
     containment violation, target already exists, record
     self-validation failure)
  2  setup error (missing jsonschema, missing required schema file,
     missing request file, missing source file, unparseable JSON)

Determinism:
  promoted_at is hard-coded to THE_EXAMPLE_PROMOTED_AT so repeated runs
  produce byte-identical output. Edit that constant to refresh the
  committed snapshot. Note: re-running after a successful run will
  always fail with exit 1 because the fail-on-existing-target rule
  protects the committed snapshot; to refresh, delete the target files
  first.
"""

import hashlib
import json
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

DEFAULT_REQUEST = (
    REPO_ROOT
    / "generated"
    / "requests"
    / "example-game"
    / "promotion_request.runtime.json"
)

PROMOTION_REQUEST_SCHEMA = REPO_ROOT / "schemas" / "promotion_request.schema.json"
PROMOTION_RECORD_SCHEMA = REPO_ROOT / "schemas" / "promotion_record.schema.json"

PROMOTER_NAME = "draft-promoter-stub"
PROMOTER_VERSION = "draft-promoter-stub-v0.1.0"

# Frozen for deterministic fixture output. Edit this value (and re-run after
# deleting the previous target files) to refresh the committed snapshot.
THE_EXAMPLE_PROMOTED_AT = "2026-04-10T18:30:00Z"


def die_setup(msg):
    sys.stderr.write(f"SETUP ERROR: {msg}\n")
    sys.exit(2)


def die_failure(msg):
    sys.stderr.write(f"FAILURE: {msg}\n")
    sys.exit(1)


def load_json(path, context):
    if not path.exists():
        die_setup(f"missing {context} file: {path}")
    try:
        with path.open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        die_setup(f"{context} JSON parse error at {path}: {e.msg}")


def sha256_of_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def canonical_dump(obj):
    # Deterministic JSON: sorted keys, 2-space indent, trailing newline.
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def derive_record_id_from_request_id(request_id):
    # pr_YYYYMMDD_xxxxxx -> pm_YYYYMMDD_xxxxxx
    if not request_id.startswith("pr_"):
        die_failure(f"request_id does not start with pr_: {request_id}")
    return "pm_" + request_id[3:]


def const_of(schema, field):
    return schema.get("properties", {}).get(field, {}).get("const")


def ensure_under(path_obj, root_obj, label):
    try:
        path_obj.relative_to(root_obj)
    except ValueError:
        die_failure(f"{label} must live under {root_obj}, got {path_obj}")


def main(argv):
    # --- load schemas ---
    for p in [PROMOTION_REQUEST_SCHEMA, PROMOTION_RECORD_SCHEMA]:
        if not p.exists():
            die_setup(f"required schema missing: {p}")

    request_schema = load_json(PROMOTION_REQUEST_SCHEMA, "promotion_request schema")
    record_schema = load_json(PROMOTION_RECORD_SCHEMA, "promotion_record schema")

    # --- load request ---
    if len(argv) > 1:
        request_path = Path(argv[1]).resolve()
    else:
        request_path = DEFAULT_REQUEST

    request = load_json(request_path, "promotion_request")

    try:
        Draft202012Validator(request_schema).validate(request)
    except ValidationError as e:
        die_failure(f"promotion_request does not validate: {e.message}")

    if request["artifact_type"] != "concept_packet_draft":
        die_failure(
            f"Package 6 stub only supports artifact_type=concept_packet_draft, "
            f"got {request['artifact_type']}"
        )
    if request["mode"] != "review":
        die_failure(
            f"Package 6 stub only supports mode=review, got {request['mode']}"
        )

    # --- containment roots ---
    drafts_root = (REPO_ROOT / "generated" / "drafts").resolve()
    review_root = (REPO_ROOT / "generated" / "review").resolve()

    source_draft_path = (REPO_ROOT / request["source_draft_ref"]["path"]).resolve()
    source_manifest_path = (
        REPO_ROOT / request["source_manifest_ref"]["path"]
    ).resolve()
    target_dir = (REPO_ROOT / request["target_path"]).resolve()

    ensure_under(source_draft_path, drafts_root, "source_draft_ref.path")
    ensure_under(source_manifest_path, drafts_root, "source_manifest_ref.path")
    ensure_under(target_dir, review_root, "target_path")

    if not source_draft_path.exists():
        die_failure(f"source draft does not exist: {source_draft_path}")
    if not source_manifest_path.exists():
        die_failure(f"source manifest does not exist: {source_manifest_path}")

    # --- hash verification ---
    actual_draft_hash = sha256_of_file(source_draft_path)
    actual_manifest_hash = sha256_of_file(source_manifest_path)

    if actual_draft_hash != request["source_draft_ref"]["hash"]:
        die_failure(
            f"draft hash mismatch: request declares "
            f"{request['source_draft_ref']['hash']} "
            f"but file is {actual_draft_hash}"
        )
    if actual_manifest_hash != request["source_manifest_ref"]["hash"]:
        die_failure(
            f"manifest hash mismatch: request declares "
            f"{request['source_manifest_ref']['hash']} "
            f"but file is {actual_manifest_hash}"
        )

    # --- target dir and fail-on-existing check ---
    target_dir.mkdir(parents=True, exist_ok=True)

    review_path = target_dir / "concept_packet.review.json"
    record_path = target_dir / "promotion_record.json"

    if review_path.exists():
        die_failure(f"target already exists: {review_path}")
    if record_path.exists():
        die_failure(f"target already exists: {record_path}")

    # --- build review doc ---
    draft = load_json(source_draft_path, "source draft")
    record_id = derive_record_id_from_request_id(request["request_id"])

    review_doc = {
        **draft,
        "promotion": {
            "request_id": request["request_id"],
            "record_id": record_id,
            "promoted_at": THE_EXAMPLE_PROMOTED_AT,
            "promoter_name": PROMOTER_NAME,
            "promoter_version": PROMOTER_VERSION,
        },
        "status": "review_ready",
    }

    review_path.write_text(canonical_dump(review_doc), encoding="utf-8")
    review_hash = sha256_of_file(review_path)

    # --- build record ---
    record = {
        "schema_version": "0.1.0",
        "record_id": record_id,
        "request_id": request["request_id"],
        "promoted_at": THE_EXAMPLE_PROMOTED_AT,
        "promoter_name": PROMOTER_NAME,
        "promoter_version": PROMOTER_VERSION,
        "source_artifacts": [
            {
                "path": str(source_draft_path.relative_to(REPO_ROOT)),
                "hash": actual_draft_hash,
                "kind": "concept_packet_draft",
            },
            {
                "path": str(source_manifest_path.relative_to(REPO_ROOT)),
                "hash": actual_manifest_hash,
                "kind": "generation_manifest",
            },
        ],
        "output_artifacts": [
            {
                "path": str(review_path.relative_to(REPO_ROOT)),
                "hash": review_hash,
                "kind": "concept_packet_review",
            }
        ],
        "schema_versions_used": {
            "promotion_request_schema": const_of(request_schema, "schema_version")
            or "unknown",
            "promotion_record_schema": const_of(record_schema, "schema_version")
            or "unknown",
            "generation_manifest_schema": "0.1.0",
        },
        "status": "success",
        "notes": None,
    }

    # Self-validate record before writing.
    try:
        Draft202012Validator(record_schema).validate(record)
    except ValidationError as e:
        die_failure(
            f"generated promotion_record does not validate against schema: "
            f"{e.message}"
        )

    record_path.write_text(canonical_dump(record), encoding="utf-8")

    # --- report ---
    print("promote_draft_stub.py — success")
    print(f"  request:    {request_path.relative_to(REPO_ROOT)}")
    print(f"  source:     {source_draft_path.relative_to(REPO_ROOT)}")
    print(f"  manifest:   {source_manifest_path.relative_to(REPO_ROOT)}")
    print(f"  review:     {review_path.relative_to(REPO_ROOT)}")
    print(f"  record:     {record_path.relative_to(REPO_ROOT)}")
    print(f"  record_id:  {record_id}")
    print("  status:     success")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
