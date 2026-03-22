"""Schema migration — compare schema against existing docs and apply fixable changes."""
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from .collection import collection_dir, ensure_collection_dir, list_documents
from .document import doc_path, read_document, write_document, apply_defaults
from .schema import load_schema, get_collection_def, validate_document


@dataclass
class MigrationAction:
    type: str  # add_default, coerce_type, prune_field, create_dir, error
    collection: str
    doc_id: str | None
    field: str | None
    description: str
    fixable: bool


def compute_migrations(schema: dict, db_path: Path) -> list[MigrationAction]:
    """Compare schema against existing documents and identify needed migrations."""
    actions = []
    collections = schema.get("collections", {})

    for col_name, col_def in collections.items():
        col_dir = collection_dir(db_path, col_name)

        # Check if collection directory exists
        if not col_dir.exists():
            actions.append(MigrationAction(
                type="create_dir",
                collection=col_name,
                doc_id=None,
                field=None,
                description=f"Create data directory for collection '{col_name}'",
                fixable=True,
            ))
            continue

        fields_def = col_def.get("fields", {})
        docs = list_documents(db_path, col_name)

        for doc in docs:
            doc_id = doc.get("id", "unknown")

            # Check for missing fields with defaults
            for field_name, field_def in fields_def.items():
                if not isinstance(field_def, dict):
                    continue
                if field_name not in doc:
                    if "default" in field_def:
                        actions.append(MigrationAction(
                            type="add_default",
                            collection=col_name,
                            doc_id=doc_id,
                            field=field_name,
                            description=f"{doc_id}: add '{field_name}' with default '{field_def['default']}'",
                            fixable=True,
                        ))
                    elif field_def.get("required"):
                        actions.append(MigrationAction(
                            type="error",
                            collection=col_name,
                            doc_id=doc_id,
                            field=field_name,
                            description=f"{doc_id}: missing required field '{field_name}' (no default available)",
                            fixable=False,
                        ))

            # Check for type coercions
            for field_name, value in doc.items():
                if field_name in ("id", "created", "updated"):
                    continue
                if field_name not in fields_def:
                    # Check if additional_fields is false
                    if not col_def.get("additional_fields", True):
                        actions.append(MigrationAction(
                            type="prune_field",
                            collection=col_name,
                            doc_id=doc_id,
                            field=field_name,
                            description=f"{doc_id}: unknown field '{field_name}'",
                            fixable=True,  # fixable with --prune
                        ))
                    continue

                field_def = fields_def[field_name]
                if not isinstance(field_def, dict):
                    continue
                ftype = field_def.get("type")

                # Check type coercion opportunities
                if ftype == "integer" and isinstance(value, str):
                    try:
                        int(value)
                        actions.append(MigrationAction(
                            type="coerce_type",
                            collection=col_name,
                            doc_id=doc_id,
                            field=field_name,
                            description=f"{doc_id}: coerce '{field_name}' from string \"{value}\" to integer",
                            fixable=True,
                        ))
                    except ValueError:
                        actions.append(MigrationAction(
                            type="error",
                            collection=col_name,
                            doc_id=doc_id,
                            field=field_name,
                            description=f"{doc_id}: field '{field_name}' is \"{value}\", cannot coerce to integer",
                            fixable=False,
                        ))
                elif ftype == "boolean" and isinstance(value, str):
                    if value.lower() in ("true", "false", "yes", "no"):
                        actions.append(MigrationAction(
                            type="coerce_type",
                            collection=col_name,
                            doc_id=doc_id,
                            field=field_name,
                            description=f"{doc_id}: coerce '{field_name}' from string \"{value}\" to boolean",
                            fixable=True,
                        ))

                # Check removed enum values
                if ftype == "enum":
                    allowed = field_def.get("values", [])
                    if value not in allowed:
                        actions.append(MigrationAction(
                            type="error",
                            collection=col_name,
                            doc_id=doc_id,
                            field=field_name,
                            description=f"{doc_id}: '{field_name}' value '{value}' not in allowed values {allowed}",
                            fixable=False,
                        ))

    # Check for data directories without schema definition
    data_dir = db_path / "data"
    if data_dir.exists():
        for d in sorted(data_dir.iterdir()):
            if d.is_dir() and d.name not in collections:
                actions.append(MigrationAction(
                    type="warning",
                    collection=d.name,
                    doc_id=None,
                    field=None,
                    description=f"Data directory '{d.name}' exists but is not in schema (will not be deleted)",
                    fixable=False,
                ))

    return actions


def apply_migrations(actions: list[MigrationAction], db_path: Path, prune: bool = False) -> tuple[int, int]:
    """Apply fixable migration actions. Returns (applied, skipped) counts."""
    config_fmt = "yaml"
    applied = 0
    skipped = 0
    backup_dir = db_path / ".migrate-backup"

    # Group actions by (collection, doc_id) for efficient file operations
    doc_actions: dict[tuple[str, str], list[MigrationAction]] = {}
    for action in actions:
        if not action.fixable:
            skipped += 1
            continue
        if action.type == "prune_field" and not prune:
            skipped += 1
            continue
        if action.type == "create_dir":
            ensure_collection_dir(db_path, action.collection)
            applied += 1
            continue
        if action.doc_id is None:
            continue
        key = (action.collection, action.doc_id)
        doc_actions.setdefault(key, []).append(action)

    for (col_name, doc_id), acts in doc_actions.items():
        path = doc_path(db_path, col_name, doc_id, config_fmt)
        if not path.exists():
            continue

        # Backup
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{col_name}_{doc_id}.yaml"
        shutil.copy2(path, backup_path)

        doc = read_document(path)
        modified = False

        for action in acts:
            if action.type == "add_default":
                schema = load_schema(db_path)
                col_def = get_collection_def(schema, col_name)
                if col_def:
                    field_def = col_def.get("fields", {}).get(action.field, {})
                    if "default" in field_def and action.field not in doc:
                        doc[action.field] = field_def["default"]
                        modified = True
                        applied += 1

            elif action.type == "coerce_type":
                schema = load_schema(db_path)
                col_def = get_collection_def(schema, col_name)
                if col_def:
                    field_def = col_def.get("fields", {}).get(action.field, {})
                    ftype = field_def.get("type")
                    value = doc.get(action.field)
                    if ftype == "integer" and isinstance(value, str):
                        try:
                            doc[action.field] = int(value)
                            modified = True
                            applied += 1
                        except ValueError:
                            skipped += 1
                    elif ftype == "boolean" and isinstance(value, str):
                        doc[action.field] = value.lower() in ("true", "yes")
                        modified = True
                        applied += 1

            elif action.type == "prune_field" and prune:
                if action.field in doc:
                    del doc[action.field]
                    modified = True
                    applied += 1

        if modified:
            write_document(path, doc, config_fmt)

    return applied, skipped
