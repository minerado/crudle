"""Count custom ``Queries`` filters — SQLAlchemy adapter.

SA-only (Memory has no ``Queries`` hook).
"""

from tests.models import Item


class TestCountCustom:
    def test_is_expensive(self, db):
        Item.insert(db, name="cheap", color="red", price=5)
        Item.insert(db, name="pricey", color="blue", price=20)

        assert Item.count(db, is_expensive=True) == 1
        assert Item.count(db, is_expensive=False) == 1

    def test_custom_and_ne_none(self, db):
        Item.insert(db, name="cheap", color="red", price=5)
        Item.insert(db, name="pricey_null", color="blue", price=None)
        Item.insert(db, name="pricey", color="green", price=20)

        assert Item.count(db, is_expensive=True, price__ne=None) == 1
