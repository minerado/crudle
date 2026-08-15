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

def test_list_with_sorting(db):
    """Test listing with sorting."""
    # Arrange
    Item.insert(db, name="Item 1", price=30)
    Item.insert(db, name="Item 2", price=10)
    Item.insert(db, name="Item 3", price=20)

    # Act
    items_sorted_by_price = Item.list(db, sort=[{"field": "price", "order": "asc"}])

    # Assert
    assert len(items_sorted_by_price) == 3
    assert items_sorted_by_price[0].price == 10
    assert items_sorted_by_price[1].price == 20
    assert items_sorted_by_price[2].price == 30

def test_list_with_sorting_desc(db):
    """Test listing with descending sorting."""
    # Arrange
    Item.insert(db, name="Item 1", price=30)
    Item.insert(db, name="Item 2", price=10)
    Item.insert(db, name="Item 3", price=20)

    # Act
    items_sorted_by_price = Item.list(db, sort=[{"field": "price", "order": "desc"}])

    # Assert
    assert len(items_sorted_by_price) == 3
    assert items_sorted_by_price[0].price == 30
    assert items_sorted_by_price[1].price == 20
    assert items_sorted_by_price[2].price == 10

def test_list_with_limit(db):
    """Test listing with limit."""
    # Arrange
    for i in range(5):
        Item.insert(db, name=f"Item {i + 1}", price=i * 10)

    # Act
    limited_items = Item.list(db, limit=3)

    # Assert
    assert len(limited_items) == 3

def test_list_with_skip(db):
    """Test listing with skip (offset)."""
    # Arrange
    for i in range(5):
        Item.insert(db, name=f"Item {i + 1}", price=i * 10)

    # Act
    skipped_items = Item.list(db, skip=2)

    # Assert
    assert len(skipped_items) == 3

def test_list_with_limit_and_skip(db):
    """Test listing with both limit and skip."""
    # Arrange
    for i in range(5):
        Item.insert(db, name=f"Item {i + 1}", price=i * 10)

    # Act
    paginated_items = Item.list(db, limit=2, skip=1)

    # Assert
    assert len(paginated_items) == 2

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

@pytest.mark.skip(reason="DISTINCT ON is only supported by PostgreSQL, not SQLite")

def test_list_with_distinct_on(db):
    """Test listing with distinct_on functionality."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="red", price=20)  # Same color as Item 1
    Item.insert(db, name="Item 3", color="blue", price=30)

    # Act
    distinct_items = Item.list(db, distinct_on=["color"])

    # Assert
    assert len(distinct_items) == 2  # Should only return one item per color
    colors = [item.color for item in distinct_items]
    assert "red" in colors
    assert "blue" in colors
    assert len(set(colors)) == 2  # All colors should be unique

@pytest.mark.skip(reason="DISTINCT ON is only supported by PostgreSQL, not SQLite")

def test_list_with_distinct_on_multiple_fields(db):
    """Test listing with distinct_on on multiple fields."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="red", price=10)  # Same color and price
    Item.insert(db, name="Item 3", color="red", price=20)  # Same color, different price
    Item.insert(
        db, name="Item 4", color="blue", price=10
    )  # Different color, same price

    # Act
    distinct_items = Item.list(db, distinct_on=["color", "price"])

    # Assert
    assert len(distinct_items) == 3  # Should return unique combinations
    combinations = [(item.color, item.price) for item in distinct_items]
    assert ("red", 10) in combinations
    assert ("red", 20) in combinations
    assert ("blue", 10) in combinations
    assert len(set(combinations)) == 3  # All combinations should be unique

@pytest.mark.skip(reason="DISTINCT ON is only supported by PostgreSQL, not SQLite")

def test_list_with_distinct_on_and_filters(db):
    """Test listing with distinct_on and filters."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="red", price=20)
    Item.insert(db, name="Item 3", color="blue", price=30)
    Item.insert(db, name="Item 4", color="green", price=40)

    # Act
    distinct_red_items = Item.list(db, color="red", distinct_on=["color"])

    # Assert
    assert len(distinct_red_items) == 1  # Only one red item should be returned
    assert distinct_red_items[0].color == "red"

@pytest.mark.skip(reason="DISTINCT ON is only supported by PostgreSQL, not SQLite")

def test_list_with_distinct_on_and_sorting(db):
    """Test listing with distinct_on and sorting."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="red", price=20)
    Item.insert(db, name="Item 3", color="blue", price=30)

    # Act
    distinct_items = Item.list(
        db, distinct_on=["color"], sort=[{"field": "price", "order": "desc"}]
    )

    # Assert
    assert len(distinct_items) == 2
    # Should return the highest priced item for each color
    colors = [item.color for item in distinct_items]
    assert "red" in colors
    assert "blue" in colors

@pytest.mark.skip(reason="DISTINCT ON is only supported by PostgreSQL, not SQLite")

@pytest.mark.skip(reason="DISTINCT ON is only supported by PostgreSQL, not SQLite")

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

@pytest.mark.skip(reason="DISTINCT ON is only supported by PostgreSQL, not SQLite")

def test_list_with_distinct_on_single_record(db):
    """Test listing with distinct_on when only one record exists."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")

    # Act
    items = Item.list(db, distinct_on=["color"])

    # Assert
    assert len(items) == 1
    assert items[0].color == "red"

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
