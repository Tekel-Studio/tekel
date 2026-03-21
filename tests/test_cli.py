import os
import yaml
from click.testing import CliRunner
from tekeldb.cli import main


def test_init_creates_structure(tmp_path):
    runner = CliRunner()
    os.chdir(tmp_path)
    result = runner.invoke(main, ["init", "--schema", "pm"])
    assert result.exit_code == 0
    assert (tmp_path / ".tekeldb").is_dir()
    assert (tmp_path / ".tekeldb" / "schema.yaml").exists()
    assert (tmp_path / ".tekeldb" / "config.yaml").exists()
    assert (tmp_path / ".tekeldb" / "counters.yaml").exists()
    assert (tmp_path / ".tekeldb" / "data" / "tasks").is_dir()
    assert (tmp_path / ".tekeldb" / "data" / "milestones").is_dir()
    assert (tmp_path / ".tekeldb" / "data" / "contacts").is_dir()


def test_init_schema_free(tmp_path):
    runner = CliRunner()
    os.chdir(tmp_path)
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / ".tekeldb").is_dir()


def test_init_already_exists(db, runner):
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_create_and_show(db, runner):
    result = runner.invoke(main, ["create", "tasks", "Test task", "--priority", "high"])
    assert result.exit_code == 0
    assert "TASK-0001" in result.output

    result = runner.invoke(main, ["show", "TASK-0001"])
    assert result.exit_code == 0
    assert "Test task" in result.output
    assert "high" in result.output


def test_create_applies_defaults(db, runner):
    runner.invoke(main, ["create", "tasks", "Default test"])
    result = runner.invoke(main, ["show", "TASK-0001"])
    assert "open" in result.output  # default status
    assert "medium" in result.output  # default priority


def test_create_sequential_ids(db, runner):
    runner.invoke(main, ["create", "tasks", "First"])
    runner.invoke(main, ["create", "tasks", "Second"])
    runner.invoke(main, ["create", "tasks", "Third"])
    result = runner.invoke(main, ["list", "tasks", "--format", "json"])
    assert "TASK-0001" in result.output
    assert "TASK-0002" in result.output
    assert "TASK-0003" in result.output


def test_list_all(db, runner):
    runner.invoke(main, ["create", "tasks", "Task A"])
    runner.invoke(main, ["create", "tasks", "Task B"])
    result = runner.invoke(main, ["list", "tasks"])
    assert result.exit_code == 0
    assert "Task A" in result.output
    assert "Task B" in result.output


def test_list_with_filter(db, runner):
    runner.invoke(main, ["create", "tasks", "High task", "--priority", "high"])
    runner.invoke(main, ["create", "tasks", "Low task", "--priority", "low"])
    result = runner.invoke(main, ["list", "tasks", "priority:high"])
    assert "High task" in result.output
    assert "Low task" not in result.output


def test_list_not_equal_filter(db, runner):
    runner.invoke(main, ["create", "tasks", "Done task", "--status", "done"])
    runner.invoke(main, ["create", "tasks", "Open task"])
    result = runner.invoke(main, ["list", "tasks", "status:!done"])
    assert "Open task" in result.output
    assert "Done task" not in result.output


def test_list_contains_filter(db, runner):
    runner.invoke(main, ["create", "tasks", "Design landing page"])
    runner.invoke(main, ["create", "tasks", "Fix bug"])
    result = runner.invoke(main, ["list", "tasks", "title:~landing"])
    assert "Design landing page" in result.output
    assert "Fix bug" not in result.output


def test_list_sort(db, runner):
    runner.invoke(main, ["create", "tasks", "A task", "--priority", "low"])
    runner.invoke(main, ["create", "tasks", "B task", "--priority", "high"])
    result = runner.invoke(main, ["list", "tasks", "--sort", "priority", "--format", "json"])
    assert result.exit_code == 0


def test_list_limit(db, runner):
    for i in range(5):
        runner.invoke(main, ["create", "tasks", f"Task {i}"])
    result = runner.invoke(main, ["list", "tasks", "--limit", "2", "--format", "json"])
    import json
    docs = json.loads(result.output)
    assert len(docs) == 2


def test_list_format_json(db, runner):
    runner.invoke(main, ["create", "tasks", "JSON test"])
    result = runner.invoke(main, ["list", "tasks", "--format", "json"])
    import json
    docs = json.loads(result.output)
    assert len(docs) == 1
    assert docs[0]["title"] == "JSON test"


def test_list_format_csv(db, runner):
    runner.invoke(main, ["create", "tasks", "CSV test"])
    result = runner.invoke(main, ["list", "tasks", "--format", "csv"])
    assert "CSV test" in result.output
    assert "id" in result.output.lower()


def test_edit(db, runner):
    runner.invoke(main, ["create", "tasks", "Edit me"])
    result = runner.invoke(main, ["edit", "TASK-0001", "--status", "in-progress"])
    assert result.exit_code == 0
    assert "Updated" in result.output

    result = runner.invoke(main, ["show", "TASK-0001"])
    assert "in-progress" in result.output


def test_edit_invalid_transition(db, runner):
    runner.invoke(main, ["create", "tasks", "Transition test"])
    # open -> in-progress is valid
    runner.invoke(main, ["edit", "TASK-0001", "--status", "in-progress"])
    # in-progress -> done is NOT valid (must go through review)
    result = runner.invoke(main, ["edit", "TASK-0001", "--status", "done"])
    assert result.exit_code == 1
    assert "Invalid transition" in result.output


def test_edit_no_fields(db, runner):
    runner.invoke(main, ["create", "tasks", "No edit"])
    result = runner.invoke(main, ["edit", "TASK-0001"])
    assert result.exit_code == 1


def test_delete(db, runner):
    runner.invoke(main, ["create", "tasks", "Delete me"])
    result = runner.invoke(main, ["delete", "TASK-0001", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output

    result = runner.invoke(main, ["show", "TASK-0001"])
    assert result.exit_code == 1


def test_delete_not_found(db, runner):
    result = runner.invoke(main, ["delete", "TASK-9999", "--yes"])
    assert result.exit_code == 1


def test_validate_all_valid(db, runner):
    runner.invoke(main, ["create", "tasks", "Valid task"])
    result = runner.invoke(main, ["validate"])
    assert result.exit_code == 0
    assert "All documents valid" in result.output


def test_validate_catches_invalid(db, runner):
    runner.invoke(main, ["create", "tasks", "Bad task"])
    # Manually break the document
    doc_path = db / ".tekeldb" / "data" / "tasks" / "TASK-0001.yaml"
    doc = yaml.safe_load(doc_path.read_text())
    doc["status"] = "invalid_status"
    with open(doc_path, "w") as f:
        yaml.safe_dump(doc, f)

    result = runner.invoke(main, ["validate"])
    assert result.exit_code == 1
    assert "not in" in result.output


def test_status(db, runner):
    runner.invoke(main, ["create", "tasks", "Status test"])
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "project-management" in result.output
    assert "tasks: 1 document" in result.output


def test_schema_show(db, runner):
    result = runner.invoke(main, ["schema", "show"])
    assert result.exit_code == 0
    assert "collections" in result.output
    assert "tasks" in result.output


def test_show_not_found(db, runner):
    result = runner.invoke(main, ["show", "TASK-9999"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_create_invalid_enum(db, runner):
    result = runner.invoke(main, ["create", "tasks", "Bad enum", "--priority", "mega"])
    assert result.exit_code == 1
    assert "not in" in result.output


def test_contacts_collection(db, runner):
    result = runner.invoke(main, ["create", "contacts", "Elif Yilmaz", "--email", "elif@co.com", "--company", "Acme"])
    assert result.exit_code == 0
    assert "CONT-0001" in result.output

    result = runner.invoke(main, ["show", "CONT-0001"])
    assert "Elif Yilmaz" in result.output
