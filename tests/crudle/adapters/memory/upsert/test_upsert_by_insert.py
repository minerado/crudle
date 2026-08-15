"""Upsert_by insert-path attr rules — Memory adapter.

Twin of SQLAlchemy ``upsert/test_upsert_by_insert.py``.
"""

from src.crudle.adapters.memory.adapter import NotLoaded
from tests.crudle.adapters.memory.models import Item, ItemList, ItemType


class TestUpsertByInsertAttrs:
    def test_merges_simple_filter_into_insert(self, db):
        result = db.upsert_by(Item, {"color": "red"}, name="a")

        assert result.name == "a"
        assert result.color == "red"
        assert db.count(Item) == 1

    def test_kwargs_win_over_filter_merge(self, db):
        result = db.upsert_by(Item, {"color": "red"}, name="a", color="blue")

        assert result.color == "blue"
        assert db.count(Item) == 1

    def test_merges_nested_filter_spelling(self, db):
        result = db.upsert_by(Item, {"filter": {"color": "green"}}, name="g")

        assert result.color == "green"
        assert result.name == "g"

    def test_does_not_merge_operator_filters(self, db):
        result = db.upsert_by(
            Item, {"color__in": ["red"]}, name="a", color="blue"
        )

        assert result.color == "blue"
        assert result.name == "a"

    def test_does_not_merge_dotted_association_filters(self, db):
        result = db.upsert_by(
            Item,
            {"item_type.name": "missing"},
            name="a",
            color="red",
        )

        assert result.name == "a"
        assert result.color == "red"
        assert result.item_type_id is None
        assert isinstance(result.item_type, NotLoaded)
        assert db.count(ItemType) == 0
        dumped = result.model_dump()
        assert "item_type.name" not in dumped

    def test_does_not_merge_relationship_dict_filters(self, db):
        result = db.upsert_by(
            Item,
            {"item_list": {"name": "Nope"}},
            name="alone",
            color="blue",
        )

        assert result.color == "blue"
        assert result.item_list_id is None
        assert db.count(ItemList) == 0

    def test_on_update_assocs_not_written_as_field(self, db):
        result = db.upsert_by(
            Item,
            {"name": "solo"},
            name="solo",
            color="red",
            on_update_assocs="raise",
        )

        assert result.name == "solo"
        dumped = result.model_dump()
        assert "on_update_assocs" not in dumped

    def test_should_raise_stripped_on_insert(self, db):
        result = db.upsert_by(
            Item, {"color": "z"}, name="n", color="z", should_raise=False
        )

        assert result.color == "z"
        dumped = result.model_dump()
        assert "should_raise" not in dumped

    def test_control_keys_in_filters_not_merged(self, db):
        attrs = db._attrs_for_upsert_insert(
            {
                "color": "red",
                "on_update_assocs": "raise",
                "should_raise": True,
                "item_type.name": "x",
            },
            {"name": "a"},
        )

        assert attrs == {"name": "a", "color": "red"}

    def test_hit_does_not_insert_extra(self, db):
        item = db.insert(Item, name="a", color="red")

        result = db.upsert_by(Item, {"color": "red"}, name="b")

        assert result.id == item.id
        assert db.count(Item) == 1
        assert db.count(ItemList) == 0
