"""List ``distinct_on`` — Memory adapter (in-process, first-row wins).

Twin of SQLAlchemy ``test_list_distinct_on.py`` where contracts align.
Memory always runs these locally; SA Postgres ``DISTINCT ON`` stays behind
``pytest.mark.postgres``.

Order of operations: filter → sort → distinct_on → skip/limit → select.
"""

from tests.crudle.adapters.memory.models import Item, ItemType

# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------


class TestListDistinctOnBasics:
    def test_one_row_per_key(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="red", price=20)
        db.insert(Item, name="Item 3", color="blue", price=30)

        items = db.list(Item, distinct_on=["color"], limit=100)

        assert len(items) == 2
        assert {item.color for item in items} == {"red", "blue"}

    def test_multiple_fields(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="red", price=10)
        db.insert(Item, name="Item 3", color="red", price=20)
        db.insert(Item, name="Item 4", color="blue", price=10)

        items = db.list(Item, distinct_on=["color", "price"], limit=100)

        assert len(items) == 3
        assert {(item.color, item.price) for item in items} == {
            ("red", 10),
            ("red", 20),
            ("blue", 10),
        }

    def test_single_record(self, db):
        db.insert(Item, name="Item 1", color="red")

        items = db.list(Item, distinct_on=["color"], limit=100)

        assert len(items) == 1
        assert items[0].color == "red"

    def test_all_unique_keys_keeps_all(self, db):
        a = db.insert(Item, name="A", color="red", price=10)
        b = db.insert(Item, name="B", color="blue", price=20)
        c = db.insert(Item, name="C", color="green", price=30)

        items = db.list(Item, distinct_on=["color"], limit=100)

        assert {item.id for item in items} == {a.id, b.id, c.id}


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


class TestListDistinctOnEdges:
    def test_empty_list_is_noop(self, db):
        db.insert(Item, name="Item 1", color="red")
        db.insert(Item, name="Item 2", color="blue")

        items = db.list(Item, distinct_on=[], limit=100)

        assert len(items) == 2

    def test_true_dedupes_by_id(self, db):
        """``distinct_on=True`` keeps one row per instance id."""
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="red", price=20)

        items = db.list(Item, distinct_on=True, limit=100)

        assert len(items) == 2

    def test_null_key_groups_together(self, db):
        a = db.insert(Item, name="A", color=None, price=10)
        b = db.insert(Item, name="B", color=None, price=20)
        c = db.insert(Item, name="C", color="red", price=30)

        items = db.list(
            Item,
            distinct_on=["color"],
            sort=[{"field": "price", "order": "asc"}],
            limit=100,
        )

        assert len(items) == 2
        by_color = {item.color: item for item in items}
        assert by_color[None].id == a.id
        assert by_color["red"].id == c.id
        assert b.id not in {item.id for item in items}

    def test_empty_table(self, db):
        assert db.list(Item, distinct_on=["color"]) == []


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------


class TestListDistinctOnCombos:
    def test_with_filter(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="red", price=20)
        db.insert(Item, name="Item 3", color="blue", price=30)
        db.insert(Item, name="Item 4", color="green", price=40)

        items = db.list(Item, color="red", distinct_on=["color"], limit=100)

        assert len(items) == 1
        assert items[0].color == "red"

    def test_sort_picks_winner(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="red", price=20)
        db.insert(Item, name="Item 3", color="blue", price=30)

        items = db.list(
            Item,
            distinct_on=["color"],
            sort=[{"field": "price", "order": "desc"}],
            limit=100,
        )

        assert len(items) == 2
        by_color = {item.color: item for item in items}
        assert by_color["red"].price == 20
        assert by_color["blue"].price == 30

    def test_asc_sort_picks_lowest(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="red", price=20)

        items = db.list(
            Item,
            distinct_on=["color"],
            sort=[{"field": "price", "order": "asc"}],
            limit=100,
        )

        assert len(items) == 1
        assert items[0].price == 10

    def test_with_select(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="red", price=20)
        db.insert(Item, name="Item 3", color="blue", price=30)

        rows = db.list(
            Item,
            distinct_on=["color"],
            select=["name", "color"],
            limit=100,
        )

        assert len(rows) == 2
        assert {row["color"] for row in rows} == {"red", "blue"}

    def test_limit_after_distinct(self, db):
        db.insert(Item, name="A", color="red", price=10)
        db.insert(Item, name="B", color="red", price=20)
        db.insert(Item, name="C", color="blue", price=30)
        db.insert(Item, name="D", color="green", price=40)

        items = db.list(
            Item,
            distinct_on=["color"],
            sort=[{"field": "price", "order": "asc"}],
            limit=2,
        )

        assert len(items) == 2
        assert [item.color for item in items] == ["red", "blue"]

    def test_nested_path(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        furniture = db.insert(ItemType, name="Furniture")
        db.insert(Item, name="A", color="red", price=10, item_type=electronics)
        db.insert(Item, name="B", color="blue", price=20, item_type=electronics)
        db.insert(Item, name="C", color="green", price=30, item_type=furniture)

        items = db.list(
            Item,
            distinct_on=["item_type.name"],
            sort=[{"field": "price", "order": "asc"}],
            limit=100,
        )

        assert len(items) == 2
        assert {item.name for item in items} == {"A", "C"}
