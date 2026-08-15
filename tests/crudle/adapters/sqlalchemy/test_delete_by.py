import pytest
from datetime import datetime, timezone

from tests.models import Item, ItemList, Tag, ItemType


def test_delete_by_should_remove_matching_record(db):
    """Test that delete_by removes a record matching the filter."""
    # Arrange
    item = Item.insert(db, name="Item 1", color="red", price=10)
    item_id = item.id
    assert len(Item.list(db)) == 1

    # Act
    result = Item.delete_by(db, color="red")

    # Assert
    assert result == item
    assert len(Item.list(db)) == 0
    assert Item.get(db, item_id) is None


def test_delete_by_should_return_none_when_no_match(db):
    """Test that delete_by returns None when no record matches the filter."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    assert len(Item.list(db)) == 1

    # Act
    result = Item.delete_by(db, color="blue")

    # Assert
    assert result is None
    assert len(Item.list(db)) == 1  # Item should still exist


def test_delete_by_should_remove_first_match_when_multiple_exist(db):
    """Test that delete_by raises error when multiple records match the filter."""
    from sqlalchemy.exc import MultipleResultsFound

    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="red", price=20)
    Item.insert(db, name="Item 3", color="blue", price=30)
    assert len(Item.list(db)) == 3

    # Act & Assert
    with pytest.raises(MultipleResultsFound):
        Item.delete_by(db, color="red")

    # Verify no items were deleted
    assert len(Item.list(db)) == 3


def test_delete_by_with_multiple_filters(db):
    """Test delete_by with multiple filter conditions."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="red", price=20)
    item3 = Item.insert(db, name="Item 3", color="blue", price=10)
    assert len(Item.list(db)) == 3

    # Act
    result = Item.delete_by(db, color="red", price=10)

    # Assert
    assert result == item1  # Should delete the red item with price 10
    assert len(Item.list(db)) == 2
    # Verify the specific item is gone
    assert Item.get(db, item1.id) is None
    # Verify other items still exist
    assert Item.get(db, item2.id) is not None
    assert Item.get(db, item3.id) is not None


def test_delete_by_with_operator_filters(db):
    """Test delete_by with operator filters."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    item3 = Item.insert(db, name="Item 3", color="green", price=30)
    assert len(Item.list(db)) == 3

    # Act - Use a filter that matches only one record
    result = Item.delete_by(db, price=20)

    # Assert
    assert result == item2  # Should delete the item with price 20
    assert len(Item.list(db)) == 2
    assert Item.get(db, item2.id) is None
    assert Item.get(db, item1.id) is not None
    assert Item.get(db, item3.id) is not None


def test_delete_by_with_in_operator(db):
    """Test delete_by with 'in' operator."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    item3 = Item.insert(db, name="Item 3", color="green", price=30)
    assert len(Item.list(db)) == 3

    # Act - Use a filter that matches only one record
    result = Item.delete_by(db, color="blue")

    # Assert
    assert result == item2  # Should delete the blue item
    assert len(Item.list(db)) == 2
    assert Item.get(db, item2.id) is None
    assert Item.get(db, item1.id) is not None
    assert Item.get(db, item3.id) is not None


def test_delete_by_with_relationship_filters(db):
    """Test delete_by with relationship filters."""
    # Arrange - Since ItemType has one-to-one relationship, create separate types
    item_type_1 = ItemType.insert(db, name="type_a")
    item_type_2 = ItemType.insert(db, name="type_b")
    item1 = Item.insert(db, name="Item 1", color="red", item_type=item_type_1)
    item2 = Item.insert(db, name="Item 2", color="blue", item_type=item_type_2)
    item3 = Item.insert(db, name="Item 3", color="green")  # No item_type
    assert len(Item.list(db)) == 3

    # Act
    result = Item.delete_by(db, **{"item_type.name": "type_a"})

    # Assert
    assert result == item1  # Should delete the item with type_a
    assert len(Item.list(db)) == 2
    assert Item.get(db, item1.id) is None
    assert Item.get(db, item2.id) is not None
    assert Item.get(db, item3.id) is not None


def test_delete_by_with_nested_relationship_filters(db):
    """Test delete_by with nested relationship filters."""
    # Arrange - Since ItemType has one-to-one relationship, create separate types
    item_type_1 = ItemType.insert(db, name="type_a")
    item_type_2 = ItemType.insert(db, name="type_b")
    item1 = Item.insert(db, name="Item 1", color="red", item_type=item_type_1)
    item2 = Item.insert(db, name="Item 2", color="blue", item_type=item_type_2)
    item3 = Item.insert(db, name="Item 3", color="green")  # No item_type
    assert len(Item.list(db)) == 3

    # Act
    result = Item.delete_by(db, **{"item_type.name": "type_b"})

    # Assert
    assert result == item2  # Should delete the item with type_b
    assert len(Item.list(db)) == 2
    assert Item.get(db, item2.id) is None
    assert Item.get(db, item1.id) is not None
    assert Item.get(db, item3.id) is not None


def test_delete_by_with_none_values(db):
    """Test delete_by with None values."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color=None, price=20)
    item3 = Item.insert(db, name="Item 3", color="green", price=None)
    assert len(Item.list(db)) == 3

    # Act
    result = Item.delete_by(db, color=None)

    # Assert
    assert result == item2  # Should delete the item with None color
    assert len(Item.list(db)) == 2
    assert Item.get(db, item2.id) is None
    assert Item.get(db, item1.id) is not None
    assert Item.get(db, item3.id) is not None


def test_delete_by_with_datetime_filters(db):
    """Test delete_by with datetime filters."""
    # Arrange
    past_time = datetime(2020, 1, 1, tzinfo=timezone.utc)

    item1 = Item.insert(db, name="Item 1", color="red")
    item2 = Item.insert(db, name="Item 2", color="blue")

    # Manually update created_at to past time for item2
    item2.created_at = past_time
    db.commit()

    assert len(Item.list(db)) == 2

    # Act
    result = Item.delete_by(db, created_at__gt=past_time)

    # Assert
    assert result == item1  # Should delete the more recent item
    assert len(Item.list(db)) == 1
    assert Item.get(db, item1.id) is None
    assert Item.get(db, item2.id) is not None


def test_delete_by_different_models(db):
    """Test delete_by with different models."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red")
    Item.insert(db, name="Item 2", color="blue")
    list1 = ItemList.insert(db, name="List 1")
    ItemList.insert(db, name="List 2")
    tag1 = Tag.insert(db, name="Tag 1")
    Tag.insert(db, name="Tag 2")

    assert len(Item.list(db)) == 2
    assert len(ItemList.list(db)) == 2
    assert len(Tag.list(db)) == 2

    # Act
    item_result = Item.delete_by(db, color="red")
    list_result = ItemList.delete_by(db, name="List 1")
    tag_result = Tag.delete_by(db, name="Tag 1")

    # Assert
    assert item_result == item1
    assert list_result == list1
    assert tag_result == tag1

    assert len(Item.list(db)) == 1
    assert len(ItemList.list(db)) == 1
    assert len(Tag.list(db)) == 1


def test_delete_by_with_empty_filters(db):
    """Test delete_by with empty filters raises error when multiple records exist."""
    from sqlalchemy.exc import MultipleResultsFound

    # Arrange
    Item.insert(db, name="Item 1", color="red")
    Item.insert(db, name="Item 2", color="blue")
    assert len(Item.list(db)) == 2

    # Act & Assert
    with pytest.raises(MultipleResultsFound):
        Item.delete_by(db)

    # Verify no items were deleted
    assert len(Item.list(db)) == 2


def test_delete_by_with_none_filters(db):
    """Test delete_by with None filters."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")
    Item.insert(db, name="Item 2", color="blue")
    assert len(Item.list(db)) == 2

    # Act
    result = Item.delete_by(db, color=None, price=None)

    # Assert
    assert result is None  # No items have both color=None and price=None
    assert len(Item.list(db)) == 2


def test_delete_by_should_commit_by_default(db):
    """Test that delete_by commits the transaction by default."""
    # Arrange
    item = Item.insert(db, name="Item 1", color="red")
    item_id = item.id
    assert len(Item.list(db)) == 1

    # Act
    result = Item.delete_by(db, color="red")

    # Assert
    assert result == item
    assert len(Item.list(db)) == 0
    # Verify the deletion is committed (item is gone from database)
    assert Item.get(db, item_id) is None


def test_delete_by_with_complex_queries(db):
    """Test delete_by with complex query combinations."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    item3 = Item.insert(db, name="Item 3", color="red", price=30)
    item4 = Item.insert(db, name="Item 4", color="green", price=40)
    assert len(Item.list(db)) == 4

    # Act - Delete first item that is red AND has price > 15
    result = Item.delete_by(db, color="red", price__gt=15)

    # Assert
    assert result == item3  # Should delete the red item with price > 15
    assert len(Item.list(db)) == 3
    assert Item.get(db, item3.id) is None
    # Verify other items still exist
    assert Item.get(db, item1.id) is not None
    assert Item.get(db, item2.id) is not None
    assert Item.get(db, item4.id) is not None


def test_delete_by_with_string_operations(db):
    """Test delete_by with string operations."""
    # Arrange
    item1 = Item.insert(db, name="Apple", color="red")
    Item.insert(db, name="Banana", color="yellow")
    Item.insert(db, name="Cherry", color="red")
    assert len(Item.list(db)) == 3

    # Act - Delete first item with name starting with 'A'
    result = Item.delete_by(db, name="Apple")

    # Assert
    assert result == item1  # Should delete Apple
    assert len(Item.list(db)) == 2


def test_delete_by_with_numeric_operations(db):
    """Test delete_by with numeric operations."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", price=10)
    item2 = Item.insert(db, name="Item 2", price=20)
    item3 = Item.insert(db, name="Item 3", price=30)
    item4 = Item.insert(db, name="Item 4", price=40)
    assert len(Item.list(db)) == 4

    # Act - Use a filter that matches only one record
    result = Item.delete_by(db, price=20)

    # Assert
    assert result == item2  # Should delete item with price 20
    assert len(Item.list(db)) == 3
    assert Item.get(db, item2.id) is None
    assert Item.get(db, item1.id) is not None
    assert Item.get(db, item3.id) is not None
    assert Item.get(db, item4.id) is not None


def test_delete_by_returns_deleted_model(db):
    """Test that delete_by returns the deleted model instance."""
    # Arrange
    item = Item.insert(db, name="Item 1", color="red", price=10)
    original_id = item.id
    original_name = item.name
    original_color = item.color
    original_price = item.price

    # Act
    result = Item.delete_by(db, color="red")

    # Assert
    assert result is not None
    assert result.id == original_id
    assert result.name == original_name
    assert result.color == original_color
    assert result.price == original_price
    # Verify it's the same object (same memory address)
    assert result is item


def test_delete_by_with_invalid_filters(db):
    """Test delete_by with invalid filter fields raises AttributeError."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")
    assert len(Item.list(db)) == 1

    # Act & Assert
    with pytest.raises(
        AttributeError, match="type object 'Item' has no attribute 'invalid_field'"
    ):
        Item.delete_by(db, invalid_field="value")

    # Verify no items were deleted
    assert len(Item.list(db)) == 1


def test_delete_by_with_mixed_valid_invalid_filters(db):
    """Test delete_by with mix of valid and invalid filters raises AttributeError."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)
    assert len(Item.list(db)) == 2

    # Act & Assert
    with pytest.raises(
        AttributeError, match="type object 'Item' has no attribute 'invalid_field'"
    ):
        Item.delete_by(db, color="red", invalid_field="value")

    # Verify no items were deleted
    assert len(Item.list(db)) == 2


def test_delete_by_raises_error_when_multiple_matches(db):
    """Test that delete_by raises error when multiple records match the filter."""
    from sqlalchemy.exc import MultipleResultsFound

    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="red", price=20)
    Item.insert(db, name="Item 3", color="blue", price=30)
    assert len(Item.list(db)) == 3

    # Act & Assert
    with pytest.raises(MultipleResultsFound):
        Item.delete_by(db, color="red")

    # Verify no items were deleted
    assert len(Item.list(db)) == 3


def test_delete_by_preserves_other_records(db):
    """Test that delete_by only affects the matching record."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    item3 = Item.insert(db, name="Item 3", color="green", price=30)
    assert len(Item.list(db)) == 3

    # Act
    result = Item.delete_by(db, color="blue")

    # Assert
    assert result == item2
    assert len(Item.list(db)) == 2
    # Verify specific items
    assert Item.get(db, item1.id) is not None  # Should still exist
    assert Item.get(db, item2.id) is None  # Should be deleted
    assert Item.get(db, item3.id) is not None  # Should still exist


def test_delete_by_with_relationship_field_filters(db):
    """Test delete_by with relationship field filters."""
    # Arrange - Since ItemType has one-to-one relationship, create separate types
    item_type_1 = ItemType.insert(db, name="type_a")
    item_type_2 = ItemType.insert(db, name="type_b")
    item1 = Item.insert(db, name="Item 1", color="red", item_type=item_type_1)
    item2 = Item.insert(db, name="Item 2", color="blue", item_type=item_type_2)
    item3 = Item.insert(db, name="Item 3", color="green")  # No item_type
    assert len(Item.list(db)) == 3

    # Act
    result = Item.delete_by(db, item_type=item_type_1)

    # Assert
    assert result == item1  # Should delete the item with item_type_1
    assert len(Item.list(db)) == 2
    assert Item.get(db, item1.id) is None
    assert Item.get(db, item2.id) is not None
    assert Item.get(db, item3.id) is not None


def test_delete_by_with_nested_field_filters(db):
    """Test delete_by with nested field filters."""
    # Arrange - Since ItemType has one-to-one relationship, create separate types
    item_type_1 = ItemType.insert(db, name="type_a")
    item_type_2 = ItemType.insert(db, name="type_b")
    item1 = Item.insert(db, name="Item 1", color="red", item_type=item_type_1)
    item2 = Item.insert(db, name="Item 2", color="blue", item_type=item_type_2)
    item3 = Item.insert(db, name="Item 3", color="green")  # No item_type
    assert len(Item.list(db)) == 3

    # Act
    result = Item.delete_by(db, **{"item_type.name": "type_a"})

    # Assert
    assert result == item1  # Should delete the item with type_a
    assert len(Item.list(db)) == 2
    assert Item.get(db, item1.id) is None
    assert Item.get(db, item2.id) is not None
    assert Item.get(db, item3.id) is not None
