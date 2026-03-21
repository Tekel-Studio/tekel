import csv
import io
import json
import yaml


def get_display_fields(collection_def: dict | None) -> list[str]:
    """Pick reasonable columns for table view."""
    if collection_def is None:
        return []
    fields = ["id"]
    for name in collection_def.get("fields", {}):
        fields.append(name)
    return fields


def format_table(docs: list[dict], fields: list[str] | None = None) -> str:
    """Fixed-width table output."""
    if not docs:
        return "No documents found."

    if not fields:
        # Derive fields from first doc
        fields = list(docs[0].keys())

    # Calculate column widths
    widths = {}
    for f in fields:
        widths[f] = len(f)
        for doc in docs:
            val = doc.get(f, "")
            val_str = _format_value(val)
            widths[f] = max(widths[f], min(len(val_str), 40))

    # Header
    header = "  ".join(f.upper().ljust(widths[f]) for f in fields)
    separator = "  ".join("-" * widths[f] for f in fields)
    lines = [header, separator]

    # Rows
    for doc in docs:
        row = "  ".join(
            _format_value(doc.get(f, "")).ljust(widths[f])[:widths[f]]
            for f in fields
        )
        lines.append(row)

    return "\n".join(lines)


def format_yaml_output(docs: list[dict]) -> str:
    parts = []
    for doc in docs:
        parts.append(yaml.safe_dump(doc, default_flow_style=False, sort_keys=False).strip())
    return "\n---\n".join(parts)


def format_json_output(docs: list[dict]) -> str:
    return json.dumps(docs, indent=2, default=str)


def format_csv_output(docs: list[dict], fields: list[str] | None = None) -> str:
    if not docs:
        return ""
    if not fields:
        fields = list(docs[0].keys())
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for doc in docs:
        writer.writerow({k: _format_value(doc.get(k, "")) for k in fields})
    return output.getvalue()


def format_single(doc: dict) -> str:
    """Pretty-print a single document."""
    return yaml.safe_dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True).strip()


def _format_value(val) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    return str(val)
