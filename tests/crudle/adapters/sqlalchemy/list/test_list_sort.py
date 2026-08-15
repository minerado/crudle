"""List sorting (`sort`) — SQLAlchemy adapter.

Sections:

- Basics — asc/desc, default order, multi-field, empty sort
- Value shapes — strings, ints, datetimes, NULLs (SQLite: NULLS first on ASC)
- Nested paths — belongs-to / deep paths via joins
- Combos — filter, limit, skip, select
- Edges — invalid fields, case of order spelling, ties

Nested collection sorts (e.g. ItemList by ``items.price``) use joins and may
multiply parent rows; that behavior is covered under Nested paths.
"""

from datetime import datetime, timedelta, timezone

import pytest

from tests.models import Item, ItemList, ItemType, Tag


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------


class TestListSortBasics:
    def test_asc(self, db):
        Item.insert(db, name="Item 1", price=30)
        Item.insert(db, name="Item 2", price=10)
        Item.insert(db, name="Item 3", price=20)

        items = Item.list(db, sort=[{"field": "price", "order": "asc"}])

        assert [item.price for item in items] == [10, 20, 30]

    def test_desc(self, db):
        Item.insert(db, name="Item 1", price=30)
        Item.insert(db, name="Item 2", price=10)
        Item.insert(db, name="Item 3", price=20)

        items = Item.list(db, sort=[{"field": "price", "order": "desc"}])

        assert [item.price for item in items] == [30, 20, 10]

    def test_default_order_is_asc(self, db):
        Item.insert(db, name="Item 1", price=30)
        Item.insert(db, name="Item 2", price=10)
        Item.insert(db, name="Item 3", price=20)

        items = Item.list(db, sort=[{"field": "price"}])

        assert [item.price for item in items] == [10, 20, 30]

    def test_order_spelling_is_case_insensitive(self, db):
        Item.insert(db, name="Item 1", price=30)
        Item.insert(db, name="Item 2", price=10)
        Item.insert(db, name="Item 3", price=20)

        items = Item.list(db, sort=[{"field": "price", "order": "DeSc"}])

        assert [item.price for item in items] == [30, 20, 10]

    def test_multi_field(self, db):
        Item.insert(db, name="Item A", color="red", price=10)
        Item.insert(db, name="Item B", color="red", price=20)
        Item.insert(db, name="Item C", color="blue", price=10)
        Item.insert(db, name="Item D", color="blue", price=20)

        items = Item.list(
            db,
            sort=[
                {"field": "color", "order": "asc"},
                {"field": "price", "order": "desc"},
            ],
        )

        assert [(item.color, item.price) for item in items] == [
            ("blue", 20),
            ("blue", 10),
            ("red", 20),
            ("red", 10),
        ]

    def test_three_field_sort(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=10)
        Item.insert(db, name="c", color="red", price=20)
        Item.insert(db, name="d", color="blue", price=10)

        items = Item.list(
            db,
            sort=[
                {"field": "color", "order": "asc"},
                {"field": "price", "order": "asc"},
                {"field": "name", "order": "desc"},
            ],
        )

        assert [item.name for item in items] == ["d", "b", "a", "c"]

    def test_empty_sort_list_preserves_default_list(self, db):
        item1 = Item.insert(db, name="Item 1", price=10)
        item2 = Item.insert(db, name="Item 2", price=20)

        items = Item.list(db, sort=[])

        assert set(items) == {item1, item2}

    def test_single_row(self, db):
        item = Item.insert(db, name="Only", price=10)

        items = Item.list(db, sort=[{"field": "price", "order": "desc"}])

        assert items == [item]


# ---------------------------------------------------------------------------
# Value shapes
# ---------------------------------------------------------------------------


class TestListSortValueShapes:
    def test_string_asc(self, db):
        Item.insert(db, name="charlie", color="red")
        Item.insert(db, name="alpha", color="blue")
        Item.insert(db, name="bravo", color="green")

        items = Item.list(db, sort=[{"field": "name", "order": "asc"}])

        assert [item.name for item in items] == ["alpha", "bravo", "charlie"]

    def test_string_desc(self, db):
        Item.insert(db, name="charlie", color="red")
        Item.insert(db, name="alpha", color="blue")
        Item.insert(db, name="bravo", color="green")

        items = Item.list(db, sort=[{"field": "name", "order": "desc"}])

        assert [item.name for item in items] == ["charlie", "bravo", "alpha"]

    def test_datetime_asc(self, db):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        Item.insert(db, name="mid", created_at=now)
        Item.insert(db, name="early", created_at=now - timedelta(days=2))
        Item.insert(db, name="late", created_at=now + timedelta(days=2))

        items = Item.list(db, sort=[{"field": "created_at", "order": "asc"}])

        assert [item.name for item in items] == ["early", "mid", "late"]

    def test_datetime_desc(self, db):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        Item.insert(db, name="mid", created_at=now)
        Item.insert(db, name="early", created_at=now - timedelta(days=2))
        Item.insert(db, name="late", created_at=now + timedelta(days=2))

        items = Item.list(db, sort=[{"field": "created_at", "order": "desc"}])

        assert [item.name for item in items] == ["late", "mid", "early"]

    def test_nulls_first_on_asc_sqlite(self, db):
        """SQLite treats NULL as smallest → ASC puts NULLs first."""
        Item.insert(db, name="priced", price=10)
        Item.insert(db, name="nullish", price=None)
        Item.insert(db, name="pricey", price=20)

        items = Item.list(db, sort=[{"field": "price", "order": "asc"}])

        assert [item.name for item in items] == ["nullish", "priced", "pricey"]

    def test_nulls_last_on_desc_sqlite(self, db):
        """SQLite NULLS are smallest → DESC puts NULLs last."""
        Item.insert(db, name="priced", price=10)
        Item.insert(db, name="nullish", price=None)
        Item.insert(db, name="pricey", price=20)

        items = Item.list(db, sort=[{"field": "price", "order": "desc"}])

        assert [item.name for item in items] == ["pricey", "priced", "nullish"]

    def test_null_strings_asc(self, db):
        Item.insert(db, name="zulu", color="red")
        Item.insert(db, name=None, color="blue")
        Item.insert(db, name="alpha", color="green")

        items = Item.list(db, sort=[{"field": "name", "order": "asc"}])

        assert items[0].name is None
        assert [item.name for item in items[1:]] == ["alpha", "zulu"]

    def test_empty_string_sorts_before_nonempty_asc(self, db):
        Item.insert(db, name="b", color="red")
        Item.insert(db, name="", color="blue")
        Item.insert(db, name="a", color="green")

        items = Item.list(db, sort=[{"field": "name", "order": "asc"}])

        assert [item.name for item in items] == ["", "a", "b"]

    def test_sort_by_id(self, db):
        first = Item.insert(db, name="first", price=99)
        second = Item.insert(db, name="second", price=1)
        third = Item.insert(db, name="third", price=50)

        items = Item.list(db, sort=[{"field": "id", "order": "asc"}])

        assert [item.id for item in items] == [first.id, second.id, third.id]


# ---------------------------------------------------------------------------
# Nested paths
# ---------------------------------------------------------------------------


class TestListSortNested:
    def test_belongs_to_field_asc(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        accessories = ItemType.insert(db, name="Accessories")
        Item.insert(db, name="Phone", item_type=electronics)
        Item.insert(db, name="Shirt", item_type=clothing)
        Item.insert(db, name="Bag", item_type=accessories)

        items = Item.list(db, sort=[{"field": "item_type.name", "order": "asc"}])

        assert [item.name for item in items] == ["Bag", "Shirt", "Phone"]

    def test_belongs_to_field_desc(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        Item.insert(db, name="Phone", item_type=electronics)
        Item.insert(db, name="Shirt", item_type=clothing)

        items = Item.list(db, sort=[{"field": "item_type.name", "order": "desc"}])

        assert [item.name for item in items] == ["Phone", "Shirt"]

    def test_belongs_to_with_null_relationship(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        Item.insert(db, name="Phone", item_type=electronics)
        Item.insert(db, name="Orphan", item_type=None)

        items = Item.list(db, sort=[{"field": "item_type.name", "order": "asc"}])

        assert items[0].name == "Orphan"
        assert items[1].name == "Phone"

    def test_nested_and_root_multi_sort(self, db):
        # ItemType is one-to-one with Item — use unique types per row
        type_a = ItemType.insert(db, name="A")
        type_b = ItemType.insert(db, name="B")
        type_c = ItemType.insert(db, name="C")
        Item.insert(db, name="a-high", price=20, item_type=type_a)
        Item.insert(db, name="b-low", price=5, item_type=type_b)
        Item.insert(db, name="c-mid", price=15, item_type=type_c)

        items = Item.list(
            db,
            sort=[
                {"field": "item_type.name", "order": "asc"},
                {"field": "price", "order": "asc"},
            ],
        )

        assert [item.name for item in items] == ["a-high", "b-low", "c-mid"]

    def test_deep_path_sort_via_join(self, db):
        """Deep sort joins related tables (may multiply parent rows)."""
        item_cheap = Item.insert(db, name="cheap-item", price=10)
        item_pricey = Item.insert(db, name="pricey-item", price=50)
        Tag.insert(db, name="alpha", items=[item_pricey])
        Tag.insert(db, name="zeta", items=[item_cheap])
        list_z = ItemList.insert(db, name="List Z", items=[item_cheap])
        list_a = ItemList.insert(db, name="List A", items=[item_pricey])

        lists = ItemList.list(
            db, sort=[{"field": "items.tags.name", "order": "asc"}]
        )

        # Join-shaped: one row per matching path; first by tag name is alpha → List A
        assert lists[0].id == list_a.id
        assert {row.id for row in lists} >= {list_a.id, list_z.id}

    def test_collection_path_sort_multiplies_parents(self, db):
        """Sorting by a 1:N field joins and can duplicate parents."""
        item1 = Item.insert(db, name="i1", price=10)
        item2 = Item.insert(db, name="i2", price=20)
        multi = ItemList.insert(db, name="Multi", items=[item1, item2])
        single = ItemList.insert(
            db,
            name="Single",
            items=[Item.insert(db, name="i3", price=15)],
        )

        lists = ItemList.list(db, sort=[{"field": "items.price", "order": "asc"}])

        # Joined row count: Multi contributes 2, Single 1
        assert len(lists) == 3
        assert sum(1 for row in lists if row.id == multi.id) == 2
        assert sum(1 for row in lists if row.id == single.id) == 1


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------


class TestListSortCombos:
    def test_sort_with_filter(self, db):
        Item.insert(db, name="red-high", color="red", price=30)
        Item.insert(db, name="blue", color="blue", price=5)
        Item.insert(db, name="red-low", color="red", price=10)

        items = Item.list(
            db,
            color="red",
            sort=[{"field": "price", "order": "asc"}],
        )

        assert [item.name for item in items] == ["red-low", "red-high"]

    def test_sort_with_nested_filter(self, db):
        # ItemType is one-to-one — one item per type
        type_a = ItemType.insert(db, name="keep")
        type_b = ItemType.insert(db, name="drop")
        Item.insert(db, name="a-mid", price=20, item_type=type_a)
        Item.insert(db, name="b", price=1, item_type=type_b)
        type_c = ItemType.insert(db, name="keep-too")
        Item.insert(db, name="c-low", price=10, item_type=type_c)

        items = Item.list(
            db,
            **{"item_type.name__in": ["keep", "keep-too"]},
            sort=[{"field": "price", "order": "asc"}],
        )

        assert [item.name for item in items] == ["c-low", "a-mid"]

    def test_sort_with_limit(self, db):
        for price in (50, 10, 40, 20, 30):
            Item.insert(db, name=f"p{price}", price=price)

        items = Item.list(
            db,
            sort=[{"field": "price", "order": "asc"}],
            limit=3,
        )

        assert [item.price for item in items] == [10, 20, 30]

    def test_sort_with_skip(self, db):
        for price in (50, 10, 40, 20, 30):
            Item.insert(db, name=f"p{price}", price=price)

        items = Item.list(
            db,
            sort=[{"field": "price", "order": "asc"}],
            skip=2,
        )

        assert [item.price for item in items] == [30, 40, 50]

    def test_sort_with_limit_and_skip(self, db):
        for price in (60, 10, 50, 20, 40, 30):
            Item.insert(db, name=f"p{price}", price=price)

        items = Item.list(
            db,
            sort=[{"field": "price", "order": "asc"}],
            skip=2,
            limit=2,
        )

        assert [item.price for item in items] == [30, 40]

    def test_sort_with_select(self, db):
        Item.insert(db, name="c", price=30)
        Item.insert(db, name="a", price=10)
        Item.insert(db, name="b", price=20)

        rows = Item.list(
            db,
            select=["name", "price"],
            sort=[{"field": "price", "order": "desc"}],
        )

        assert [row["name"] for row in rows] == ["c", "b", "a"]

    def test_sort_field_not_in_select(self, db):
        Item.insert(db, name="c", price=30)
        Item.insert(db, name="a", price=10)
        Item.insert(db, name="b", price=20)

        rows = Item.list(
            db,
            select=["name"],
            sort=[{"field": "price", "order": "asc"}],
        )

        assert [row["name"] for row in rows] == ["a", "b", "c"]

    def test_sort_with_return_dict(self, db):
        Item.insert(db, name="c", price=30)
        Item.insert(db, name="a", price=10)

        rows = Item.list(
            db,
            return_dict=True,
            sort=[{"field": "price", "order": "asc"}],
        )

        assert [row["name"] for row in rows] == ["a", "c"]


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


class TestListSortEdges:
    def test_invalid_field_raises_or_errors(self, db):
        Item.insert(db, name="Item 1", price=10)

        with pytest.raises(Exception):
            Item.list(db, sort=[{"field": "not_a_column", "order": "asc"}])

    def test_invalid_nested_field_raises_or_errors(self, db):
        Item.insert(db, name="Item 1", price=10)

        with pytest.raises(Exception):
            Item.list(db, sort=[{"field": "item_type.nope", "order": "asc"}])

    def test_stable_secondary_when_primary_ties(self, db):
        Item.insert(db, name="b", color="red", price=10)
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="c", color="red", price=10)

        items = Item.list(
            db,
            sort=[
                {"field": "price", "order": "asc"},
                {"field": "name", "order": "asc"},
            ],
        )

        assert [item.name for item in items] == ["a", "b", "c"]

    def test_opposite_orders_on_same_field_pair(self, db):
        """Two specs can target different fields with opposite directions."""
        Item.insert(db, name="x", color="a", price=2)
        Item.insert(db, name="y", color="a", price=1)
        Item.insert(db, name="z", color="b", price=9)

        items = Item.list(
            db,
            sort=[
                {"field": "color", "order": "desc"},
                {"field": "price", "order": "asc"},
            ],
        )

        assert [item.name for item in items] == ["z", "y", "x"]

    def test_sort_after_empty_result(self, db):
        items = Item.list(
            db,
            color="missing",
            sort=[{"field": "price", "order": "asc"}],
        )

        assert items == []

    def test_unicode_string_sort(self, db):
        Item.insert(db, name="österreich", price=1)
        Item.insert(db, name="apple", price=2)
        Item.insert(db, name="zebra", price=3)

        items = Item.list(db, sort=[{"field": "name", "order": "asc"}])

        names = [item.name for item in items]
        assert names == sorted(names)

    def test_negative_and_zero_prices(self, db):
        Item.insert(db, name="neg", price=-5)
        Item.insert(db, name="zero", price=0)
        Item.insert(db, name="pos", price=5)

        items = Item.list(db, sort=[{"field": "price", "order": "asc"}])

        assert [item.name for item in items] == ["neg", "zero", "pos"]

    def test_sort_does_not_drop_unrelated_filters(self, db):
        Item.insert(db, name="keep", color="red", price=30)
        Item.insert(db, name="drop-color", color="blue", price=10)
        Item.insert(db, name="keep-low", color="red", price=5)

        items = Item.list(
            db,
            color="red",
            price__ge=5,
            sort=[{"field": "price", "order": "desc"}],
        )

        assert [item.name for item in items] == ["keep", "keep-low"]
