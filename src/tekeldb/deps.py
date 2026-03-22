"""Dependency / reference inspector."""
from pathlib import Path

from .collection import list_documents
from .schema import load_schema, get_collection_def


def get_forward_refs(doc: dict, collection_def: dict) -> list[tuple[str, str, list[str]]]:
    """Get outgoing references: [(ref_field, target_collection, [target_ids])]."""
    refs_def = collection_def.get("refs", {})
    result = []
    for ref_name, ref_def in refs_def.items():
        if ref_name not in doc:
            continue
        target_collection = ref_def["collection"]
        value = doc[ref_name]
        if isinstance(value, list):
            ids = [str(v) for v in value]
        else:
            ids = [str(value)]
        result.append((ref_name, target_collection, ids))
    return result


def get_reverse_refs(doc_id: str, schema: dict, db_path: Path) -> list[tuple[str, str, str]]:
    """Find all documents that reference this doc_id.

    Returns: [(source_id, source_collection, ref_field)]
    """
    result = []
    for col_name, col_def in schema.get("collections", {}).items():
        refs_def = col_def.get("refs", {})
        if not refs_def:
            continue

        docs = list_documents(db_path, col_name)
        for doc in docs:
            source_id = doc.get("id", "unknown")
            if source_id == doc_id:
                continue
            for ref_name, ref_def in refs_def.items():
                if ref_name not in doc:
                    continue
                value = doc[ref_name]
                if isinstance(value, list):
                    if doc_id in [str(v) for v in value]:
                        result.append((source_id, col_name, ref_name))
                elif str(value) == doc_id:
                    result.append((source_id, col_name, ref_name))

    return result


def format_deps_output(doc: dict, forward: list, reverse: list) -> str:
    """Format dependency output for display."""
    doc_id = doc.get("id", "unknown")
    title = doc.get("title") or doc.get("name") or ""
    lines = [f'{doc_id} "{title}"' if title else doc_id, ""]

    if forward:
        lines.append("  References:")
        for ref_name, target_col, ids in forward:
            ids_str = ", ".join(ids)
            lines.append(f"    {ref_name} -> {ids_str} ({target_col})")
    else:
        lines.append("  References: none")

    lines.append("")

    if reverse:
        lines.append("  Referenced by:")
        for source_id, source_col, ref_name in reverse:
            lines.append(f"    {source_id} ({source_col}.{ref_name})")
    else:
        lines.append("  Referenced by: none")

    return "\n".join(lines)
