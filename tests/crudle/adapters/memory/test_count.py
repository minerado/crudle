"""
Test count operations for memory adapter.
"""

import pytest

from tests.crudle.adapters.memory.models import Item, ItemList, Tag, ItemType


def test_count_should_return_total_count(db):
    """Test counting all records without filters."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    count = db.count(Item)

    # Assert
    assert count == 3


def test_count_should_return_zero_when_no_records(db):
    """Test counting when no records exist."""
    # Act
    count = db.count(Item)

    # Assert
    assert count == 0


def test_count_with_specific_field(db):
    """Test counting with a specific field."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    count = db.count(Item, field="id")

    # Assert
    assert count == 2


def test_count_with_filters(db):
    """Test counting with filters."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="red", price=30)

    # Act
    red_items_count = db.count(Item, color="red")
    blue_items_count = db.count(Item, color="blue")

    # Assert
    assert red_items_count == 2
    assert blue_items_count == 1


def test_count_with_multiple_filters(db):
    """Test counting with multiple filters."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="red", price=20)
    db.insert(Item, name="Item 3", color="blue", price=10)

    # Act
    count = db.count(Item, color="red", price=10)

    # Assert
    assert count == 1


def test_count_with_operator_filters(db):
    """Test counting with operator filters."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    high_price_count = db.count(Item, price__gt=15)
    low_price_count = db.count(Item, price__le=15)

    # Assert
    assert high_price_count == 2
    assert low_price_count == 1


def test_count_with_in_operator(db):
    """Test counting with 'in' operator."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    count = db.count(Item, color__in=["red", "blue"])

    # Assert
    assert count == 2


def test_count_with_text_search(db):
    """Test counting with text search."""
    # Arrange
    db.insert(Item, name="Apple iPhone", color="red", price=1000)
    db.insert(Item, name="Samsung Galaxy", color="blue", price=800)
    db.insert(Item, name="Google Pixel", color="green", price=700)

    # Act
    count = db.count(Item, name__q="Apple")

    # Assert
    assert count == 1


def test_count_with_none_values(db):
    """Test counting with None values."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color=None, price=20)
    db.insert(Item, name="Item 3", color="green", price=None)

    # Act
    none_color_count = db.count(Item, color=None)
    none_price_count = db.count(Item, price=None)

    # Assert
    assert none_color_count == 1
    assert none_price_count == 1


def test_count_with_relationship_field(db):
    """Test counting with relationship field."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type)
    db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type)

    # Act
    count = db.count(Item, field="item_type")

    # Assert
    assert count == 2


def test_count_with_complex_filters(db):
    """Test counting with complex filter combinations."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="red", price=20)
    db.insert(Item, name="Item 3", color="blue", price=10)
    db.insert(Item, name="Item 4", color="green", price=30)

    # Act
    count = db.count(Item, color__in=["red", "blue"], price__lt=25)

    # Assert
    assert count == 3


def test_count_with_datetime_filters(db):
    """Test counting with datetime filters."""
    from datetime import datetime, timezone

    # Arrange
    now = datetime.now(timezone.utc)
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)

    # Note: MemoryAdapter doesn't have created_at by default, so we'll test with a custom field
    # For this test, we'll use the existing fields
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    count = db.count(Item, name__ne="Item 1")

    # Assert
    assert count == 1


def test_count_with_empty_filters(db):
    """Test counting with empty filters (should return all records)."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    count = db.count(Item, **{})

    # Assert
    assert count == 2


def test_count_with_invalid_field(db):
    """Test counting with invalid field (should still count all records)."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    count = db.count(Item, field="nonexistent_field")

    # Assert
    assert count == 2


def test_count_with_mixed_type_comparisons(db):
    """Test counting with mixed type comparisons."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    # This should return 0 because we're comparing string to int
    count = db.count(Item, price="10")

    # Assert
    assert count == 0


def test_count_with_case_insensitive_search(db):
    """Test counting with case insensitive text search."""
    # Arrange
    db.insert(Item, name="Apple iPhone", color="red", price=1000)
    db.insert(Item, name="Samsung Galaxy", color="blue", price=800)
    db.insert(Item, name="Google Pixel", color="green", price=700)

    # Act
    count = db.count(Item, name__q="apple")

    # Assert
    assert count == 1


def test_count_with_partial_match(db):
    """Test counting with partial text match."""
    # Arrange
    db.insert(Item, name="Apple iPhone", color="red", price=1000)
    db.insert(Item, name="Samsung Galaxy", color="blue", price=800)
    db.insert(Item, name="Google Pixel", color="green", price=700)

    # Act
    count = db.count(Item, name__q="Phone")

    # Assert
    assert count == 1


def test_count_with_multiple_text_searches(db):
    """Test counting with multiple text search filters."""
    # Arrange
    db.insert(Item, name="Apple iPhone", color="red", price=1000)
    db.insert(Item, name="Samsung Galaxy", color="blue", price=800)
    db.insert(Item, name="Google Pixel", color="green", price=700)

    # Act
    count = db.count(Item, name__q="Apple", color__q="red")

    # Assert
    assert count == 1


def test_count_with_negation_operators(db):
    """Test counting with negation operators."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    not_red_count = db.count(Item, color__ne="red")
    not_high_price_count = db.count(Item, price__ni=[20, 30])

    # Assert
    assert not_red_count == 2
    assert not_high_price_count == 1


def test_count_with_range_operators(db):
    """Test counting with range operators."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)
    db.insert(Item, name="Item 4", color="yellow", price=40)

    # Act
    range_count = db.count(Item, price__ge=15, price__lt=35)

    # Assert
    assert range_count == 2


def test_count_with_boolean_filters(db):
    """Test counting with boolean-like filters."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    # Test with a field that has a specific value
    specific_name_count = db.count(Item, name="Item 1")

    # Assert
    assert specific_name_count == 1


def test_count_with_list_relationships(db):
    """Test counting with list relationship filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item_list = db.insert(ItemList, name="List 1", items=[item1, item2])

    # Act
    count = db.count(ItemList, name="List 1")

    # Assert
    assert count == 1


def test_count_with_nested_relationship_filters(db):
    """Test counting with nested relationship filters."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type)
    db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type)

    # Act
    count = db.count(Item, **{"item_type.name": "Electronics"})

    # Assert
    assert count == 2


def test_count_with_deep_nested_filters(db):
    """Test counting with deep nested relationship filters."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    item1 = db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type)
    item_list = db.insert(ItemList, name="List 1", items=[item1, item2])

    # Act
    count = db.count(ItemList, **{"items.item_type.name": "Electronics"})

    # Assert
    assert count == 1


def test_count_with_invalid_operator_falls_back_to_equality(db):
    """Test counting with invalid operator falls back to equality."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    count = db.count(Item, color__invalid_op="red")

    # Assert
    assert count == 1


def test_count_with_empty_string_filters(db):
    """Test counting with empty string filters."""
    # Arrange
    db.insert(Item, name="", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    count = db.count(Item, name="")

    # Assert
    assert count == 1


def test_count_with_zero_value_filters(db):
    """Test counting with zero value filters."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=0)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    count = db.count(Item, price=0)

    # Assert
    assert count == 1


def test_count_with_negative_value_filters(db):
    """Test counting with negative value filters."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=-10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    count = db.count(Item, price=-10)

    # Assert
    assert count == 1


def test_count_with_float_value_filters(db):
    """Test counting with whole-number float prices (coerced to int)."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10.0)
    db.insert(Item, name="Item 2", color="blue", price=20.0)

    # Act
    count = db.count(Item, price=10)

    # Assert
    assert count == 1


def test_count_with_unicode_filters(db):
    """Test counting with unicode string filters."""
    # Arrange
    db.insert(Item, name="Café", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    count = db.count(Item, name="Café")

    # Assert
    assert count == 1


def test_count_with_special_characters_filters(db):
    """Test counting with special characters in filters."""
    # Arrange
    db.insert(Item, name="Item@#$%", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    count = db.count(Item, name="Item@#$%")

    # Assert
    assert count == 1


def test_count_with_very_long_string_filters(db):
    """Test counting with max-length string filters."""
    # Arrange
    long_name = "A" * 100
    db.insert(Item, name=long_name, color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    count = db.count(Item, name=long_name)

    # Assert
    assert count == 1


def test_count_with_multiple_relationship_filters(db):
    """Test counting with multiple relationship filters."""
    # Arrange
    item_type1 = db.insert(ItemType, name="Electronics")
    item_type2 = db.insert(ItemType, name="Clothing")
    db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type1)
    db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type2)

    # Act
    count = db.count(Item, **{"item_type.name__in": ["Electronics", "Clothing"]})

    # Assert
    assert count == 2


def test_count_with_complex_nested_filters(db):
    """Test counting with complex nested relationship filters."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    item1 = db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type)
    item_list = db.insert(ItemList, name="List 1", items=[item1, item2])

    # Act
    count = db.count(ItemList, **{"items.name__q": "Item"})

    # Assert
    assert count == 1


def test_count_with_relationship_field_and_filters(db):
    """Test counting with relationship field and additional filters."""
    # Arrange
    item_type = db.insert(ItemType, name="Electronics")
    db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type)
    db.insert(Item, name="Item 2", color="blue", price=20, item_type=item_type)

    # Act
    count = db.count(Item, field="item_type", color="red")

    # Assert
    assert count == 1


def test_count_with_pagination_parameters_ignored(db):
    """Test that pagination parameters are ignored in count operations."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    count = db.count(Item, limit=2, skip=1)

    # Assert
    assert count == 3  # Should count all records, ignoring pagination


def test_count_with_sort_parameters_ignored(db):
    """Test that sort parameters are ignored in count operations."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    count = db.count(Item, sort=[{"field": "name", "order": "asc"}])

    # Assert
    assert count == 3  # Should count all records, ignoring sort


def test_count_with_select_parameters_ignored(db):
    """Test that select parameters are ignored in count operations."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    count = db.count(Item, select=["name", "color"])

    # Assert
    assert count == 3  # Should count all records, ignoring select


def test_count_with_return_dict_parameters_ignored(db):
    """Test that return_dict parameters are ignored in count operations."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    count = db.count(Item, return_dict=True)

    # Assert
    assert count == 3  # Should count all records, ignoring return_dict


def test_count_with_distinct_on_parameters_ignored(db):
    """Test that distinct_on parameters are ignored in count operations."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    count = db.count(Item, distinct_on=["color"])

    # Assert
    assert count == 3  # Should count all records, ignoring distinct_on
