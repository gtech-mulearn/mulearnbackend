import ast
import sys
from pathlib import Path

import pytest

from building_blocks import errors
from building_blocks.errors import (
    Conflict,
    DependencyUnavailable,
    DomainError,
    Forbidden,
    NotFound,
    RateLimited,
    Unauthorized,
    Unprocessable,
    ValidationFailed,
    error_code,
    registry,
)


@pytest.fixture(autouse=True)
def empty_registry(monkeypatch):
    monkeypatch.setattr(errors, "_registry", {})


@pytest.mark.parametrize(
    ("category", "status", "code"),
    [
        (ValidationFailed, 400, "validation_error"),
        (Unauthorized, 401, "unauthorized"),
        (Forbidden, 403, "forbidden"),
        (NotFound, 404, "not_found"),
        (Conflict, 409, "conflict"),
        (Unprocessable, 422, "unprocessable"),
        (RateLimited, 429, "rate_limited"),
        (DependencyUnavailable, 503, "dependency_unavailable"),
    ],
)
def test_each_category_carries_its_status_and_code(category, status, code):
    assert issubclass(category, DomainError)
    assert category.http_status == status
    assert category.code == code
    assert category.title
    assert category.public_message


def test_a_registered_error_gets_its_code_and_title():
    @error_code("events.not_bookmarkable", "Event can't be bookmarked")
    class NotBookmarkable(Conflict):
        public_message = "Cancelled or past events cannot be bookmarked."

    assert NotBookmarkable.code == "events.not_bookmarkable"
    assert NotBookmarkable.title == "Event can't be bookmarked"
    assert NotBookmarkable.http_status == 409
    assert registry() == {"events.not_bookmarkable": NotBookmarkable}


def test_an_instance_carries_the_public_message():
    @error_code("events.not_found", "Event not found")
    class EventNotFound(NotFound):
        public_message = "That event doesn't exist."

    assert EventNotFound().public_message == "That event doesn't exist."
    assert str(EventNotFound()) == "That event doesn't exist."
    assert EventNotFound("Event 42 doesn't exist.").public_message == "Event 42 doesn't exist."
    with pytest.raises(NotFound):
        raise EventNotFound()


def test_a_duplicate_code_raises():
    @error_code("karma.duplicate_award", "Already awarded")
    class First(Conflict):
        pass

    with pytest.raises(ValueError, match="karma.duplicate_award"):

        @error_code("karma.duplicate_award", "Already awarded")
        class Second(Conflict):
            pass

    assert registry() == {"karma.duplicate_award": First}


def test_one_class_cant_be_registered_twice():
    @error_code("karma.first", "First")
    class Twice(Conflict):
        pass

    with pytest.raises(ValueError, match="already registered"):
        error_code("karma.second", "Second")(Twice)


@pytest.mark.parametrize(
    "code",
    [
        "notfound",
        "Events.not_found",
        "events.not-found",
        "events.not found",
        "events.",
        ".code",
        "a.b.c",
        "e1.x",
        "",
        "events.not_found\n",
    ],
)
def test_a_badly_formatted_code_raises(code):
    with pytest.raises(ValueError, match="module"):

        @error_code(code, "Title")
        class Bad(Conflict):
            pass

    assert registry() == {}


def test_only_domain_errors_can_be_registered():
    with pytest.raises(TypeError, match="DomainError"):

        @error_code("events.plain", "Plain")
        class Plain(Exception):
            pass


def test_a_title_is_required():
    with pytest.raises(ValueError, match="title"):

        @error_code("events.untitled", " ")
        class Untitled(Conflict):
            pass


def test_the_registry_is_a_copy():
    registry()["events.injected"] = Conflict

    assert registry() == {}


def test_the_module_imports_only_the_standard_library():
    imported = set()
    for node in ast.walk(ast.parse(Path(errors.__file__).read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    assert imported <= set(sys.stdlib_module_names)
