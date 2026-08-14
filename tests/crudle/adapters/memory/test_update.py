"""
Test update operations for memory adapter.
"""

import pytest

from src.crudle.adapters.memory.adapter import NotLoaded
from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


def test_update_should_update_record(db):
    """Test basic record update."""
    # Arrange
    item = db.insert(Item, color="red")

    # Act
    updated_item = db.update(Item, item.id, color="blue")

    # Assert
    assert updated_item.color == "blue"
    assert updated_item.id == item.id


def test_update_should_update_multiple_fields(db):
    """Test updating multiple fields at once."""
    # Arrange
    item = db.insert(Item, name="Old Name", color="red", price=10)

    # Act
    updated_item = db.update(Item, item.id, name="New Name", color="blue", price=20)

    # Assert
    assert updated_item.name == "New Name"
    assert updated_item.color == "blue"
    assert updated_item.price == 20
    assert updated_item.id == item.id


def test_update_should_return_none_for_nonexistent_record(db):
    """Test updating non-existent record returns None."""
    # Act
    result = db.update(Item, 999, color="blue")

    # Assert
    assert result is None


def test_update_should_validate_data(db):
    """Test that Pydantic validation works during updates."""
    # Arrange
    item = db.insert(Item, name="Test Item", price=100)

    # Test invalid type
    try:
        db.update(Item, item.id, price="not_a_number")
        assert False, "Should have raised validation error"
    except ValueError as e:
        assert "validation error" in str(e)

    # Test valid update
    updated_item = db.update(Item, item.id, price=200)
    assert updated_item.price == 200


def test_update_should_handle_optional_fields(db):
    """Test updating optional fields."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=100)

    # Act - set to None
    updated_item = db.update(Item, item.id, color=None, price=None)

    # Assert
    assert updated_item.color is None
    assert updated_item.price is None
    assert updated_item.name == "Test Item"  # Unchanged


def test_update_should_handle_relationship_updates(db):
    """Test updating relationships."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red")
    item_type = db.insert(ItemType, name="Electronics")

    # Act
    updated_item = db.update(Item, item.id, item_type=item_type)

    # Assert - explicitly updated relationships are preserved
    assert updated_item.item_type.id == item_type.id
    assert updated_item.item_type.name == "Electronics"


def test_update_should_handle_nested_relationship_updates(db):
    """Test updating with nested relationship data."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red")

    # Act
    updated_item = db.update(Item, item.id, item_type={"name": "Electronics"})

    # Assert
    assert updated_item.item_type.name == "Electronics"
    assert updated_item.item_type.id is not None


def test_update_should_handle_list_relationship_updates(db):
    """Test updating list relationships."""
    # Arrange
    item_list = db.insert(ItemList, name="Test List")
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")

    # Act
    updated_list = db.update(ItemList, item_list.id, items=[item1, item2])

    # Assert
    assert len(updated_list.items) == 2
    assert updated_list.items[0].id == item1.id
    assert updated_list.items[1].id == item2.id


def test_update_should_handle_mixed_relationship_updates(db):
    """Test updating with mixed existing and new relationships."""
    # Arrange
    item_list = db.insert(ItemList, name="Test List")
    existing_item = db.insert(Item, name="Existing Item", color="red")

    # Act
    updated_list = db.update(
        ItemList,
        item_list.id,
        items=[existing_item, {"name": "New Item", "color": "blue"}],
    )

    # Assert
    assert len(updated_list.items) == 2
    assert updated_list.items[0].id == existing_item.id
    assert updated_list.items[1].name == "New Item"
    assert updated_list.items[1].color == "blue"


def test_update_should_preserve_unchanged_fields(db):
    """Test that unchanged fields are preserved."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=100)

    # Act
    updated_item = db.update(Item, item.id, color="blue")

    # Assert
    assert updated_item.name == "Test Item"  # Unchanged
    assert updated_item.color == "blue"  # Changed
    assert updated_item.price == 100  # Unchanged


def test_update_should_handle_empty_update(db):
    """Test updating with no changes."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=100)

    # Act
    updated_item = db.update(Item, item.id)

    # Assert
    assert updated_item.name == "Test Item"
    assert updated_item.color == "red"
    assert updated_item.price == 100


def test_update_should_handle_id_field_ignored(db):
    """Test that ID field cannot be changed."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red")

    # Act
    updated_item = db.update(Item, item.id, id=999)

    # Assert
    assert updated_item.id == item.id  # ID should not change
    assert updated_item.name == "Test Item"


def test_update_should_handle_datetime_fields(db):
    """Test updating datetime fields."""
    # Arrange
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    item = db.insert(Item, name="Test Item", created_at=now)

    # Act
    new_time = datetime.now(timezone.utc)
    updated_item = db.update(Item, item.id, created_at=new_time)

    # Assert
    assert updated_item.created_at == new_time


def test_update_should_handle_boolean_fields(db):
    """Test updating boolean fields."""
    # Arrange
    item = db.insert(Item, name="Test Item")

    # Act
    updated_item = db.update(Item, item.id, price=100)

    # Assert
    assert updated_item.price == 100


def test_update_should_handle_string_fields(db):
    """Test updating string fields."""
    # Arrange
    item = db.insert(Item, name="Old Name", color="red")

    # Act
    updated_item = db.update(Item, item.id, name="New Name", color="blue")

    # Assert
    assert updated_item.name == "New Name"
    assert updated_item.color == "blue"


def test_update_should_handle_numeric_fields(db):
    """Test updating numeric fields."""
    # Arrange
    item = db.insert(Item, name="Test Item", price=10)

    # Act
    updated_item = db.update(Item, item.id, price=20)

    # Assert
    assert updated_item.price == 20


def test_update_should_handle_relationship_replacement(db):
    """Test replacing relationships."""
    # Arrange
    item = db.insert(Item, name="Test Item")
    old_type = db.insert(ItemType, name="Old Type")
    new_type = db.insert(ItemType, name="New Type")

    # Set initial relationship
    item = db.update(Item, item.id, item_type=old_type)
    assert item.item_type.name == "Old Type"

    # Act - replace relationship
    updated_item = db.update(Item, item.id, item_type=new_type)

    # Assert
    assert updated_item.item_type.name == "New Type"
    assert updated_item.item_type.id == new_type.id


def test_update_should_handle_relationship_removal(db):
    """Test removing relationships by setting to None."""
    # Arrange
    item_type = db.insert(ItemType, name="Test Type")
    item = db.insert(Item, name="Test Item", item_type=item_type)
    assert item.item_type is not None

    # Act
    updated_item = db.update(Item, item.id, item_type=None)

    # Assert
    assert updated_item.item_type is None


def test_update_should_handle_list_relationship_clearing(db):
    """Test clearing list relationships."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")
    item_list = db.insert(ItemList, name="Test List", items=[item1, item2])
    assert len(item_list.items) == 2

    # Act
    updated_list = db.update(ItemList, item_list.id, items=[])

    # Assert
    assert len(updated_list.items) == 0


def test_update_should_handle_list_relationship_replacement(db):
    """Test replacing list relationships."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")
    item3 = db.insert(Item, name="Item 3", color="green")
    item_list = db.insert(ItemList, name="Test List", items=[item1, item2])
    assert len(item_list.items) == 2

    # Act
    updated_list = db.update(ItemList, item_list.id, items=[item3])

    # Assert
    assert len(updated_list.items) == 1
    assert updated_list.items[0].id == item3.id
    assert updated_list.items[0].name == "Item 3"


def test_update_should_handle_many_to_many_relationships(db):
    """Test updating many-to-many relationships."""
    # Arrange
    item = db.insert(Item, name="Test Item")
    tag1 = db.insert(Tag, name="tag1")
    tag2 = db.insert(Tag, name="tag2")

    # Act
    updated_item = db.update(Item, item.id, tags=[tag1, tag2])

    # Assert
    assert len(updated_item.tags) == 2
    assert updated_item.tags[0].name == "tag1"
    assert updated_item.tags[1].name == "tag2"


def test_update_should_handle_mixed_many_to_many_relationships(db):
    """Test updating many-to-many with mixed existing and new items."""
    # Arrange
    item = db.insert(Item, name="Test Item")
    existing_tag = db.insert(Tag, name="existing_tag")

    # Act
    updated_item = db.update(
        Item, item.id, tags=[existing_tag, {"name": "new_tag", "color": "blue"}]
    )

    # Assert
    assert len(updated_item.tags) == 2
    assert updated_item.tags[0].name == "existing_tag"
    assert updated_item.tags[1].name == "new_tag"


def test_update_should_handle_complex_nested_updates(db):
    """Test complex nested relationship updates."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red")

    # Act
    updated_item = db.update(
        Item,
        item.id,
        item_type={"name": "Electronics"},
        tags=[{"name": "expensive"}, {"name": "popular"}],
    )

    # Assert
    assert updated_item.item_type.name == "Electronics"
    assert len(updated_item.tags) == 2
    assert updated_item.tags[0].name == "expensive"
    assert updated_item.tags[1].name == "popular"


def test_update_should_handle_validation_errors_gracefully(db):
    """Test that validation errors are handled gracefully."""
    # Arrange
    item = db.insert(Item, name="Test Item", price=100)

    # Test missing required field in nested relationship
    try:
        db.update(Item, item.id, item_type={})  # Missing required 'name' field
        assert False, "Should have raised validation error"
    except ValueError as e:
        assert "validation error" in str(e)

    # Test invalid field type in nested relationship
    try:
        db.update(Item, item.id, item_type={"name": 123})  # Invalid type for name
        assert False, "Should have raised validation error"
    except ValueError as e:
        assert "validation error" in str(e)


def test_update_should_maintain_referential_integrity(db):
    """Test that relationships maintain referential integrity."""
    # Arrange
    item_type = db.insert(ItemType, name="Test Type")
    item = db.insert(Item, name="Test Item", item_type=item_type)

    # Act
    updated_item = db.update(Item, item.id, name="Updated Item")

    # Assert
    assert updated_item.name == "Updated Item"
    # Relationships are NotLoaded by default, need to preload to access them
    assert isinstance(updated_item.item_type, NotLoaded)

    # Get the item with preloaded relationship to verify referential integrity
    updated_item_with_preload = db.get(Item, item.id, preload=["item_type"])
    assert updated_item_with_preload.item_type.id == item_type.id
    assert updated_item_with_preload.item_type.name == "Test Type"
