import json
from click.testing import CliRunner
from tekel.cli import main


def test_add_collection(db, runner):
    result = runner.invoke(main, ["schema", "add-collection", "sprints", "--id-prefix", "SPR"])
    assert result.exit_code == 0
    assert "Added collection" in result.output

    # Verify schema updated
    schema = json.loads((db / ".tekel" / "schema.json").read_text())
    assert "sprints" in schema["collections"]
    assert schema["collections"]["sprints"]["id_prefix"] == "SPR"

    # Verify data directory created
    assert (db / ".tekel" / "data" / "sprints").is_dir()


def test_add_collection_already_exists(db, runner):
    result = runner.invoke(main, ["schema", "add-collection", "tasks"])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_add_field(db, runner):
    result = runner.invoke(main, ["schema", "add-field", "tasks", "estimate", "integer", "--min", "0", "--max", "100"])
    assert result.exit_code == 0
    assert "Added field" in result.output

    schema = json.loads((db / ".tekel" / "schema.json").read_text())
    field = schema["collections"]["tasks"]["fields"]["estimate"]
    assert field["type"] == "integer"
    assert field["min"] == 0
    assert field["max"] == 100


def test_add_field_required_with_default(db, runner):
    result = runner.invoke(main, ["schema", "add-field", "tasks", "team", "string", "--required", "--default", "core"])
    assert result.exit_code == 0

    schema = json.loads((db / ".tekel" / "schema.json").read_text())
    field = schema["collections"]["tasks"]["fields"]["team"]
    assert field["required"] is True
    assert field["default"] == "core"


def test_add_field_enum_with_values(db, runner):
    result = runner.invoke(main, ["schema", "add-field", "tasks", "size", "enum", "--values", "S,M,L,XL"])
    assert result.exit_code == 0

    schema = json.loads((db / ".tekel" / "schema.json").read_text())
    field = schema["collections"]["tasks"]["fields"]["size"]
    assert field["values"] == ["S", "M", "L", "XL"]


def test_add_field_unknown_collection(db, runner):
    result = runner.invoke(main, ["schema", "add-field", "nonexistent", "foo", "string"])
    assert result.exit_code == 1
    assert "not found" in result.output
