"""List filters: equality operator (`eq` / bare field).

High-level sections (reuse this shape for other operators):

- Matches — filter finds the expected rows
- Misses — filter correctly returns no rows
- Spellings — bare field, field__eq, nested path / nested dict
- Value shapes — None, empty string, numbers, etc.
"""

from datetime import datetime, timezone

from tests.models import Item, ItemList, ItemType, Tag

# ---------------------------------------------------------------------------
# Matches — when equality finds rows
# ---------------------------------------------------------------------------


class TestListEqMatches:
    def test_bare_field_string(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        item3 = Item.insert(db, name="Item 3", color="red", price=30)

        red_items = Item.list(db, color="red")

        assert set(red_items) == {item1, item3}
        assert item2 not in red_items

    def test_multiple_fields_anded(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        Item.insert(db, name="Item 2", color="red", price=20)
        Item.insert(db, name="Item 3", color="blue", price=10)

        items = Item.list(db, color="red", price__eq=10)

        assert items == [item1]


# ---------------------------------------------------------------------------
# Misses — when equality correctly returns empty
# ---------------------------------------------------------------------------


class TestListEqMisses:
    def test_no_matching_value(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)

        assert Item.list(db, color="purple") == []
        assert Item.list(db, color__eq="purple") == []

    def test_partial_and_does_not_match(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)

        assert Item.list(db, color="red", price__eq=99) == []


# ---------------------------------------------------------------------------
# Spellings — bare vs __eq vs nested forms
# ---------------------------------------------------------------------------


class TestListEqSpellings:
    def test_explicit_eq_matches_bare(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        Item.insert(db, name="Item 2", color="blue", price=20)
        item3 = Item.insert(db, name="Item 3", color="red", price=30)

        bare = Item.list(db, color="red")
        explicit = Item.list(db, color__eq="red")

        assert set(bare) == {item1, item3}
        assert set(explicit) == set(bare)

    def test_nested_dotted_path(self, db):
        item1 = Item.insert(db, name="Item 1", color="red")
        item2 = Item.insert(db, name="Item 2", color="blue")
        list1 = ItemList.insert(db, name="List 1", items=[item1, item2])
        ItemList.insert(db, name="List 2", items=[item2])

        lists = ItemList.list(db, **{"items.color": "red"})

        assert lists == [list1]

    def test_nested_dotted_path_with_explicit_eq(self, db):
        item1 = Item.insert(db, name="Item 1", color="red")
        item2 = Item.insert(db, name="Item 2", color="blue")
        list1 = ItemList.insert(db, name="List 1", items=[item1, item2])
        ItemList.insert(db, name="List 2", items=[item2])

        lists = ItemList.list(db, **{"items.color__eq": "red"})

        assert lists == [list1]

    def test_nested_dict_filter(self, db):
        item1 = Item.insert(db, name="Item 1", color="red")
        item2 = Item.insert(db, name="Item 2", color="blue")
        list1 = ItemList.insert(db, name="List 1", items=[item1, item2])
        ItemList.insert(db, name="List 2", items=[item2])

        lists = ItemList.list(db, filter={"items": {"color": "red"}})

        assert lists == [list1]

    def test_nested_deep_dotted_path(self, db):
        item1 = Item.insert(db, name="Item 1", color="red")
        item2 = Item.insert(db, name="Item 2", color="blue")
        list1 = ItemList.insert(db, name="List 1", items=[item1])
        ItemList.insert(db, name="List 2", items=[item2])
        Tag.insert(db, name="expensive", items=[item1])
        Tag.insert(db, name="cheap", items=[item2])

        lists = ItemList.list(db, **{"items.tags.name": "expensive"})

        assert lists == [list1]

    def test_belongs_to_relationship(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        item1 = Item.insert(db, name="Phone", color="red", item_type=electronics)
        Item.insert(db, name="Shirt", color="blue", item_type=clothing)

        items = Item.list(db, **{"item_type.name": "Electronics"})

        assert items == [item1]


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListEqValueShapes:
    def test_none(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color=None, price=20)
        item3 = Item.insert(db, name="Item 3", color="blue", price=None)

        assert Item.list(db, color=None) == [item2]
        assert Item.list(db, color__eq=None) == [item2]
        assert Item.list(db, price=None) == [item3]
        assert Item.list(db, price__eq=None) == [item3]

    def test_empty_string(self, db):
        item_empty = Item.insert(db, name="", color="red", price=10)
        Item.insert(db, name="Item 2", color="blue", price=20)
        item_null = Item.insert(db, name=None, color="green", price=30)

        assert Item.list(db, name="") == [item_empty]
        assert Item.list(db, name__eq="") == [item_empty]
        assert Item.list(db, name=None) == [item_null]
        assert Item.list(db, name__eq=None) == [item_null]

    def test_integer(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        Item.insert(db, name="Item 2", color="blue", price=20)

        assert Item.list(db, price=10) == [item1]
        assert Item.list(db, price__eq=10) == [item1]

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Column is naive UTC in the test model; strip tz for SQLite insert
        moment_naive = moment.replace(tzinfo=None)
        other_naive = other.replace(tzinfo=None)

        item1 = Item.insert(db, name="Item 1", color="red", created_at=moment_naive)
        Item.insert(db, name="Item 2", color="blue", created_at=other_naive)

        assert Item.list(db, created_at=moment_naive) == [item1]
        assert Item.list(db, created_at__eq=moment_naive) == [item1]
