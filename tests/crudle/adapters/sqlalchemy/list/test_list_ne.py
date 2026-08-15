"""List filters: not-equal operator (`ne`).

High-level sections (reuse this shape for other operators):

- Matches — filter finds the expected rows
- Misses — filter correctly returns no rows
- Spellings — field__ne, nested path / nested dict
- Value shapes — None, empty string, numbers, etc.

Note: there is no bare-field form for `ne` (bare `field=value` is always `eq`).
"""

from datetime import datetime, timezone

from tests.models import Item, ItemList, ItemType, Tag

# ---------------------------------------------------------------------------
# Matches — when not-equal finds rows
# ---------------------------------------------------------------------------


class TestListNeMatches:
    def test_string(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        item3 = Item.insert(db, name="Item 3", color="green", price=30)

        items = Item.list(db, color__ne="red")

        assert set(items) == {item2, item3}
        assert item1 not in items

    def test_multiple_fields_anded(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        Item.insert(db, name="Item 3", color="blue", price=10)

        # blue AND price != 10 → only item2
        items = Item.list(db, color="blue", price__ne=10)

        assert items == [item2]
        assert item1 not in items


# ---------------------------------------------------------------------------
# Misses — when not-equal correctly returns empty
# ---------------------------------------------------------------------------


class TestListNeMisses:
    def test_all_rows_equal_value(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)
        Item.insert(db, name="Item 2", color="red", price=20)

        assert Item.list(db, color__ne="red") == []

    def test_partial_and_does_not_match(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)

        # color matches but price__ne cannot (only price is 10)
        assert Item.list(db, color="red", price__ne=10) == []


# ---------------------------------------------------------------------------
# Spellings — explicit __ne and nested forms
# ---------------------------------------------------------------------------


class TestListNeSpellings:
    def test_nested_dotted_path(self, db):
        item_red = Item.insert(db, name="Item 1", color="red")
        item_blue = Item.insert(db, name="Item 2", color="blue")
        # List 1 has a non-red item → matches color__ne=red
        list1 = ItemList.insert(db, name="List 1", items=[item_red, item_blue])
        # List 2 only red → does not match
        ItemList.insert(db, name="List 2", items=[item_red])

        lists = ItemList.list(db, **{"items.color__ne": "red"})

        assert lists == [list1]

    def test_nested_dict_filter(self, db):
        item_red = Item.insert(db, name="Item 1", color="red")
        item_blue = Item.insert(db, name="Item 2", color="blue")
        list1 = ItemList.insert(db, name="List 1", items=[item_red, item_blue])
        ItemList.insert(db, name="List 2", items=[item_red])

        lists = ItemList.list(db, filter={"items": {"color__ne": "red"}})

        assert lists == [list1]

    def test_nested_deep_dotted_path(self, db):
        item1 = Item.insert(db, name="Item 1", color="red")
        item2 = Item.insert(db, name="Item 2", color="blue")
        ItemList.insert(db, name="List 1", items=[item1])
        list2 = ItemList.insert(db, name="List 2", items=[item2])
        Tag.insert(db, name="expensive", items=[item1])
        Tag.insert(db, name="cheap", items=[item2])

        lists = ItemList.list(db, **{"items.tags.name__ne": "expensive"})

        assert lists == [list2]

    def test_belongs_to_relationship(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        Item.insert(db, name="Phone", color="red", item_type=electronics)
        shirt = Item.insert(db, name="Shirt", color="blue", item_type=clothing)

        items = Item.list(db, **{"item_type.name__ne": "Electronics"})

        assert items == [shirt]


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListNeValueShapes:
    def test_none_excludes_null_columns_for_value(self, db):
        """color__ne='red' excludes NULL (SQL three-valued logic)."""
        item_red = Item.insert(db, name="Item 1", color="red", price=10)
        item_blue = Item.insert(db, name="Item 2", color="blue", price=20)
        Item.insert(db, name="Item 3", color=None, price=30)

        items = Item.list(db, color__ne="red")

        assert set(items) == {item_blue}
        assert item_red not in items

    def test_ne_none_means_is_not_null(self, db):
        """color__ne=None → IS NOT NULL (SQLAlchemy behavior)."""
        item_red = Item.insert(db, name="Item 1", color="red", price=10)
        item_blue = Item.insert(db, name="Item 2", color="blue", price=20)
        Item.insert(db, name="Item 3", color=None, price=30)

        items = Item.list(db, color__ne=None)

        assert set(items) == {item_red, item_blue}

    def test_empty_string(self, db):
        item_empty = Item.insert(db, name="", color="red", price=10)
        item_named = Item.insert(db, name="Item 2", color="blue", price=20)
        item_null = Item.insert(db, name=None, color="green", price=30)

        assert set(Item.list(db, name__ne="")) == {item_named}
        # NULL name is excluded by name__ne="" (same as color__ne="red")
        assert item_null not in Item.list(db, name__ne="")
        assert item_empty not in Item.list(db, name__ne="")

    def test_integer(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)

        assert Item.list(db, price__ne=10) == [item2]
        assert item1 not in Item.list(db, price__ne=10)

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        moment_naive = moment.replace(tzinfo=None)
        other_naive = other.replace(tzinfo=None)

        item1 = Item.insert(db, name="Item 1", color="red", created_at=moment_naive)
        item2 = Item.insert(db, name="Item 2", color="blue", created_at=other_naive)

        assert Item.list(db, created_at__ne=moment_naive) == [item2]
        assert item1 not in Item.list(db, created_at__ne=moment_naive)
