import pytest
from datetime import datetime, timezone

from tests.models import Item, ItemList, Tag

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

def test_list_with_nested_filters(db):
    """Test listing with nested relationship filters."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red")
    item2 = Item.insert(db, name="Item 2", color="blue")
    item3 = Item.insert(db, name="Item 3", color="green")

    list1 = ItemList.insert(db, name="List 1", items=[item1, item2])
    list2 = ItemList.insert(db, name="List 2", items=[item3])

    # Act
    lists_with_red_items = ItemList.list(db, **{"items.color": "red"})

    # Assert
    assert len(lists_with_red_items) == 1
    assert list1 in lists_with_red_items
    assert list2 not in lists_with_red_items

def test_list_with_deep_nested_filters(db):
    """Test listing with deeply nested relationship filters."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red")
    item2 = Item.insert(db, name="Item 2", color="blue")

    list1 = ItemList.insert(db, name="List 1", items=[item1])
    list2 = ItemList.insert(db, name="List 2", items=[item2])

    Tag.insert(db, name="expensive", items=[item1])
    Tag.insert(db, name="cheap", items=[item2])

    # Act
    lists_with_expensive_items = ItemList.list(db, **{"items.tags.name": "expensive"})

    # Assert
    assert len(lists_with_expensive_items) == 1
    assert list1 in lists_with_expensive_items
    assert list2 not in lists_with_expensive_items

def test_list_with_empty_distinct_on(db):
    """Test listing with empty distinct_on array."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")
    Item.insert(db, name="Item 2", color="blue")

    # Act
    items = Item.list(db, distinct_on=[])

    # Assert
    assert len(items) == 2
    # Should return all items (no distinct filtering)

def test_list_with_custom_filters(db):
    """Test listing with custom filters defined in Queries class."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", price=10)
    item2 = Item.insert(db, name="Item 2", price=20)
    item3 = Item.insert(db, name="Item 3", price=30)

    # Create a custom model with custom filters
    class CustomItem(Item):
        class Queries:
            def filter_expensive(self, query, value):
                if value:
                    return query.filter(Item.price > 15)
                return query

    # Act
    expensive_items = CustomItem.list(db, expensive=True)

    # Assert
    assert len(expensive_items) == 2
    # Check by ID since the objects are different types
    expensive_ids = [item.id for item in expensive_items]
    assert item2.id in expensive_ids
    assert item3.id in expensive_ids
    assert item1.id not in expensive_ids

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

def test_list_with_relationship_filters_and_operators(db):
    """Test listing with relationship filters using operators."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    item3 = Item.insert(db, name="Item 3", color="green", price=30)

    list1 = ItemList.insert(db, name="List 1", items=[item2])
    list2 = ItemList.insert(db, name="List 2", items=[item3])

    # Act
    lists_with_expensive_items = ItemList.list(db, **{"items.price__gt": 15})

    # Assert
    assert len(lists_with_expensive_items) == 2
    assert list1 in lists_with_expensive_items  # has item2 with price=20
    assert list2 in lists_with_expensive_items  # has item3 with price=30

def test_list_with_custom_filter(db):
    """Test listing with custom filter."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)

    # Act
    items = Item.list(db, is_expensive=True)

    # Assert
    assert len(items) == 1
    assert items[0].name == "Item 2"
