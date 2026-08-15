"""List sorting (`sort`) — Memory adapter.

Twin of SQLAlchemy ``test_list_sort.py`` where contracts align.

NULL ordering matches SQLite (NULLS first on ASC, last on DESC). Nested
belongs-to sorts preload relationship hops. Sorting by a 1:N collection path
is undefined for Memory (no join multiplication); those cases stay SA-only.
"""

from datetime import datetime, timedelta, timezone

from tests.crudle.adapters.memory.models import Item, ItemType

# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------


class TestListSortBasics:
    def test_asc(self, db):
        db.insert(Item, name="Item 1", price=30)
        db.insert(Item, name="Item 2", price=10)
        db.insert(Item, name="Item 3", price=20)

        items = db.list(Item, sort=[{"field": "price", "order": "asc"}])

        assert [item.price for item in items] == [10, 20, 30]

    def test_desc(self, db):
        db.insert(Item, name="Item 1", price=30)
        db.insert(Item, name="Item 2", price=10)
        db.insert(Item, name="Item 3", price=20)

        items = db.list(Item, sort=[{"field": "price", "order": "desc"}])

        assert [item.price for item in items] == [30, 20, 10]

    def test_default_order_is_asc(self, db):
        db.insert(Item, name="Item 1", price=30)
        db.insert(Item, name="Item 2", price=10)
        db.insert(Item, name="Item 3", price=20)

        items = db.list(Item, sort=[{"field": "price"}])

        assert [item.price for item in items] == [10, 20, 30]

    def test_order_spelling_is_case_insensitive(self, db):
        db.insert(Item, name="Item 1", price=30)
        db.insert(Item, name="Item 2", price=10)
        db.insert(Item, name="Item 3", price=20)

        items = db.list(Item, sort=[{"field": "price", "order": "DeSc"}])

        assert [item.price for item in items] == [30, 20, 10]

    def test_multi_field(self, db):
        db.insert(Item, name="Item A", color="red", price=10)
        db.insert(Item, name="Item B", color="red", price=20)
        db.insert(Item, name="Item C", color="blue", price=10)
        db.insert(Item, name="Item D", color="blue", price=20)

        items = db.list(
            Item,
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
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="b", color="red", price=10)
        db.insert(Item, name="c", color="red", price=20)
        db.insert(Item, name="d", color="blue", price=10)

        items = db.list(
            Item,
            sort=[
                {"field": "color", "order": "asc"},
                {"field": "price", "order": "asc"},
                {"field": "name", "order": "desc"},
            ],
        )

        assert [item.name for item in items] == ["d", "b", "a", "c"]

    def test_empty_sort_list_preserves_default_list(self, db):
        item1 = db.insert(Item, name="Item 1", price=10)
        item2 = db.insert(Item, name="Item 2", price=20)

        items = db.list(Item, sort=[])

        assert {item.id for item in items} == {item1.id, item2.id}

    def test_single_row(self, db):
        item = db.insert(Item, name="Only", price=10)

        items = db.list(Item, sort=[{"field": "price", "order": "desc"}])

        assert items == [item]


# ---------------------------------------------------------------------------
# Value shapes
# ---------------------------------------------------------------------------


class TestListSortValueShapes:
    def test_string_asc(self, db):
        db.insert(Item, name="charlie", color="red")
        db.insert(Item, name="alpha", color="blue")
        db.insert(Item, name="bravo", color="green")

        items = db.list(Item, sort=[{"field": "name", "order": "asc"}])

        assert [item.name for item in items] == ["alpha", "bravo", "charlie"]

    def test_string_desc(self, db):
        db.insert(Item, name="charlie", color="red")
        db.insert(Item, name="alpha", color="blue")
        db.insert(Item, name="bravo", color="green")

        items = db.list(Item, sort=[{"field": "name", "order": "desc"}])

        assert [item.name for item in items] == ["charlie", "bravo", "alpha"]

    def test_datetime_asc(self, db):
        now = datetime.now(timezone.utc)
        db.insert(Item, name="mid", created_at=now)
        db.insert(Item, name="early", created_at=now - timedelta(days=2))
        db.insert(Item, name="late", created_at=now + timedelta(days=2))

        items = db.list(Item, sort=[{"field": "created_at", "order": "asc"}])

        assert [item.name for item in items] == ["early", "mid", "late"]

    def test_datetime_desc(self, db):
        now = datetime.now(timezone.utc)
        db.insert(Item, name="mid", created_at=now)
        db.insert(Item, name="early", created_at=now - timedelta(days=2))
        db.insert(Item, name="late", created_at=now + timedelta(days=2))

        items = db.list(Item, sort=[{"field": "created_at", "order": "desc"}])

        assert [item.name for item in items] == ["late", "mid", "early"]

    def test_nulls_first_on_asc(self, db):
        db.insert(Item, name="priced", price=10)
        db.insert(Item, name="nullish", price=None)
        db.insert(Item, name="pricey", price=20)

        items = db.list(Item, sort=[{"field": "price", "order": "asc"}])

        assert [item.name for item in items] == ["nullish", "priced", "pricey"]

    def test_nulls_last_on_desc(self, db):
        db.insert(Item, name="priced", price=10)
        db.insert(Item, name="nullish", price=None)
        db.insert(Item, name="pricey", price=20)

        items = db.list(Item, sort=[{"field": "price", "order": "desc"}])

        assert [item.name for item in items] == ["pricey", "priced", "nullish"]

    def test_null_strings_asc(self, db):
        db.insert(Item, name="zulu", color="red")
        db.insert(Item, name=None, color="blue")
        db.insert(Item, name="alpha", color="green")

        items = db.list(Item, sort=[{"field": "name", "order": "asc"}])

        assert items[0].name is None
        assert [item.name for item in items[1:]] == ["alpha", "zulu"]

    def test_empty_string_sorts_before_nonempty_asc(self, db):
        db.insert(Item, name="b", color="red")
        db.insert(Item, name="", color="blue")
        db.insert(Item, name="a", color="green")

        items = db.list(Item, sort=[{"field": "name", "order": "asc"}])

        assert [item.name for item in items] == ["", "a", "b"]

    def test_sort_by_id(self, db):
        first = db.insert(Item, name="first", price=99)
        second = db.insert(Item, name="second", price=1)
        third = db.insert(Item, name="third", price=50)

        items = db.list(Item, sort=[{"field": "id", "order": "asc"}])

        assert [item.id for item in items] == [first.id, second.id, third.id]


# ---------------------------------------------------------------------------
# Nested paths (belongs-to / to-one)
# ---------------------------------------------------------------------------


class TestListSortNested:
    def test_belongs_to_field_asc(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        accessories = db.insert(ItemType, name="Accessories")
        db.insert(Item, name="Phone", item_type=electronics)
        db.insert(Item, name="Shirt", item_type=clothing)
        db.insert(Item, name="Bag", item_type=accessories)

        items = db.list(Item, sort=[{"field": "item_type.name", "order": "asc"}])

        assert [item.name for item in items] == ["Bag", "Shirt", "Phone"]

    def test_belongs_to_field_desc(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        db.insert(Item, name="Phone", item_type=electronics)
        db.insert(Item, name="Shirt", item_type=clothing)

        items = db.list(Item, sort=[{"field": "item_type.name", "order": "desc"}])

        assert [item.name for item in items] == ["Phone", "Shirt"]

    def test_belongs_to_with_null_relationship(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        db.insert(Item, name="Phone", item_type=electronics)
        db.insert(Item, name="Orphan", item_type=None)

        items = db.list(Item, sort=[{"field": "item_type.name", "order": "asc"}])

        assert items[0].name == "Orphan"
        assert items[1].name == "Phone"

    def test_nested_and_root_multi_sort(self, db):
        type_a = db.insert(ItemType, name="A")
        type_b = db.insert(ItemType, name="B")
        type_c = db.insert(ItemType, name="C")
        db.insert(Item, name="a-high", price=20, item_type=type_a)
        db.insert(Item, name="b-low", price=5, item_type=type_b)
        db.insert(Item, name="c-mid", price=15, item_type=type_c)

        items = db.list(
            Item,
            sort=[
                {"field": "item_type.name", "order": "asc"},
                {"field": "price", "order": "asc"},
            ],
        )

        assert [item.name for item in items] == ["a-high", "b-low", "c-mid"]


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------


class TestListSortCombos:
    def test_sort_with_filter(self, db):
        db.insert(Item, name="red-high", color="red", price=30)
        db.insert(Item, name="blue", color="blue", price=5)
        db.insert(Item, name="red-low", color="red", price=10)

        items = db.list(
            Item,
            color="red",
            sort=[{"field": "price", "order": "asc"}],
        )

        assert [item.name for item in items] == ["red-low", "red-high"]

    def test_sort_with_nested_filter(self, db):
        type_a = db.insert(ItemType, name="keep")
        type_b = db.insert(ItemType, name="drop")
        type_c = db.insert(ItemType, name="keep-too")
        db.insert(Item, name="a-mid", price=20, item_type=type_a)
        db.insert(Item, name="b", price=1, item_type=type_b)
        db.insert(Item, name="c-low", price=10, item_type=type_c)

        items = db.list(
            Item,
            **{"item_type.name__in": ["keep", "keep-too"]},
            sort=[{"field": "price", "order": "asc"}],
        )

        assert [item.name for item in items] == ["c-low", "a-mid"]

    def test_sort_with_limit(self, db):
        for price in (50, 10, 40, 20, 30):
            db.insert(Item, name=f"p{price}", price=price)

        items = db.list(
            Item,
            sort=[{"field": "price", "order": "asc"}],
            limit=3,
        )

        assert [item.price for item in items] == [10, 20, 30]

    def test_sort_with_skip(self, db):
        for price in (50, 10, 40, 20, 30):
            db.insert(Item, name=f"p{price}", price=price)

        items = db.list(
            Item,
            sort=[{"field": "price", "order": "asc"}],
            skip=2,
        )

        assert [item.price for item in items] == [30, 40, 50]

    def test_sort_with_limit_and_skip(self, db):
        for price in (60, 10, 50, 20, 40, 30):
            db.insert(Item, name=f"p{price}", price=price)

        items = db.list(
            Item,
            sort=[{"field": "price", "order": "asc"}],
            skip=2,
            limit=2,
        )

        assert [item.price for item in items] == [30, 40]

    def test_sort_with_select(self, db):
        db.insert(Item, name="c", price=30)
        db.insert(Item, name="a", price=10)
        db.insert(Item, name="b", price=20)

        rows = db.list(
            Item,
            select=["name", "price"],
            sort=[{"field": "price", "order": "desc"}],
        )

        assert [row["name"] for row in rows] == ["c", "b", "a"]

    def test_sort_field_not_in_select(self, db):
        db.insert(Item, name="c", price=30)
        db.insert(Item, name="a", price=10)
        db.insert(Item, name="b", price=20)

        rows = db.list(
            Item,
            select=["name"],
            sort=[{"field": "price", "order": "asc"}],
        )

        assert [row["name"] for row in rows] == ["a", "b", "c"]

    def test_sort_with_return_dict(self, db):
        db.insert(Item, name="c", price=30)
        db.insert(Item, name="a", price=10)

        rows = db.list(
            Item,
            return_dict=True,
            sort=[{"field": "price", "order": "asc"}],
        )

        assert [row["name"] for row in rows] == ["a", "c"]


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


class TestListSortEdges:
    def test_invalid_field_sorts_as_nullish(self, db):
        """Unknown fields resolve to None for every row (stable no-op order)."""
        a = db.insert(Item, name="a", price=10)
        b = db.insert(Item, name="b", price=20)

        items = db.list(Item, sort=[{"field": "not_a_column", "order": "asc"}])

        assert {item.id for item in items} == {a.id, b.id}

    def test_stable_secondary_when_primary_ties(self, db):
        db.insert(Item, name="b", color="red", price=10)
        db.insert(Item, name="a", color="red", price=10)
        db.insert(Item, name="c", color="red", price=10)

        items = db.list(
            Item,
            sort=[
                {"field": "price", "order": "asc"},
                {"field": "name", "order": "asc"},
            ],
        )

        assert [item.name for item in items] == ["a", "b", "c"]

    def test_opposite_orders_on_same_field_pair(self, db):
        db.insert(Item, name="x", color="a", price=2)
        db.insert(Item, name="y", color="a", price=1)
        db.insert(Item, name="z", color="b", price=9)

        items = db.list(
            Item,
            sort=[
                {"field": "color", "order": "desc"},
                {"field": "price", "order": "asc"},
            ],
        )

        assert [item.name for item in items] == ["z", "y", "x"]

    def test_sort_after_empty_result(self, db):
        items = db.list(
            Item,
            color="missing",
            sort=[{"field": "price", "order": "asc"}],
        )

        assert items == []

    def test_sort_with_distinct_on(self, db):
        db.insert(Item, name="Item 1", color="red", price=10)
        db.insert(Item, name="Item 2", color="red", price=20)
        db.insert(Item, name="Item 3", color="blue", price=30)

        items = db.list(
            Item,
            distinct_on=["color"],
            sort=[{"field": "price", "order": "desc"}],
        )

        assert len(items) == 2
        by_color = {item.color: item for item in items}
        assert by_color["red"].price == 20
        assert by_color["blue"].price == 30

    def test_unicode_string_sort(self, db):
        db.insert(Item, name="österreich", price=1)
        db.insert(Item, name="apple", price=2)
        db.insert(Item, name="zebra", price=3)

        items = db.list(Item, sort=[{"field": "name", "order": "asc"}])

        names = [item.name for item in items]
        assert names == sorted(names)

    def test_negative_and_zero_prices(self, db):
        db.insert(Item, name="neg", price=-5)
        db.insert(Item, name="zero", price=0)
        db.insert(Item, name="pos", price=5)

        items = db.list(Item, sort=[{"field": "price", "order": "asc"}])

        assert [item.name for item in items] == ["neg", "zero", "pos"]

    def test_sort_does_not_drop_unrelated_filters(self, db):
        db.insert(Item, name="keep", color="red", price=30)
        db.insert(Item, name="drop-color", color="blue", price=10)
        db.insert(Item, name="keep-low", color="red", price=5)

        items = db.list(
            Item,
            color="red",
            price__ge=5,
            sort=[{"field": "price", "order": "desc"}],
        )

        assert [item.name for item in items] == ["keep", "keep-low"]
