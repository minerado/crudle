"""
Test list operations for memory adapter.
"""

from datetime import datetime, timezone

import pytest

from tests.crudle.adapters.memory.models import Item, ItemType


def test_list_should_return_all_records(db):
    """Test listing all records without filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item3 = db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    items = db.list(Item)

    # Assert
    assert len(items) == 3
    assert item1 in items
    assert item2 in items
    assert item3 in items

def test_list_should_return_empty_list_when_no_records(db):
    """Test listing when no records exist."""
    # Act
    items = db.list(Item)

    # Assert
    assert items == []

def test_list_with_eq_operator(db):
    """Test listing with equality operator."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item3 = db.insert(Item, name="Item 3", color="red", price=30)

    # Act
    red_items = db.list(Item, color="red")
    blue_items = db.list(Item, color="blue")

    # Assert
    assert len(red_items) == 2
    assert item1 in red_items
    assert item3 in red_items
    assert item2 not in red_items

    assert len(blue_items) == 1
    assert item2 in blue_items

def test_list_with_multiple_filters(db):
    """Test listing with multiple filters combined."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="red", price=20)
    item3 = db.insert(Item, name="Item 3", color="blue", price=10)
    item4 = db.insert(Item, name="Item 4", color="red", price=30)

    # Act
    red_expensive_items = db.list(Item, color="red", price__gt=15)

    # Assert
    assert len(red_expensive_items) == 2
    assert item2 in red_expensive_items
    assert item4 in red_expensive_items
    assert item1 not in red_expensive_items
    assert item3 not in red_expensive_items

def test_list_with_datetime_filters(db):
    """Test listing with datetime filters."""
    # Arrange
    now = datetime.now(timezone.utc)
    item1 = db.insert(Item, name="Item 1", created_at=now)
    item2 = db.insert(Item, name="Item 2", created_at=now)

    # Act
    items_by_date = db.list(Item, created_at__ge=now)

    # Assert
    assert len(items_by_date) == 2
    assert item1 in items_by_date
    assert item2 in items_by_date

def test_list_with_empty_filters(db):
    """Test listing with empty filter dictionary."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")

    # Act
    items = db.list(Item, **{})

    # Assert
    assert len(items) == 2
    assert item1 in items
    assert item2 in items

def test_list_with_none_values(db):
    """Test listing with None values in filters."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color=None, price=20)
    item3 = db.insert(Item, name="Item 3", color="blue", price=None)

    # Act
    items_with_none_color = db.list(Item, color=None)
    items_with_none_price = db.list(Item, price=None)

    # Assert
    assert len(items_with_none_color) == 1
    assert item2 in items_with_none_color

    assert len(items_with_none_price) == 1
    assert item3 in items_with_none_price

def test_list_with_complex_queries(db):
    """Test listing with complex queries combining multiple operators."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="red", price=30)
    db.insert(Item, name="Item 4", color="green", price=15)
    item5 = db.insert(Item, name="Item 5", color="red", price=25)

    # Act
    complex_query = db.list(Item, color__in=["red", "blue"], price__ge=15, price__lt=30)

    # Assert
    assert len(complex_query) == 2
    assert item2 in complex_query  # blue, price=20
    assert item5 in complex_query  # red, price=25

def test_list_with_invalid_operator_raises(db):
    """Test that invalid operators raise like SQLAlchemy."""
    db.insert(Item, name="Item 1", color="red")

    with pytest.raises(Exception, match="Forbidden operator"):
        db.list(Item, color__invalid_op="red")

def test_list_with_nested_dict_filters(db):
    """Test nested dict filters are flattened like SQLAlchemy."""
    item_type = db.insert(ItemType, name="Electronics")
    db.insert(Item, name="Item 1", color="red", price=10, item_type=item_type)
    db.insert(Item, name="Item 2", color="blue", price=20)

    items = db.list(Item, **{"item_type": {"name": "Electronics"}})
    assert len(items) == 1
    assert items[0].name == "Item 1"

def test_list_with_mixed_type_comparisons(db):
    """Test that type mismatches in comparisons return False."""
    # Arrange
    db.insert(Item, name="Item 1", price=10)
    db.insert(Item, name="Item 2", price=20)

    # Act
    items = db.list(Item, price__gt="not_a_number")

    # Assert
    assert len(items) == 0  # Should return empty due to type mismatch

