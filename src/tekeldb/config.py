from pathlib import Path
import yaml

DEFAULT_CONFIG = {
    "format": "yaml",
    "id_strategy": "sequential",
    "strict": False,
    "timestamps": True,
}


def find_db(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) to find a .tekeldb directory."""
    current = start or Path.cwd()
    while True:
        candidate = current / ".tekeldb"
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            raise FileNotFoundError("No .tekeldb database found in current or parent directories.")
        current = parent


def load_config(db_path: Path) -> dict:
    config_file = db_path / "config.yaml"
    if config_file.exists():
        with open(config_file) as f:
            user_config = yaml.safe_load(f) or {}
        return {**DEFAULT_CONFIG, **user_config}
    return dict(DEFAULT_CONFIG)


def write_config(db_path: Path, config: dict) -> None:
    with open(db_path / "config.yaml", "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)
