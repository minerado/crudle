"""Delete_by custom ``Queries`` filters — SQLAlchemy adapter.
"""

from tests.models import Item


class TestDeleteByCustom:
    def test_is_expensive(self, db):
        Item.insert(db, name="cheap", color="red", price=5)
        keep = Item.insert(db, name="pricey", color="blue", price=20)

        assert Item.delete_by(db, is_expensive=True).id == keep.id
        assert Item.count(db) == 1

    def test_custom_and_filter(self, db):
        Item.insert(db, name="cheap", color="red", price=5)
        Item.insert(db, name="pricey_blue", color="blue", price=20)
        keep = Item.insert(db, name="pricey_red", color="red", price=30)

        assert Item.delete_by(db, is_expensive=True, color="red").id == keep.id
