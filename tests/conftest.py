import os
import pytest
from click.testing import CliRunner
from tekel.cli import main
import yaml


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db(tmp_path, runner):
    """Initialize a tekel with the PM schema and pre-populated sample docs."""
    os.chdir(tmp_path)
    result = runner.invoke(main, ["init", "--schema", "pm"])
    assert result.exit_code == 0

    db_path = tmp_path / ".tekel"
    _write_sample_docs(db_path)
    return tmp_path


def _write_yaml(path, data):
    with open(path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def _write_sample_docs(db_path):
    tasks_dir = db_path / "data" / "tasks"

    _write_yaml(tasks_dir / "TASK-0001.yaml", {
        "id": "TASK-0001",
        "title": "Design landing page",
        "status": "open",
        "priority": "high",
        "assignee": "elif",
        "tags": ["design", "website"],
    })
    _write_yaml(tasks_dir / "TASK-0002.yaml", {
        "id": "TASK-0002",
        "title": "Fix login bug",
        "status": "open",
        "priority": "critical",
        "assignee": "mehmet",
    })
    _write_yaml(tasks_dir / "TASK-0003.yaml", {
        "id": "TASK-0003",
        "title": "Write tests",
        "status": "done",
        "priority": "medium",
    })

    contacts_dir = db_path / "data" / "contacts"
    _write_yaml(contacts_dir / "CONT-0001.yaml", {
        "id": "CONT-0001",
        "name": "Elif Yilmaz",
        "email": "elif@co.com",
        "company": "Acme Corp",
    })
