"""
Association update strategy tests for memory adapter (README parity).
"""

import pytest
from sqlalchemy.exc import IntegrityError

from tests.crudle.adapters.memory.models import Item, ItemList


def test_update_on_raise_blocks_removing_collection_members(db):
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")
    item_list = db.insert(ItemList, name="List", items=[item1, item2])

    with pytest.raises(IntegrityError):
        db.update(ItemList, item_list.id, items=[item1], on_update_assocs="raise")


def test_update_on_delete_all_replaces_collection(db):
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")
    item3 = db.insert(Item, name="Item 3", color="green")
    item_list = db.insert(ItemList, name="List", items=[item1, item2])

    updated = db.update(
        ItemList, item_list.id, items=[item3], on_update_assocs="delete_all"
    )
    assert len(updated.items) == 1
    assert updated.items[0].id == item3.id
    assert db.get(Item, item1.id) is None
    assert db.get(Item, item2.id) is None


def test_update_on_nilify_all_clears_child_fks(db):
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")
    item_list = db.insert(ItemList, name="List", items=[item1, item2])

    updated = db.update(
        ItemList, item_list.id, items=[item1], on_update_assocs="nilify_all"
    )
    assert len(updated.items) == 1
    assert updated.items[0].id == item1.id

    remaining = db.get(Item, item2.id)
    assert remaining is not None
    assert remaining.item_list_id is None
