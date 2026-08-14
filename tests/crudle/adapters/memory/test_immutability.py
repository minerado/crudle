"""Tests for complete immutability of the MemoryAdapter."""

import pytest
from src.crudle.adapters.memory.adapter import MemoryAdapter, NotLoaded
from .models import Item, ItemList, ItemType, Tag


class TestImmutability:
    """Test complete immutability of the MemoryAdapter."""

    def test_insert_returns_immutable_copy(self, db):
        """Test that insert returns an immutable copy."""
        # Act
        item = db.insert(Item, name="Test Item", color="red")

        # Try to mutate the returned object
        item.name = "HACKED!"
        item.color = "BLUE!"

        # Assert - original object is mutated but DB is not
        assert item.name == "HACKED!"
        assert item.color == "BLUE!"

        # Get from DB - should be unchanged
        item_from_db = db.get(Item, item.id)
        assert item_from_db.name == "Test Item"
        assert item_from_db.color == "red"
        assert item is not item_from_db  # Different objects

    def test_get_returns_immutable_copy(self, db):
        """Test that get returns an immutable copy."""
        # Arrange
        item = db.insert(Item, name="Test Item", color="red")

        # Act
        retrieved_item = db.get(Item, item.id)
        retrieved_item.name = "HACKED!"

        # Assert
        assert retrieved_item.name == "HACKED!"

        # Get again - should be unchanged
        item_from_db = db.get(Item, item.id)
        assert item_from_db.name == "Test Item"
        assert retrieved_item is not item_from_db  # Different objects

    def test_list_returns_immutable_copies(self, db):
        """Test that list returns immutable copies."""
        # Arrange
        db.insert(Item, name="Item 1", color="red")
        db.insert(Item, name="Item 2", color="blue")

        # Act
        items = db.list(Item)
        items[0].name = "HACKED!"

        # Assert
        assert items[0].name == "HACKED!"

        # Get from DB - should be unchanged
        items_from_db = db.list(Item)
        assert items_from_db[0].name == "Item 1"
        assert items[0] is not items_from_db[0]  # Different objects

    def test_get_by_returns_immutable_copy(self, db):
        """Test that get_by returns an immutable copy."""
        # Arrange
        item = db.insert(Item, name="Test Item", color="red")

        # Act
        retrieved_item = db.get_by(Item, name="Test Item")
        retrieved_item.name = "HACKED!"

        # Assert
        assert retrieved_item.name == "HACKED!"

        # Get from DB - should be unchanged
        item_from_db = db.get_by(Item, name="Test Item")
        assert item_from_db.name == "Test Item"
        assert retrieved_item is not item_from_db  # Different objects

    def test_update_returns_immutable_copy(self, db):
        """Test that update returns an immutable copy."""
        # Arrange
        item = db.insert(Item, name="Test Item", color="red")

        # Act
        updated_item = db.update(Item, item.id, color="blue")
        updated_item.name = "HACKED!"

        # Assert
        assert updated_item.name == "HACKED!"

        # Get from DB - should show the update but not the hack
        item_from_db = db.get(Item, item.id)
        assert item_from_db.name == "Test Item"  # Not hacked
        assert item_from_db.color == "blue"  # But updated
        assert updated_item is not item_from_db  # Different objects

    def test_delete_returns_immutable_copy(self, db):
        """Test that delete returns an immutable copy."""
        # Arrange
        item = db.insert(Item, name="Test Item", color="red")

        # Act
        deleted_item = db.delete(Item, item.id)
        deleted_item.name = "HACKED!"

        # Assert
        assert deleted_item.name == "HACKED!"
        assert db.get(Item, item.id) is None  # Actually deleted

    def test_foreign_key_setting_does_not_mutate_original_objects(self, db):
        """Test that foreign key setting doesn't mutate original objects."""
        # Arrange
        item = db.insert(Item, name="Test Item", color="red")
        original_item_list_id = item.item_list_id

        # Act
        item_list = db.insert(ItemList, items=[item])

        # Assert - original item should be unchanged
        assert item.item_list_id == original_item_list_id  # Still None
        assert item.name == "Test Item"  # Unchanged

        # But the stored version should have the foreign key
        item_from_db = db.get(Item, item.id)
        assert item_from_db.item_list_id == item_list.id
        assert item is not item_from_db  # Different objects

    def test_preload_returns_immutable_copy(self, db):
        """Test that preload returns an immutable copy."""
        # Arrange
        item_type = db.insert(ItemType, name="Test Type")
        item = db.insert(Item, name="Test Item", color="red", item_type_id=item_type.id)

        # Act
        item_with_preload = db.get(Item, item.id, preload=["item_type"])
        item_with_preload.name = "HACKED!"
        item_with_preload.item_type.name = "HACKED TYPE!"

        # Assert
        assert item_with_preload.name == "HACKED!"
        assert item_with_preload.item_type.name == "HACKED TYPE!"

        # Get from DB - should be unchanged
        item_from_db = db.get(Item, item.id, preload=["item_type"])
        assert item_from_db.name == "Test Item"
        assert item_from_db.item_type.name == "Test Type"
        assert item_with_preload is not item_from_db  # Different objects

    def test_nested_objects_are_also_immutable(self, db):
        """Test that nested objects in relationships are also immutable."""
        # Arrange
        item_type = db.insert(ItemType, name="Test Type")
        item = db.insert(Item, name="Test Item", color="red", item_type_id=item_type.id)

        # Act
        item_with_preload = db.get(Item, item.id, preload=["item_type"])
        item_with_preload.item_type.name = "HACKED TYPE!"

        # Assert
        assert item_with_preload.item_type.name == "HACKED TYPE!"

        # Get the item_type directly - should be unchanged
        item_type_from_db = db.get(ItemType, item_type.id)
        assert item_type_from_db.name == "Test Type"
        assert item_with_preload.item_type is not item_type_from_db  # Different objects

    def test_multiple_operations_maintain_immutability(self, db):
        """Test that multiple operations maintain immutability."""
        # Arrange
        item = db.insert(Item, name="Test Item", color="red")

        # Act - multiple operations
        item1 = db.get(Item, item.id)
        item1.name = "HACKED 1"

        item2 = db.get(Item, item.id)
        item2.name = "HACKED 2"

        item3 = db.list(Item)[0]
        item3.name = "HACKED 3"

        # Assert - all should be different objects and DB unchanged
        assert item1.name == "HACKED 1"
        assert item2.name == "HACKED 2"
        assert item3.name == "HACKED 3"

        # All should be different objects
        assert item1 is not item2
        assert item2 is not item3
        assert item1 is not item3

        # DB should be unchanged
        item_from_db = db.get(Item, item.id)
        assert item_from_db.name == "Test Item"
        assert item_from_db is not item1
        assert item_from_db is not item2
        assert item_from_db is not item3

    def test_immutability_with_relationships(self, db):
        """Test immutability with complex relationships."""
        # Arrange
        item_type = db.insert(ItemType, name="Test Type")
        item = db.insert(Item, name="Test Item", color="red", item_type_id=item_type.id)
        item_list = db.insert(ItemList, name="Test List", items=[item])

        # Act - get with preload
        item_with_preload = db.get(Item, item.id, preload=["item_type", "item_list"])

        # Try to mutate everything
        item_with_preload.name = "HACKED ITEM"
        item_with_preload.item_type.name = "HACKED TYPE"
        item_with_preload.item_list.name = "HACKED LIST"

        # Assert - mutations should not affect DB
        item_from_db = db.get(Item, item.id, preload=["item_type", "item_list"])
        assert item_from_db.name == "Test Item"
        assert item_from_db.item_type.name == "Test Type"
        assert item_from_db.item_list.name == "Test List"

        # All should be different objects
        assert item_with_preload is not item_from_db
        assert item_with_preload.item_type is not item_from_db.item_type
        assert item_with_preload.item_list is not item_from_db.item_list
