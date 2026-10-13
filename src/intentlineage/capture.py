"""Read-only inspection of artifacts from the recovered shared Etiq wrapper."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


class CaptureError(ValueError):
    """The artifact cannot be treated as complete capture evidence."""

    def __init__(self, message, *, status=None, scan_errors=None):
        super().__init__(message)
        self.status = status
        self.scan_errors = scan_errors


@dataclass(frozen=True)
class CaptureArtifacts:
    """Original artifacts and direct references into Etiq's existing graph."""

    scan: dict
    lineage: dict
    nodes_by_id: dict
    causal_edges: tuple


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CaptureError(f"Unreadable JSON artifact: {path}: {error}") from error


def _contained_file(directory, relative, field):
    if not isinstance(relative, str) or not relative.strip() or Path(relative).is_absolute():
        raise CaptureError(f"{field} must identify a relative file")
    resolved = (directory / relative).resolve()
    if not resolved.is_relative_to(directory.resolve()):
        raise CaptureError(f"{field} must stay inside its artifact/workspace directory")
    return resolved


def load_capture(scan_path, *, workspace_root=None):
    """Inspect status/errors before lineage; preserve original evidence and IDs.

    Supplying the workspace also validates the selected entry and current source
    hash. Synthetic fixtures may omit this check; they are not executed evidence.
    This reader does not construct graphs or infer unobserved dataframe values.
    """
    path = Path(scan_path).resolve()
    scan = _read_json(path)
    if not isinstance(scan, dict):
        raise CaptureError("scan-result.json must be an object")
    status, errors = scan.get("status"), scan.get("scan_errors")
    if status != "completed" or errors != []:
        raise CaptureError(f"Capture status={status}; scan_errors={json.dumps(errors)}",
                           status=status, scan_errors=errors)
    if scan.get("lineage_format") != "json" or scan.get("lineage_generated") is not True:
        raise CaptureError("A generated JSON lineage artifact is required")
    lineage_path = _contained_file(path.parent, scan.get("lineage_path"), "lineage_path")
    if workspace_root is not None:
        root = Path(workspace_root).resolve()
        if not path.is_relative_to(root):
            raise CaptureError("The scan artifact must stay inside the workspace")
        entry = _contained_file(root, scan.get("entry_file_path"), "entry_file_path")
        if scan.get("target") != scan.get("entry_file_path"):
            raise CaptureError("Capture target differs from entry_file_path")
        if not entry.is_file() or hashlib.sha256(entry.read_bytes()).hexdigest() != scan.get("entry_file_hash"):
            raise CaptureError("Capture is stale for the current entry file")
    lineage = _read_json(lineage_path)
    if not isinstance(lineage, dict) or not isinstance(lineage.get("objects"), list) or not isinstance(lineage.get("edges"), list):
        raise CaptureError("Unsupported JSON lineage: objects and edges lists are required")
    nodes = {}
    for node in lineage["objects"]:
        if not isinstance(node, dict) or "_gvid" not in node or node["_gvid"] in nodes:
            raise CaptureError("Lineage objects need unique original _gvid identifiers")
        nodes[node["_gvid"]] = node
    edges = []
    for edge in lineage["edges"]:
        if not isinstance(edge, dict) or edge.get("tail") not in nodes or edge.get("head") not in nodes:
            raise CaptureError("Lineage edge references an absent original node")
        edges.append((edge["tail"], edge["head"]))
    return CaptureArtifacts(scan, lineage, nodes, tuple(edges))
