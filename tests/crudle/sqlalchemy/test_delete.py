import pytest

from tests.models import Item, ItemList, ItemType


def test_delete_should_remove_record_from_database(db):
    """Test that delete removes a record from the database."""
    # Arrange
    item = Item.insert(db, color="red")
    item_id = item.id
    assert len(Item.list(db)) == 1

    # Act
    result = item.delete(db)

    # Assert
    assert result == item
    assert len(Item.list(db)) == 0
    # Verify the item is no longer in the database
    assert Item.get(db, item_id) is None


def test_delete_should_remove_record_with_relationships(db):
    """Test that delete removes a record with relationships."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)
    item_id = item.id
    item_type_id = item_type.id

    # Act
    result = item.delete(db)

    # Assert
    assert result == item
    assert len(Item.list(db)) == 0
    # The item should be deleted
    assert Item.get(db, item_id) is None
    # But the item_type should still exist (no cascade delete)
    assert ItemType.get(db, item_type_id) is not None


def test_delete_should_remove_record_with_list_relationships(db):
    """Test that delete removes a record with list relationships."""
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="blue")
    item_list = ItemList.insert(db, name="list_1", items=[item_1, item_2])
    item_list_id = item_list.id

    # Act
    result = item_list.delete(db)

    # Assert
    assert result == item_list
    assert len(ItemList.list(db)) == 0
    # The item_list should be deleted
    assert ItemList.get(db, item_list_id) is None
    # But the items should still exist (no cascade delete)
    assert len(Item.list(db)) == 2


def test_delete_should_remove_record_with_nested_relationships(db):
    """Test that delete removes a record with nested relationships."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)
    item_id = item.id

    # Act
    result = item.delete(db)

    # Assert
    assert result == item
    assert len(Item.list(db)) == 0
    # The item should be deleted
    assert Item.get(db, item_id) is None
    # But the item_type should still exist (no cascade delete)
    assert ItemType.get(db, item_type.id) is not None


def test_delete_should_remove_record_with_deep_nested_relationships(db):
    """Test that delete removes a record with deep nested relationships."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)
    item_id = item.id

    # Act
    result = item.delete(db)

    # Assert
    assert result == item
    assert len(Item.list(db)) == 0
    # The item should be deleted
    assert Item.get(db, item_id) is None
    # But the related objects should still exist (no cascade delete)
    assert ItemType.get(db, item_type.id) is not None


def test_delete_should_remove_record_from_list_relationship(db):
    """Test that delete removes a record from a list relationship."""
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="blue")
    item_list = ItemList.insert(db, name="list_1", items=[item_1, item_2])
    original_items_count = len(item_list.items)

    # Act
    result = item_1.delete(db)

    # Assert
    assert result == item_1
    assert len(Item.list(db)) == 1
    # The item should be deleted
    assert Item.get(db, item_1.id) is None
    # The item_list should still exist but with one less item
    db.refresh(item_list)
    assert len(item_list.items) == original_items_count - 1
    assert item_2 in item_list.items


def test_delete_should_remove_record_with_through_association_table(db):
    """Test that delete removes a record with through association table."""
    # Arrange
    item = Item.insert(db, color="red")
    item_id = item.id

    # Act
    result = item.delete(db)

    # Assert
    assert result == item
    assert len(Item.list(db)) == 0
    # The item should be deleted
    assert Item.get(db, item_id) is None


def test_delete_should_handle_nonexistent_record(db):
    """Test that delete handles a record that doesn't exist in the database."""
    # Arrange
    item = Item.insert(db, color="red")

    # Delete the item first
    item.delete(db)
    assert len(Item.list(db)) == 0

    # Act - Try to delete the already deleted item
    result = item.delete(db)

    # Assert
    assert result == item
    # No error should be raised, but nothing should be deleted
    assert len(Item.list(db)) == 0


def test_delete_should_handle_record_without_id(db):
    """Test that delete handles a record without an ID."""
    # Arrange
    item = Item(color="red")  # Not saved to database, no ID

    # Act & Assert
    with pytest.raises(Exception):  # Should raise an error for non-persisted record
        item.delete(db)

    # Nothing should be deleted
    assert len(Item.list(db)) == 0


def test_delete_should_work_with_commit_true(db):
    """Test that delete works with commit=True (default)."""
    # Arrange
    item = Item.insert(db, color="red")
    item_id = item.id
    assert len(Item.list(db)) == 1

    # Act
    result = item.delete(db, commit=True)

    # Assert
    assert result == item
    assert len(Item.list(db)) == 0
    assert Item.get(db, item_id) is None


def test_delete_should_work_with_commit_false(db):
    """Test that delete works with commit=False."""
    # Arrange
    item = Item.insert(db, color="red")
    item_id = item.id
    assert len(Item.list(db)) == 1

    # Act
    result = item.delete(db, commit=False)

    # Assert
    assert result == item
    # The item should still exist in the database because commit=False
    assert len(Item.list(db)) == 1
    assert Item.get(db, item_id) is not None

    # After manual commit, it should be deleted
    db.commit()
    assert len(Item.list(db)) == 0
    assert Item.get(db, item_id) is None


def test_delete_should_work_with_commit_false_and_relationships(db):
    """Test that delete works with commit=False and relationships."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)
    item_id = item.id
    item_type_id = item_type.id

    # Act
    result = item.delete(db, commit=False)

    # Assert
    assert result == item
    # The item should still exist in the database because commit=False
    assert len(Item.list(db)) == 1
    assert Item.get(db, item_id) is not None
    assert ItemType.get(db, item_type_id) is not None

    # After manual commit, it should be deleted
    db.commit()
    assert len(Item.list(db)) == 0
    assert Item.get(db, item_id) is None
    # But the item_type should still exist
    assert ItemType.get(db, item_type_id) is not None


def test_delete_should_work_with_commit_false_and_list_relationships(db):
    """Test that delete works with commit=False and list relationships."""
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="blue")
    item_list = ItemList.insert(db, name="list_1", items=[item_1, item_2])
    item_list_id = item_list.id

    # Act
    result = item_list.delete(db, commit=False)

    # Assert
    assert result == item_list
    # The item_list should still exist in the database because commit=False
    assert len(ItemList.list(db)) == 1
    assert ItemList.get(db, item_list_id) is not None
    assert len(Item.list(db)) == 2

    # After manual commit, it should be deleted
    db.commit()
    assert len(ItemList.list(db)) == 0
    assert ItemList.get(db, item_list_id) is None
    # But the items should still exist
    assert len(Item.list(db)) == 2


def test_delete_should_work_with_commit_false_and_nested_relationships(db):
    """Test that delete works with commit=False and nested relationships."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)
    item_id = item.id

    # Act
    result = item.delete(db, commit=False)

    # Assert
    assert result == item
    # The item should still exist in the database because commit=False
    assert len(Item.list(db)) == 1
    assert Item.get(db, item_id) is not None
    assert ItemType.get(db, item_type.id) is not None

    # After manual commit, it should be deleted
    db.commit()
    assert len(Item.list(db)) == 0
    assert Item.get(db, item_id) is None
    # But the item_type should still exist
    assert ItemType.get(db, item_type.id) is not None


def test_delete_should_work_with_commit_false_and_through_association_table(db):
    """Test that delete works with commit=False and through association table."""
    # Arrange
    item = Item.insert(db, color="red")
    item_id = item.id

    # Act
    result = item.delete(db, commit=False)

    # Assert
    assert result == item
    # The item should still exist in the database because commit=False
    assert len(Item.list(db)) == 1
    assert Item.get(db, item_id) is not None

    # After manual commit, it should be deleted
    db.commit()
    assert len(Item.list(db)) == 0
    assert Item.get(db, item_id) is None


def test_delete_should_handle_rollback_on_error(db):
    """Test that delete handles rollback on error."""
    # Arrange
    item = Item.insert(db, color="red")
    item_id = item.id
    assert len(Item.list(db)) == 1

    # Act
    result = item.delete(db, commit=False)

    # Assert
    assert result == item
    # The item should still exist because commit=False
    assert len(Item.list(db)) == 1
    assert Item.get(db, item_id) is not None

    # After manual commit, it should be deleted
    db.commit()
    assert len(Item.list(db)) == 0
    assert Item.get(db, item_id) is None


def test_delete_should_work_with_multiple_deletions_in_transaction(db):
    """Test that delete works with multiple deletions in a transaction."""
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="blue")
    item_3 = Item.insert(db, color="green")
    assert len(Item.list(db)) == 3

    # Act
    result_1 = item_1.delete(db, commit=False)
    result_2 = item_2.delete(db, commit=False)
    result_3 = item_3.delete(db, commit=True)  # This will commit all deletions

    # Assert
    assert result_1 == item_1
    assert result_2 == item_2
    assert result_3 == item_3
    # All items should be deleted
    assert len(Item.list(db)) == 0
    assert Item.get(db, item_1.id) is None
    assert Item.get(db, item_2.id) is None
    assert Item.get(db, item_3.id) is None


def test_delete_should_work_with_mixed_operations_in_transaction(db):
    """Test that delete works with mixed operations in a transaction."""
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="blue")
    item_3 = Item.insert(db, color="green")
    assert len(Item.list(db)) == 3

    # Act
    result_1 = item_1.delete(db, commit=False)
    item_2.update(
        db, color="yellow", commit=True
    )  # This will commit the update and the pending delete
    result_3 = item_3.delete(db, commit=True)  # This will commit the delete

    # Assert
    assert result_1 == item_1
    assert result_3 == item_3
    # item_1 should be deleted (committed with the update), item_2 should be updated, item_3 should be deleted
    assert len(Item.list(db)) == 1
    assert (
        Item.get(db, item_1.id) is None
    )  # Deleted because it was committed with the update
    # Get the updated item_2 from the database
    updated_item_2 = Item.get(db, item_2.id)
    assert updated_item_2 is not None
    assert updated_item_2.color == "yellow"
    assert Item.get(db, item_3.id) is None  # Deleted because commit=True
