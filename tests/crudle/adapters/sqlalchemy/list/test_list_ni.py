"""List filters: not-in operator (`ni`).

High-level sections (reuse this shape for other operators):

- Matches — filter finds the expected rows
- Misses — filter correctly returns no rows
- Spellings — field__ni, nested path / nested dict
- Value shapes — None, empty list, empty string, numbers, etc.

Note: there is no bare-field form for `ni` (bare `field=value` is always `eq`).
SQL three-valued logic: NULL columns do not match NOT IN (non-empty lists).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import ArgumentError

from tests.models import Item, ItemList, ItemType, Tag

# ---------------------------------------------------------------------------
# Matches — when not-in finds rows
# ---------------------------------------------------------------------------


class TestListNiMatches:
    def test_string_list(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)
        item3 = Item.insert(db, name="Item 3", color="green", price=30)
        item4 = Item.insert(db, name="Item 4", color="yellow", price=40)

        items = Item.list(db, color__ni=["red", "blue"])

        assert set(items) == {item3, item4}
        assert item1 not in items
        assert item2 not in items

    def test_multiple_fields_anded(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="red", price=20)
        Item.insert(db, name="Item 3", color="blue", price=30)

        items = Item.list(db, color="red", price__ni=[10])

        assert items == [item2]
        assert item1 not in items


# ---------------------------------------------------------------------------
# Misses — when not-in correctly returns empty
# ---------------------------------------------------------------------------


class TestListNiMisses:
    def test_all_rows_in_list(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)
        Item.insert(db, name="Item 2", color="blue", price=20)

        assert Item.list(db, color__ni=["red", "blue"]) == []

    def test_partial_and_does_not_match(self, db):
        Item.insert(db, name="Item 1", color="red", price=10)

        assert Item.list(db, color="red", price__ni=[10]) == []


# ---------------------------------------------------------------------------
# Spellings — explicit __ni and nested forms
# ---------------------------------------------------------------------------


class TestListNiSpellings:
    def test_nested_dotted_path(self, db):
        item_red = Item.insert(db, name="Item 1", color="red")
        item_blue = Item.insert(db, name="Item 2", color="blue")
        # List 1 has a non-red/blue? has blue only → does not match ni red,blue
        # Actually ni ["red"] → list with blue matches
        list1 = ItemList.insert(db, name="List 1", items=[item_red, item_blue])
        ItemList.insert(db, name="List 2", items=[item_red])

        lists = ItemList.list(db, **{"items.color__ni": ["red"]})

        assert lists == [list1]

    def test_nested_dict_filter(self, db):
        item_red = Item.insert(db, name="Item 1", color="red")
        item_blue = Item.insert(db, name="Item 2", color="blue")
        list1 = ItemList.insert(db, name="List 1", items=[item_red, item_blue])
        ItemList.insert(db, name="List 2", items=[item_red])

        lists = ItemList.list(db, filter={"items": {"color__ni": ["red"]}})

        assert lists == [list1]

    def test_nested_deep_dotted_path(self, db):
        item1 = Item.insert(db, name="Item 1", color="red")
        item2 = Item.insert(db, name="Item 2", color="blue")
        ItemList.insert(db, name="List 1", items=[item1])
        list2 = ItemList.insert(db, name="List 2", items=[item2])
        Tag.insert(db, name="expensive", items=[item1])
        Tag.insert(db, name="cheap", items=[item2])

        lists = ItemList.list(db, **{"items.tags.name__ni": ["expensive"]})

        assert lists == [list2]

    def test_belongs_to_relationship(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        Item.insert(db, name="Phone", color="red", item_type=electronics)
        shirt = Item.insert(db, name="Shirt", color="blue", item_type=clothing)

        items = Item.list(db, **{"item_type.name__ni": ["Electronics"]})

        assert items == [shirt]


# ---------------------------------------------------------------------------
# Value shapes — None, empty string, numbers, datetimes
# ---------------------------------------------------------------------------


class TestListNiValueShapes:
    def test_null_column_excluded_for_nonempty_list(self, db):
        """NULL NOT IN ('red','blue') is unknown → row excluded."""
        item_green = Item.insert(db, name="Item 1", color="green", price=10)
        Item.insert(db, name="Item 2", color=None, price=20)
        Item.insert(db, name="Item 3", color="red", price=30)

        items = Item.list(db, color__ni=["red", "blue"])

        assert items == [item_green]

    def test_none_in_list_matches_nothing(self, db):
        """NOT IN (... NULL ...) is never true in SQL."""
        Item.insert(db, name="Item 1", color="red", price=10)
        Item.insert(db, name="Item 2", color="blue", price=20)
        Item.insert(db, name="Item 3", color=None, price=30)

        assert Item.list(db, color__ni=["red", None]) == []

    def test_empty_list_includes_null(self, db):
        """NOT IN () matches all rows, including NULL columns."""
        item_red = Item.insert(db, name="Item 1", color="red", price=10)
        item_null = Item.insert(db, name="Item 2", color=None, price=20)

        assert set(Item.list(db, color__ni=[])) == {item_red, item_null}

    def test_none_filter_value_rejected(self, db):
        """color__ni=None is not a valid IN expression list."""
        Item.insert(db, name="Item 1", color="red", price=10)

        with pytest.raises(ArgumentError):
            Item.list(db, color__ni=None)

    def test_empty_string(self, db):
        item_empty = Item.insert(db, name="", color="red", price=10)
        item_named = Item.insert(db, name="Item 2", color="blue", price=20)

        assert Item.list(db, name__ni=[""]) == [item_named]
        assert item_empty not in Item.list(db, name__ni=[""])

    def test_integer(self, db):
        item1 = Item.insert(db, name="Item 1", color="red", price=10)
        item2 = Item.insert(db, name="Item 2", color="blue", price=20)

        assert Item.list(db, price__ni=[10]) == [item2]
        assert item1 not in Item.list(db, price__ni=[10])

    def test_datetime(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        moment_naive = moment.replace(tzinfo=None)
        other_naive = other.replace(tzinfo=None)

        item1 = Item.insert(db, name="Item 1", color="red", created_at=moment_naive)
        item2 = Item.insert(db, name="Item 2", color="blue", created_at=other_naive)

        assert Item.list(db, created_at__ni=[moment_naive]) == [item2]
        assert item1 not in Item.list(db, created_at__ni=[moment_naive])
