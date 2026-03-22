"""Git pre-commit hook management."""
from pathlib import Path
import stat


HOOK_SCRIPT = """\
#!/bin/sh
# tekeldb pre-commit hook — validates staged YAML documents against schema
STAGED=$(git diff --cached --name-only --diff-filter=ACM | grep '\\.tekeldb/data/.*\\.yaml$' || true)
if [ -n "$STAGED" ]; then
    echo "tekeldb: validating staged documents..."
    tekeldb validate --files $STAGED
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        echo ""
        echo "Commit aborted. Run 'tekeldb validate --fix' to auto-correct fixable issues."
        exit 1
    fi
fi
"""


def find_git_dir(start: Path | None = None) -> Path | None:
    """Walk up from start to find the .git directory."""
    current = start or Path.cwd()
    while True:
        candidate = current / ".git"
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def install_hook(start: Path | None = None) -> Path:
    """Install the tekeldb pre-commit hook. Returns the hook file path."""
    git_dir = find_git_dir(start)
    if git_dir is None:
        raise FileNotFoundError("No .git directory found. Is this a Git repository?")

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "pre-commit"

    if hook_path.exists():
        content = hook_path.read_text()
        if "tekeldb" in content:
            raise FileExistsError("tekeldb pre-commit hook is already installed.")
        raise FileExistsError(
            f"A pre-commit hook already exists at {hook_path}. "
            "Remove it first or add tekeldb validation manually."
        )

    hook_path.write_text(HOOK_SCRIPT)
    # Make executable
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)
    return hook_path


def uninstall_hook(start: Path | None = None) -> None:
    """Remove the tekeldb pre-commit hook."""
    git_dir = find_git_dir(start)
    if git_dir is None:
        raise FileNotFoundError("No .git directory found.")

    hook_path = git_dir / "hooks" / "pre-commit"
    if not hook_path.exists():
        raise FileNotFoundError("No pre-commit hook found.")

    content = hook_path.read_text()
    if "tekeldb" not in content:
        raise ValueError("The existing pre-commit hook was not installed by tekeldb.")

    hook_path.unlink()


def is_hook_installed(start: Path | None = None) -> bool:
    """Check if the tekeldb pre-commit hook is installed."""
    git_dir = find_git_dir(start)
    if git_dir is None:
        return False
    hook_path = git_dir / "hooks" / "pre-commit"
    if not hook_path.exists():
        return False
    return "tekeldb" in hook_path.read_text()
