#!/usr/bin/env python3
"""
generate_concept_packet_stub.py — Package 5 artifact generator stub

Deterministic, no-AI generator that reads a generation_request pointing at
a concept_brief and writes:

  1. <target>/concept_packet.draft.json
  2. <target>/concept_packet.manifest.json

The draft is a pure structural transform of the brief. No LLM calls, no
network, no promotion. The draft is explicitly NOT an authoritative concept
packet — it is a draft with status='draft_generated' and is only ever
written under generated/drafts/.

Usage:
  python3 scripts/generate_concept_packet_stub.py [request.json]

If no request path is given, defaults to:
  schemas/examples/generation_request.example.json

Exit codes:
  0  generation succeeded, manifest written and self-validated
  1  generation failure (bad input, schema mismatch, hash mismatch,
     containment violation, manifest self-validation failure)
  2  setup error (missing jsonschema, missing required schema file,
     missing request file, missing source brief file, unparseable JSON)

Determinism:
  generated_at is hard-coded to THE_EXAMPLE_GENERATED_AT so repeated runs
  produce byte-identical output. Edit that constant to refresh the
  committed snapshot.
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

DEFAULT_REQUEST = REPO_ROOT / "schemas" / "examples" / "generation_request.example.json"

GENERATION_REQUEST_SCHEMA = REPO_ROOT / "schemas" / "generation_request.schema.json"
GENERATION_MANIFEST_SCHEMA = REPO_ROOT / "schemas" / "generation_manifest.schema.json"
CONCEPT_BRIEF_SCHEMA = REPO_ROOT / "schemas" / "concept_brief.schema.json"
CONCEPT_PACKET_SCHEMA = REPO_ROOT / "schemas" / "concept_packet.schema.json"

GENERATOR_NAME = "concept-packet-stub"
GENERATOR_VERSION = "concept-packet-stub-v0.2.0"

# Package 8: manifest.generated_at is derived from the generation_request's
# own created_at field. This is deterministic by construction (same request,
# same output, always) and honest relative to its inputs by construction
# (the timestamp literally IS the request author's stated creation time).
# No global frozen constant is needed.


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


def derive_manifest_id_from_request_id(request_id):
    # gr_YYYYMMDD_xxxxxx -> gm_YYYYMMDD_xxxxxx
    if not request_id.startswith("gr_"):
        die_failure(f"request_id does not start with gr_: {request_id}")
    return "gm_" + request_id[3:]


def build_draft(brief, request, manifest_id):
    # Pure structural transform. No interpretation, no enrichment.
    # Package 7 v0.2.0: carry through constraints, misconception_targets,
    # success_condition, interaction_type_candidate, family_candidate, and
    # target_skill.ccss_candidate from the brief. Adds schema_version for
    # validation against concept_packet.schema.json.
    #
    # Package 8: author_notes is intentionally NOT carried through. It is an
    # intake-phase field on concept_brief (free-form author intent notes)
    # and has no place in the downstream packet. Design intent reaches the
    # packet through constraints, not through author_notes. See the
    # author_notes description in concept_brief.schema.json for the formal
    # statement of this rule.
    return {
        "schema_version": "0.1.0",
        "slug": brief["proposed_slug"],
        "title": brief["title"],
        "source_brief_id": brief["brief_id"],
        "generated_from": {
            "request_id": request["request_id"],
            "manifest_id": manifest_id,
            "generator_name": GENERATOR_NAME,
            "generator_version": GENERATOR_VERSION,
        },
        "concept_summary": brief["concept_summary"],
        "core_mechanic": {
            "player_action": brief["core_mechanic"]["player_action"],
            "feedback_loop": brief["core_mechanic"]["feedback_loop"],
        },
        "target_learners": {
            "grade_band_candidate": brief["target_learners"]["grade_band_candidate"],
            "prerequisites_candidate": brief["target_learners"].get(
                "prerequisites_candidate", []
            ),
        },
        "math_domain": brief["math_domain"],
        "target_skill": {
            "description": brief["target_skill"]["description"],
            "ccss_candidate": brief["target_skill"].get("ccss_candidate", []),
        },
        "interaction_type_candidate": brief.get(
            "interaction_type_candidate", "unresolved"
        ),
        "family_candidate": brief.get("family_candidate"),
        "misconception_targets": brief.get("misconception_targets", []),
        "success_condition": brief["success_condition"],
        "constraints": brief.get("constraints", []),
        "status": "draft_generated",
    }


def const_of(schema, field):
    return (
        schema.get("properties", {})
        .get(field, {})
        .get("const")
    )


def main(argv):
    # --- load schemas ---
    for p in [
        GENERATION_REQUEST_SCHEMA,
        GENERATION_MANIFEST_SCHEMA,
        CONCEPT_BRIEF_SCHEMA,
        CONCEPT_PACKET_SCHEMA,
    ]:
        if not p.exists():
            die_setup(f"required schema missing: {p}")
    req_schema = load_json(GENERATION_REQUEST_SCHEMA, "generation_request schema")
    mf_schema = load_json(GENERATION_MANIFEST_SCHEMA, "generation_manifest schema")
    brief_schema = load_json(CONCEPT_BRIEF_SCHEMA, "concept_brief schema")
    packet_schema = load_json(CONCEPT_PACKET_SCHEMA, "concept_packet schema")

    # --- load request ---
    if len(argv) > 1:
        request_path = Path(argv[1]).resolve()
    else:
        request_path = DEFAULT_REQUEST
    request = load_json(request_path, "generation_request")

    try:
        Draft202012Validator(req_schema).validate(request)
    except ValidationError as e:
        die_failure(f"request does not validate: {e.message}")

    if request["source_type"] != "concept_brief":
        die_failure(
            f"Package 5 stub only supports source_type=concept_brief, "
            f"got {request['source_type']}"
        )
    if request["artifact_type"] != "concept_packet_draft":
        die_failure(
            f"Package 5 stub only supports artifact_type=concept_packet_draft, "
            f"got {request['artifact_type']}"
        )

    # --- load and validate source brief ---
    brief_path = (REPO_ROOT / request["source_ref"]["path"]).resolve()
    brief = load_json(brief_path, "concept_brief source")
    try:
        Draft202012Validator(brief_schema).validate(brief)
    except ValidationError as e:
        die_failure(f"source concept_brief does not validate: {e.message}")

    actual_brief_hash = sha256_of_file(brief_path)
    declared_brief_hash = request["source_ref"]["hash"]
    if actual_brief_hash != declared_brief_hash:
        die_failure(
            f"source hash mismatch: request declares {declared_brief_hash} "
            f"but file is {actual_brief_hash}"
        )

    # --- compute and containment-check target paths ---
    target_dir = (REPO_ROOT / request["target_path"]).resolve()
    generated_drafts_root = (REPO_ROOT / "generated" / "drafts").resolve()
    try:
        target_dir.relative_to(generated_drafts_root)
    except ValueError:
        die_failure(
            f"target_path must live under generated/drafts/, got {target_dir}"
        )
    target_dir.mkdir(parents=True, exist_ok=True)

    draft_path = target_dir / "concept_packet.draft.json"
    manifest_path = target_dir / "concept_packet.manifest.json"

    # --- build draft ---
    manifest_id = derive_manifest_id_from_request_id(request["request_id"])
    draft = build_draft(brief, request, manifest_id)

    # Self-validate draft against concept_packet.schema.json before writing.
    try:
        Draft202012Validator(packet_schema).validate(draft)
    except ValidationError as e:
        die_failure(
            f"generated draft does not validate against concept_packet schema: "
            f"{e.message}"
        )

    draft_path.write_text(canonical_dump(draft), encoding="utf-8")
    draft_hash = sha256_of_file(draft_path)

    # --- build manifest ---
    manifest = {
        "schema_version": "0.1.0",
        "manifest_id": manifest_id,
        "request_id": request["request_id"],
        "generated_at": request["created_at"],
        "generator_name": GENERATOR_NAME,
        "generator_version": GENERATOR_VERSION,
        "source_artifacts": [
            {
                "path": request["source_ref"]["path"],
                "hash": actual_brief_hash,
                "kind": "concept_brief",
            }
        ],
        "output_artifacts": [
            {
                "path": str(draft_path.relative_to(REPO_ROOT)),
                "hash": draft_hash,
                "kind": "concept_packet_draft",
            }
        ],
        "schema_versions_used": {
            "generation_request_schema": const_of(req_schema, "schema_version")
            or "unknown",
            "generation_manifest_schema": const_of(mf_schema, "schema_version")
            or "unknown",
            "concept_brief_schema": const_of(brief_schema, "schema_version"),
            "build_plan_schema": None,
        },
        "status": "success",
        "notes": None,
    }

    # Self-validate manifest before writing.
    try:
        Draft202012Validator(mf_schema).validate(manifest)
    except ValidationError as e:
        die_failure(
            f"generated manifest does not validate against schema: {e.message}"
        )

    manifest_path.write_text(canonical_dump(manifest), encoding="utf-8")

    # --- report ---
    print("generate_concept_packet_stub.py — success")
    print(f"  request:      {request_path.relative_to(REPO_ROOT)}")
    print(f"  source brief: {brief_path.relative_to(REPO_ROOT)}")
    print(f"  draft:        {draft_path.relative_to(REPO_ROOT)}")
    print(f"  manifest:     {manifest_path.relative_to(REPO_ROOT)}")
    print(f"  manifest_id:  {manifest_id}")
    print(f"  status:       success")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
