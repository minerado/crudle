from tests.models.item import Item


def test_get_by_should_return_record(db):
    """Test getting a record by ID."""
    # Arrange
    new_item = Item.insert(db, color="red")

    # Act
    item = Item.get_by(db, color="red")

    # Assert
    assert item.id == new_item.id


def test_get_by_should_return_none_if_record_does_not_exist(db):
    # Arrange
    item = Item.get_by(db, color="red")

    # Assert
    assert item is None
