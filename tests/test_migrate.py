import yaml
from click.testing import CliRunner
from tekel.cli import main


def test_migrate_no_changes_needed(db, runner):
    result = runner.invoke(main, ["schema", "migrate", "--dry-run"])
    # With valid docs matching schema, there may be actions for missing default fields
    assert result.exit_code == 0


def test_migrate_adds_defaults(db, runner):
    # Add a new field with a default to the schema
    schema_path = db / ".tekel" / "schema.yaml"
    schema = yaml.safe_load(schema_path.read_text())
    schema["collections"]["tasks"]["fields"]["team"] = {"type": "string", "default": "core"}
    with open(schema_path, "w") as f:
        yaml.safe_dump(schema, f, default_flow_style=False, sort_keys=False)

    # Dry run first
    result = runner.invoke(main, ["schema", "migrate", "--dry-run"])
    assert "team" in result.output
    assert "fix" in result.output.lower()

    # Apply
    result = runner.invoke(main, ["schema", "migrate", "--yes"])
    assert result.exit_code == 0
    assert "applied" in result.output.lower()

    # Verify docs now have the field
    doc = yaml.safe_load((db / ".tekel" / "data" / "tasks" / "TASK-0001.yaml").read_text())
    assert doc["team"] == "core"


def test_migrate_flags_missing_required(db, runner):
    schema_path = db / ".tekel" / "schema.yaml"
    schema = yaml.safe_load(schema_path.read_text())
    schema["collections"]["tasks"]["fields"]["owner"] = {"type": "string", "required": True}
    with open(schema_path, "w") as f:
        yaml.safe_dump(schema, f, default_flow_style=False, sort_keys=False)

    result = runner.invoke(main, ["schema", "migrate", "--dry-run"])
    assert "manual" in result.output.lower()
    assert "owner" in result.output


def test_migrate_type_coercion(db, runner):
    # Add an integer field to schema
    schema_path = db / ".tekel" / "schema.yaml"
    schema = yaml.safe_load(schema_path.read_text())
    schema["collections"]["tasks"]["fields"]["points"] = {"type": "integer", "min": 0, "max": 100}
    with open(schema_path, "w") as f:
        yaml.safe_dump(schema, f, default_flow_style=False, sort_keys=False)

    # Write a doc with a string value for points
    doc_path = db / ".tekel" / "data" / "tasks" / "TASK-0001.yaml"
    doc = yaml.safe_load(doc_path.read_text())
    doc["points"] = "42"
    with open(doc_path, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)

    result = runner.invoke(main, ["schema", "migrate", "--yes"])
    assert result.exit_code == 0

    # Verify coercion
    doc = yaml.safe_load(doc_path.read_text())
    assert doc["points"] == 42
    assert isinstance(doc["points"], int)


def test_migrate_prune(db, runner):
    # Set additional_fields to false
    schema_path = db / ".tekel" / "schema.yaml"
    schema = yaml.safe_load(schema_path.read_text())
    schema["collections"]["tasks"]["additional_fields"] = False
    with open(schema_path, "w") as f:
        yaml.safe_dump(schema, f, default_flow_style=False, sort_keys=False)

    # Add unknown field to doc
    doc_path = db / ".tekel" / "data" / "tasks" / "TASK-0001.yaml"
    doc = yaml.safe_load(doc_path.read_text())
    doc["junk_field"] = "remove me"
    with open(doc_path, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)

    # Without --prune, it should be skipped
    result = runner.invoke(main, ["schema", "migrate", "--dry-run"])
    assert "junk_field" in result.output

    # With --prune, it should be removed
    result = runner.invoke(main, ["schema", "migrate", "--prune", "--yes"])
    assert result.exit_code == 0

    doc = yaml.safe_load(doc_path.read_text())
    assert "junk_field" not in doc


def test_migrate_creates_collection_dir(db, runner):
    # Add a new collection to schema
    schema_path = db / ".tekel" / "schema.yaml"
    schema = yaml.safe_load(schema_path.read_text())
    schema["collections"]["sprints"] = {"id_prefix": "SPR", "fields": {}}
    with open(schema_path, "w") as f:
        yaml.safe_dump(schema, f, default_flow_style=False, sort_keys=False)

    result = runner.invoke(main, ["schema", "migrate", "--yes"])
    assert result.exit_code == 0
    assert (db / ".tekel" / "data" / "sprints").is_dir()


def test_migrate_backup(db, runner):
    # Add field with default
    schema_path = db / ".tekel" / "schema.yaml"
    schema = yaml.safe_load(schema_path.read_text())
    schema["collections"]["tasks"]["fields"]["team"] = {"type": "string", "default": "core"}
    with open(schema_path, "w") as f:
        yaml.safe_dump(schema, f, default_flow_style=False, sort_keys=False)

    runner.invoke(main, ["schema", "migrate", "--yes"])

    # Verify backup exists
    backup_dir = db / ".tekel" / ".migrate-backup"
    assert backup_dir.exists()
    backup_files = list(backup_dir.iterdir())
    assert len(backup_files) > 0
