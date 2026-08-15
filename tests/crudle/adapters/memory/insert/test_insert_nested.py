"""Nested insert associations — Memory adapter.

Twin of SQLAlchemy ``insert/test_insert_nested.py``.
"""

import pytest

from src.crudle.adapters.memory.adapter import NotLoaded
from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


class TestInsertNestedBelongsTo:
    def test_existing_instance(self, db):
        lst = db.insert(ItemList, name="L1")

        item = db.insert(Item, color="red", item_list=lst)

        assert item.item_list_id == lst.id
        assert item.item_list.name == "L1"

    def test_new_dict(self, db):
        item = db.insert(Item, color="red", item_list={"name": "L1"})

        assert item.item_list.name == "L1"
        assert item.item_list.id is not None
        assert db.count(ItemList) == 1

    def test_existing_by_id_dict(self, db):
        lst = db.insert(ItemList, name="L1")

        item = db.insert(Item, color="red", item_list={"id": lst.id})

        assert item.item_list_id == lst.id
        assert db.count(ItemList) == 1

    def test_missing_id_raises(self, db):
        with pytest.raises(ValueError, match="ItemList"):
            db.insert(Item, color="red", item_list={"id": 999})

        assert db.count(Item) == 0

    def test_new_dict_with_nested_children(self, db):
        item = db.insert(
            Item,
            color="red",
            item_list={
                "name": "L1",
                "items": [{"color": "blue"}, {"color": "green"}],
            },
        )

        assert item.item_list.name == "L1"
        assert {i.color for i in item.item_list.items} == {"blue", "green"}
        assert db.count(Item) == 3
        assert db.count(ItemList) == 1

    def test_one_to_one_new(self, db):
        item = db.insert(Item, color="red", item_type={"name": "Electronics"})

        assert item.item_type.name == "Electronics"
        assert db.count(ItemType) == 1


class TestInsertNestedHasMany:
    def test_new_children(self, db):
        lst = db.insert(
            ItemList,
            name="L1",
            items=[{"color": "red"}, {"color": "blue"}],
        )

        assert len(lst.items) == 2
        assert db.count(Item) == 2

    def test_existing_children(self, db):
        a = db.insert(Item, color="red")
        b = db.insert(Item, color="blue")

        lst = db.insert(ItemList, name="L1", items=[a, b])

        assert {i.id for i in lst.items} == {a.id, b.id}

    def test_existing_by_id_dict(self, db):
        a = db.insert(Item, color="red")

        lst = db.insert(ItemList, name="L1", items=[{"id": a.id}])

        assert lst.items[0].id == a.id
        assert db.count(Item) == 1

    def test_missing_child_id_raises(self, db):
        with pytest.raises(ValueError, match="Item"):
            db.insert(ItemList, name="L1", items=[{"id": 999}])

        assert db.count(ItemList) == 0

    def test_partial_nested_failure_rolls_back_orphans(self, db):
        """Earlier nested creates must not survive a later missing-id failure."""
        with pytest.raises(ValueError, match="Item"):
            db.insert(
                ItemList,
                name="L1",
                items=[{"color": "red"}, {"id": 999}],
            )

        assert db.count(ItemList) == 0
        assert db.count(Item) == 0

    def test_empty_list(self, db):
        lst = db.insert(ItemList, name="L1", items=[])

        assert lst.items == []
        assert db.count(Item) == 0


class TestInsertNestedM2M:
    def test_new_tags_on_item(self, db):
        item = db.insert(
            Item, color="red", tags=[{"name": "sale"}, {"name": "new"}]
        )

        assert {t.name for t in item.tags} == {"sale", "new"}
        assert db.count(Tag) == 2

    def test_existing_tags(self, db):
        t1 = db.insert(Tag, name="sale")
        t2 = db.insert(Tag, name="new")

        item = db.insert(Item, color="red", tags=[t1, t2])

        assert {t.id for t in item.tags} == {t1.id, t2.id}

    def test_tag_with_items(self, db):
        a = db.insert(Item, color="red")

        tag = db.insert(Tag, name="sale", items=[a, {"color": "blue"}])

        assert len(tag.items) == 2
        assert db.count(Item) == 2

    def test_reverse_keeps_prior_links_with_stale_notloaded_copy(self, db):
        item = db.insert(Item, name="gadget", color="red")
        assert isinstance(item.tags, NotLoaded)

        db.insert(Tag, name="sale", items=[item])
        db.insert(Tag, name="new", items=[item])

        stored = db.get(Item, item.id, preload=["tags"])
        assert {t.name for t in stored.tags} == {"sale", "new"}


class TestInsertNestedDeep:
    def test_list_items_with_new_tags(self, db):
        lst = db.insert(
            ItemList,
            name="L1",
            items=[
                {"color": "red", "tags": [{"name": "tag_1"}]},
                {"color": "blue", "tags": [{"name": "tag_2"}]},
            ],
        )

        assert lst.items[0].tags[0].name == "tag_1"
        assert lst.items[1].tags[0].name == "tag_2"
        assert db.count(Tag) == 2

    def test_list_items_with_existing_tags(self, db):
        t1 = db.insert(Tag, name="tag_1")
        t2 = db.insert(Tag, name="tag_2")

        lst = db.insert(
            ItemList,
            name="L1",
            items=[
                {"color": "red", "tags": [t1]},
                {"color": "blue", "tags": [t2]},
            ],
        )

        assert lst.items[0].tags[0].id == t1.id
        assert lst.items[1].tags[0].id == t2.id

    def test_mixed_existing_instance_id_dict_and_new(self, db):
        t1 = db.insert(Tag, name="tag_1")
        t2 = db.insert(Tag, name="tag_2")

        lst = db.insert(
            ItemList,
            name="L1",
            items=[
                {"color": "red", "tags": [t1]},
                {
                    "color": "blue",
                    "tags": [{"id": t2.id}, {"name": "tag_3"}],
                },
            ],
        )

        assert lst.items[0].tags[0].id == t1.id
        assert lst.items[1].tags[0].id == t2.id
        assert lst.items[1].tags[1].name == "tag_3"
        assert db.count(Tag) == 3

    def test_link_by_id_does_not_update_existing(self, db):
        tag = db.insert(Tag, name="tag_1")

        lst = db.insert(
            ItemList,
            name="L1",
            items=[{"color": "red", "tags": [{"id": tag.id, "name": "renamed"}]}],
        )

        assert lst.items[0].tags[0].name == "tag_1"
        assert db.get(Tag, tag.id).name == "tag_1"
        assert db.count(Tag) == 1

    def test_deep_item_type_under_list(self, db):
        lst = db.insert(
            ItemList,
            name="L1",
            items=[
                {
                    "color": "red",
                    "item_type": {"name": "Electronics"},
                    "tags": [{"name": "sale"}],
                }
            ],
        )

        assert lst.items[0].item_type.name == "Electronics"
        assert lst.items[0].tags[0].name == "sale"
        assert db.count(ItemType) == 1
