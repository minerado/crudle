"""Declared delete cascade — Memory twin.

Memory delete is always Ecto ``:nothing``: related rows are not cascaded,
nilified, or restricted. DB / SQLAlchemy cascade policy is not simulated.
See ``sqlalchemy/delete/test_delete_cascade.py`` for declared SA/FK behavior.
"""

from tests.crudle.adapters.memory.models import Item, ItemList


class TestDeleteCascadeNothing:
    """Memory stays ``:nothing`` regardless of how SA models declare policy."""

    def test_parent_delete_leaves_children(self, db):
        a = db.insert(Item, name="a", color="red")
        b = db.insert(Item, name="b", color="blue")
        lst = db.insert(ItemList, name="L1", items=[a, b])

        db.delete(ItemList, lst.id)

        assert db.get(ItemList, lst.id) is None
        assert db.get(Item, a.id) is not None
        assert db.get(Item, b.id) is not None
