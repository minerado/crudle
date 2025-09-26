from tests.models.item import Item


def test_get_should_return_record(db):
    """Test getting a record by ID."""
    # Arrange
    new_item = Item.insert(db, name="Test Item")

    # Act
    item = Item.get(db, new_item.id)

    # Assert
    assert item.id == new_item.id


def test_get_should_return_none_if_record_does_not_exist(db):
    # Arrange
    item = Item.get(db, 1)

    # Assert
    assert item is None
