"""List custom filters (``Queries.filter_*``) — SQLAlchemy adapter.

Custom filters are declared on the model’s ``Queries`` class. ``filter_foo``
becomes the ``foo=`` list kwarg. The query builder mixes ``Queries`` into
``SQLAlchemyQueryBuilder`` for each ``list`` / ``get_by`` / ``build_query``.

Memory has no ``Queries`` hook — SA-only suite.

Patterns in this file:

- Shared ``Item.is_expensive`` (declared on ``tests.models.Item``)
- Local subclasses with their own ``Queries`` (same tables, no new schema)

Sections: naming, value handling, composition, relationships, combos.
"""

from tests.models import Item, ItemList


# ---------------------------------------------------------------------------
# Local models / Queries (same tables via subclass, or tiny helpers)
# ---------------------------------------------------------------------------


class ItemWithExpensiveFilter(Item):
    """Subclass that only exposes ``expensive=`` (does not inherit Item.Queries)."""

    class Queries:
        def filter_expensive(self, query, value):
            if value:
                return query.filter(Item.price > 15)
            return query


class ItemWithExtendedQueries(Item):
    """Keeps ``is_expensive`` and adds ``expensive``."""

    class Queries(Item.Queries):
        def filter_expensive(self, query, value):
            if value:
                return query.filter(Item.price > 15)
            return query


class ItemListWithRedFilter(ItemList):
    class Queries:
        def filter_has_red_item(self, query, value):
            if value:
                return query.filter(ItemList.items.any(Item.color == "red"))
            return query


class ItemWithMultiCustom(Item):
    class Queries:
        def filter_min_price(self, query, value):
            return query.filter(Item.price >= value)

        def filter_color_name(self, query, value):
            return query.filter(Item.color == value)


# ---------------------------------------------------------------------------
# Naming — filter_X → X=
# ---------------------------------------------------------------------------


class TestListCustomNaming:
    def test_model_declared_is_expensive(self, db):
        Item.insert(db, name="cheap", color="red", price=10)
        expensive = Item.insert(db, name="pricey", color="blue", price=20)

        items = Item.list(db, is_expensive=True)

        assert items == [expensive]

    def test_subclass_filter_maps_to_kwarg(self, db):
        Item.insert(db, name="Item 1", price=10)
        item2 = Item.insert(db, name="Item 2", price=20)
        item3 = Item.insert(db, name="Item 3", price=30)

        items = ItemWithExpensiveFilter.list(db, expensive=True)

        assert {item.id for item in items} == {item2.id, item3.id}

    def test_multi_word_filter_name(self, db):
        """``filter_is_expensive`` → ``is_expensive`` (split on first ``_`` only)."""
        Item.insert(db, name="cheap", price=5)
        expensive = Item.insert(db, name="pricey", price=50)

        items = Item.list(db, is_expensive=True)

        assert items == [expensive]

    def test_queries_inheritance_keeps_parent_filters(self, db):
        Item.insert(db, name="cheap", price=10)
        mid = Item.insert(db, name="mid", price=20)
        high = Item.insert(db, name="high", price=30)

        via_parent = ItemWithExtendedQueries.list(db, is_expensive=True)
        via_child = ItemWithExtendedQueries.list(db, expensive=True)

        # is_expensive: price > 10; expensive: price > 15
        assert {item.id for item in via_parent} == {mid.id, high.id}
        assert {item.id for item in via_child} == {mid.id, high.id}


# ---------------------------------------------------------------------------
# Value handling
# ---------------------------------------------------------------------------


class TestListCustomValues:
    def test_true_applies_filter(self, db):
        Item.insert(db, name="cheap", price=10)
        expensive = Item.insert(db, name="pricey", price=20)

        assert Item.list(db, is_expensive=True) == [expensive]

    def test_false_applies_inverse_when_implemented(self, db):
        cheap = Item.insert(db, name="cheap", price=10)
        Item.insert(db, name="pricey", price=20)

        assert Item.list(db, is_expensive=False) == [cheap]

    def test_false_can_be_noop(self, db):
        """Subclass that ignores falsy values leaves the query unchanged."""
        cheap = Item.insert(db, name="cheap", price=10)
        expensive = Item.insert(db, name="pricey", price=20)

        items = ItemWithExpensiveFilter.list(db, expensive=False, limit=100)

        assert {item.id for item in items} == {cheap.id, expensive.id}

    def test_omitted_does_not_apply(self, db):
        cheap = Item.insert(db, name="cheap", price=10)
        expensive = Item.insert(db, name="pricey", price=20)

        items = Item.list(db, limit=100)

        assert {item.id for item in items} == {cheap.id, expensive.id}

    def test_non_bool_value(self, db):
        Item.insert(db, name="low", price=5)
        mid = Item.insert(db, name="mid", price=15)
        high = Item.insert(db, name="high", price=25)

        items = ItemWithMultiCustom.list(db, min_price=15)

        assert {item.id for item in items} == {mid.id, high.id}


# ---------------------------------------------------------------------------
# Composition with built-in filters / assoc
# ---------------------------------------------------------------------------


class TestListCustomComposition:
    def test_custom_and_field_filter(self, db):
        Item.insert(db, name="a", color="red", price=20)
        keep = Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="blue", price=5)

        items = Item.list(db, is_expensive=True, color="blue")

        assert items == [keep]

    def test_two_custom_filters_anded(self, db):
        Item.insert(db, name="a", color="red", price=20)
        keep = Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="blue", price=5)

        items = ItemWithMultiCustom.list(
            db, min_price=15, color_name="blue"
        )

        assert [item.id for item in items] == [keep.id]

    def test_custom_and_assoc_filter(self, db):
        red_expensive = Item.insert(db, name="re", color="red", price=20)
        red_cheap = Item.insert(db, name="rc", color="red", price=5)
        blue_expensive = Item.insert(db, name="be", color="blue", price=20)
        keep = ItemList.insert(db, name="Keep", items=[red_expensive])
        ItemList.insert(db, name="CheapRed", items=[red_cheap])
        ItemList.insert(db, name="BlueExp", items=[blue_expensive])

        lists = ItemListWithRedFilter.list(
            db,
            has_red_item=True,
            **{"items.price__gt": 15},
        )

        assert [lst.id for lst in lists] == [keep.id]

    def test_custom_no_match_returns_empty(self, db):
        Item.insert(db, name="cheap", price=5)

        assert Item.list(db, is_expensive=True) == []


# ---------------------------------------------------------------------------
# Relationship-aware custom filters
# ---------------------------------------------------------------------------


class TestListCustomRelationships:
    def test_filter_using_any(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        blue = Item.insert(db, name="blue", color="blue", price=10)
        list1 = ItemList.insert(db, name="L1", items=[red, blue])
        ItemList.insert(db, name="L2", items=[blue])

        lists = ItemListWithRedFilter.list(db, has_red_item=True)

        assert [lst.id for lst in lists] == [list1.id]

    def test_relationship_filter_false_is_noop(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        blue = Item.insert(db, name="blue", color="blue", price=10)
        list1 = ItemList.insert(db, name="L1", items=[red])
        list2 = ItemList.insert(db, name="L2", items=[blue])

        lists = ItemListWithRedFilter.list(db, has_red_item=False, limit=100)

        assert {lst.id for lst in lists} == {list1.id, list2.id}


# ---------------------------------------------------------------------------
# Combos with list options
# ---------------------------------------------------------------------------


class TestListCustomCombos:
    def test_with_sort(self, db):
        Item.insert(db, name="b", price=20)
        Item.insert(db, name="a", price=30)
        Item.insert(db, name="c", price=5)

        items = Item.list(
            db,
            is_expensive=True,
            sort=[{"field": "name", "order": "asc"}],
        )

        assert [item.name for item in items] == ["a", "b"]

    def test_with_limit(self, db):
        for i in range(5):
            Item.insert(db, name=f"Item {i}", price=20 + i)

        items = Item.list(
            db,
            is_expensive=True,
            sort=[{"field": "price", "order": "asc"}],
            limit=2,
        )

        assert len(items) == 2
        assert [item.price for item in items] == [20, 21]

    def test_with_select(self, db):
        Item.insert(db, name="cheap", price=5)
        Item.insert(db, name="pricey", price=20)

        rows = Item.list(db, is_expensive=True, select=["name", "price"])

        assert len(rows) == 1
        assert rows[0]["name"] == "pricey"
        assert rows[0]["price"] == 20
