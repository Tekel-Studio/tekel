import json
from click.testing import CliRunner
from tekel.cli import main
from tekel.views import parse_view_from_command


def test_view_save_and_run(db, runner):
    result = runner.invoke(main, ["view", "save", "open-tasks", "list tasks status:open"])
    assert result.exit_code == 0
    assert "Saved" in result.output

    result = runner.invoke(main, ["view", "run", "open-tasks"])
    assert result.exit_code == 0
    assert "Design landing page" in result.output
    assert "Write tests" not in result.output  # status=done


def test_view_save_with_sort(db, runner):
    runner.invoke(main, ["view", "save", "sorted", "list tasks --sort -priority"])
    result = runner.invoke(main, ["view", "run", "sorted", "--format", "json"])
    assert result.exit_code == 0
    docs = json.loads(result.output)
    assert len(docs) == 3


def test_view_list(db, runner):
    runner.invoke(main, ["view", "save", "v1", "list tasks status:open"])
    runner.invoke(main, ["view", "save", "v2", "list tasks status:done"])

    result = runner.invoke(main, ["view", "list"])
    assert result.exit_code == 0
    assert "v1" in result.output
    assert "v2" in result.output


def test_view_show(db, runner):
    runner.invoke(main, ["view", "save", "my-view", "list tasks status:open --sort -priority"])
    result = runner.invoke(main, ["view", "show", "my-view"])
    assert result.exit_code == 0
    assert "tasks" in result.output
    assert "status:open" in result.output


def test_view_delete(db, runner):
    runner.invoke(main, ["view", "save", "temp", "list tasks"])
    result = runner.invoke(main, ["view", "delete", "temp"])
    assert result.exit_code == 0
    assert "Deleted" in result.output

    result = runner.invoke(main, ["view", "run", "temp"])
    assert result.exit_code == 1


def test_view_not_found(db, runner):
    result = runner.invoke(main, ["view", "run", "nonexistent"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_parse_view_from_command():
    view_def = parse_view_from_command("list tasks status:open priority:high --sort -due --limit 10")
    assert view_def["collection"] == "tasks"
    assert view_def["filters"] == ["status:open", "priority:high"]
    assert view_def["sort"] == "-due"
    assert view_def["limit"] == 10


def test_parse_view_simple():
    view_def = parse_view_from_command("tasks")
    assert view_def["collection"] == "tasks"
    assert "filters" not in view_def
