from tekeldb.schema import validate_document


TASK_COLLECTION_DEF = {
    "id_prefix": "TASK",
    "fields": {
        "title": {"type": "string", "required": True},
        "status": {"type": "enum", "values": ["open", "in-progress", "done"], "default": "open", "required": True},
        "priority": {"type": "enum", "values": ["low", "medium", "high"], "default": "medium"},
        "points": {"type": "integer", "min": 0, "max": 100},
        "email": {"type": "string", "format": "email"},
        "active": {"type": "boolean"},
        "tags": {"type": "list", "items": "string"},
    },
    "transitions": {
        "status": {
            "open": ["in-progress"],
            "in-progress": ["done", "open"],
            "done": [],
        },
    },
}


def test_valid_document():
    doc = {"id": "TASK-0001", "title": "Test", "status": "open", "priority": "high"}
    errors = validate_document(doc, TASK_COLLECTION_DEF)
    assert errors == []


def test_missing_required():
    doc = {"id": "TASK-0001", "status": "open"}  # missing title
    errors = validate_document(doc, TASK_COLLECTION_DEF)
    assert any("title" in e for e in errors)


def test_invalid_enum():
    doc = {"id": "TASK-0001", "title": "Test", "status": "invalid", "priority": "high"}
    errors = validate_document(doc, TASK_COLLECTION_DEF)
    assert any("not in" in e for e in errors)


def test_integer_min_max():
    doc = {"id": "TASK-0001", "title": "Test", "status": "open", "points": -1}
    errors = validate_document(doc, TASK_COLLECTION_DEF)
    assert any("below minimum" in e for e in errors)

    doc["points"] = 101
    errors = validate_document(doc, TASK_COLLECTION_DEF)
    assert any("above maximum" in e for e in errors)

    doc["points"] = 50
    errors = validate_document(doc, TASK_COLLECTION_DEF)
    assert not any("points" in e for e in errors)


def test_email_format():
    doc = {"id": "TASK-0001", "title": "Test", "status": "open", "email": "bad"}
    errors = validate_document(doc, TASK_COLLECTION_DEF)
    assert any("email" in e for e in errors)

    doc["email"] = "good@example.com"
    errors = validate_document(doc, TASK_COLLECTION_DEF)
    assert not any("email" in e for e in errors)


def test_boolean_type():
    doc = {"id": "TASK-0001", "title": "Test", "status": "open", "active": "yes"}
    errors = validate_document(doc, TASK_COLLECTION_DEF)
    assert any("boolean" in e for e in errors)


def test_valid_transition():
    existing = {"status": "open"}
    doc = {"id": "TASK-0001", "title": "Test", "status": "in-progress"}
    errors = validate_document(doc, TASK_COLLECTION_DEF, existing_doc=existing)
    assert not any("transition" in e.lower() for e in errors)


def test_invalid_transition():
    existing = {"status": "open"}
    doc = {"id": "TASK-0001", "title": "Test", "status": "done"}
    errors = validate_document(doc, TASK_COLLECTION_DEF, existing_doc=existing)
    assert any("Invalid transition" in e for e in errors)


# --- any type ---


def test_any_field_type():
    """Fields with type 'any' should accept any value."""
    col_def = {
        "fields": {
            "title": {"type": "string", "required": True},
            "payload": {"type": "any"},
        }
    }
    # String value
    doc = {"id": "X-1", "title": "Test", "payload": "hello"}
    assert validate_document(doc, col_def) == []

    # Integer value
    doc["payload"] = 42
    assert validate_document(doc, col_def) == []

    # List value
    doc["payload"] = [1, 2, 3]
    assert validate_document(doc, col_def) == []

    # Dict value
    doc["payload"] = {"nested": "object"}
    assert validate_document(doc, col_def) == []

    # None value
    doc["payload"] = None
    assert validate_document(doc, col_def) == []


# --- additional_fields ---


def test_additional_fields_allowed_by_default():
    """Extra fields should pass validation when additional_fields is not set."""
    doc = {"id": "TASK-0001", "title": "Test", "status": "open", "extra_field": "hello"}
    errors = validate_document(doc, TASK_COLLECTION_DEF)
    assert not any("Unknown field" in e for e in errors)


def test_additional_fields_false_rejects_unknown():
    col_def = {
        **TASK_COLLECTION_DEF,
        "additional_fields": False,
    }
    doc = {"id": "TASK-0001", "title": "Test", "status": "open", "unknown": "bad"}
    errors = validate_document(doc, col_def)
    assert any("Unknown field" in e for e in errors)


def test_additional_fields_true_allows_unknown():
    col_def = {
        **TASK_COLLECTION_DEF,
        "additional_fields": True,
    }
    doc = {"id": "TASK-0001", "title": "Test", "status": "open", "extra": "fine"}
    errors = validate_document(doc, col_def)
    assert not any("Unknown field" in e for e in errors)


# --- json field type ---


def test_json_field_valid_string():
    col_def = {"fields": {"data": {"type": "json"}}}
    doc = {"id": "X-1", "data": '{"key": "value"}'}
    assert validate_document(doc, col_def) == []


def test_json_field_invalid_string():
    col_def = {"fields": {"data": {"type": "json"}}}
    doc = {"id": "X-1", "data": "not json {"}
    errors = validate_document(doc, col_def)
    assert any("not valid JSON" in e for e in errors)


def test_json_field_native_dict():
    col_def = {"fields": {"data": {"type": "json"}}}
    doc = {"id": "X-1", "data": {"key": "value"}}
    assert validate_document(doc, col_def) == []


def test_json_field_native_list():
    col_def = {"fields": {"data": {"type": "json"}}}
    doc = {"id": "X-1", "data": [1, 2, 3]}
    assert validate_document(doc, col_def) == []


def test_json_field_invalid_type():
    col_def = {"fields": {"data": {"type": "json"}}}
    doc = {"id": "X-1", "data": 42}
    errors = validate_document(doc, col_def)
    assert any("JSON" in e for e in errors)
