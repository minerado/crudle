from datetime import datetime, timezone

from tests.models import Item


def test_list_should_return_all_records(db):
    """Test listing all records without filters."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    item3 = Item.insert(db, name="Item 3", color="green", price=30)

    # Act
    items = Item.list(db)

    # Assert
    assert len(items) == 3
    assert item1 in items
    assert item2 in items
    assert item3 in items

def test_list_should_return_empty_list_when_no_records(db):
    """Test listing when no records exist."""
    # Act
    items = Item.list(db)

    # Assert
    assert items == []

def test_list_with_multiple_filters(db):
    """Test listing with multiple filters combined."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="red", price=20)
    item3 = Item.insert(db, name="Item 3", color="blue", price=10)
    item4 = Item.insert(db, name="Item 4", color="red", price=30)

    # Act
    red_expensive_items = Item.list(db, color="red", price__gt=15)

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
    item1 = Item.insert(db, name="Item 1", created_at=now)
    item2 = Item.insert(db, name="Item 2", created_at=now)

    # Act
    items_by_date = Item.list(db, created_at__ge=now)

    # Assert
    assert len(items_by_date) == 2
    assert item1 in items_by_date
    assert item2 in items_by_date

def test_list_with_empty_filters(db):
    """Test listing with empty filter dictionary."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red")
    item2 = Item.insert(db, name="Item 2", color="blue")

    # Act
    items = Item.list(db, **{})

    # Assert
    assert len(items) == 2
    assert item1 in items
    assert item2 in items

def test_list_with_complex_queries(db):
    """Test listing with complex queries combining multiple operators."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    Item.insert(db, name="Item 3", color="red", price=30)
    Item.insert(db, name="Item 4", color="green", price=15)
    item5 = Item.insert(db, name="Item 5", color="red", price=25)

    # Act
    complex_query = Item.list(db, color__in=["red", "blue"], price__ge=15, price__lt=30)

    # Assert
    assert len(complex_query) == 2
    assert item2 in complex_query  # blue, price=20
    assert item5 in complex_query  # red, price=25

