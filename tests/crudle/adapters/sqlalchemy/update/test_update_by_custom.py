"""Update_by custom ``Queries`` filters — SQLAlchemy adapter.

SA-only (Memory has no ``Queries`` hook).
"""

from tests.models import Item


class TestUpdateByCustom:
    def test_is_expensive(self, db):
        Item.insert(db, name="cheap", color="red", price=5)
        keep = Item.insert(db, name="pricey", color="blue", price=20)

        assert (
            Item.update_by(db, {"is_expensive": True}, name="hit").id == keep.id
        )
        assert Item.get(db, keep.id).name == "hit"

    def test_custom_and_filter(self, db):
        Item.insert(db, name="cheap", color="red", price=5)
        Item.insert(db, name="pricey_blue", color="blue", price=20)
        keep = Item.insert(db, name="pricey_red", color="red", price=30)

        assert (
            Item.update_by(
                db, {"is_expensive": True, "color": "red"}, name="hit"
            ).id
            == keep.id
        )
