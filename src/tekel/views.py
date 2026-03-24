"""Saved views — named, reusable queries."""
import json
from pathlib import Path


def load_views(db_path: Path) -> dict:
    """Load views.json. Returns empty dict if not found."""
    views_file = db_path / "views.json"
    if not views_file.exists():
        return {}
    with open(views_file) as f:
        data = json.load(f) or {}
    return data.get("views", {})


def save_views(db_path: Path, views: dict) -> None:
    """Write views to views.json."""
    with open(db_path / "views.json", "w") as f:
        json.dump({"views": views}, f, indent=2)
        f.write("\n")


def get_view(db_path: Path, name: str) -> dict | None:
    views = load_views(db_path)
    return views.get(name)


def add_view(db_path: Path, name: str, view_def: dict) -> None:
    views = load_views(db_path)
    views[name] = view_def
    save_views(db_path, views)


def delete_view(db_path: Path, name: str) -> bool:
    views = load_views(db_path)
    if name not in views:
        return False
    del views[name]
    save_views(db_path, views)
    return True


def parse_view_from_command(command_str: str) -> dict:
    """Parse a command string like 'list tasks status:open --sort -priority' into a view def."""
    parts = command_str.split()

    # Skip leading 'list' if present
    if parts and parts[0] == "list":
        parts = parts[1:]

    if not parts:
        raise ValueError("View command must include a collection name.")

    view_def = {"collection": parts[0]}
    parts = parts[1:]

    filters = []
    i = 0
    while i < len(parts):
        arg = parts[i]
        if arg == "--sort" and i + 1 < len(parts):
            view_def["sort"] = parts[i + 1]
            i += 2
        elif arg == "--limit" and i + 1 < len(parts):
            view_def["limit"] = int(parts[i + 1])
            i += 2
        elif arg == "--format" and i + 1 < len(parts):
            view_def["format"] = parts[i + 1]
            i += 2
        elif not arg.startswith("--"):
            filters.append(arg)
            i += 1
        else:
            i += 1

    if filters:
        view_def["filters"] = filters

    return view_def
