from pathlib import Path
import yaml


def read_document(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def write_document(path: Path, doc: dict, fmt: str = "yaml") -> None:
    """Write document to file. Used by validate --fix and schema migrate."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(doc, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def apply_defaults(doc: dict, collection_def: dict) -> dict:
    """Fill in default values for missing fields."""
    fields_def = collection_def.get("fields", {})
    for field_name, field_def in fields_def.items():
        if isinstance(field_def, dict) and "default" in field_def:
            if field_name not in doc:
                doc[field_name] = field_def["default"]
    return doc


def doc_path(db_path: Path, collection: str, doc_id: str, fmt: str = "yaml") -> Path:
    ext = {"yaml": ".yaml", "json": ".json", "toml": ".toml"}.get(fmt, ".yaml")
    return db_path / "data" / collection / f"{doc_id}{ext}"
