from tekeldb.query import parse_filter, match_document, sort_documents, text_search


def test_parse_filter_exact():
    assert parse_filter("status:open") == ("status", "=", "open")


def test_parse_filter_not_equal():
    assert parse_filter("status:!done") == ("status", "!", "done")


def test_parse_filter_contains():
    assert parse_filter("title:~landing") == ("title", "~", "landing")


def test_parse_filter_greater():
    assert parse_filter("priority:>3") == ("priority", ">", "3")


def test_parse_filter_less_equal():
    assert parse_filter("due:<=2026-04-01") == ("due", "<=", "2026-04-01")


def test_match_exact():
    doc = {"status": "open", "priority": "high"}
    assert match_document(doc, [("status", "=", "open")])
    assert not match_document(doc, [("status", "=", "closed")])


def test_match_case_insensitive():
    doc = {"status": "Open"}
    assert match_document(doc, [("status", "=", "open")])


def test_match_not_equal():
    doc = {"status": "open"}
    assert match_document(doc, [("status", "!", "done")])
    assert not match_document(doc, [("status", "!", "open")])


def test_match_contains():
    doc = {"title": "Design landing page"}
    assert match_document(doc, [("title", "~", "landing")])
    assert not match_document(doc, [("title", "~", "login")])


def test_match_list_membership():
    doc = {"tags": ["design", "website"]}
    assert match_document(doc, [("tags", "=", "design")])
    assert not match_document(doc, [("tags", "=", "backend")])


def test_match_greater():
    doc = {"points": 5}
    assert match_document(doc, [("points", ">", "3")])
    assert not match_document(doc, [("points", ">", "10")])


def test_match_multiple_filters():
    doc = {"status": "open", "priority": "high"}
    assert match_document(doc, [("status", "=", "open"), ("priority", "=", "high")])
    assert not match_document(doc, [("status", "=", "open"), ("priority", "=", "low")])


def test_match_missing_field():
    doc = {"status": "open"}
    assert not match_document(doc, [("priority", "=", "high")])


def test_sort_ascending():
    docs = [{"name": "C"}, {"name": "A"}, {"name": "B"}]
    result = sort_documents(docs, "name")
    assert [d["name"] for d in result] == ["A", "B", "C"]


def test_sort_descending():
    docs = [{"name": "C"}, {"name": "A"}, {"name": "B"}]
    result = sort_documents(docs, "-name")
    assert [d["name"] for d in result] == ["C", "B", "A"]


# --- Dot notation (json fields) ---


def test_dot_notation_query():
    doc = {"api_response": '{"event": "push", "repo": "tekeldb"}'}
    assert match_document(doc, [("api_response.event", "=", "push")])
    assert not match_document(doc, [("api_response.event", "=", "pull")])


def test_dot_notation_native_dict():
    doc = {"metadata": {"source": "github", "count": 3}}
    assert match_document(doc, [("metadata.source", "=", "github")])


def test_dot_notation_missing():
    doc = {"title": "Test"}
    assert not match_document(doc, [("metadata.key", "=", "value")])


# --- Text search ---


def test_text_search_matches():
    doc = {"id": "T-1", "title": "Design landing page", "status": "open"}
    assert text_search(doc, "landing")
    assert text_search(doc, "LANDING")  # case insensitive


def test_text_search_no_match():
    doc = {"id": "T-1", "title": "Fix bug", "status": "open"}
    assert not text_search(doc, "landing")


def test_text_search_skips_non_string():
    doc = {"id": "T-1", "title": "Test", "count": 42}
    assert not text_search(doc, "42")  # 42 is int, not string
