"""List association / relationship filters — Memory adapter.

Twin of SQLAlchemy ``test_list_assoc.py`` where contracts align.

Nested filters that share a relationship prefix must be satisfied by the same
related row (SQLAlchemy join semantics). Memory Item has no ``item_tags``
association-object path; use ``tags`` for M:N.

Invalid association paths return no rows (no raise); SA typically errors.
"""

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag

# ---------------------------------------------------------------------------
# Cardinality
# ---------------------------------------------------------------------------


class TestListAssocCardinality:
    def test_has_many(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        blue = db.insert(Item, name="blue", color="blue", price=20)
        list1 = db.insert(ItemList, name="L1", items=[red, blue])
        db.insert(ItemList, name="L2", items=[blue])

        lists = db.list(ItemList, **{"items.color": "red"}, limit=100)

        assert [lst.id for lst in lists] == [list1.id]

    def test_belongs_to(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        phone = db.insert(Item, name="Phone", color="red", item_type=electronics)
        db.insert(Item, name="Shirt", color="blue", item_type=clothing)

        items = db.list(Item, **{"item_type.name": "Electronics"}, limit=100)

        assert [item.id for item in items] == [phone.id]

    def test_many_to_many(self, db):
        gadget = db.insert(Item, name="Gadget", color="red", price=10)
        cloth = db.insert(Item, name="Cloth", color="blue", price=20)
        db.insert(Tag, name="sale", items=[gadget])
        db.insert(Tag, name="new", items=[cloth])

        items = db.list(Item, **{"tags.name": "sale"}, limit=100)

        assert [item.id for item in items] == [gadget.id]

    def test_many_to_many_reverse(self, db):
        gadget = db.insert(Item, name="Gadget", color="red", price=10)
        cloth = db.insert(Item, name="Cloth", color="blue", price=20)
        sale = db.insert(Tag, name="sale", items=[gadget])
        db.insert(Tag, name="new", items=[cloth])

        tags = db.list(Tag, **{"items.name": "Gadget"}, limit=100)

        assert [tag.id for tag in tags] == [sale.id]


# ---------------------------------------------------------------------------
# Match semantics
# ---------------------------------------------------------------------------


class TestListAssocMatchSemantics:
    def test_any_match_not_all_match(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        blue = db.insert(Item, name="blue", color="blue", price=20)
        list1 = db.insert(ItemList, name="L1", items=[red, blue])

        lists = db.list(ItemList, **{"items.color": "red"}, limit=100)

        assert [lst.id for lst in lists] == [list1.id]

    def test_empty_collection_does_not_match(self, db):
        db.insert(ItemList, name="Empty", items=[])
        red = db.insert(Item, name="red", color="red", price=10)
        db.insert(ItemList, name="Full", items=[red])

        lists = db.list(ItemList, **{"items.color": "red"}, limit=100)

        assert len(lists) == 1
        assert lists[0].name == "Full"

    def test_missing_to_one_does_not_match(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        db.insert(Item, name="Phone", color="red", item_type=electronics)
        db.insert(Item, name="Orphan", color="blue", item_type=None)

        items = db.list(Item, **{"item_type.name": "Electronics"}, limit=100)

        assert len(items) == 1
        assert items[0].name == "Phone"

    def test_parent_dedupe_under_collection_fanout(self, db):
        a = db.insert(Item, name="a", color="red", price=1)
        b = db.insert(Item, name="b", color="red", price=2)
        list1 = db.insert(ItemList, name="L1", items=[a, b])

        lists = db.list(ItemList, **{"items.color": "red"}, limit=100)

        assert len(lists) == 1
        assert lists[0].id == list1.id

    def test_same_row_and_on_collection(self, db):
        """``items.color`` + ``items.price__gt`` must hold on one child, not two."""
        red_cheap = db.insert(Item, name="rc", color="red", price=5)
        blue_expensive = db.insert(Item, name="be", color="blue", price=50)
        split = db.insert(
            ItemList, name="Split", items=[red_cheap, blue_expensive]
        )
        red_expensive = db.insert(Item, name="re", color="red", price=50)
        together = db.insert(ItemList, name="Together", items=[red_expensive])

        lists = db.list(
            ItemList,
            **{"items.color": "red", "items.price__gt": 15},
            limit=100,
        )

        assert [lst.id for lst in lists] == [together.id]
        assert split.id not in {lst.id for lst in lists}

    def test_same_row_and_deep_path(self, db):
        red_expensive = db.insert(Item, name="re", color="red", price=10)
        red_cheap = db.insert(Item, name="rc", color="red", price=10)
        blue_expensive = db.insert(Item, name="be", color="blue", price=10)
        db.insert(Tag, name="expensive", items=[red_expensive, blue_expensive])
        db.insert(Tag, name="cheap", items=[red_cheap])

        together = db.insert(ItemList, name="Together", items=[red_expensive])
        db.insert(ItemList, name="SplitColor", items=[red_cheap])
        db.insert(ItemList, name="SplitTag", items=[blue_expensive])

        lists = db.list(
            ItemList,
            **{"items.color": "red", "items.tags.name": "expensive"},
            limit=100,
        )

        assert [lst.id for lst in lists] == [together.id]

    def test_cross_assoc_and_with_root(self, db):
        keep_item = db.insert(Item, name="keep-child", color="red", price=10)
        drop_item = db.insert(Item, name="drop-child", color="red", price=10)
        db.insert(ItemList, name="Keep", items=[keep_item])
        db.insert(ItemList, name="Drop", items=[drop_item])

        lists = db.list(
            ItemList,
            name="Keep",
            **{"items.color": "red"},
            limit=100,
        )

        assert len(lists) == 1
        assert lists[0].name == "Keep"

    def test_no_match_returns_empty(self, db):
        blue = db.insert(Item, name="blue", color="blue", price=10)
        db.insert(ItemList, name="L1", items=[blue])

        assert db.list(ItemList, **{"items.color": "red"}, limit=100) == []


# ---------------------------------------------------------------------------
# Spellings
# ---------------------------------------------------------------------------


class TestListAssocSpellings:
    def test_dotted(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        list1 = db.insert(ItemList, name="L1", items=[red])
        db.insert(ItemList, name="L2", items=[])

        lists = db.list(ItemList, **{"items.color": "red"}, limit=100)

        assert [lst.id for lst in lists] == [list1.id]

    def test_dotted_with_operator(self, db):
        cheap = db.insert(Item, name="cheap", color="red", price=10)
        expensive = db.insert(Item, name="expensive", color="blue", price=20)
        list1 = db.insert(ItemList, name="L1", items=[cheap, expensive])
        db.insert(ItemList, name="L2", items=[cheap])

        lists = db.list(ItemList, **{"items.price__gt": 15}, limit=100)

        assert [lst.id for lst in lists] == [list1.id]

    def test_nested_dict_filter(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        list1 = db.insert(ItemList, name="L1", items=[red])
        db.insert(ItemList, name="L2", items=[])

        lists = db.list(
            ItemList, filter={"items": {"color": "red"}}, limit=100
        )

        assert [lst.id for lst in lists] == [list1.id]

    def test_nested_dict_deep(self, db):
        item = db.insert(Item, name="Gadget", color="red", price=10)
        list1 = db.insert(ItemList, name="L1", items=[item])
        db.insert(ItemList, name="L2", items=[])
        db.insert(Tag, name="expensive", items=[item])

        lists = db.list(
            ItemList,
            filter={"items": {"tags": {"name": "expensive"}}},
            limit=100,
        )

        assert [lst.id for lst in lists] == [list1.id]

    def test_deep_dotted_path(self, db):
        item1 = db.insert(Item, name="Item 1", color="red")
        item2 = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="L1", items=[item1])
        db.insert(ItemList, name="L2", items=[item2])
        db.insert(Tag, name="expensive", items=[item1])
        db.insert(Tag, name="cheap", items=[item2])

        lists = db.list(
            ItemList, **{"items.tags.name": "expensive"}, limit=100
        )

        assert [lst.id for lst in lists] == [list1.id]

    def test_belongs_to_dotted(self, db):
        electronics = db.insert(ItemType, name="Electronics")
        phone = db.insert(Item, name="Phone", color="red", item_type=electronics)
        db.insert(Item, name="Other", color="blue")

        items = db.list(Item, **{"item_type.name": "Electronics"}, limit=100)

        assert [item.id for item in items] == [phone.id]


# ---------------------------------------------------------------------------
# Operators on assoc paths (representatives)
# ---------------------------------------------------------------------------


class TestListAssocOperators:
    def test_eq(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        list1 = db.insert(ItemList, name="L1", items=[red])
        db.insert(ItemList, name="L2", items=[])

        lists = db.list(ItemList, **{"items.color__eq": "red"}, limit=100)

        assert [lst.id for lst in lists] == [list1.id]

    def test_ne(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        blue = db.insert(Item, name="blue", color="blue", price=20)
        only_red = db.insert(ItemList, name="OnlyRed", items=[red])
        has_blue = db.insert(ItemList, name="HasBlue", items=[red, blue])

        lists = db.list(ItemList, **{"items.color__ne": "red"}, limit=100)

        assert has_blue.id in {lst.id for lst in lists}
        assert only_red.id not in {lst.id for lst in lists}

    def test_gt(self, db):
        cheap = db.insert(Item, name="cheap", color="red", price=10)
        expensive = db.insert(Item, name="expensive", color="blue", price=20)
        list1 = db.insert(ItemList, name="L1", items=[expensive])
        db.insert(ItemList, name="L2", items=[cheap])

        lists = db.list(ItemList, **{"items.price__gt": 15}, limit=100)

        assert [lst.id for lst in lists] == [list1.id]

    def test_in(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        green = db.insert(Item, name="green", color="green", price=20)
        list1 = db.insert(ItemList, name="L1", items=[red])
        db.insert(ItemList, name="L2", items=[green])

        lists = db.list(
            ItemList, **{"items.color__in": ["red", "blue"]}, limit=100
        )

        assert [lst.id for lst in lists] == [list1.id]

    def test_ni(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        green = db.insert(Item, name="green", color="green", price=20)
        list1 = db.insert(ItemList, name="L1", items=[green])
        db.insert(ItemList, name="L2", items=[red])

        lists = db.list(
            ItemList, **{"items.color__ni": ["red", "blue"]}, limit=100
        )

        assert [lst.id for lst in lists] == [list1.id]


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


class TestListAssocEdges:
    def test_null_related_scalar(self, db):
        null_color = db.insert(Item, name="nullish", color=None, price=10)
        red = db.insert(Item, name="red", color="red", price=20)
        list1 = db.insert(ItemList, name="L1", items=[null_color])
        db.insert(ItemList, name="L2", items=[red])

        lists = db.list(ItemList, **{"items.color": None}, limit=100)

        assert [lst.id for lst in lists] == [list1.id]

    def test_invalid_path_returns_empty(self, db):
        """Memory skips unknown association paths; SA typically raises."""
        db.insert(Item, name="x", color="red", price=10)

        assert db.list(Item, **{"no_such_rel.name": "x"}, limit=100) == []

    def test_root_and_assoc_together(self, db):
        a = db.insert(Item, name="keep-child", color="red", price=10)
        b = db.insert(Item, name="drop-child", color="red", price=10)
        keep = db.insert(ItemList, name="Keep", items=[a])
        db.insert(ItemList, name="Drop", items=[b])

        lists = db.list(
            ItemList, name="Keep", **{"items.color": "red"}, limit=100
        )

        assert [lst.id for lst in lists] == [keep.id]


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------


class TestListAssocCombos:
    def test_assoc_filter_with_sort(self, db):
        cheap = db.insert(Item, name="cheap", color="red", price=10)
        mid = db.insert(Item, name="mid", color="red", price=20)
        db.insert(ItemList, name="B", items=[mid])
        db.insert(ItemList, name="A", items=[cheap])

        lists = db.list(
            ItemList,
            **{"items.color": "red"},
            sort=[{"field": "name", "order": "asc"}],
            limit=100,
        )

        assert [lst.name for lst in lists] == ["A", "B"]

    def test_assoc_filter_with_limit(self, db):
        for i in range(3):
            item = db.insert(Item, name=f"i{i}", color="red", price=10)
            db.insert(ItemList, name=f"L{i}", items=[item])

        lists = db.list(
            ItemList,
            **{"items.color": "red"},
            sort=[{"field": "name", "order": "asc"}],
            limit=2,
        )

        assert [lst.name for lst in lists] == ["L0", "L1"]

    def test_assoc_filter_with_select(self, db):
        red = db.insert(Item, name="red", color="red", price=10)
        db.insert(ItemList, name="L1", items=[red])
        db.insert(ItemList, name="L2", items=[])

        rows = db.list(
            ItemList,
            **{"items.color": "red"},
            select=["name"],
            limit=100,
        )

        assert len(rows) == 1
        assert rows[0]["name"] == "L1"
