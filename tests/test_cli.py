import json
import os
from click.testing import CliRunner
from tekel.cli import main


# --- Init ---


def test_init_creates_structure(tmp_path):
    runner = CliRunner()
    os.chdir(tmp_path)
    result = runner.invoke(main, ["init", "--schema", "pm"])
    assert result.exit_code == 0
    assert (tmp_path / ".tekel").is_dir()
    assert (tmp_path / ".tekel" / "schema.json").exists()
    assert (tmp_path / ".tekel" / "config.json").exists()
    assert (tmp_path / ".tekel" / "data" / "tasks").is_dir()
    assert (tmp_path / ".tekel" / "data" / "milestones").is_dir()
    assert (tmp_path / ".tekel" / "data" / "contacts").is_dir()


def test_init_schema_free(tmp_path):
    runner = CliRunner()
    os.chdir(tmp_path)
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / ".tekel").is_dir()


def test_init_already_exists(db, runner):
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 1
    assert "already exists" in result.output


# --- Show ---


def test_show(db, runner):
    result = runner.invoke(main, ["show", "TASK-0001"])
    assert result.exit_code == 0
    assert "Design landing page" in result.output
    assert "high" in result.output


def test_show_not_found(db, runner):
    result = runner.invoke(main, ["show", "TASK-9999"])
    assert result.exit_code == 1
    assert "not found" in result.output


# --- List ---


def test_list_all(db, runner):
    result = runner.invoke(main, ["list", "tasks"])
    assert result.exit_code == 0
    assert "Design landing page" in result.output
    assert "Fix login bug" in result.output
    assert "Write tests" in result.output


def test_list_with_filter(db, runner):
    result = runner.invoke(main, ["list", "tasks", "priority:high"])
    assert "Design landing page" in result.output
    assert "Fix login bug" not in result.output


def test_list_not_equal_filter(db, runner):
    result = runner.invoke(main, ["list", "tasks", "status:!done"])
    assert "Design landing page" in result.output
    assert "Write tests" not in result.output


def test_list_contains_filter(db, runner):
    result = runner.invoke(main, ["list", "tasks", "title:~landing"])
    assert "Design landing page" in result.output
    assert "Fix login bug" not in result.output


def test_list_sort(db, runner):
    result = runner.invoke(main, ["list", "tasks", "--sort", "priority", "--format", "json"])
    assert result.exit_code == 0


def test_list_limit(db, runner):
    result = runner.invoke(main, ["list", "tasks", "--limit", "2", "--format", "json"])
    docs = json.loads(result.output)
    assert len(docs) == 2


def test_list_format_json(db, runner):
    result = runner.invoke(main, ["list", "tasks", "--format", "json"])
    docs = json.loads(result.output)
    assert len(docs) == 3
    titles = [d["title"] for d in docs]
    assert "Design landing page" in titles


def test_list_format_csv(db, runner):
    result = runner.invoke(main, ["list", "tasks", "--format", "csv"])
    assert "Design landing page" in result.output
    assert "id" in result.output.lower()


# --- Validate ---


def test_validate_all_valid(db, runner):
    result = runner.invoke(main, ["validate"])
    assert result.exit_code == 0
    assert "All documents valid" in result.output


def test_validate_catches_invalid(db, runner):
    doc_path = db / ".tekel" / "data" / "tasks" / "TASK-0001.json"
    doc = json.loads(doc_path.read_text())
    doc["status"] = "invalid_status"
    with open(doc_path, "w") as f:
        json.dump(doc, f, indent=2)

    result = runner.invoke(main, ["validate"])
    assert result.exit_code == 1
    assert "not in" in result.output


def test_validate_fix(db, runner):
    # Remove the status field (has a default of "open")
    doc_path = db / ".tekel" / "data" / "tasks" / "TASK-0001.json"
    doc = json.loads(doc_path.read_text())
    del doc["status"]
    with open(doc_path, "w") as f:
        json.dump(doc, f, indent=2)

    result = runner.invoke(main, ["validate", "--fix"])
    assert "Fixed" in result.output

    # Verify the fix was applied
    doc = json.loads(doc_path.read_text())
    assert doc["status"] == "open"


# --- Status ---


def test_status(db, runner):
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "project-management" in result.output
    assert "tasks: 3 documents" in result.output


# --- Schema ---


def test_schema_show(db, runner):
    result = runner.invoke(main, ["schema", "show"])
    assert result.exit_code == 0
    assert "collections" in result.output
    assert "tasks" in result.output


# --- Additional fields & any type ---


def test_additional_fields_allowed_by_default(db, runner):
    """Extra fields not in schema should be allowed by default."""
    result = runner.invoke(main, ["validate"])
    # Add an extra field to a doc
    doc_path = db / ".tekel" / "data" / "tasks" / "TASK-0001.json"
    doc = json.loads(doc_path.read_text())
    doc["custom_note"] = "this is extra"
    with open(doc_path, "w") as f:
        json.dump(doc, f, indent=2)

    result = runner.invoke(main, ["validate"])
    assert result.exit_code == 0


def test_additional_fields_rejected(db, runner):
    """When additional_fields is false, extra fields should be rejected."""
    # Modify the schema to set additional_fields: false on tasks
    schema_path = db / ".tekel" / "schema.json"
    schema = json.loads(schema_path.read_text())
    schema["collections"]["tasks"]["additional_fields"] = False
    with open(schema_path, "w") as f:
        json.dump(schema, f, indent=2)

    # Add an unknown field
    doc_path = db / ".tekel" / "data" / "tasks" / "TASK-0001.json"
    doc = json.loads(doc_path.read_text())
    doc["unknown_field"] = "should fail"
    with open(doc_path, "w") as f:
        json.dump(doc, f, indent=2)

    result = runner.invoke(main, ["validate"])
    assert result.exit_code == 1
    assert "Unknown field" in result.output


# --- CRUD commands should not exist ---


def test_create_command_removed(db, runner):
    result = runner.invoke(main, ["create", "tasks", "Test"])
    assert result.exit_code != 0


def test_edit_command_removed(db, runner):
    result = runner.invoke(main, ["edit", "TASK-0001"])
    assert result.exit_code != 0


def test_delete_command_removed(db, runner):
    result = runner.invoke(main, ["delete", "TASK-0001"])
    assert result.exit_code != 0


# --- Phase 2: count ---


def test_count_all(db, runner):
    result = runner.invoke(main, ["count", "tasks"])
    assert result.exit_code == 0
    assert "3" in result.output


def test_count_filtered(db, runner):
    result = runner.invoke(main, ["count", "tasks", "status:open"])
    assert result.exit_code == 0
    assert "2" in result.output


def test_count_group_by(db, runner):
    result = runner.invoke(main, ["count", "tasks", "--group-by", "status"])
    assert result.exit_code == 0
    assert "open" in result.output
    assert "done" in result.output
    assert "Total" in result.output


# --- Phase 2: find ---


def test_find_matches(db, runner):
    result = runner.invoke(main, ["find", "landing"])
    assert result.exit_code == 0
    assert "Design landing page" in result.output


def test_find_no_match(db, runner):
    result = runner.invoke(main, ["find", "nonexistent"])
    assert result.exit_code == 0
    assert "No matches" in result.output


def test_find_case_insensitive(db, runner):
    result = runner.invoke(main, ["find", "LANDING"])
    assert result.exit_code == 0
    assert "Design landing page" in result.output


def test_find_specific_collection(db, runner):
    result = runner.invoke(main, ["find", "Elif", "--collection", "contacts"])
    assert result.exit_code == 0
    assert "Elif" in result.output


# --- Phase 2: export ---


def test_export_json(db, runner):
    result = runner.invoke(main, ["export", "--collection", "tasks", "--format", "json"])
    assert result.exit_code == 0
    docs = json.loads(result.output)
    assert len(docs) == 3


def test_export_csv(db, runner):
    result = runner.invoke(main, ["export", "--collection", "tasks", "--format", "csv"])
    assert result.exit_code == 0
    assert "id" in result.output.lower()


def test_export_to_file(db, runner):
    out_path = str(db / "export.json")
    result = runner.invoke(main, ["export", "--collection", "tasks", "--format", "json", "--output", out_path])
    assert result.exit_code == 0
    assert "Exported" in result.output
    data = json.loads((db / "export.json").read_text())
    assert len(data) == 3
