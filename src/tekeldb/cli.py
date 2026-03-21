import shutil
import sys
from pathlib import Path

import click
import yaml

from . import __version__
from .config import DEFAULT_CONFIG, find_db, load_config, write_config
from .schema import (
    get_collection_def,
    get_first_string_field,
    load_schema,
    validate_document,
    validate_refs,
)
from .idgen import generate_id
from .document import (
    apply_auto_fields,
    apply_defaults,
    apply_timestamps,
    doc_path,
    read_document,
    write_document,
)
from .collection import (
    collection_dir,
    ensure_collection_dir,
    find_document_by_id,
    list_documents,
    resolve_collection_from_id,
)
from .query import match_document, parse_filter, sort_documents
from .formatter import (
    format_csv_output,
    format_json_output,
    format_single,
    format_table,
    format_yaml_output,
    get_display_fields,
)


BUILTIN_SCHEMAS = {
    "pm": "pm.yaml",
}


@click.group()
@click.version_option(__version__, prog_name="tekeldb")
def main():
    """tekeldb — A schema-driven, flat-file document database."""
    pass


# --- Database lifecycle ---


@main.command()
@click.option("--schema", "schema_opt", default=None, help="Built-in schema name or path to schema file.")
def init(schema_opt):
    """Create a new tekeldb database in the current directory."""
    db_path = Path.cwd() / ".tekeldb"
    if db_path.exists():
        click.echo("Error: .tekeldb already exists in this directory.", err=True)
        sys.exit(1)

    db_path.mkdir()
    (db_path / "data").mkdir()

    # Write config
    write_config(db_path, dict(DEFAULT_CONFIG))

    # Write counters
    with open(db_path / "counters.yaml", "w") as f:
        yaml.safe_dump({}, f)

    # Handle schema
    if schema_opt:
        if schema_opt in BUILTIN_SCHEMAS:
            src = Path(__file__).parent / "schemas" / BUILTIN_SCHEMAS[schema_opt]
            shutil.copy(src, db_path / "schema.yaml")
        elif Path(schema_opt).exists():
            shutil.copy(schema_opt, db_path / "schema.yaml")
        else:
            click.echo(f"Error: Schema '{schema_opt}' not found.", err=True)
            sys.exit(1)
    else:
        # Empty schema (schema-free mode)
        with open(db_path / "schema.yaml", "w") as f:
            yaml.safe_dump({"version": "1.0", "name": "default"}, f)

    # Create collection directories from schema
    schema = load_schema(db_path)
    if schema:
        for col_name in schema.get("collections", {}):
            ensure_collection_dir(db_path, col_name)

    click.echo(f"Initialized tekeldb database at {db_path}")


@main.command()
def status():
    """Show database summary."""
    db_path = find_db()
    schema = load_schema(db_path)
    config = load_config(db_path)

    name = schema.get("name", "unnamed") if schema else "schema-free"
    click.echo(f"Database: {name}")
    click.echo(f"Location: {db_path}")
    click.echo(f"Format: {config.get('format', 'yaml')}")
    click.echo(f"ID Strategy: {config.get('id_strategy', 'sequential')}")
    click.echo()

    if schema:
        collections = schema.get("collections", {})
        click.echo(f"Collections ({len(collections)}):")
        for col_name in collections:
            docs = list_documents(db_path, col_name)
            click.echo(f"  {col_name}: {len(docs)} documents")

            # Show status breakdown if there's a status enum field
            col_def = collections[col_name]
            fields = col_def.get("fields", {})
            if "status" in fields:
                status_counts = {}
                for doc in docs:
                    s = doc.get("status", "unknown")
                    status_counts[s] = status_counts.get(s, 0) + 1
                if status_counts:
                    parts = [f"{k}: {v}" for k, v in sorted(status_counts.items())]
                    click.echo(f"    ({', '.join(parts)})")
    else:
        # Schema-free: list any directories under data/
        data_dir = db_path / "data"
        if data_dir.exists():
            for d in sorted(data_dir.iterdir()):
                if d.is_dir():
                    count = sum(1 for f in d.iterdir() if f.is_file())
                    click.echo(f"  {d.name}: {count} documents")


# --- Schema commands ---


@main.group()
def schema():
    """Schema management commands."""
    pass


@schema.command("show")
def schema_show():
    """Print the current schema."""
    db_path = find_db()
    schema_file = db_path / "schema.yaml"
    if schema_file.exists():
        click.echo(schema_file.read_text())
    else:
        click.echo("No schema file found.")


# --- CRUD ---


@main.command()
@click.argument("collection")
@click.argument("title")
@click.pass_context
def create(ctx, collection, title):
    """Create a new document in a collection."""
    db_path = find_db()
    schema = load_schema(db_path)
    config = load_config(db_path)

    col_def = get_collection_def(schema, collection) if schema else None
    if schema and col_def is None:
        click.echo(f"Error: Collection '{collection}' not found in schema.", err=True)
        sys.exit(1)

    # Parse extra args as --field value pairs
    extra_fields = _parse_extra_args(ctx.args)

    # Build document
    doc = {}

    # Set the title/name field
    if col_def:
        title_field = get_first_string_field(col_def)
    else:
        title_field = "title"
    doc[title_field] = title

    # Merge extra fields
    for key, value in extra_fields.items():
        doc[key] = value

    # Apply defaults and auto fields
    if col_def:
        doc = apply_defaults(doc, col_def)
        doc = apply_auto_fields(doc, col_def)

    # Generate ID
    prefix = col_def.get("id_prefix", collection.upper()[:4]) if col_def else collection.upper()[:4]
    strategy = config.get("id_strategy", "sequential")
    doc_id = generate_id(db_path, collection, prefix, strategy)
    doc = {"id": doc_id, **doc}

    # Timestamps
    doc = apply_timestamps(doc, config.get("timestamps", True), is_new=True)

    # Validate
    if col_def:
        errors = validate_document(doc, col_def)
        if config.get("strict"):
            errors.extend(validate_refs(doc, col_def, db_path))
        if errors:
            click.echo("Validation errors:", err=True)
            for e in errors:
                click.echo(f"  - {e}", err=True)
            sys.exit(1)

    # Write
    fmt = config.get("format", "yaml")
    path = doc_path(db_path, collection, doc_id, fmt)
    ensure_collection_dir(db_path, collection)
    write_document(path, doc, fmt)

    click.echo(f"Created {doc_id}")


# Allow unknown options for dynamic schema fields
create.context_settings = dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
)


@main.command()
@click.argument("doc_id")
def show(doc_id):
    """Show a single document."""
    db_path = find_db()
    schema = load_schema(db_path)
    result = find_document_by_id(db_path, schema, doc_id)
    if result is None:
        click.echo(f"Error: Document '{doc_id}' not found.", err=True)
        sys.exit(1)
    _, doc = result
    click.echo(format_single(doc))


@main.command("list")
@click.argument("collection")
@click.argument("filters", nargs=-1)
@click.option("--sort", "sort_field", default=None, help="Sort by field. Prefix with - for descending.")
@click.option("--format", "fmt", default="table", type=click.Choice(["table", "yaml", "json", "csv"]))
@click.option("--limit", default=0, type=int, help="Limit number of results.")
def list_cmd(collection, filters, sort_field, fmt, limit):
    """List documents in a collection with optional filters."""
    db_path = find_db()
    schema = load_schema(db_path)

    if schema:
        col_def = get_collection_def(schema, collection)
    else:
        col_def = None

    docs = list_documents(db_path, collection)

    # Apply filters
    if filters:
        parsed_filters = [parse_filter(f) for f in filters]
        docs = [d for d in docs if match_document(d, parsed_filters)]

    # Sort
    if sort_field:
        docs = sort_documents(docs, sort_field)

    # Limit
    if limit > 0:
        docs = docs[:limit]

    # Format output
    fields = get_display_fields(col_def) if col_def else None
    if fmt == "table":
        click.echo(format_table(docs, fields))
    elif fmt == "yaml":
        click.echo(format_yaml_output(docs))
    elif fmt == "json":
        click.echo(format_json_output(docs))
    elif fmt == "csv":
        click.echo(format_csv_output(docs, fields))


@main.command()
@click.argument("doc_id")
@click.pass_context
def edit(ctx, doc_id):
    """Edit fields on an existing document."""
    db_path = find_db()
    schema = load_schema(db_path)
    config = load_config(db_path)

    result = find_document_by_id(db_path, schema, doc_id)
    if result is None:
        click.echo(f"Error: Document '{doc_id}' not found.", err=True)
        sys.exit(1)

    path, doc = result
    existing_doc = dict(doc)

    # Parse extra args
    extra_fields = _parse_extra_args(ctx.args)
    if not extra_fields:
        click.echo("No fields to update. Use --field value syntax.", err=True)
        sys.exit(1)

    # Merge
    for key, value in extra_fields.items():
        doc[key] = value

    # Validate
    col_name = resolve_collection_from_id(schema, doc_id)
    col_def = get_collection_def(schema, col_name) if schema and col_name else None
    if col_def:
        errors = validate_document(doc, col_def, existing_doc=existing_doc)
        if config.get("strict"):
            errors.extend(validate_refs(doc, col_def, db_path))
        if errors:
            click.echo("Validation errors:", err=True)
            for e in errors:
                click.echo(f"  - {e}", err=True)
            sys.exit(1)

    # Update timestamp
    doc = apply_timestamps(doc, config.get("timestamps", True), is_new=False)

    # Write back
    fmt = config.get("format", "yaml")
    write_document(path, doc, fmt)
    click.echo(f"Updated {doc_id}")


edit.context_settings = dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
)


@main.command()
@click.argument("doc_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def delete(doc_id, yes):
    """Delete a document."""
    db_path = find_db()
    schema = load_schema(db_path)

    result = find_document_by_id(db_path, schema, doc_id)
    if result is None:
        click.echo(f"Error: Document '{doc_id}' not found.", err=True)
        sys.exit(1)

    path, _ = result

    if not yes:
        click.confirm(f"Delete {doc_id}?", abort=True)

    path.unlink()
    click.echo(f"Deleted {doc_id}")


@main.command()
@click.option("--collection", default=None, help="Validate only this collection.")
@click.option("--fix", is_flag=True, help="Auto-fix fixable issues (apply defaults).")
def validate(collection, fix):
    """Validate documents against the schema."""
    db_path = find_db()
    schema = load_schema(db_path)
    config = load_config(db_path)

    if not schema:
        click.echo("No schema defined. Nothing to validate.")
        return

    collections_to_check = [collection] if collection else list(schema.get("collections", {}).keys())
    total_errors = 0

    for col_name in collections_to_check:
        col_def = get_collection_def(schema, col_name)
        if col_def is None:
            click.echo(f"Warning: Collection '{col_name}' not found in schema.", err=True)
            continue

        docs = list_documents(db_path, col_name)
        for doc in docs:
            doc_id = doc.get("id", "unknown")
            errors = validate_document(doc, col_def)
            errors.extend(validate_refs(doc, col_def, db_path))

            if errors and fix:
                # Try to fix by applying defaults
                fixed_doc = apply_defaults(dict(doc), col_def)
                remaining_errors = validate_document(fixed_doc, col_def)
                if len(remaining_errors) < len(errors):
                    fmt = config.get("format", "yaml")
                    path = doc_path(db_path, col_name, doc_id, fmt)
                    write_document(path, fixed_doc, fmt)
                    click.echo(f"  Fixed {doc_id}: applied defaults")
                    errors = remaining_errors

            if errors:
                total_errors += len(errors)
                click.echo(f"{doc_id}:")
                for e in errors:
                    click.echo(f"  - {e}")

    if total_errors == 0:
        click.echo("All documents valid.")
    else:
        click.echo(f"\n{total_errors} error(s) found.")
        sys.exit(1)


# --- Helpers ---


def _parse_extra_args(args: list[str]) -> dict:
    """Parse ['--field', 'value', ...] into a dict. Repeated keys become lists."""
    result = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            key = arg[2:].replace("-", "_")
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                value = _coerce_cli_value(args[i + 1])
                if key in result:
                    # Accumulate into list
                    if isinstance(result[key], list):
                        result[key].append(value)
                    else:
                        result[key] = [result[key], value]
                else:
                    result[key] = value
                i += 2
            else:
                result[key] = True
                i += 1
        else:
            i += 1
    return result


def _coerce_cli_value(value: str):
    """Try to coerce CLI string value to appropriate Python type."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


if __name__ == "__main__":
    main()
