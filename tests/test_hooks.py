import os
from pathlib import Path
from click.testing import CliRunner
from tekeldb.cli import main
from tekeldb.hooks import install_hook, uninstall_hook, is_hook_installed


def test_hook_install(db, runner):
    # Create a .git directory
    git_dir = db / ".git" / "hooks"
    git_dir.mkdir(parents=True)

    result = runner.invoke(main, ["hook", "install"])
    assert result.exit_code == 0
    assert "Installed" in result.output

    hook_path = db / ".git" / "hooks" / "pre-commit"
    assert hook_path.exists()
    content = hook_path.read_text()
    assert "tekeldb" in content


def test_hook_uninstall(db, runner):
    git_dir = db / ".git" / "hooks"
    git_dir.mkdir(parents=True)

    runner.invoke(main, ["hook", "install"])
    result = runner.invoke(main, ["hook", "uninstall"])
    assert result.exit_code == 0
    assert "Removed" in result.output

    hook_path = db / ".git" / "hooks" / "pre-commit"
    assert not hook_path.exists()


def test_hook_install_no_git(db, runner):
    result = runner.invoke(main, ["hook", "install"])
    assert result.exit_code == 1
    assert "No .git" in result.output


def test_hook_install_already_exists(db, runner):
    git_dir = db / ".git" / "hooks"
    git_dir.mkdir(parents=True)

    runner.invoke(main, ["hook", "install"])
    result = runner.invoke(main, ["hook", "install"])
    assert result.exit_code == 1
    assert "already installed" in result.output


def test_is_hook_installed(db):
    assert not is_hook_installed(db)

    git_dir = db / ".git" / "hooks"
    git_dir.mkdir(parents=True)
    install_hook(db)
    assert is_hook_installed(db)
