"""List pagination (`limit` / `skip`) — SQLAlchemy adapter.

Sections:

- Basics — limit, skip, combined window, default limit
- Edges — empty result, past end, limit 0, limit None, oversize limit
- Combos — filter, sort, select / return_dict
- Join caveat — relationship select multiplies rows before limit (see select suite)

Default ``list`` limit is 25 (``SQLAlchemyQueryBuilder.DEFAULT_QUERY_LIMIT``).
"""

import pytest

from tests.models import Item, ItemList


def _insert_priced(db, n: int):
    return [Item.insert(db, name=f"Item {i}", color="red", price=i * 10) for i in range(n)]


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------


class TestListLimitBasics:
    def test_limit(self, db):
        _insert_priced(db, 5)

        items = Item.list(db, limit=3)

        assert len(items) == 3

    def test_skip(self, db):
        items = _insert_priced(db, 5)

        skipped = Item.list(db, skip=2, limit=100)

        assert len(skipped) == 3
        assert {item.id for item in skipped} == {items[2].id, items[3].id, items[4].id}

    def test_limit_and_skip(self, db):
        items = _insert_priced(db, 5)

        page = Item.list(
            db,
            sort=[{"field": "price", "order": "asc"}],
            skip=1,
            limit=2,
        )

        assert [item.price for item in page] == [10, 20]
        assert [item.id for item in page] == [items[1].id, items[2].id]

    def test_default_limit_is_25(self, db):
        _insert_priced(db, 30)

        assert len(Item.list(db)) == 25
        assert len(Item.list(db, limit=100)) == 30

    def test_skip_zero_is_noop(self, db):
        items = _insert_priced(db, 3)

        result = Item.list(db, skip=0, limit=100)

        assert {item.id for item in result} == {item.id for item in items}

    def test_limit_one(self, db):
        items = _insert_priced(db, 3)

        result = Item.list(
            db,
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

        assert Item.list(db, limit=0) == []

    def test_limit_none_means_no_limit(self, db):
        _insert_priced(db, 30)

        items = Item.list(db, limit=None)

        assert len(items) == 30

    def test_skip_past_end_returns_empty(self, db):
        _insert_priced(db, 3)

        assert Item.list(db, skip=10, limit=100) == []

    def test_skip_equal_to_count_returns_empty(self, db):
        _insert_priced(db, 3)

        assert Item.list(db, skip=3, limit=100) == []

    def test_limit_larger_than_dataset(self, db):
        items = _insert_priced(db, 3)

        result = Item.list(db, limit=100)

        assert len(result) == 3
        assert {item.id for item in result} == {item.id for item in items}

    def test_empty_table(self, db):
        assert Item.list(db, limit=10, skip=5) == []

    def test_negative_limit_raises_or_errors(self, db):
        _insert_priced(db, 3)

        with pytest.raises(Exception):
            Item.list(db, limit=-1)

    def test_negative_skip_raises_or_errors(self, db):
        _insert_priced(db, 3)

        with pytest.raises(Exception):
            Item.list(db, skip=-1)


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------


class TestListLimitCombos:
    def test_limit_with_filter(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="red", price=30)
        Item.insert(db, name="d", color="red", price=40)

        items = Item.list(
            db,
            color="red",
            sort=[{"field": "price", "order": "asc"}],
            limit=2,
        )

        assert [item.name for item in items] == ["a", "c"]

    def test_skip_with_filter(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="red", price=30)
        Item.insert(db, name="d", color="red", price=40)

        items = Item.list(
            db,
            color="red",
            sort=[{"field": "price", "order": "asc"}],
            skip=1,
            limit=100,
        )

        assert [item.name for item in items] == ["c", "d"]

    def test_stable_pages_with_sort(self, db):
        _insert_priced(db, 6)

        page1 = Item.list(
            db,
            sort=[{"field": "price", "order": "asc"}],
            skip=0,
            limit=2,
        )
        page2 = Item.list(
            db,
            sort=[{"field": "price", "order": "asc"}],
            skip=2,
            limit=2,
        )
        page3 = Item.list(
            db,
            sort=[{"field": "price", "order": "asc"}],
            skip=4,
            limit=2,
        )

        assert [item.price for item in page1] == [0, 10]
        assert [item.price for item in page2] == [20, 30]
        assert [item.price for item in page3] == [40, 50]

    def test_limit_with_select(self, db):
        _insert_priced(db, 5)

        rows = Item.list(
            db,
            select=["name", "price"],
            sort=[{"field": "price", "order": "asc"}],
            limit=2,
        )

        assert len(rows) == 2
        assert [row["price"] for row in rows] == [0, 10]

    def test_limit_with_return_dict(self, db):
        _insert_priced(db, 4)

        rows = Item.list(
            db,
            return_dict=True,
            sort=[{"field": "price", "order": "asc"}],
            skip=1,
            limit=2,
        )

        assert [row["price"] for row in rows] == [10, 20]
        assert all("item_list" not in row for row in rows)

    def test_limit_after_nested_filter(self, db):
        cheap = Item.insert(db, name="cheap", color="red", price=5)
        mid = Item.insert(db, name="mid", color="blue", price=20)
        high = Item.insert(db, name="high", color="green", price=50)
        ItemList.insert(db, name="L1", items=[cheap])
        ItemList.insert(db, name="L2", items=[mid])
        ItemList.insert(db, name="L3", items=[high])

        lists = ItemList.list(
            db,
            **{"items.price__gt": 10},
            sort=[{"field": "name", "order": "asc"}],
            limit=1,
        )

        assert len(lists) == 1
        assert lists[0].name == "L2"
