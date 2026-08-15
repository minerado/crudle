"""List ``distinct_on`` — SQLAlchemy / Postgres ``DISTINCT ON``.

Requires Postgres. Opt in with:

    CRUDLE_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/postgres \\
      pytest -m postgres

Without the env var, these tests are skipped.

SQLite does not support ``DISTINCT ON``; default list tests use SQLite.
Memory implements ``distinct_on`` in-process (see memory list/sort suites).
"""

import pytest

from tests.models import Item

pytestmark = pytest.mark.postgres


def test_list_with_distinct_on(postgres_db):
    """One row per distinct_on key."""
    Item.insert(postgres_db, name="Item 1", color="red", price=10)
    Item.insert(postgres_db, name="Item 2", color="red", price=20)
    Item.insert(postgres_db, name="Item 3", color="blue", price=30)

    distinct_items = Item.list(postgres_db, distinct_on=["color"])

    assert len(distinct_items) == 2
    colors = [item.color for item in distinct_items]
    assert "red" in colors
    assert "blue" in colors
    assert len(set(colors)) == 2


def test_list_with_distinct_on_multiple_fields(postgres_db):
    """Unique combinations across multiple distinct_on fields."""
    Item.insert(postgres_db, name="Item 1", color="red", price=10)
    Item.insert(postgres_db, name="Item 2", color="red", price=10)
    Item.insert(postgres_db, name="Item 3", color="red", price=20)
    Item.insert(postgres_db, name="Item 4", color="blue", price=10)

    distinct_items = Item.list(postgres_db, distinct_on=["color", "price"])

    assert len(distinct_items) == 3
    combinations = {(item.color, item.price) for item in distinct_items}
    assert combinations == {("red", 10), ("red", 20), ("blue", 10)}


def test_list_with_distinct_on_and_filters(postgres_db):
    """Filters apply before / with distinct_on."""
    Item.insert(postgres_db, name="Item 1", color="red", price=10)
    Item.insert(postgres_db, name="Item 2", color="red", price=20)
    Item.insert(postgres_db, name="Item 3", color="blue", price=30)
    Item.insert(postgres_db, name="Item 4", color="green", price=40)

    distinct_red_items = Item.list(postgres_db, color="red", distinct_on=["color"])

    assert len(distinct_red_items) == 1
    assert distinct_red_items[0].color == "red"


def test_list_with_distinct_on_and_sorting(postgres_db):
    """Sort chooses which row wins within each distinct_on group."""
    Item.insert(postgres_db, name="Item 1", color="red", price=10)
    Item.insert(postgres_db, name="Item 2", color="red", price=20)
    Item.insert(postgres_db, name="Item 3", color="blue", price=30)

    distinct_items = Item.list(
        postgres_db,
        distinct_on=["color"],
        sort=[{"field": "price", "order": "desc"}],
    )

    assert len(distinct_items) == 2
    by_color = {item.color: item for item in distinct_items}
    assert by_color["red"].price == 20
    assert by_color["blue"].price == 30


def test_list_with_distinct_on_single_record(postgres_db):
    Item.insert(postgres_db, name="Item 1", color="red")

    items = Item.list(postgres_db, distinct_on=["color"])

    assert len(items) == 1
    assert items[0].color == "red"


def test_list_with_select_and_distinct_on(postgres_db):
    """distinct_on works with select projection."""
    Item.insert(postgres_db, name="Item 1", color="red", price=10)
    Item.insert(postgres_db, name="Item 2", color="red", price=20)
    Item.insert(postgres_db, name="Item 3", color="blue", price=30)

    distinct_items = Item.list(
        postgres_db, distinct_on=["color"], select=["name", "color"]
    )

    assert len(distinct_items) == 2
    colors = [item["color"] for item in distinct_items]
    assert "red" in colors
    assert "blue" in colors


def test_list_with_sort_and_distinct_on(postgres_db):
    """Same contract as sort suite: highest price per color."""
    Item.insert(postgres_db, name="Item 1", color="red", price=10)
    Item.insert(postgres_db, name="Item 2", color="red", price=20)
    Item.insert(postgres_db, name="Item 3", color="blue", price=30)

    items = Item.list(
        postgres_db,
        distinct_on=["color"],
        sort=[{"field": "price", "order": "desc"}],
    )

    assert len(items) == 2
    by_color = {item.color: item for item in items}
    assert by_color["red"].price == 20
    assert by_color["blue"].price == 30
