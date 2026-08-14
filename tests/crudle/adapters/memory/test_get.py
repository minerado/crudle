"""
Test get operations for memory adapter.
"""

from tests.crudle.adapters.memory.models import Item


def test_get_should_return_record(db):
    """Test getting a record by ID."""
    # Arrange
    new_item = db.insert(Item, name="Test Item")

    # Act
    item = db.get(Item, new_item.id)

    # Assert
    assert item.id == new_item.id
    assert item.name == "Test Item"


def test_get_should_return_none_if_record_does_not_exist(db):
    """Test getting a non-existent record returns None."""
    # Act
    item = db.get(Item, 1)

    # Assert
    assert item is None


def test_get_with_different_id_types(db):
    """Test getting records with different ID types."""
    # Arrange
    item1 = db.insert(Item, name="Item 1")
    item2 = db.insert(Item, name="Item 2")

    # Act & Assert
    assert db.get(Item, item1.id).name == "Item 1"
    assert db.get(Item, item2.id).name == "Item 2"
    assert db.get(Item, 999) is None
