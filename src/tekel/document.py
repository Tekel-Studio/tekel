import json
from pathlib import Path


def read_document(path: Path) -> dict:
    with open(path) as f:
        return json.load(f) or {}


def write_document(path: Path, doc: dict) -> None:
    """Write document to file. Used by validate --fix and schema migrate."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(doc, f, indent=2, default=str)
        f.write("\n")


def apply_defaults(doc: dict, collection_def: dict) -> dict:
    """Fill in default values for missing fields."""
    fields_def = collection_def.get("fields", {})
    for field_name, field_def in fields_def.items():
        if isinstance(field_def, dict) and "default" in field_def:
            if field_name not in doc:
                doc[field_name] = field_def["default"]
    return doc


def doc_path(db_path: Path, collection: str, doc_id: str) -> Path:
    return db_path / "data" / collection / f"{doc_id}.json"
