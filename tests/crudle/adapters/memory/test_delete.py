"""
Test delete operations for memory adapter.
"""

import pytest

from tests.crudle.adapters.memory.models import Item, ItemList, Tag, ItemType


def test_delete_should_remove_record(db):
    """Test deleting a record by ID."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act
    deleted_item = db.delete(Item, item.id)

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item.id
    assert deleted_item.name == "Test Item"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is None


def test_delete_should_return_none_for_nonexistent_record(db):
    """Test deleting a nonexistent record returns None."""
    # Act
    result = db.delete(Item, 999)

    # Assert
    assert result is None


def test_delete_should_handle_different_id_types(db):
    """Test deleting with different ID types."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act - Test with string ID
    deleted_item = db.delete(Item, str(item.id))

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item.id


def test_delete_should_maintain_referential_integrity(db):
    """Test that deleting maintains referential integrity."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    item = db.insert(Item, name="Test Item", color="red", price=10, item_type=item_type)

    # Act
    deleted_item = db.delete(Item, item.id)

    # Assert
    assert deleted_item is not None
    # The item_type should still exist
    item_type_check = db.get(ItemType, item_type.id)
    assert item_type_check is not None


def test_delete_should_handle_relationships(db):
    """Test deleting records with relationships."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item_list = db.insert(ItemList, name="Test List", items=[item1, item2])

    # Act
    deleted_list = db.delete(ItemList, item_list.id)

    # Assert
    assert deleted_list is not None
    assert deleted_list.id == item_list.id

    # Verify it's actually deleted
    retrieved_list = db.get(ItemList, item_list.id)
    assert retrieved_list is None

    # Items should still exist
    item1_check = db.get(Item, item1.id)
    item2_check = db.get(Item, item2.id)
    assert item1_check is not None
    assert item2_check is not None


def test_delete_should_handle_many_to_many_relationships(db):
    """Test deleting records with many-to-many relationships."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)
    tag1 = db.insert(Tag, name="tag1", color="blue")
    tag2 = db.insert(Tag, name="tag2", color="green")

    # Add tags to item
    updated_item = db.update(Item, item.id, tags=[tag1, tag2])

    # Act
    deleted_item = db.delete(Item, item.id)

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item.id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is None

    # Tags should still exist
    tag1_check = db.get(Tag, tag1.id)
    tag2_check = db.get(Tag, tag2.id)
    assert tag1_check is not None
    assert tag2_check is not None


def test_delete_should_handle_nested_relationships(db):
    """Test deleting records with nested relationships."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    item = db.insert(Item, name="Test Item", color="red", price=10, item_type=item_type)
    item_list = db.insert(ItemList, name="Test List", items=[item])

    # Act
    deleted_item = db.delete(Item, item.id)

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item.id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is None

    # Related objects should still exist
    item_type_check = db.get(ItemType, item_type.id)
    item_list_check = db.get(ItemList, item_list.id)
    assert item_type_check is not None
    assert item_list_check is not None


def test_delete_should_handle_complex_relationships(db):
    """Test deleting records with complex relationship structures."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    item1 = db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type)
    tag1 = db.insert(Tag, name="tag1", color="green")
    tag2 = db.insert(Tag, name="tag2", color="yellow")

    # Create complex relationships
    updated_item1 = db.update(Item, item1.id, tags=[tag1, tag2])
    updated_item2 = db.update(Item, item2.id, tags=[tag1])
    item_list = db.insert(ItemList, name="Test List", items=[item1, item2])

    # Act
    deleted_item = db.delete(Item, item1.id)

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item1.id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item1.id)
    assert retrieved_item is None

    # All other objects should still exist
    item2_check = db.get(Item, item2.id)
    item_type_check = db.get(ItemType, item_type.id)
    tag1_check = db.get(Tag, tag1.id)
    tag2_check = db.get(Tag, tag2.id)
    item_list_check = db.get(ItemList, item_list.id)

    assert item2_check is not None
    assert item_type_check is not None
    assert tag1_check is not None
    assert tag2_check is not None
    assert item_list_check is not None


def test_delete_should_handle_validation_errors(db):
    """Test deleting with invalid data doesn't cause issues."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act - Try to delete with invalid ID type
    try:
        result = db.delete(Item, "invalid_id")
    except (ValueError, TypeError):
        # This is expected behavior for invalid ID types
        result = None

    # Assert
    # The original item should still exist
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is not None


def test_delete_should_handle_empty_database(db):
    """Test deleting from empty database."""
    # Act
    result = db.delete(Item, 1)

    # Assert
    assert result is None


def test_delete_should_handle_multiple_deletions(db):
    """Test deleting multiple records."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item3 = db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    deleted1 = db.delete(Item, item1.id)
    deleted2 = db.delete(Item, item2.id)
    deleted3 = db.delete(Item, item3.id)

    # Assert
    assert deleted1 is not None
    assert deleted2 is not None
    assert deleted3 is not None

    # Verify all are deleted
    assert db.get(Item, item1.id) is None
    assert db.get(Item, item2.id) is None
    assert db.get(Item, item3.id) is None


def test_delete_should_handle_deletion_of_related_records(db):
    """Test deleting records that are referenced by other records."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    item = db.insert(Item, name="Test Item", color="red", price=10, item_type=item_type)

    # Act
    deleted_item_type = db.delete(ItemType, item_type.id)

    # Assert
    assert deleted_item_type is not None
    assert deleted_item_type.id == item_type.id

    # Verify it's actually deleted
    retrieved_item_type = db.get(ItemType, item_type.id)
    assert retrieved_item_type is None

    # The item should still exist but with a null reference
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is not None


def test_delete_should_handle_cascading_deletions(db):
    """Test that deletions don't cascade by default (MemoryAdapter behavior)."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    item = db.insert(Item, name="Test Item", color="red", price=10, item_type=item_type)

    # Act
    deleted_item = db.delete(Item, item.id)

    # Assert
    assert deleted_item is not None

    # The item_type should still exist (no cascading)
    item_type_check = db.get(ItemType, item_type.id)
    assert item_type_check is not None


def test_delete_should_handle_large_datasets(db):
    """Test deleting from large datasets."""
    # Arrange
    items = []
    for i in range(100):
        item = db.insert(Item, name=f"Item {i}", color="red", price=i)
        items.append(item)

    # Act
    deleted_item = db.delete(Item, items[50].id)

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == items[50].id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, items[50].id)
    assert retrieved_item is None

    # Other items should still exist
    for i in range(100):
        if i != 50:
            retrieved_item = db.get(Item, items[i].id)
            assert retrieved_item is not None


def test_delete_should_handle_concurrent_operations(db):
    """Test deleting with concurrent-like operations."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)

    # Act - Simulate concurrent operations
    deleted1 = db.delete(Item, item1.id)
    updated2 = db.update(Item, item2.id, name="Updated Item 2")
    deleted2 = db.delete(Item, item2.id)

    # Assert
    assert deleted1 is not None
    assert deleted2 is not None
    assert updated2 is not None

    # Both should be deleted
    assert db.get(Item, item1.id) is None
    assert db.get(Item, item2.id) is None


def test_delete_should_handle_edge_case_ids(db):
    """Test deleting with edge case IDs."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)
    item_id = item.id

    # Act & Assert - Test various edge cases
    # Test with the actual ID
    deleted_item = db.delete(Item, item_id)
    assert deleted_item is not None

    # Verify it's deleted
    assert db.get(Item, item_id) is None


def test_delete_should_handle_relationship_cleanup(db):
    """Test that deleting properly cleans up relationships."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item_list = db.insert(ItemList, name="Test List", items=[item1, item2])

    # Act
    deleted_item = db.delete(Item, item1.id)

    # Assert
    assert deleted_item is not None

    # The item should be deleted
    assert db.get(Item, item1.id) is None

    # The list should still exist
    retrieved_list = db.get(ItemList, item_list.id)
    assert retrieved_list is not None

    # The remaining item should still exist
    retrieved_item2 = db.get(Item, item2.id)
    assert retrieved_item2 is not None


def test_delete_should_handle_validation_errors_gracefully(db):
    """Test that delete handles validation errors gracefully."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act - Try to delete with None ID
    result = db.delete(Item, None)

    # Assert
    assert result is None

    # The original item should still exist
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is not None


def test_delete_should_handle_negative_ids(db):
    """Test deleting with negative IDs."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act
    result = db.delete(Item, -1)

    # Assert
    assert result is None

    # The original item should still exist
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is not None


def test_delete_should_handle_zero_id(db):
    """Test deleting with zero ID."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act
    result = db.delete(Item, 0)

    # Assert
    assert result is None

    # The original item should still exist
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is not None


def test_delete_should_handle_float_ids(db):
    """Test deleting with float IDs."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act
    result = db.delete(Item, float(item.id))

    # Assert
    assert result is not None
    assert result.id == item.id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is None


def test_delete_should_handle_string_numeric_ids(db):
    """Test deleting with string numeric IDs."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act
    result = db.delete(Item, str(item.id))

    # Assert
    assert result is not None
    assert result.id == item.id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is None


def test_delete_should_handle_boolean_ids(db):
    """Test deleting with boolean IDs."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act
    result = db.delete(Item, True)

    # Assert
    assert result is None

    # The original item should still exist
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is not None


def test_delete_should_handle_list_ids(db):
    """Test deleting with list IDs."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act
    result = db.delete(Item, [item.id])

    # Assert
    assert result is None

    # The original item should still exist
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is not None


def test_delete_should_handle_dict_ids(db):
    """Test deleting with dictionary IDs."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act
    result = db.delete(Item, {"id": item.id})

    # Assert
    assert result is None

    # The original item should still exist
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is not None


def test_delete_should_handle_complex_object_ids(db):
    """Test deleting with complex object IDs."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act
    result = db.delete(Item, item)

    # Assert
    assert result is None

    # The original item should still exist
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is not None
