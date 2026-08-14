"""
Test get_by operations for memory adapter.
"""

from tests.crudle.adapters.memory.models import Item


def test_get_by_should_return_record(db):
    """Test getting a record by filters."""
    # Arrange
    db.insert(Item, name="Test Item", color="red")

    # Act
    item = db.get_by(Item, name="Test Item")

    # Assert
    assert item is not None
    assert item.name == "Test Item"
    assert item.color == "red"


def test_get_by_should_return_none_if_no_match(db):
    """Test getting a record that doesn't exist returns None."""
    # Arrange
    db.insert(Item, name="Test Item", color="red")

    # Act
    item = db.get_by(Item, name="Non-existent Item")

    # Assert
    assert item is None


def test_get_by_with_multiple_filters(db):
    """Test getting a record with multiple filters."""
    # Arrange
    db.insert(Item, name="Test Item", color="red", price=100)
    db.insert(Item, name="Test Item", color="blue", price=100)

    # Act
    item = db.get_by(Item, name="Test Item", color="red")

    # Assert
    assert item is not None
    assert item.name == "Test Item"
    assert item.color == "red"
    assert item.price == 100


def test_get_by_with_operator_filters(db):
    """Test getting a record with operator filters."""
    # Arrange
    db.insert(Item, name="Expensive Item", price=150)
    db.insert(Item, name="Cheap Item", price=50)

    # Act
    item = db.get_by(Item, price__gt=100)

    # Assert
    assert item is not None
    assert item.name == "Expensive Item"
    assert item.price == 150
