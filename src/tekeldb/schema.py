from pathlib import Path
import re
from datetime import date, datetime
import yaml


def load_schema(db_path: Path) -> dict | None:
    """Load schema.yaml. Returns None if empty/missing (schema-free mode)."""
    schema_file = db_path / "schema.yaml"
    if not schema_file.exists():
        return None
    with open(schema_file) as f:
        schema = yaml.safe_load(f)
    if not schema or not schema.get("collections"):
        return None
    return schema


def get_collection_def(schema: dict | None, name: str) -> dict | None:
    """Get a collection definition from the schema."""
    if schema is None:
        return None
    collections = schema.get("collections", {})
    if name not in collections:
        raise KeyError(f"Collection '{name}' not found in schema.")
    return collections[name]


def get_first_string_field(collection_def: dict) -> str:
    """Find the first required string field (used for the positional title arg)."""
    for field_name, field_def in collection_def.get("fields", {}).items():
        if isinstance(field_def, dict) and field_def.get("type") == "string" and field_def.get("required"):
            return field_name
    # Fallback: first string field
    for field_name, field_def in collection_def.get("fields", {}).items():
        if isinstance(field_def, dict) and field_def.get("type") == "string":
            return field_name
    return "title"


def get_collection_by_prefix(schema: dict | None, prefix: str) -> tuple[str, dict] | None:
    """Find a collection by its ID prefix."""
    if schema is None:
        return None
    for name, col_def in schema.get("collections", {}).items():
        if col_def.get("id_prefix", "").upper() == prefix.upper():
            return name, col_def
    return None


def validate_document(doc: dict, collection_def: dict, existing_doc: dict | None = None) -> list[str]:
    """Validate a document against its collection schema. Returns list of errors."""
    errors = []
    fields_def = collection_def.get("fields", {})

    # Check required fields
    for field_name, field_def in fields_def.items():
        if isinstance(field_def, dict) and field_def.get("required"):
            if field_name not in doc or doc[field_name] is None:
                errors.append(f"Missing required field: {field_name}")

    # Validate each field present in the document
    for field_name, value in doc.items():
        if field_name in ("id", "created", "updated"):
            continue
        # Skip ref fields
        if field_name in collection_def.get("refs", {}):
            continue
        if field_name not in fields_def:
            continue  # Allow extra fields silently for now
        field_def = fields_def[field_name]
        if isinstance(field_def, dict):
            errors.extend(_validate_field(field_name, value, field_def))

    # Check transitions
    transitions = collection_def.get("transitions", {})
    if existing_doc and transitions:
        for field_name, transition_map in transitions.items():
            if field_name in doc and field_name in existing_doc:
                old_val = existing_doc[field_name]
                new_val = doc[field_name]
                if old_val != new_val and old_val in transition_map:
                    allowed = transition_map[old_val]
                    if new_val not in allowed:
                        errors.append(
                            f"Invalid transition for '{field_name}': "
                            f"'{old_val}' -> '{new_val}'. "
                            f"Allowed: {allowed}"
                        )

    return errors


def validate_refs(doc: dict, collection_def: dict, db_path: Path) -> list[str]:
    """Check that referenced document IDs actually exist on disk."""
    errors = []
    refs_def = collection_def.get("refs", {})
    for ref_name, ref_def in refs_def.items():
        if ref_name not in doc:
            continue
        target_collection = ref_def["collection"]
        ref_type = ref_def.get("type", "one")
        data_dir = db_path / "data" / target_collection

        if ref_type == "one":
            ref_id = doc[ref_name]
            if ref_id and not _ref_exists(data_dir, ref_id):
                errors.append(f"Broken reference '{ref_name}': {ref_id} not found in {target_collection}")
        elif ref_type == "many":
            ref_ids = doc[ref_name] if isinstance(doc[ref_name], list) else [doc[ref_name]]
            for ref_id in ref_ids:
                if ref_id and not _ref_exists(data_dir, ref_id):
                    errors.append(f"Broken reference '{ref_name}': {ref_id} not found in {target_collection}")

    return errors


def _ref_exists(data_dir: Path, doc_id: str) -> bool:
    for ext in (".yaml", ".json", ".toml"):
        if (data_dir / f"{doc_id}{ext}").exists():
            return True
    return False


def _validate_field(field_name: str, value, field_def: dict) -> list[str]:
    errors = []
    ftype = field_def.get("type")

    if value is None:
        return errors

    if ftype == "string":
        if not isinstance(value, str):
            errors.append(f"Field '{field_name}': expected string, got {type(value).__name__}")
        elif field_def.get("format") == "email":
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
                errors.append(f"Field '{field_name}': invalid email format")
        elif field_def.get("format") == "url":
            if not re.match(r"^https?://", value):
                errors.append(f"Field '{field_name}': invalid URL format")

    elif ftype == "text":
        if not isinstance(value, str):
            errors.append(f"Field '{field_name}': expected text, got {type(value).__name__}")

    elif ftype == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"Field '{field_name}': expected integer, got {type(value).__name__}")
        else:
            if "min" in field_def and value < field_def["min"]:
                errors.append(f"Field '{field_name}': value {value} below minimum {field_def['min']}")
            if "max" in field_def and value > field_def["max"]:
                errors.append(f"Field '{field_name}': value {value} above maximum {field_def['max']}")

    elif ftype == "float":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"Field '{field_name}': expected float, got {type(value).__name__}")
        else:
            if "min" in field_def and value < field_def["min"]:
                errors.append(f"Field '{field_name}': value {value} below minimum {field_def['min']}")
            if "max" in field_def and value > field_def["max"]:
                errors.append(f"Field '{field_name}': value {value} above maximum {field_def['max']}")

    elif ftype == "boolean":
        if not isinstance(value, bool):
            errors.append(f"Field '{field_name}': expected boolean, got {type(value).__name__}")

    elif ftype == "date":
        if not isinstance(value, (date, datetime)):
            if isinstance(value, str):
                try:
                    date.fromisoformat(value)
                except ValueError:
                    errors.append(f"Field '{field_name}': invalid date format")
            else:
                errors.append(f"Field '{field_name}': expected date, got {type(value).__name__}")

    elif ftype == "datetime":
        if not isinstance(value, datetime):
            if isinstance(value, str):
                try:
                    datetime.fromisoformat(value)
                except ValueError:
                    errors.append(f"Field '{field_name}': invalid datetime format")
            else:
                errors.append(f"Field '{field_name}': expected datetime, got {type(value).__name__}")

    elif ftype == "enum":
        allowed = field_def.get("values", [])
        if value not in allowed:
            errors.append(f"Field '{field_name}': '{value}' not in {allowed}")

    elif ftype == "list":
        if not isinstance(value, list):
            errors.append(f"Field '{field_name}': expected list, got {type(value).__name__}")

    elif ftype == "object":
        if not isinstance(value, dict):
            errors.append(f"Field '{field_name}': expected object, got {type(value).__name__}")

    return errors
