"""Adapted from raluca07/use_case_icp at 5bd37b1ca3e49e940fc885839fa56411203afee0.
Source provenance and adaptation map: resources/reference-use-case-icp/reuse-v4.json.
No top-level upstream licence was found; retained for authorized local adaptation.
"""
from __future__ import annotations
from copy import deepcopy
from collections.abc import Mapping, Callable
from typing import Any
import json
import math
from statistics import mean

def _encode(value: Any) -> bytes:
    # Minimal dependency copied from upstream fault_experiment._encode.
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")

def _json_value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def inspect_catalogue_artifact(
    catalogue: Mapping[str, Any],
    package: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    python_executor: Callable[[Mapping[str, Any], str], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Inspect one visible frozen catalogue artifact through the July operation path."""
    if "artifact_inspection" not in package.get("available_operations", []):
        raise ValueError("artifact inspection is unavailable in this reviewer package")
    ref = str(request.get("node_ref") or "")
    visible = {
        str(value["node_ref"])
        for value in package.get("runtime_evidence", {}).get("nodes", [])
    }
    if ref not in visible:
        raise ValueError("artifact inspection requires a currently visible node")
    job = catalogue["jobs"][catalogue["assigned_job_id"]]
    node = next((value for value in job["nodes"] if str(value["node_ref"]) == ref), None)
    if node is None or node.get("artifact_content") is None:
        raise ValueError("visible node has no captured artifact value")
    inspection = str(request.get("inspection") or "read")
    start = int(request.get("start") or 0)
    count = int(request.get("count") or 20)
    if start < 0 or count < 1:
        raise ValueError("artifact read ranges must be positive")
    content = node["artifact_content"]
    base = {
        "operation": "artifact_inspection",
        "node_ref": ref,
        "inspection": inspection,
        "artifact_kind": node.get("artifact_kind"),
        "artifact_value_sha256": node.get("artifact_value_sha256"),
        "artifact_truncated_at_capture": bool(node.get("artifact_truncated")),
    }
    if inspection == "describe":
        if node.get("artifact_kind") == "table":
            rows = list(content.get("rows", []))
            columns = list(map(str, content.get("columns", [])))
            requested = list(map(str, request.get("columns", [])))
            unknown = set(requested) - set(columns)
            if unknown:
                raise ValueError(f"describe requested unknown columns: {sorted(unknown)}")
            numeric = {}
            for column in requested:
                values = [
                    row[column]
                    for row in rows
                    if isinstance(row.get(column), (int, float))
                    and not isinstance(row.get(column), bool)
                ]
                if values:
                    try:
                        finite = all(math.isfinite(value) for value in values)
                    except (OverflowError, TypeError, ValueError) as error:
                        raise ValueError(f"Unsupported numeric statistics for column {column!r}: values exceed finite numeric support") from error
                    if not finite:
                        raise ValueError(f"Unsupported numeric statistics for column {column!r}: non-finite value")
                    ordered = sorted(values)
                    middle = len(ordered) // 2
                    numeric[column] = {
                        "count": len(values),
                        "minimum": min(values),
                        "maximum": max(values),
                        "mean": mean(values),
                        "median": ordered[middle]
                        if len(ordered) % 2
                        else mean(ordered[middle - 1:middle + 1]),
                    }
            result = {
                "row_count": len(rows),
                "column_count": len(columns),
                "columns": columns,
                "json_value_types": {
                    column: sorted({_json_value_type(row.get(column)) for row in rows})
                    for column in columns
                },
                "null_counts": {
                    column: sum(row.get(column) is None for row in rows)
                    for column in columns
                },
                "numeric_statistics": numeric,
            }
        elif node.get("artifact_kind") == "document":
            text = str(content)
            result = {
                "character_count": len(text),
                "line_count": len(text.splitlines()),
                "capture_metadata": {
                    "artifact_size": deepcopy(node.get("artifact_size")),
                    "artifact_truncated": bool(node.get("artifact_truncated")),
                    "artifact_value_sha256": node.get("artifact_value_sha256"),
                },
            }
        else:
            result = {
                "json_value_type": _json_value_type(content),
                "artifact_size": deepcopy(node.get("artifact_size")),
            }
        if request.get("include_raw_metadata") is True:
            result["raw_metadata"] = deepcopy(node.get("raw_metadata", {}))
            result["raw_metadata_sha256"] = node.get("raw_metadata_sha256")
    elif inspection == "full":
        result = {"content": deepcopy(content), "more_available": False, "full_data_requested": True}
    elif inspection == "python":
        if python_executor is None:
            raise ValueError("python artifact inspection is disabled: signed production sandbox unavailable")
        result = {
            **dict(python_executor(node, str(request.get("code") or ""))),
            "python_analysis_requested": True,
        }
    elif inspection == "read":
        query = str(request.get("query") or "")
        if node.get("artifact_kind") == "document":
            text = str(content)
            if query:
                lowered, needle, offset, matches = text.casefold(), query.casefold(), 0, []
                while len(matches) < count:
                    found = lowered.find(needle, offset)
                    if found < 0:
                        break
                    matches.append({"character_offset": found, "text": text[found:found + len(query)]})
                    offset = found + max(1, len(query))
                result = {
                    "content": matches,
                    "returned_document_characters": sum(len(value["text"]) for value in matches),
                    "more_available": lowered.find(needle, offset) >= 0,
                }
            else:
                selected = text[start:start + count]
                result = {
                    "content": selected,
                    "returned_document_characters": len(selected),
                    "more_available": start + len(selected) < len(text),
                }
        elif node.get("artifact_kind") == "table":
            rows = list(content.get("rows", []))
            available = list(map(str, content.get("columns", [])))
            columns = list(map(str, request.get("columns", []))) or available
            unknown = set(columns) - set(available)
            if unknown:
                raise ValueError(f"read requested unknown columns: {sorted(unknown)}")
            if query:
                rows = [row for row in rows if query.casefold() in json.dumps(row, ensure_ascii=False).casefold()]
            selected = [
                {column: row.get(column) for column in columns}
                for row in rows[start:start + count]
            ]
            result = {
                "content": selected,
                "columns": columns,
                "returned_rows": len(selected),
                "returned_columns": len(columns),
                "more_available": start + len(selected) < len(rows),
            }
        else:
            values = content if isinstance(content, list) else [content]
            selected = deepcopy(values[start:start + count])
            result = {"content": selected, "returned_records": len(selected), "more_available": start + len(selected) < len(values)}
    else:
        raise ValueError(f"unknown artifact inspection choice: {inspection}")
    response = {**base, **result}
    response["artifact_bytes_returned"] = len(_encode(response.get("content", response.get("result"))))
    return response
