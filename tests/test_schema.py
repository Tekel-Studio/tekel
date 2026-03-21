from tekeldb.schema import validate_document, get_first_string_field


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


def test_get_first_string_field():
    assert get_first_string_field(TASK_COLLECTION_DEF) == "title"
