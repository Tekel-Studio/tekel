import csv
import io
import json


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
    return json.dumps(doc, indent=2, default=str)


def format_validation_json(results: list[dict]) -> str:
    """Format validation results as JSON."""
    return json.dumps(results, indent=2)


def format_validation_junit(results: list[dict]) -> str:
    """Format validation results as JUnit XML."""
    total = sum(len(r.get("files", [])) for r in results)
    failures = sum(
        sum(1 for f in r.get("files", []) if f.get("errors"))
        for r in results
    )

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<testsuites>',
        f'  <testsuite name="tekel" tests="{total}" failures="{failures}">',
    ]

    for r in results:
        collection = r.get("collection", "unknown")
        for f in r.get("files", []):
            doc_id = f.get("id", "unknown")
            errors = f.get("errors", [])
            if errors:
                lines.append(f'    <testcase name="{doc_id}" classname="{collection}">')
                for e in errors:
                    # Escape XML special characters
                    msg = e.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                    lines.append(f'      <failure message="{msg}"/>')
                lines.append(f'    </testcase>')
            else:
                lines.append(f'    <testcase name="{doc_id}" classname="{collection}"/>')

    lines.append('  </testsuite>')
    lines.append('</testsuites>')
    return "\n".join(lines)


def _format_value(val) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    return str(val)
