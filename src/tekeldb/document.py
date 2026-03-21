from pathlib import Path
from datetime import datetime
import yaml


def read_document(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def write_document(path: Path, doc: dict, fmt: str = "yaml") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        if fmt == "yaml":
            yaml.safe_dump(doc, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        else:
            yaml.safe_dump(doc, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def apply_defaults(doc: dict, collection_def: dict) -> dict:
    """Fill in default values for missing fields."""
    fields_def = collection_def.get("fields", {})
    for field_name, field_def in fields_def.items():
        if isinstance(field_def, dict) and "default" in field_def:
            if field_name not in doc:
                doc[field_name] = field_def["default"]
    return doc


def apply_auto_fields(doc: dict, collection_def: dict) -> dict:
    """Set auto: true datetime fields to current time."""
    fields_def = collection_def.get("fields", {})
    for field_name, field_def in fields_def.items():
        if isinstance(field_def, dict) and field_def.get("auto") and field_def.get("type") == "datetime":
            if field_name not in doc:
                doc[field_name] = datetime.now().isoformat()
    return doc


def apply_timestamps(doc: dict, timestamps: bool, is_new: bool) -> dict:
    """Add created/updated timestamps."""
    if not timestamps:
        return doc
    now = datetime.now().isoformat()
    if is_new:
        doc["created"] = now
    doc["updated"] = now
    return doc


def doc_path(db_path: Path, collection: str, doc_id: str, fmt: str = "yaml") -> Path:
    ext = {"yaml": ".yaml", "json": ".json", "toml": ".toml"}.get(fmt, ".yaml")
    return db_path / "data" / collection / f"{doc_id}{ext}"
