import re
from datetime import date, datetime


def parse_filter(filter_str: str) -> tuple[str, str, str]:
    """Parse 'field:op value' into (field, operator, value).

    Operators: = (default), >, <, >=, <=, !, ~
    """
    m = re.match(r"^([^:]+):(>=|<=|>|<|!|~)?(.+)$", filter_str)
    if not m:
        raise ValueError(f"Invalid filter: {filter_str}")
    field = m.group(1)
    op = m.group(2) or "="
    value = m.group(3)
    return field, op, value


def _coerce_value(value_str: str):
    """Try to coerce a string to int, float, date, or leave as string."""
    # Try int
    try:
        return int(value_str)
    except ValueError:
        pass
    # Try float
    try:
        return float(value_str)
    except ValueError:
        pass
    # Try date
    try:
        return date.fromisoformat(value_str)
    except ValueError:
        pass
    # Try datetime
    try:
        return datetime.fromisoformat(value_str)
    except ValueError:
        pass
    return value_str


def match_document(doc: dict, filters: list[tuple[str, str, str]]) -> bool:
    """Check if a document matches all filters (AND logic)."""
    for field, op, value_str in filters:
        doc_value = doc.get(field)
        if doc_value is None:
            return False

        # For list fields, = checks membership
        if isinstance(doc_value, list) and op == "=":
            if value_str.lower() not in [str(v).lower() for v in doc_value]:
                return False
            continue

        coerced = _coerce_value(value_str)

        # Normalize for comparison
        if isinstance(doc_value, date) and not isinstance(doc_value, datetime) and isinstance(coerced, str):
            try:
                coerced = date.fromisoformat(coerced)
            except ValueError:
                pass

        if op == "=":
            if str(doc_value).lower() != str(coerced).lower():
                return False
        elif op == "!":
            if str(doc_value).lower() == str(coerced).lower():
                return False
        elif op == "~":
            if value_str.lower() not in str(doc_value).lower():
                return False
        elif op == ">":
            if not (doc_value > coerced):
                return False
        elif op == "<":
            if not (doc_value < coerced):
                return False
        elif op == ">=":
            if not (doc_value >= coerced):
                return False
        elif op == "<=":
            if not (doc_value <= coerced):
                return False

    return True


def sort_documents(docs: list[dict], sort_field: str) -> list[dict]:
    """Sort documents. Leading '-' means descending."""
    descending = sort_field.startswith("-")
    if descending:
        sort_field = sort_field[1:]

    def sort_key(doc):
        val = doc.get(sort_field)
        if val is None:
            return ("", ) if not descending else ("\xff",)
        return (val,)

    return sorted(docs, key=sort_key, reverse=descending)
