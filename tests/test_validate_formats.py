import json
import os
from xml.etree import ElementTree
from click.testing import CliRunner
from tekel.cli import main


def test_validate_json_output(db, runner):
    result = runner.invoke(main, ["validate", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    # All valid, so no errors in any file
    for col in data:
        for f in col["files"]:
            assert f["errors"] == []


def test_validate_json_with_errors(db, runner):
    doc_path = db / ".tekel" / "data" / "tasks" / "TASK-0001.json"
    doc = json.loads(doc_path.read_text())
    doc["status"] = "invalid"
    with open(doc_path, "w") as f:
        json.dump(doc, f, indent=2)

    result = runner.invoke(main, ["validate", "--format", "json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    # Find the tasks collection results
    tasks_result = [r for r in data if r["collection"] == "tasks"][0]
    task1 = [f for f in tasks_result["files"] if f["id"] == "TASK-0001"][0]
    assert len(task1["errors"]) > 0


def test_validate_junit_output(db, runner):
    result = runner.invoke(main, ["validate", "--format", "junit"])
    assert result.exit_code == 0
    root = ElementTree.fromstring(result.output)
    assert root.tag == "testsuites"
    suite = root.find("testsuite")
    assert suite.get("name") == "tekel"
    assert int(suite.get("failures")) == 0


def test_validate_junit_with_failures(db, runner):
    doc_path = db / ".tekel" / "data" / "tasks" / "TASK-0001.json"
    doc = json.loads(doc_path.read_text())
    doc["status"] = "bad"
    with open(doc_path, "w") as f:
        json.dump(doc, f, indent=2)

    result = runner.invoke(main, ["validate", "--format", "junit"])
    assert result.exit_code == 1
    root = ElementTree.fromstring(result.output)
    suite = root.find("testsuite")
    assert int(suite.get("failures")) > 0
    # Check failure element exists
    failures = root.findall(".//failure")
    assert len(failures) > 0


def test_validate_files_specific(db, runner):
    file_path = str(db / ".tekel" / "data" / "tasks" / "TASK-0001.json")
    result = runner.invoke(main, ["validate", "--files", file_path])
    assert result.exit_code == 0
    assert "All documents valid" in result.output


def test_validate_files_with_error(db, runner):
    doc_path = db / ".tekel" / "data" / "tasks" / "TASK-0001.json"
    doc = json.loads(doc_path.read_text())
    doc["status"] = "invalid"
    with open(doc_path, "w") as f:
        json.dump(doc, f, indent=2)

    result = runner.invoke(main, ["validate", "--files", str(doc_path)])
    assert result.exit_code == 1
    assert "not in" in result.output
