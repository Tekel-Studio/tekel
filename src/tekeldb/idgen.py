from pathlib import Path
import uuid
import yaml


def load_counters(db_path: Path) -> dict:
    counters_file = db_path / "counters.yaml"
    if counters_file.exists():
        with open(counters_file) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_counters(db_path: Path, counters: dict) -> None:
    with open(db_path / "counters.yaml", "w") as f:
        yaml.safe_dump(counters, f, default_flow_style=False)


def generate_id(db_path: Path, collection: str, prefix: str, strategy: str = "sequential") -> str:
    if strategy == "uuid":
        return f"{prefix}-{uuid.uuid4()}"
    elif strategy == "ulid":
        try:
            import ulid
            return f"{prefix}-{ulid.new()}"
        except ImportError:
            return f"{prefix}-{uuid.uuid4()}"
    else:  # sequential
        counters = load_counters(db_path)
        current = counters.get(collection, 0) + 1
        counters[collection] = current
        save_counters(db_path, counters)
        return f"{prefix}-{current:04d}"
