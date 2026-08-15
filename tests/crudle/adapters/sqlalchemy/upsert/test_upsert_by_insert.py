"""Upsert_by insert-path attr rules — SQLAlchemy adapter.

On miss, upsert merges simple filter equality into insert attrs and
must not write update-only control keys as columns.
"""

from tests.models import Item, ItemList, ItemType


class TestUpsertByInsertAttrs:
    def test_merges_simple_filter_into_insert(self, db):
        result = Item.upsert_by(db, {"color": "red"}, name="a")

        assert result.name == "a"
        assert result.color == "red"
        assert Item.count(db) == 1

    def test_kwargs_win_over_filter_merge(self, db):
        result = Item.upsert_by(
            db, {"color": "red"}, name="a", color="blue"
        )

        assert result.color == "blue"
        assert Item.count(db) == 1

    def test_merges_nested_filter_spelling(self, db):
        result = Item.upsert_by(
            db, {"filter": {"color": "green"}}, name="g"
        )

        assert result.color == "green"
        assert result.name == "g"

    def test_does_not_merge_operator_filters(self, db):
        result = Item.upsert_by(
            db, {"color__in": ["red"]}, name="a", color="blue"
        )

        assert result.color == "blue"
        assert result.name == "a"

    def test_does_not_merge_dotted_association_filters(self, db):
        """Association hops are query syntax, not writable columns."""
        result = Item.upsert_by(
            db,
            {"item_type.name": "missing"},
            name="a",
            color="red",
        )

        assert result.name == "a"
        assert result.color == "red"
        assert result.item_type is None
        assert "item_type.name" not in result.__dict__
        assert ItemType.count(db) == 0

    def test_does_not_merge_relationship_dict_filters(self, db):
        result = Item.upsert_by(
            db,
            {"item_list": {"name": "Nope"}},
            name="alone",
            color="blue",
        )

        assert result.color == "blue"
        assert result.item_list_id is None
        assert ItemList.count(db) == 0

    def test_on_update_assocs_not_written_as_column(self, db):
        result = Item.upsert_by(
            db,
            {"name": "solo"},
            name="solo",
            color="red",
            on_update_assocs="raise",
        )

        assert result.name == "solo"
        assert "on_update_assocs" not in result.__dict__

    def test_should_raise_stripped_on_insert(self, db):
        result = Item.upsert_by(
            db, {"color": "z"}, name="n", color="z", should_raise=False
        )

        assert result.color == "z"
        assert "should_raise" not in result.__dict__

    def test_control_keys_in_filters_not_merged(self, db):
        """Defense: control keys must not become columns even if only in filters.

        Placing them in ``filters`` still fails in ``get_by`` today; exercise
        the merge helper directly so the miss-path contract stays locked.
        """
        attrs = Item._attrs_for_upsert_insert(
            {
                "color": "red",
                "on_update_assocs": "raise",
                "should_raise": True,
                "item_type.name": "x",
            },
            {"name": "a"},
        )

        assert attrs == {"name": "a", "color": "red"}

    def test_commit_false_on_insert(self, db):
        result = Item.upsert_by(
            db, {"color": "red"}, name="a", color="red", commit=False
        )

        assert result.name == "a"
        assert result.id is None
        assert Item.count(db) == 0

        db.commit()

        assert result.id is not None
        assert Item.count(db) == 1

    def test_hit_does_not_insert_extra(self, db):
        item = Item.insert(db, name="a", color="red")

        result = Item.upsert_by(db, {"color": "red"}, name="b")

        assert result.id == item.id
        assert Item.count(db) == 1
        assert ItemList.count(db) == 0
