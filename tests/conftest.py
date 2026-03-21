import os
import pytest
from click.testing import CliRunner
from tekeldb.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db(tmp_path, runner):
    """Initialize a tekeldb with the PM schema in a temp directory."""
    os.chdir(tmp_path)
    result = runner.invoke(main, ["init", "--schema", "pm"])
    assert result.exit_code == 0
    return tmp_path
