"""
Test delete_by operations for memory adapter.
"""

import pytest

from tests.crudle.adapters.memory.models import Item, ItemList, Tag, ItemType


def test_delete_by_should_remove_record(db):
    """Test deleting a record by filters."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act
    deleted_item = db.delete_by(Item, name="Test Item")

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item.id
    assert deleted_item.name == "Test Item"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is None


def test_delete_by_should_return_none_if_no_match(db):
    """Test deleting when no records match the filters."""
    # Arrange
    db.insert(Item, name="Test Item", color="red", price=10)

    # Act
    result = db.delete_by(Item, name="Nonexistent Item")

    # Assert
    assert result is None


def test_delete_by_should_delete_first_match(db):
    """Test that delete_by deletes the first matching record."""
    # Arrange
    item1 = db.insert(Item, name="Test Item", color="red", price=10)
    item2 = db.insert(Item, name="Test Item", color="blue", price=20)

    # Act
    deleted_item = db.delete_by(Item, name="Test Item")

    # Assert
    assert deleted_item is not None
    # Should delete the first one found
    assert deleted_item.id == item1.id

    # Verify it's actually deleted
    retrieved_item1 = db.get(Item, item1.id)
    assert retrieved_item1 is None

    # The second item should still exist
    retrieved_item2 = db.get(Item, item2.id)
    assert retrieved_item2 is not None


def test_delete_by_should_handle_multiple_filters(db):
    """Test deleting with multiple filters."""
    # Arrange
    item1 = db.insert(Item, name="Test Item", color="red", price=10)
    item2 = db.insert(Item, name="Test Item", color="blue", price=20)
    item3 = db.insert(Item, name="Other Item", color="red", price=10)

    # Act
    deleted_item = db.delete_by(Item, name="Test Item", color="red")

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item1.id

    # Verify it's actually deleted
    retrieved_item1 = db.get(Item, item1.id)
    assert retrieved_item1 is None

    # Other items should still exist
    retrieved_item2 = db.get(Item, item2.id)
    retrieved_item3 = db.get(Item, item3.id)
    assert retrieved_item2 is not None
    assert retrieved_item3 is not None


def test_delete_by_should_handle_operator_filters(db):
    """Test deleting with operator filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item3 = db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    deleted_item = db.delete_by(Item, price__gt=15)

    # Assert
    assert deleted_item is not None
    # Should delete the first item with price > 15
    assert deleted_item.price > 15

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None


def test_delete_by_should_handle_complex_filters(db):
    """Test deleting with complex filter combinations."""
    # Arrange
    item1 = db.insert(Item, name="Apple iPhone", color="red", price=1000)
    item2 = db.insert(Item, name="Samsung Galaxy", color="blue", price=800)
    item3 = db.insert(Item, name="Google Pixel", color="green", price=700)

    # Act
    deleted_item = db.delete_by(Item, name__q="Apple", price__gt=500)

    # Assert
    assert deleted_item is not None
    assert deleted_item.name == "Apple iPhone"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None


def test_delete_by_should_handle_relationship_filters(db):
    """Test deleting with relationship filters."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    item1 = db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type)

    # Act
    deleted_item = db.delete_by(Item, **{"item_type.name": "Electronics"})

    # Assert
    assert deleted_item is not None
    # Should delete the first item with the relationship
    assert deleted_item.id in [item1.id, item2.id]

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None


def test_delete_by_should_handle_nested_relationship_filters(db):
    """Test deleting with nested relationship filters."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    item1 = db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type)
    item_list = db.insert(ItemList, name="Test List", items=[item1, item2])

    # Act
    deleted_list = db.delete_by(ItemList, **{"items.name": "Item 1"})

    # Assert
    assert deleted_list is not None
    assert deleted_list.id == item_list.id

    # Verify it's actually deleted
    retrieved_list = db.get(ItemList, item_list.id)
    assert retrieved_list is None


def test_delete_by_should_handle_text_search_filters(db):
    """Test deleting with text search filters."""
    # Arrange
    item1 = db.insert(Item, name="Apple iPhone", color="red", price=1000)
    item2 = db.insert(Item, name="Samsung Galaxy", color="blue", price=800)
    item3 = db.insert(Item, name="Google Pixel", color="green", price=700)

    # Act
    deleted_item = db.delete_by(Item, name__q="Apple")

    # Assert
    assert deleted_item is not None
    assert deleted_item.name == "Apple iPhone"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None


def test_delete_by_should_handle_case_insensitive_filters(db):
    """Test deleting with case insensitive filters."""
    # Arrange
    item1 = db.insert(Item, name="Apple iPhone", color="red", price=1000)
    item2 = db.insert(Item, name="Samsung Galaxy", color="blue", price=800)

    # Act
    deleted_item = db.delete_by(Item, name__q="apple")

    # Assert
    assert deleted_item is not None
    assert deleted_item.name == "Apple iPhone"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None


def test_delete_by_should_handle_partial_matches(db):
    """Test deleting with partial text matches."""
    # Arrange
    item1 = db.insert(Item, name="Apple iPhone", color="red", price=1000)
    item2 = db.insert(Item, name="Samsung Galaxy", color="blue", price=800)
    item3 = db.insert(Item, name="Google Pixel", color="green", price=700)

    # Act
    deleted_item = db.delete_by(Item, name__q="Phone")

    # Assert
    assert deleted_item is not None
    assert deleted_item.name == "Apple iPhone"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None


def test_delete_by_should_handle_invalid_operators(db):
    """Test deleting with invalid operators falls back to equality."""
    # Arrange
    item1 = db.insert(Item, name="Test Item", color="red", price=10)
    item2 = db.insert(Item, name="Other Item", color="blue", price=20)

    # Act
    deleted_item = db.delete_by(Item, name__invalid_op="Test Item")

    # Assert
    assert deleted_item is not None
    assert deleted_item.name == "Test Item"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None


def test_delete_by_should_handle_type_mismatches(db):
    """Test deleting with type mismatches."""
    # Arrange
    item1 = db.insert(Item, name="Test Item", color="red", price=10)
    item2 = db.insert(Item, name="Other Item", color="blue", price=20)

    # Act
    result = db.delete_by(Item, price="10")  # String vs int

    # Assert
    assert result is None

    # No items should be deleted
    retrieved_item1 = db.get(Item, item1.id)
    retrieved_item2 = db.get(Item, item2.id)
    assert retrieved_item1 is not None
    assert retrieved_item2 is not None


def test_delete_by_should_handle_multiple_matches_first_wins(db):
    """Test that delete_by deletes only the first match when multiple exist."""
    # Arrange
    item1 = db.insert(Item, name="Test Item", color="red", price=10)
    item2 = db.insert(Item, name="Test Item", color="blue", price=20)
    item3 = db.insert(Item, name="Test Item", color="green", price=30)

    # Act
    deleted_item = db.delete_by(Item, name="Test Item")

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item1.id  # First match

    # Verify only the first is deleted
    retrieved_item1 = db.get(Item, item1.id)
    retrieved_item2 = db.get(Item, item2.id)
    retrieved_item3 = db.get(Item, item3.id)

    assert retrieved_item1 is None
    assert retrieved_item2 is not None
    assert retrieved_item3 is not None


def test_delete_by_should_handle_empty_filters(db):
    """Test deleting with empty filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    deleted_item = db.delete_by(Item, **{})

    # Assert
    assert deleted_item is not None
    # Should delete the first item found
    assert deleted_item.id in [item1.id, item2.id]

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None


def test_delete_by_should_handle_none_values(db):
    """Test deleting with None values."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color=None, price=20)

    # Act
    deleted_item = db.delete_by(Item, color=None)

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item2.id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item2.id)
    assert retrieved_item is None


def test_delete_by_should_handle_boolean_filters(db):
    """Test deleting with boolean-like filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    deleted_item = db.delete_by(Item, name="Item 1")

    # Assert
    assert deleted_item is not None
    assert deleted_item.name == "Item 1"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item1.id)
    assert retrieved_item is None


def test_delete_by_should_handle_unicode_filters(db):
    """Test deleting with unicode string filters."""
    # Arrange
    item1 = db.insert(Item, name="Café", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    deleted_item = db.delete_by(Item, name="Café")

    # Assert
    assert deleted_item is not None
    assert deleted_item.name == "Café"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item1.id)
    assert retrieved_item is None


def test_delete_by_should_handle_special_characters_filters(db):
    """Test deleting with special characters in filters."""
    # Arrange
    item1 = db.insert(Item, name="Item@#$%", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    deleted_item = db.delete_by(Item, name="Item@#$%")

    # Assert
    assert deleted_item is not None
    assert deleted_item.name == "Item@#$%"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item1.id)
    assert retrieved_item is None


def test_delete_by_should_handle_very_long_string_filters(db):
    """Test deleting with very long string filters."""
    # Arrange
    long_name = "A" * 100
    item1 = db.insert(Item, name=long_name, color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    deleted_item = db.delete_by(Item, name=long_name)

    # Assert
    assert deleted_item is not None
    assert deleted_item.name == long_name

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item1.id)
    assert retrieved_item is None


def test_delete_by_should_handle_relationship_replacement(db):
    """Test deleting with relationship replacement scenarios."""
    # Arrange
    item_type1 = db.insert(ItemType, name="Electronics")
    item_type2 = db.insert(ItemType, name="Clothing")
    item1 = db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type1)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type2)

    # Act
    deleted_item = db.delete_by(Item, **{"item_type.name": "Electronics"})

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item1.id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item1.id)
    assert retrieved_item is None

    # The other item should still exist
    retrieved_item2 = db.get(Item, item2.id)
    assert retrieved_item2 is not None


def test_delete_by_should_handle_relationship_removal(db):
    """Test deleting with relationship removal scenarios."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    item1 = db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type)

    # Act
    deleted_item = db.delete_by(Item, name="Item 1")

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item1.id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item1.id)
    assert retrieved_item is None

    # The other item should still exist
    retrieved_item2 = db.get(Item, item2.id)
    assert retrieved_item2 is not None


def test_delete_by_should_handle_complex_nested_filters(db):
    """Test deleting with complex nested relationship filters."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    item1 = db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type)
    item_list = db.insert(ItemList, name="Test List", items=[item1, item2])

    # Act
    deleted_list = db.delete_by(ItemList, **{"items.item_type.name": "Electronics"})

    # Assert
    assert deleted_list is not None
    assert deleted_list.id == item_list.id

    # Verify it's actually deleted
    retrieved_list = db.get(ItemList, item_list.id)
    assert retrieved_list is None


def test_delete_by_should_handle_large_datasets(db):
    """Test deleting from large datasets."""
    # Arrange
    items = []
    for i in range(100):
        item = db.insert(Item, name=f"Item {i}", color="red", price=i)
        items.append(item)

    # Act
    deleted_item = db.delete_by(Item, name="Item 50")

    # Assert
    assert deleted_item is not None
    assert deleted_item.name == "Item 50"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None

    # Other items should still exist
    for i in range(100):
        if i != 50:
            retrieved_item = db.get(Item, items[i].id)
            assert retrieved_item is not None


def test_delete_by_should_handle_concurrent_operations(db):
    """Test deleting with concurrent-like operations."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)

    # Act - Simulate concurrent operations
    deleted1 = db.delete_by(Item, name="Item 1")
    updated2 = db.update(Item, item2.id, name="Updated Item 2")
    deleted2 = db.delete_by(Item, name="Updated Item 2")

    # Assert
    assert deleted1 is not None
    assert deleted2 is not None
    assert updated2 is not None

    # Both should be deleted
    assert db.get(Item, item1.id) is None
    assert db.get(Item, item2.id) is None


def test_delete_by_should_handle_edge_case_filters(db):
    """Test deleting with edge case filter values."""
    # Arrange
    item1 = db.insert(Item, name="", color="red", price=0)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    deleted_item = db.delete_by(Item, name="")

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item1.id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item1.id)
    assert retrieved_item is None


def test_delete_by_should_handle_negative_value_filters(db):
    """Test deleting with negative value filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=-10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    deleted_item = db.delete_by(Item, price=-10)

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item1.id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item1.id)
    assert retrieved_item is None


def test_delete_by_should_handle_float_value_filters(db):
    """Test deleting with whole-number float prices (coerced to int)."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10.0)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20.0)

    # Act
    deleted_item = db.delete_by(Item, price=10)

    # Assert
    assert deleted_item is not None
    assert deleted_item.id == item1.id

    # Verify it's actually deleted
    retrieved_item = db.get(Item, item1.id)
    assert retrieved_item is None


def test_delete_by_should_handle_list_filters(db):
    """Test deleting with list filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item3 = db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    deleted_item = db.delete_by(Item, color__in=["red", "blue"])

    # Assert
    assert deleted_item is not None
    assert deleted_item.color in ["red", "blue"]

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None


def test_delete_by_should_handle_negation_filters(db):
    """Test deleting with negation filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item3 = db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    deleted_item = db.delete_by(Item, color__ne="red")

    # Assert
    assert deleted_item is not None
    assert deleted_item.color != "red"

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None


def test_delete_by_should_handle_range_filters(db):
    """Test deleting with range filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item3 = db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    deleted_item = db.delete_by(Item, price__ge=15, price__lt=25)

    # Assert
    assert deleted_item is not None
    assert 15 <= deleted_item.price < 25

    # Verify it's actually deleted
    retrieved_item = db.get(Item, deleted_item.id)
    assert retrieved_item is None


def test_delete_by_should_handle_mixed_type_filters(db):
    """Test deleting with mixed type filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    result = db.delete_by(Item, name="Item 1", price="10")  # String vs int

    # Assert
    assert result is None

    # No items should be deleted due to type mismatch
    retrieved_item1 = db.get(Item, item1.id)
    retrieved_item2 = db.get(Item, item2.id)
    assert retrieved_item1 is not None
    assert retrieved_item2 is not None


def test_delete_by_should_handle_validation_errors_gracefully(db):
    """Test that delete_by handles validation errors gracefully."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=10)

    # Act - Try to delete with invalid filter
    try:
        result = db.delete_by(Item, invalid_field="value")
    except (AttributeError, KeyError):
        # This is expected behavior for invalid fields
        result = None

    # Assert
    # The original item should still exist
    retrieved_item = db.get(Item, item.id)
    assert retrieved_item is not None


def test_delete_by_should_handle_empty_database(db):
    """Test deleting from empty database."""
    # Act
    result = db.delete_by(Item, name="Test Item")

    # Assert
    assert result is None


def test_delete_by_should_handle_multiple_deletions(db):
    """Test deleting multiple records with multiple calls."""
    # Arrange
    item1 = db.insert(Item, name="Test Item", color="red", price=10)
    item2 = db.insert(Item, name="Test Item", color="blue", price=20)
    item3 = db.insert(Item, name="Other Item", color="green", price=30)

    # Act
    deleted1 = db.delete_by(Item, name="Test Item")
    deleted2 = db.delete_by(Item, name="Test Item")
    deleted3 = db.delete_by(Item, name="Other Item")

    # Assert
    assert deleted1 is not None
    assert deleted2 is not None
    assert deleted3 is not None

    # All should be deleted
    assert db.get(Item, item1.id) is None
    assert db.get(Item, item2.id) is None
    assert db.get(Item, item3.id) is None


def test_delete_by_should_handle_relationship_cleanup(db):
    """Test that delete_by properly cleans up relationships."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item_list = db.insert(ItemList, name="Test List", items=[item1, item2])

    # Act
    deleted_item = db.delete_by(Item, name="Item 1")

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
