"""Insert commit=False — SQLAlchemy adapter.

Assumes the test session uses ``autoflush=False`` (see ``tests/conftest.py``):
pending rows stay invisible to ``count`` / ``list`` until ``db.commit()``
(or an explicit flush). Primary keys are assigned on flush, not magically
only on commit.
"""

from tests.models import Item, ItemList, ItemType, Tag


class TestInsertCommitFalse:
    def test_scalar_not_persisted_until_commit(self, db):
        item = Item.insert(db, color="red", commit=False)

        assert item.color == "red"
        assert item.id is None
        assert Item.count(db) == 0

        db.commit()

        assert item.id is not None
        assert Item.count(db) == 1

    def test_belongs_to_new_not_persisted(self, db):
        item = Item.insert(
            db, color="red", item_type={"name": "type_1"}, commit=False
        )

        assert item.item_type.name == "type_1"
        assert item.id is None
        assert item.item_type.id is None
        assert ItemType.count(db) == 0

        db.commit()

        assert item.id is not None
        assert item.item_type.id is not None
        assert ItemType.count(db) == 1

    def test_has_many_new_not_persisted(self, db):
        lst = ItemList.insert(
            db,
            name="L1",
            items=[{"color": "red"}, {"color": "blue"}],
            commit=False,
        )

        assert len(lst.items) == 2
        assert lst.id is None
        assert lst.items[0].id is None
        assert Item.count(db) == 0

        db.commit()

        assert lst.id is not None
        assert Item.count(db) == 2

    def test_m2m_new_not_persisted(self, db):
        item = Item.insert(
            db,
            color="red",
            tags=[{"name": "tag_1"}, {"name": "tag_2"}],
            commit=False,
        )

        assert len(item.tags) == 2
        assert item.tags[0].id is None
        assert Tag.count(db) == 0

        db.commit()

        assert item.id is not None
        assert Tag.count(db) == 2

    def test_mixed_belongs_to_and_m2m_not_persisted(self, db):
        item = Item.insert(
            db,
            color="red",
            item_type={"name": "Electronics"},
            tags=[{"name": "sale"}, {"name": "new"}],
            commit=False,
        )

        assert item.item_type.name == "Electronics"
        assert {t.name for t in item.tags} == {"sale", "new"}
        assert item.id is None
        assert item.item_type.id is None
        assert all(t.id is None for t in item.tags)
        assert Item.count(db) == 0
        assert ItemType.count(db) == 0
        assert Tag.count(db) == 0

        db.commit()

        assert item.id is not None
        assert item.item_type.id is not None
        assert ItemType.count(db) == 1
        assert Tag.count(db) == 2

    def test_empty_relationships(self, db):
        item = Item.insert(db, color="red", tags=[], commit=False)

        assert item.tags == []
        assert item.id is None
        assert Item.count(db) == 0
        assert Tag.count(db) == 0

        db.commit()

        assert item.id is not None
        assert Item.count(db) == 1

    def test_deep_nested_not_persisted(self, db):
        lst = ItemList.insert(
            db,
            name="L1",
            items=[
                {"color": "red", "tags": [{"name": "t1"}]},
                {"color": "blue", "item_type": {"name": "type_1"}},
            ],
            commit=False,
        )

        assert lst.id is None
        assert len(lst.items) == 2
        assert lst.items[0].color == "red"
        assert lst.items[0].tags[0].name == "t1"
        assert lst.items[1].item_type.name == "type_1"
        assert all(i.id is None for i in lst.items)
        assert lst.items[0].tags[0].id is None
        assert lst.items[1].item_type.id is None
        assert Item.count(db) == 0
        assert Tag.count(db) == 0
        assert ItemType.count(db) == 0

        db.commit()

        assert lst.id is not None
        assert Item.count(db) == 2
        assert Tag.count(db) == 1
        assert ItemType.count(db) == 1
        assert lst.items[0].tags[0].id is not None
        assert lst.items[1].item_type.id is not None

    def test_link_existing_not_duplicated_on_commit(self, db):
        tag = Tag.insert(db, name="sale")

        item = Item.insert(db, color="red", tags=[{"id": tag.id}], commit=False)

        assert Tag.count(db) == 1
        assert item.tags[0].id == tag.id

        db.commit()

        assert item.id is not None
        assert Tag.count(db) == 1
        assert item.tags[0].id == tag.id

    def test_commit_true_persists(self, db):
        item = Item.insert(db, color="red", commit=True)

        assert item.id is not None
        assert Item.count(db) == 1
