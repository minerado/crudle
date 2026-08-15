"""List association / relationship filters — SQLAlchemy adapter.

Owns filtering *through* associations (the core Crudle dialect), not per-operator
value matrices (those stay in ``test_list_eq`` / ``gt`` / …).

Sections:

- Cardinality — has-many, belongs-to / to-one, many-to-many
- Match semantics — any-match, empty/missing, dedupe, same-row AND
- Spellings — dotted, dotted+op, nested dict, deep multi-hop
- Operators on assoc paths — one representative per op family
- Edges — NULL related scalars, invalid path, root + assoc
- Combos — light sort / limit / select with assoc filters

Default ``distinct_on=True`` applies SQL ``DISTINCT``, so join fan-out does not
duplicate parents in entity ``list`` results.
"""

import pytest
from sqlalchemy.exc import ArgumentError

from tests.models import Item, ItemList, ItemTag, ItemType, Tag

# ---------------------------------------------------------------------------
# Cardinality
# ---------------------------------------------------------------------------


class TestListAssocCardinality:
    def test_has_many(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        blue = Item.insert(db, name="blue", color="blue", price=20)
        list1 = ItemList.insert(db, name="L1", items=[red, blue])
        ItemList.insert(db, name="L2", items=[blue])

        lists = ItemList.list(db, **{"items.color": "red"})

        assert lists == [list1]

    def test_belongs_to(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        clothing = ItemType.insert(db, name="Clothing")
        phone = Item.insert(db, name="Phone", color="red", item_type=electronics)
        Item.insert(db, name="Shirt", color="blue", item_type=clothing)

        items = Item.list(db, **{"item_type.name": "Electronics"})

        assert items == [phone]

    def test_many_to_many(self, db):
        gadget = Item.insert(db, name="Gadget", color="red", price=10)
        cloth = Item.insert(db, name="Cloth", color="blue", price=20)
        Tag.insert(db, name="sale", items=[gadget])
        Tag.insert(db, name="new", items=[cloth])

        items = Item.list(db, **{"tags.name": "sale"})

        assert items == [gadget]

    def test_many_to_many_reverse(self, db):
        gadget = Item.insert(db, name="Gadget", color="red", price=10)
        cloth = Item.insert(db, name="Cloth", color="blue", price=20)
        sale = Tag.insert(db, name="sale", items=[gadget])
        Tag.insert(db, name="new", items=[cloth])

        tags = Tag.list(db, **{"items.name": "Gadget"})

        assert tags == [sale]

    def test_association_object_path(self, db):
        gadget = Item.insert(db, name="Gadget", color="red", price=10)
        sale = Tag.insert(db, name="sale")
        ItemTag.insert(db, item=gadget, tag=sale)
        other = Item.insert(db, name="Other", color="blue", price=20)
        Tag.insert(db, name="new", items=[other])

        items = Item.list(db, **{"item_tags.tag.name": "sale"})

        assert [item.id for item in items] == [gadget.id]


# ---------------------------------------------------------------------------
# Match semantics
# ---------------------------------------------------------------------------


class TestListAssocMatchSemantics:
    def test_any_match_not_all_match(self, db):
        """Parent matches when any related row qualifies (mixed children)."""
        red = Item.insert(db, name="red", color="red", price=10)
        blue = Item.insert(db, name="blue", color="blue", price=20)
        list1 = ItemList.insert(db, name="L1", items=[red, blue])

        lists = ItemList.list(db, **{"items.color": "red"})

        assert lists == [list1]

    def test_empty_collection_does_not_match(self, db):
        ItemList.insert(db, name="Empty", items=[])
        red = Item.insert(db, name="red", color="red", price=10)
        ItemList.insert(db, name="Full", items=[red])

        lists = ItemList.list(db, **{"items.color": "red"})

        assert len(lists) == 1
        assert lists[0].name == "Full"

    def test_missing_to_one_does_not_match(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        Item.insert(db, name="Phone", color="red", item_type=electronics)
        Item.insert(db, name="Orphan", color="blue", item_type=None)

        items = Item.list(db, **{"item_type.name": "Electronics"})

        assert len(items) == 1
        assert items[0].name == "Phone"

    def test_parent_dedupe_under_join_fanout(self, db):
        """Two matching children still yield one parent (DISTINCT default)."""
        a = Item.insert(db, name="a", color="red", price=1)
        b = Item.insert(db, name="b", color="red", price=2)
        list1 = ItemList.insert(db, name="L1", items=[a, b])

        lists = ItemList.list(db, **{"items.color": "red"})

        assert lists == [list1]
        assert len(lists) == 1

    def test_same_row_and_on_collection(self, db):
        """``items.color`` + ``items.price__gt`` must hold on one child, not two."""
        red_cheap = Item.insert(db, name="rc", color="red", price=5)
        blue_expensive = Item.insert(db, name="be", color="blue", price=50)
        split = ItemList.insert(
            db, name="Split", items=[red_cheap, blue_expensive]
        )
        red_expensive = Item.insert(db, name="re", color="red", price=50)
        together = ItemList.insert(db, name="Together", items=[red_expensive])

        lists = ItemList.list(
            db,
            **{"items.color": "red", "items.price__gt": 15},
        )

        assert lists == [together]
        assert split not in lists

    def test_same_row_and_deep_path(self, db):
        """Deep hop AND: one item that is red and tagged expensive."""
        red_expensive = Item.insert(db, name="re", color="red", price=10)
        red_cheap = Item.insert(db, name="rc", color="red", price=10)
        blue_expensive = Item.insert(db, name="be", color="blue", price=10)
        Tag.insert(db, name="expensive", items=[red_expensive, blue_expensive])
        Tag.insert(db, name="cheap", items=[red_cheap])

        together = ItemList.insert(db, name="Together", items=[red_expensive])
        ItemList.insert(db, name="SplitColor", items=[red_cheap])
        ItemList.insert(db, name="SplitTag", items=[blue_expensive])

        lists = ItemList.list(
            db,
            **{"items.color": "red", "items.tags.name": "expensive"},
        )

        assert lists == [together]

    def test_cross_assoc_and_with_root(self, db):
        keep_item = Item.insert(db, name="keep-child", color="red", price=10)
        drop_item = Item.insert(db, name="drop-child", color="red", price=10)
        ItemList.insert(db, name="Keep", items=[keep_item])
        ItemList.insert(db, name="Drop", items=[drop_item])

        lists = ItemList.list(
            db,
            name="Keep",
            **{"items.color": "red"},
        )

        assert len(lists) == 1
        assert lists[0].name == "Keep"

    def test_no_match_returns_empty(self, db):
        blue = Item.insert(db, name="blue", color="blue", price=10)
        ItemList.insert(db, name="L1", items=[blue])

        assert ItemList.list(db, **{"items.color": "red"}) == []


# ---------------------------------------------------------------------------
# Spellings
# ---------------------------------------------------------------------------


class TestListAssocSpellings:
    def test_dotted(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        list1 = ItemList.insert(db, name="L1", items=[red])
        ItemList.insert(db, name="L2", items=[])

        assert ItemList.list(db, **{"items.color": "red"}) == [list1]

    def test_dotted_with_operator(self, db):
        cheap = Item.insert(db, name="cheap", color="red", price=10)
        expensive = Item.insert(db, name="expensive", color="blue", price=20)
        list1 = ItemList.insert(db, name="L1", items=[cheap, expensive])
        ItemList.insert(db, name="L2", items=[cheap])

        lists = ItemList.list(db, **{"items.price__gt": 15})

        assert lists == [list1]

    def test_nested_dict_filter(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        list1 = ItemList.insert(db, name="L1", items=[red])
        ItemList.insert(db, name="L2", items=[])

        lists = ItemList.list(db, filter={"items": {"color": "red"}})

        assert lists == [list1]

    def test_nested_dict_deep(self, db):
        item = Item.insert(db, name="Gadget", color="red", price=10)
        list1 = ItemList.insert(db, name="L1", items=[item])
        ItemList.insert(db, name="L2", items=[])
        Tag.insert(db, name="expensive", items=[item])

        lists = ItemList.list(
            db, filter={"items": {"tags": {"name": "expensive"}}}
        )

        assert lists == [list1]

    def test_deep_dotted_path(self, db):
        item1 = Item.insert(db, name="Item 1", color="red")
        item2 = Item.insert(db, name="Item 2", color="blue")
        list1 = ItemList.insert(db, name="L1", items=[item1])
        ItemList.insert(db, name="L2", items=[item2])
        Tag.insert(db, name="expensive", items=[item1])
        Tag.insert(db, name="cheap", items=[item2])

        lists = ItemList.list(db, **{"items.tags.name": "expensive"})

        assert lists == [list1]

    def test_belongs_to_dotted(self, db):
        electronics = ItemType.insert(db, name="Electronics")
        phone = Item.insert(db, name="Phone", color="red", item_type=electronics)
        Item.insert(db, name="Other", color="blue")

        assert Item.list(db, **{"item_type.name": "Electronics"}) == [phone]


# ---------------------------------------------------------------------------
# Operators on assoc paths (representatives)
# ---------------------------------------------------------------------------


class TestListAssocOperators:
    def test_eq(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        list1 = ItemList.insert(db, name="L1", items=[red])
        ItemList.insert(db, name="L2", items=[])

        assert ItemList.list(db, **{"items.color__eq": "red"}) == [list1]

    def test_ne(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        blue = Item.insert(db, name="blue", color="blue", price=20)
        only_red = ItemList.insert(db, name="OnlyRed", items=[red])
        has_blue = ItemList.insert(db, name="HasBlue", items=[red, blue])

        lists = ItemList.list(db, **{"items.color__ne": "red"})

        assert has_blue in lists
        assert only_red not in lists

    def test_gt(self, db):
        cheap = Item.insert(db, name="cheap", color="red", price=10)
        expensive = Item.insert(db, name="expensive", color="blue", price=20)
        list1 = ItemList.insert(db, name="L1", items=[expensive])
        ItemList.insert(db, name="L2", items=[cheap])

        assert ItemList.list(db, **{"items.price__gt": 15}) == [list1]

    def test_in(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        green = Item.insert(db, name="green", color="green", price=20)
        list1 = ItemList.insert(db, name="L1", items=[red])
        ItemList.insert(db, name="L2", items=[green])

        lists = ItemList.list(db, **{"items.color__in": ["red", "blue"]})

        assert lists == [list1]

    def test_ni(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        green = Item.insert(db, name="green", color="green", price=20)
        list1 = ItemList.insert(db, name="L1", items=[green])
        ItemList.insert(db, name="L2", items=[red])

        lists = ItemList.list(db, **{"items.color__ni": ["red", "blue"]})

        assert lists == [list1]


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


class TestListAssocEdges:
    def test_null_related_scalar(self, db):
        null_color = Item.insert(db, name="nullish", color=None, price=10)
        red = Item.insert(db, name="red", color="red", price=20)
        list1 = ItemList.insert(db, name="L1", items=[null_color])
        ItemList.insert(db, name="L2", items=[red])

        lists = ItemList.list(db, **{"items.color": None})

        assert lists == [list1]

    def test_invalid_path_raises_or_errors(self, db):
        Item.insert(db, name="x", color="red", price=10)

        with pytest.raises((AttributeError, ArgumentError, Exception)):
            Item.list(db, **{"no_such_rel.name": "x"})

    def test_root_and_assoc_together(self, db):
        a = Item.insert(db, name="keep-child", color="red", price=10)
        b = Item.insert(db, name="drop-child", color="red", price=10)
        keep = ItemList.insert(db, name="Keep", items=[a])
        ItemList.insert(db, name="Drop", items=[b])

        lists = ItemList.list(db, name="Keep", **{"items.color": "red"})

        assert lists == [keep]


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------


class TestListAssocCombos:
    def test_assoc_filter_with_sort(self, db):
        cheap = Item.insert(db, name="cheap", color="red", price=10)
        mid = Item.insert(db, name="mid", color="red", price=20)
        ItemList.insert(db, name="B", items=[mid])
        ItemList.insert(db, name="A", items=[cheap])

        lists = ItemList.list(
            db,
            **{"items.color": "red"},
            sort=[{"field": "name", "order": "asc"}],
        )

        assert [lst.name for lst in lists] == ["A", "B"]

    def test_assoc_filter_with_limit(self, db):
        for i in range(3):
            item = Item.insert(db, name=f"i{i}", color="red", price=10)
            ItemList.insert(db, name=f"L{i}", items=[item])

        lists = ItemList.list(
            db,
            **{"items.color": "red"},
            sort=[{"field": "name", "order": "asc"}],
            limit=2,
        )

        assert [lst.name for lst in lists] == ["L0", "L1"]

    def test_assoc_filter_with_select(self, db):
        red = Item.insert(db, name="red", color="red", price=10)
        ItemList.insert(db, name="L1", items=[red])
        ItemList.insert(db, name="L2", items=[])

        rows = ItemList.list(
            db,
            **{"items.color": "red"},
            select=["name"],
        )

        assert len(rows) == 1
        assert rows[0]["name"] == "L1"
