import yaml
from click.testing import CliRunner
from tekel.cli import main


def _add_refs_to_docs(db):
    """Add reference fields to test documents."""
    # Add a milestone
    ms_dir = db / ".tekel" / "data" / "milestones"
    with open(ms_dir / "MS-0001.yaml", "w") as f:
        yaml.safe_dump({
            "id": "MS-0001",
            "title": "Q2 Launch",
            "status": "planned",
        }, f, sort_keys=False)

    # Update TASK-0001 to reference the milestone and block TASK-0002
    task_path = db / ".tekel" / "data" / "tasks" / "TASK-0001.yaml"
    doc = yaml.safe_load(task_path.read_text())
    doc["milestone"] = "MS-0001"
    doc["blocks"] = ["TASK-0002"]
    with open(task_path, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False)


def test_deps_forward(db, runner):
    _add_refs_to_docs(db)
    result = runner.invoke(main, ["deps", "TASK-0001"])
    assert result.exit_code == 0
    assert "MS-0001" in result.output
    assert "TASK-0002" in result.output
    assert "References:" in result.output


def test_deps_reverse(db, runner):
    _add_refs_to_docs(db)
    result = runner.invoke(main, ["deps", "MS-0001"])
    assert result.exit_code == 0
    assert "TASK-0001" in result.output
    assert "Referenced by:" in result.output


def test_deps_no_refs(db, runner):
    result = runner.invoke(main, ["deps", "TASK-0003"])
    assert result.exit_code == 0
    assert "none" in result.output.lower()


def test_deps_not_found(db, runner):
    result = runner.invoke(main, ["deps", "TASK-9999"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_deps_reverse_flag(db, runner):
    _add_refs_to_docs(db)
    result = runner.invoke(main, ["deps", "TASK-0002", "--reverse"])
    assert result.exit_code == 0
    assert "TASK-0001" in result.output
