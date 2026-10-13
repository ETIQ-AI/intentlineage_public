"""Lazy catalogue adapted from use_case_icp n27pb_experiment at 5bd37b1.
Single job/order agnostic; descriptors bind existing artifact refs and hashes.
See resources/reference-use-case-icp/reuse-v4.json for source hashes/notices.
"""
from copy import deepcopy
from collections.abc import Mapping
from typing import Any
from ..native_capture import digest

def _artifact_descriptor(instance_id, node):
    ref = node['artifact_ref']
    return {'artifact_ref': ref, 'kind': node['artifact_kind'],
            'captured_value_sha256': digest(node['artifact_content']),
            'truncated': node['artifact_truncated']}, ref

def _payload_lazy_catalogue(catalogue: Mapping[str, Any], instance_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    reviewer_nodes: dict[str, dict[str, Any]] = {}
    artifacts: dict[str, Any] = {}
    omissions = []
    body_keys = {"artifact_content", "value_preview", "raw_value", "value", "content", "rows", "text"}
    for job_id in catalogue["jobs"]:
        for original in catalogue["jobs"][job_id]["native_graph"]["nodes"]:
            node = deepcopy(original)
            paths = []
            payload_values = [original.get(key) for key in ("artifact_content", "value_preview") if original.get(key) is not None]
            for key in list(node):
                value = node[key]
                duplicate = key in body_keys or any(value == payload for payload in payload_values)
                if duplicate:
                    if value is not None:
                        paths.append(key)
                    node.pop(key)
            if original.get("artifact_content") is not None:
                descriptor, artifact_ref = _artifact_descriptor(instance_id, original)
                node["artifact_descriptor"] = descriptor
                operation_node = {
                    "node_ref": artifact_ref,
                    "artifact_kind": original.get("artifact_kind"),
                    "artifact_content": deepcopy(original["artifact_content"]),
                    "artifact_truncated": bool(original.get("artifact_truncated")),
                    "artifact_size": deepcopy(original.get("artifact_size")),
                    "artifact_value_sha256": descriptor["captured_value_sha256"],
                    "raw_metadata": {}, "raw_metadata_sha256": digest({}),
                }
                artifacts[artifact_ref] = {
                    "artifact_ref": artifact_ref, "job_id": job_id,
                    "native_node_ref": original["native_node_ref"],
                    "complete_native_node": deepcopy(original),
                    "operation_node": operation_node,
                    "descriptor": deepcopy(descriptor),
                }
            reviewer_nodes[original["native_node_ref"]] = node
            if paths:
                omissions.append({
                    "job_id": job_id, "native_node_ref": original["native_node_ref"],
                    "omitted_field_paths": sorted(paths),
                    "complete_node_sha256": digest(original),
                    "reviewer_node_sha256": digest(node),
                })
    reviewer = {"schema_version": "n27pb-payload-lazy-native-nodes-1", "nodes": reviewer_nodes}
    reviewer["reviewer_nodes_sha256"] = digest(reviewer)
    disclosure = {"schema_version": "n27pb-artifact-disclosure-catalogue-1", "artifacts": artifacts}
    disclosure["catalogue_sha256"] = digest(disclosure)
    manifest = {
        "schema_version": "n27pb-field-omission-manifest-1", "instance": instance_id,
        "omissions": omissions, "artifact_count": len(artifacts),
        "body_keys_withheld": sorted(body_keys),
        "direct_duplicate_scan_passed": True,
    }
    manifest["manifest_sha256"] = digest(manifest)
    return reviewer, disclosure, manifest
