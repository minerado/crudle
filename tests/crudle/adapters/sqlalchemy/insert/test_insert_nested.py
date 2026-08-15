"""Nested insert associations — SQLAlchemy adapter.

The hard surface: dict creates, existing instance / ``{id:}`` links,
mixed payloads, deep nests, and “link by id does not update”.
"""

import pytest
from sqlalchemy.exc import NoResultFound

from tests.models import Item, ItemList, ItemType, Tag


class TestInsertNestedBelongsTo:
    def test_existing_instance(self, db):
        lst = ItemList.insert(db, name="L1")

        item = Item.insert(db, color="red", item_list=lst)

        assert item.item_list_id == lst.id
        assert item.item_list.name == "L1"

    def test_new_dict(self, db):
        item = Item.insert(db, color="red", item_list={"name": "L1"})

        assert item.item_list.name == "L1"
        assert ItemList.count(db) == 1

    def test_existing_by_id_dict(self, db):
        lst = ItemList.insert(db, name="L1")

        item = Item.insert(db, color="red", item_list={"id": lst.id})

        assert item.item_list_id == lst.id
        assert ItemList.count(db) == 1

    def test_missing_id_raises(self, db):
        with pytest.raises(NoResultFound, match="ItemList"):
            Item.insert(db, color="red", item_list={"id": 999})

        assert Item.count(db) == 0

    def test_new_dict_with_nested_children(self, db):
        """Singular create dicts recurse like list members."""
        item = Item.insert(
            db,
            color="red",
            item_list={
                "name": "L1",
                "items": [{"color": "blue"}, {"color": "green"}],
            },
        )

        assert item.item_list.name == "L1"
        # Parent is also linked via back_populates → 3 items on the list.
        assert {i.color for i in item.item_list.items} == {"red", "blue", "green"}
        assert Item.count(db) == 3
        assert ItemList.count(db) == 1

    def test_one_to_one_new(self, db):
        item = Item.insert(db, color="red", item_type={"name": "Electronics"})

        assert item.item_type.name == "Electronics"
        assert ItemType.count(db) == 1


class TestInsertNestedHasMany:
    def test_new_children(self, db):
        lst = ItemList.insert(
            db,
            name="L1",
            items=[{"color": "red"}, {"color": "blue"}],
        )

        assert len(lst.items) == 2
        assert Item.count(db) == 2

    def test_existing_children(self, db):
        a = Item.insert(db, color="red")
        b = Item.insert(db, color="blue")

        lst = ItemList.insert(db, name="L1", items=[a, b])

        assert {i.id for i in lst.items} == {a.id, b.id}

    def test_existing_by_id_dict(self, db):
        a = Item.insert(db, color="red")

        lst = ItemList.insert(db, name="L1", items=[{"id": a.id}])

        assert lst.items[0].id == a.id
        assert Item.count(db) == 1

    def test_missing_child_id_raises(self, db):
        with pytest.raises(NoResultFound, match="Item"):
            ItemList.insert(db, name="L1", items=[{"id": 999}])

        assert ItemList.count(db) == 0
        assert Item.count(db) == 0

    def test_empty_list(self, db):
        lst = ItemList.insert(db, name="L1", items=[])

        assert lst.items == []
        assert Item.count(db) == 0


class TestInsertNestedM2M:
    def test_new_tags_on_item(self, db):
        item = Item.insert(
            db, color="red", tags=[{"name": "sale"}, {"name": "new"}]
        )

        assert {t.name for t in item.tags} == {"sale", "new"}
        assert Tag.count(db) == 2

    def test_existing_tags(self, db):
        t1 = Tag.insert(db, name="sale")
        t2 = Tag.insert(db, name="new")

        item = Item.insert(db, color="red", tags=[t1, t2])

        assert {t.id for t in item.tags} == {t1.id, t2.id}

    def test_tag_with_items(self, db):
        a = Item.insert(db, color="red")

        tag = Tag.insert(db, name="sale", items=[a, {"color": "blue"}])

        assert len(tag.items) == 2
        assert Item.count(db) == 2


class TestInsertNestedDeep:
    def test_list_items_with_new_tags(self, db):
        lst = ItemList.insert(
            db,
            name="L1",
            items=[
                {"color": "red", "tags": [{"name": "tag_1"}]},
                {"color": "blue", "tags": [{"name": "tag_2"}]},
            ],
        )

        assert lst.items[0].tags[0].name == "tag_1"
        assert lst.items[1].tags[0].name == "tag_2"
        assert Tag.count(db) == 2

    def test_list_items_with_existing_tags(self, db):
        t1 = Tag.insert(db, name="tag_1")
        t2 = Tag.insert(db, name="tag_2")

        lst = ItemList.insert(
            db,
            name="L1",
            items=[
                {"color": "red", "tags": [t1]},
                {"color": "blue", "tags": [t2]},
            ],
        )

        assert lst.items[0].tags[0].id == t1.id
        assert lst.items[1].tags[0].id == t2.id

    def test_mixed_existing_instance_id_dict_and_new(self, db):
        t1 = Tag.insert(db, name="tag_1")
        t2 = Tag.insert(db, name="tag_2")

        lst = ItemList.insert(
            db,
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
        assert Tag.count(db) == 3

    def test_link_by_id_does_not_update_existing(self, db):
        tag = Tag.insert(db, name="tag_1")

        lst = ItemList.insert(
            db,
            name="L1",
            items=[{"color": "red", "tags": [{"id": tag.id, "name": "renamed"}]}],
        )

        assert lst.items[0].tags[0].name == "tag_1"
        assert Tag.get(db, tag.id).name == "tag_1"
        assert Tag.count(db) == 1

    def test_deep_item_type_under_list(self, db):
        lst = ItemList.insert(
            db,
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
        assert ItemType.count(db) == 1
