from pathlib import Path
from .document import read_document
from .schema import get_collection_by_prefix


def collection_dir(db_path: Path, collection: str) -> Path:
    return db_path / "data" / collection


def ensure_collection_dir(db_path: Path, collection: str) -> Path:
    d = collection_dir(db_path, collection)
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_documents(db_path: Path, collection: str) -> list[dict]:
    """Read all documents in a collection directory."""
    col_dir = collection_dir(db_path, collection)
    if not col_dir.exists():
        return []
    docs = []
    for f in sorted(col_dir.iterdir()):
        if f.suffix in (".yaml", ".json", ".toml") and f.is_file():
            docs.append(read_document(f))
    return docs


def find_document_by_id(db_path: Path, schema: dict | None, doc_id: str) -> tuple[Path, dict] | None:
    """Given an ID like TASK-0001, find and return (path, doc)."""
    # Extract prefix (everything before the last dash-separated segment)
    parts = doc_id.split("-", 1)
    if len(parts) < 2:
        return None

    prefix = parts[0]
    result = get_collection_by_prefix(schema, prefix)
    if result is None:
        # Schema-free: try all collection directories
        data_dir = db_path / "data"
        if data_dir.exists():
            for col_dir in data_dir.iterdir():
                if col_dir.is_dir():
                    for ext in (".yaml", ".json", ".toml"):
                        path = col_dir / f"{doc_id}{ext}"
                        if path.exists():
                            return path, read_document(path)
        return None

    col_name, _ = result
    for ext in (".yaml", ".json", ".toml"):
        path = db_path / "data" / col_name / f"{doc_id}{ext}"
        if path.exists():
            return path, read_document(path)
    return None


def resolve_collection_from_id(schema: dict | None, doc_id: str) -> str | None:
    """Map an ID prefix to a collection name."""
    parts = doc_id.split("-", 1)
    if len(parts) < 2:
        return None
    result = get_collection_by_prefix(schema, parts[0])
    if result:
        return result[0]
    return None
