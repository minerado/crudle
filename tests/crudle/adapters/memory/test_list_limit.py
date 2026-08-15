"""List pagination (`limit` / `skip`) — Memory adapter.

Twin of SQLAlchemy ``test_list_limit.py`` where contracts align.

Default ``list`` limit is 25. ``limit=None`` means no cap. Negative
``limit`` / ``skip`` raise ``ValueError`` (Python slices would otherwise wrap).
"""

import pytest

from tests.crudle.adapters.memory.models import Item, ItemList


def _insert_priced(db, n: int):
    return [
        db.insert(Item, name=f"Item {i}", color="red", price=i * 10) for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------


class TestListLimitBasics:
    def test_limit(self, db):
        _insert_priced(db, 5)

        items = db.list(Item, limit=3)

        assert len(items) == 3

    def test_skip(self, db):
        items = _insert_priced(db, 5)

        skipped = db.list(Item, skip=2, limit=100)

        assert len(skipped) == 3
        assert {item.id for item in skipped} == {items[2].id, items[3].id, items[4].id}

    def test_limit_and_skip(self, db):
        items = _insert_priced(db, 5)

        page = db.list(
            Item,
            sort=[{"field": "price", "order": "asc"}],
            skip=1,
            limit=2,
        )

        assert [item.price for item in page] == [10, 20]
        assert [item.id for item in page] == [items[1].id, items[2].id]

    def test_default_limit_is_25(self, db):
        _insert_priced(db, 30)

        assert len(db.list(Item)) == 25
        assert len(db.list(Item, limit=100)) == 30

    def test_skip_zero_is_noop(self, db):
        items = _insert_priced(db, 3)

        result = db.list(Item, skip=0, limit=100)

        assert {item.id for item in result} == {item.id for item in items}

    def test_limit_one(self, db):
        items = _insert_priced(db, 3)

        result = db.list(
            Item,
            sort=[{"field": "price", "order": "asc"}],
            limit=1,
        )

        assert len(result) == 1
        assert result[0].id == items[0].id


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


class TestListLimitEdges:
    def test_limit_zero_returns_empty(self, db):
        _insert_priced(db, 3)

        assert db.list(Item, limit=0) == []

    def test_limit_none_means_no_limit(self, db):
        _insert_priced(db, 30)

        items = db.list(Item, limit=None)

        assert len(items) == 30

    def test_skip_past_end_returns_empty(self, db):
        _insert_priced(db, 3)

        assert db.list(Item, skip=10, limit=100) == []

    def test_skip_equal_to_count_returns_empty(self, db):
        _insert_priced(db, 3)

        assert db.list(Item, skip=3, limit=100) == []

    def test_limit_larger_than_dataset(self, db):
        items = _insert_priced(db, 3)

        result = db.list(Item, limit=100)

        assert len(result) == 3
        assert {item.id for item in result} == {item.id for item in items}

    def test_empty_table(self, db):
        assert db.list(Item, limit=10, skip=5) == []

    def test_negative_limit_raises(self, db):
        _insert_priced(db, 3)

        with pytest.raises(ValueError, match="limit"):
            db.list(Item, limit=-1)

    def test_negative_skip_raises(self, db):
        _insert_priced(db, 3)

        with pytest.raises(ValueError, match="skip"):
            db.list(Item, skip=-1)


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------


class TestListLimitCombos:
    def test_limit_with_filter(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)
        db.insert(Item, name="c", color="red", price=30)
        db.insert(Item, name="d", color="red", price=40)

        items = db.list(
            Item,
            color="red",
            sort=[{"field": "price", "order": "asc"}],
            limit=2,
        )

        assert [item.name for item in items] == ["a", "c"]

    def test_skip_with_filter(self, db):
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="blue", price=20)
        db.insert(Item, name="c", color="red", price=30)
        db.insert(Item, name="d", color="red", price=40)

        items = db.list(
            Item,
            color="red",
            sort=[{"field": "price", "order": "asc"}],
            skip=1,
            limit=100,
        )

        assert [item.name for item in items] == ["c", "d"]

    def test_stable_pages_with_sort(self, db):
        _insert_priced(db, 6)

        page1 = db.list(
            Item,
            sort=[{"field": "price", "order": "asc"}],
            skip=0,
            limit=2,
        )
        page2 = db.list(
            Item,
            sort=[{"field": "price", "order": "asc"}],
            skip=2,
            limit=2,
        )
        page3 = db.list(
            Item,
            sort=[{"field": "price", "order": "asc"}],
            skip=4,
            limit=2,
        )

        assert [item.price for item in page1] == [0, 10]
        assert [item.price for item in page2] == [20, 30]
        assert [item.price for item in page3] == [40, 50]

    def test_limit_with_select(self, db):
        _insert_priced(db, 5)

        rows = db.list(
            Item,
            select=["name", "price"],
            sort=[{"field": "price", "order": "asc"}],
            limit=2,
        )

        assert len(rows) == 2
        assert [row["price"] for row in rows] == [0, 10]

    def test_limit_with_return_dict(self, db):
        _insert_priced(db, 4)

        rows = db.list(
            Item,
            return_dict=True,
            sort=[{"field": "price", "order": "asc"}],
            skip=1,
            limit=2,
        )

        assert [row["price"] for row in rows] == [10, 20]

    def test_limit_after_nested_filter(self, db):
        cheap = db.insert(Item, name="cheap", color="red", price=5)
        mid = db.insert(Item, name="mid", color="blue", price=20)
        high = db.insert(Item, name="high", color="green", price=50)
        db.insert(ItemList, name="L1", items=[cheap])
        db.insert(ItemList, name="L2", items=[mid])
        db.insert(ItemList, name="L3", items=[high])

        lists = db.list(
            ItemList,
            **{"items.price__gt": 10},
            sort=[{"field": "name", "order": "asc"}],
            limit=1,
        )

        assert len(lists) == 1
        assert lists[0].name == "L2"
