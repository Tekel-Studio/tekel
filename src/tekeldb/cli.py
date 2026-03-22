import shutil
import sys
from pathlib import Path

import click
import yaml

from . import __version__
from .config import DEFAULT_CONFIG, find_db, load_config, write_config
from .schema import (
    get_collection_def,
    load_schema,
    validate_document,
    validate_refs,
)
from .document import (
    apply_defaults,
    doc_path,
    read_document,
    write_document,
)
from .collection import (
    collection_dir,
    ensure_collection_dir,
    find_document_by_id,
    list_documents,
)
from .query import match_document, parse_filter, sort_documents, text_search
from .formatter import (
    format_csv_output,
    format_json_output,
    format_single,
    format_table,
    format_validation_json,
    format_validation_junit,
    format_yaml_output,
    get_display_fields,
)


BUILTIN_SCHEMAS = {
    "pm": "pm.yaml",
}


@click.group()
@click.version_option(__version__, prog_name="tekeldb")
def main():
    """tekeldb — Schema validation and query engine for flat-file YAML data."""
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


@schema.command("add-collection")
@click.argument("name")
@click.option("--id-prefix", default=None, help="ID prefix for documents in this collection.")
def schema_add_collection(name, id_prefix):
    """Add a new collection to the schema."""
    db_path = find_db()
    schema_file = db_path / "schema.yaml"
    schema_data = yaml.safe_load(schema_file.read_text()) or {}

    if "collections" not in schema_data:
        schema_data["collections"] = {}

    if name in schema_data["collections"]:
        click.echo(f"Error: Collection '{name}' already exists.", err=True)
        sys.exit(1)

    col_def = {"fields": {}}
    if id_prefix:
        col_def["id_prefix"] = id_prefix

    schema_data["collections"][name] = col_def
    with open(schema_file, "w") as f:
        yaml.safe_dump(schema_data, f, default_flow_style=False, sort_keys=False)

    ensure_collection_dir(db_path, name)
    click.echo(f"Added collection '{name}'")


@schema.command("add-field")
@click.argument("collection")
@click.argument("field_name")
@click.argument("field_type")
@click.option("--required", is_flag=True, help="Make field required.")
@click.option("--default", "default_val", default=None, help="Default value.")
@click.option("--values", default=None, help="Comma-separated enum values.")
@click.option("--min", "min_val", type=int, default=None, help="Minimum value.")
@click.option("--max", "max_val", type=int, default=None, help="Maximum value.")
def schema_add_field(collection, field_name, field_type, required, default_val, values, min_val, max_val):
    """Add a field to a collection's schema."""
    db_path = find_db()
    schema_file = db_path / "schema.yaml"
    schema_data = yaml.safe_load(schema_file.read_text()) or {}

    collections = schema_data.get("collections", {})
    if collection not in collections:
        click.echo(f"Error: Collection '{collection}' not found.", err=True)
        sys.exit(1)

    field_def = {"type": field_type}
    if required:
        field_def["required"] = True
    if default_val is not None:
        field_def["default"] = default_val
    if values:
        field_def["values"] = [v.strip() for v in values.split(",")]
    if min_val is not None:
        field_def["min"] = min_val
    if max_val is not None:
        field_def["max"] = max_val

    collections[collection].setdefault("fields", {})[field_name] = field_def
    with open(schema_file, "w") as f:
        yaml.safe_dump(schema_data, f, default_flow_style=False, sort_keys=False)

    click.echo(f"Added field '{field_name}' ({field_type}) to '{collection}'")


@schema.command("migrate")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
@click.option("--prune", is_flag=True, help="Remove fields not in schema.")
def schema_migrate(dry_run, yes, prune):
    """Apply schema changes to existing documents."""
    from .migrate import compute_migrations, apply_migrations

    db_path = find_db()
    schema_data = load_schema(db_path)
    if not schema_data:
        click.echo("No schema defined. Nothing to migrate.")
        return

    actions = compute_migrations(schema_data, db_path)
    if not actions:
        click.echo("No migrations needed. All documents match the schema.")
        return

    fixable = [a for a in actions if a.fixable and (a.type != "prune_field" or prune)]
    unfixable = [a for a in actions if not a.fixable or (a.type == "prune_field" and not prune)]

    click.echo(f"Found {len(actions)} migration action(s):")
    for action in actions:
        marker = "[fix]" if action in fixable else "[manual]"
        click.echo(f"  {marker} {action.description}")

    if dry_run:
        click.echo(f"\nDry run: {len(fixable)} fixable, {len(unfixable)} need manual attention.")
        return

    if not fixable:
        click.echo(f"\nNo auto-fixable actions. {len(unfixable)} need manual attention.")
        sys.exit(1)

    if not yes:
        click.confirm(f"\nApply {len(fixable)} fixable migration(s)?", abort=True)

    applied, skipped = apply_migrations(actions, db_path, prune=prune)
    click.echo(f"\nMigration complete: {applied} applied, {skipped} skipped.")
    if unfixable:
        click.echo(f"{len(unfixable)} issue(s) need manual attention.")
        sys.exit(1)


# --- Read operations ---


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


def _execute_query(db_path, schema, collection, filters=None, sort_field=None, fmt="table", limit=0):
    """Shared query logic for list and view commands. Returns formatted output string."""
    col_def = get_collection_def(schema, collection) if schema else None
    docs = list_documents(db_path, collection)

    if filters:
        parsed_filters = [parse_filter(f) for f in filters]
        docs = [d for d in docs if match_document(d, parsed_filters)]

    if sort_field:
        docs = sort_documents(docs, sort_field)

    if limit and limit > 0:
        docs = docs[:limit]

    fields = get_display_fields(col_def) if col_def else None
    if fmt == "table":
        return format_table(docs, fields)
    elif fmt == "yaml":
        return format_yaml_output(docs)
    elif fmt == "json":
        return format_json_output(docs)
    elif fmt == "csv":
        return format_csv_output(docs, fields)
    return format_table(docs, fields)


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
    click.echo(_execute_query(db_path, schema, collection, filters, sort_field, fmt, limit))


@main.command()
@click.argument("collection")
@click.argument("filters", nargs=-1)
@click.option("--group-by", default=None, help="Aggregate counts by field value.")
def count(collection, filters, group_by):
    """Count documents in a collection."""
    db_path = find_db()
    schema = load_schema(db_path)
    docs = list_documents(db_path, collection)

    if filters:
        parsed_filters = [parse_filter(f) for f in filters]
        docs = [d for d in docs if match_document(d, parsed_filters)]

    if group_by:
        groups = {}
        for doc in docs:
            key = str(doc.get(group_by, "unknown"))
            groups[key] = groups.get(key, 0) + 1
        for key, cnt in sorted(groups.items()):
            click.echo(f"  {key}: {cnt}")
        click.echo(f"\nTotal: {len(docs)}")
    else:
        click.echo(len(docs))


@main.command()
@click.argument("text")
@click.option("--collection", default=None, help="Limit search to one collection.")
@click.option("--format", "fmt", default="table", type=click.Choice(["table", "yaml", "json"]))
def find(text, collection, fmt):
    """Full-text search across documents."""
    db_path = find_db()
    schema = load_schema(db_path)

    if collection:
        collections_to_search = [collection]
    elif schema:
        collections_to_search = list(schema.get("collections", {}).keys())
    else:
        data_dir = db_path / "data"
        collections_to_search = [d.name for d in data_dir.iterdir() if d.is_dir()] if data_dir.exists() else []

    matching_docs = []
    for col_name in collections_to_search:
        col_def = get_collection_def(schema, col_name) if schema else None
        schema_fields = col_def.get("fields", {}) if col_def else None
        docs = list_documents(db_path, col_name)
        for doc in docs:
            if text_search(doc, text, schema_fields):
                matching_docs.append(doc)

    if not matching_docs:
        click.echo("No matches found.")
        return

    col_def = get_collection_def(schema, collections_to_search[0]) if schema and len(collections_to_search) == 1 else None
    fields = get_display_fields(col_def) if col_def else None
    if fmt == "table":
        click.echo(format_table(matching_docs, fields))
    elif fmt == "yaml":
        click.echo(format_yaml_output(matching_docs))
    elif fmt == "json":
        click.echo(format_json_output(matching_docs))


@main.command()
@click.option("--collection", default=None, help="Export only this collection.")
@click.option("--format", "fmt", default="yaml", type=click.Choice(["yaml", "json", "csv"]))
@click.option("--output", "output_path", default=None, type=click.Path(), help="Write to file instead of stdout.")
def export(collection, fmt, output_path):
    """Export documents from the database."""
    db_path = find_db()
    schema = load_schema(db_path)

    if collection:
        collections_to_export = [collection]
    elif schema:
        collections_to_export = list(schema.get("collections", {}).keys())
    else:
        data_dir = db_path / "data"
        collections_to_export = [d.name for d in data_dir.iterdir() if d.is_dir()] if data_dir.exists() else []

    all_docs = []
    for col_name in collections_to_export:
        all_docs.extend(list_documents(db_path, col_name))

    if not all_docs:
        click.echo("No documents to export.")
        return

    col_def = get_collection_def(schema, collections_to_export[0]) if schema and len(collections_to_export) == 1 else None
    fields = get_display_fields(col_def) if col_def else None

    if fmt == "yaml":
        output = format_yaml_output(all_docs)
    elif fmt == "json":
        output = format_json_output(all_docs)
    elif fmt == "csv":
        output = format_csv_output(all_docs, fields)
    else:
        output = format_yaml_output(all_docs)

    if output_path:
        Path(output_path).write_text(output)
        click.echo(f"Exported {len(all_docs)} documents to {output_path}")
    else:
        click.echo(output)


@main.command()
@click.argument("doc_id")
@click.option("--reverse", is_flag=True, help="Show only incoming references.")
def deps(doc_id, reverse):
    """Show document dependencies and references."""
    from .deps import get_forward_refs, get_reverse_refs, format_deps_output

    db_path = find_db()
    schema = load_schema(db_path)
    result = find_document_by_id(db_path, schema, doc_id)
    if result is None:
        click.echo(f"Error: Document '{doc_id}' not found.", err=True)
        sys.exit(1)

    _, doc = result

    if schema:
        # Find collection def for this doc
        parts = doc_id.split("-", 1)
        from .schema import get_collection_by_prefix
        col_result = get_collection_by_prefix(schema, parts[0]) if len(parts) >= 2 else None
        col_def = col_result[1] if col_result else {}
    else:
        col_def = {}

    forward = [] if reverse else get_forward_refs(doc, col_def)
    reverse_refs = get_reverse_refs(doc_id, schema, db_path) if schema else []

    click.echo(format_deps_output(doc, forward, reverse_refs))


# --- Views ---


@main.group()
def view():
    """Manage and run saved views."""
    pass


@view.command("run")
@click.argument("name")
@click.option("--format", "fmt", default=None, type=click.Choice(["table", "yaml", "json", "csv"]))
def view_run(name, fmt):
    """Run a saved view."""
    from .views import get_view
    db_path = find_db()
    schema = load_schema(db_path)
    view_def = get_view(db_path, name)
    if view_def is None:
        click.echo(f"Error: View '{name}' not found.", err=True)
        sys.exit(1)

    out_fmt = fmt or view_def.get("format", "table")
    click.echo(_execute_query(
        db_path, schema,
        collection=view_def["collection"],
        filters=view_def.get("filters"),
        sort_field=view_def.get("sort"),
        fmt=out_fmt,
        limit=view_def.get("limit", 0),
    ))


@view.command("list")
def view_list():
    """List all saved views."""
    from .views import load_views
    db_path = find_db()
    views = load_views(db_path)
    if not views:
        click.echo("No saved views.")
        return
    for name, view_def in views.items():
        desc = view_def.get("description", "")
        col = view_def.get("collection", "")
        click.echo(f"  {name}: {desc}" if desc else f"  {name} ({col})")


@view.command("save")
@click.argument("name")
@click.argument("query")
def view_save(name, query):
    """Save a query as a named view."""
    from .views import add_view, parse_view_from_command
    db_path = find_db()
    view_def = parse_view_from_command(query)
    add_view(db_path, name, view_def)
    click.echo(f"Saved view '{name}'")


@view.command("show")
@click.argument("name")
def view_show_cmd(name):
    """Show a view definition."""
    from .views import get_view
    db_path = find_db()
    view_def = get_view(db_path, name)
    if view_def is None:
        click.echo(f"Error: View '{name}' not found.", err=True)
        sys.exit(1)
    click.echo(yaml.safe_dump(view_def, default_flow_style=False, sort_keys=False).strip())


@view.command("delete")
@click.argument("name")
def view_delete(name):
    """Delete a saved view."""
    from .views import delete_view
    db_path = find_db()
    if delete_view(db_path, name):
        click.echo(f"Deleted view '{name}'")
    else:
        click.echo(f"Error: View '{name}' not found.", err=True)
        sys.exit(1)


# --- Git hooks ---


@main.group()
def hook():
    """Git hook management."""
    pass


@hook.command("install")
def hook_install():
    """Install the tekeldb pre-commit hook."""
    from .hooks import install_hook
    try:
        path = install_hook()
        click.echo(f"Installed pre-commit hook at {path}")
    except (FileNotFoundError, FileExistsError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@hook.command("uninstall")
def hook_uninstall():
    """Remove the tekeldb pre-commit hook."""
    from .hooks import uninstall_hook
    try:
        uninstall_hook()
        click.echo("Removed pre-commit hook.")
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# --- Validation ---


@main.command()
@click.option("--collection", default=None, help="Validate only this collection.")
@click.option("--fix", is_flag=True, help="Auto-fix fixable issues (apply defaults).")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json", "junit"]))
@click.option("--files", multiple=True, type=click.Path(), help="Validate specific files only.")
def validate(collection, fix, fmt, files):
    """Validate documents against the schema."""
    db_path = find_db()
    schema = load_schema(db_path)
    config = load_config(db_path)

    if not schema:
        click.echo("No schema defined. Nothing to validate.")
        return

    # If --files is provided, validate only those specific files
    if files:
        total_errors = 0
        results = []
        for file_path in files:
            fp = Path(file_path)
            if not fp.exists():
                click.echo(f"Warning: File not found: {file_path}", err=True)
                continue
            doc = read_document(fp)
            doc_id = doc.get("id", fp.stem)

            # Determine collection from path
            col_name = fp.parent.name
            try:
                col_def = get_collection_def(schema, col_name)
            except KeyError:
                click.echo(f"Warning: Collection '{col_name}' not in schema, skipping {file_path}", err=True)
                continue

            errors = validate_document(doc, col_def)
            errors.extend(validate_refs(doc, col_def, db_path))

            if fmt == "text" and errors:
                total_errors += len(errors)
                click.echo(f"{doc_id}:")
                for e in errors:
                    click.echo(f"  - {e}")

            results.append({"collection": col_name, "files": [{"id": doc_id, "errors": errors}]})

        if fmt == "json":
            click.echo(format_validation_json(results))
            if any(e for r in results for f in r["files"] for e in f["errors"]):
                sys.exit(1)
        elif fmt == "junit":
            click.echo(format_validation_junit(results))
            if any(e for r in results for f in r["files"] for e in f["errors"]):
                sys.exit(1)
        elif fmt == "text":
            if total_errors == 0:
                click.echo("All documents valid.")
            else:
                click.echo(f"\n{total_errors} error(s) found.")
                sys.exit(1)
        return

    # Standard validation: walk collections
    collections_to_check = [collection] if collection else list(schema.get("collections", {}).keys())
    total_errors = 0
    results = []

    for col_name in collections_to_check:
        col_def = get_collection_def(schema, col_name)
        if col_def is None:
            click.echo(f"Warning: Collection '{col_name}' not found in schema.", err=True)
            continue

        col_results = {"collection": col_name, "files": []}
        docs = list_documents(db_path, col_name)
        for doc in docs:
            doc_id = doc.get("id", "unknown")
            errors = validate_document(doc, col_def)
            errors.extend(validate_refs(doc, col_def, db_path))

            if errors and fix:
                fixed_doc = apply_defaults(dict(doc), col_def)
                remaining_errors = validate_document(fixed_doc, col_def)
                if len(remaining_errors) < len(errors):
                    path = doc_path(db_path, col_name, doc_id, config.get("format", "yaml"))
                    write_document(path, fixed_doc, config.get("format", "yaml"))
                    if fmt == "text":
                        click.echo(f"  Fixed {doc_id}: applied defaults")
                    errors = remaining_errors

            col_results["files"].append({"id": doc_id, "errors": errors})

            if fmt == "text" and errors:
                total_errors += len(errors)
                click.echo(f"{doc_id}:")
                for e in errors:
                    click.echo(f"  - {e}")

        results.append(col_results)

    if fmt == "json":
        click.echo(format_validation_json(results))
        if any(e for r in results for f in r["files"] for e in f["errors"]):
            sys.exit(1)
    elif fmt == "junit":
        click.echo(format_validation_junit(results))
        if any(e for r in results for f in r["files"] for e in f["errors"]):
            sys.exit(1)
    elif fmt == "text":
        if total_errors == 0:
            click.echo("All documents valid.")
        else:
            click.echo(f"\n{total_errors} error(s) found.")
            sys.exit(1)


if __name__ == "__main__":
    main()
