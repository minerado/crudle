"""
Test list operations for memory adapter.
"""

import pytest
from datetime import datetime, timezone

from tests.crudle.adapters.memory.models import Item, ItemList, Tag, ItemType


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


def test_list_with_lt_operator(db):
    """Test listing with less than operator."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", price=10)
    item2 = db.insert(Item, name="Item 2", price=20)
    item3 = db.insert(Item, name="Item 3", price=30)

    # Act
    cheap_items = db.list(Item, price__lt=25)

    # Assert
    assert len(cheap_items) == 2
    assert item1 in cheap_items
    assert item2 in cheap_items
    assert item3 not in cheap_items


def test_list_with_le_operator(db):
    """Test listing with less than or equal operator."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", price=10)
    item2 = db.insert(Item, name="Item 2", price=20)
    item3 = db.insert(Item, name="Item 3", price=30)

    # Act
    items_le_20 = db.list(Item, price__le=20)

    # Assert
    assert len(items_le_20) == 2
    assert item1 in items_le_20
    assert item2 in items_le_20
    assert item3 not in items_le_20


def test_list_with_in_operator(db):
    """Test listing with in operator."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")
    item3 = db.insert(Item, name="Item 3", color="green")
    item4 = db.insert(Item, name="Item 4", color="yellow")

    # Act
    selected_items = db.list(Item, color__in=["red", "blue"])

    # Assert
    assert len(selected_items) == 2
    assert item1 in selected_items
    assert item2 in selected_items
    assert item3 not in selected_items
    assert item4 not in selected_items


def test_list_with_ni_operator(db):
    """Test listing with not in operator."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")
    item3 = db.insert(Item, name="Item 3", color="green")
    item4 = db.insert(Item, name="Item 4", color="yellow")

    # Act
    excluded_items = db.list(Item, color__ni=["red", "blue"])

    # Assert
    assert len(excluded_items) == 2
    assert item3 in excluded_items
    assert item4 in excluded_items
    assert item1 not in excluded_items
    assert item2 not in excluded_items


def test_list_with_q_operator(db):
    """Test listing with q (text search) operator."""
    # Arrange
    item1 = db.insert(Item, name="Apple iPhone", color="red")
    item2 = db.insert(Item, name="Samsung Galaxy", color="blue")
    item3 = db.insert(Item, name="Google Pixel", color="green")

    # Act
    search_results = db.list(Item, name__q="Apple")

    # Assert
    assert len(search_results) == 1
    assert item1 in search_results
    assert item2 not in search_results
    assert item3 not in search_results


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


def test_list_with_nested_filters(db):
    """Test listing with nested relationship filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")
    item3 = db.insert(Item, name="Item 3", color="green")

    list1 = db.insert(ItemList, name="List 1", items=[item1, item2])
    list2 = db.insert(ItemList, name="List 2", items=[item3])

    # Act
    lists_with_red_items = db.list(ItemList, **{"items.color": "red"})

    # Assert
    assert len(lists_with_red_items) == 1
    assert list1 in lists_with_red_items
    assert list2 not in lists_with_red_items


def test_list_with_deep_nested_filters(db):
    """Test listing with deeply nested relationship filters."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")

    list1 = db.insert(ItemList, name="List 1", items=[item1])
    list2 = db.insert(ItemList, name="List 2", items=[item2])

    tag1 = db.insert(Tag, name="expensive", items=[item1])
    tag2 = db.insert(Tag, name="cheap", items=[item2])

    # Act
    lists_with_expensive_items = db.list(ItemList, **{"items.tags.name": "expensive"})

    # Assert
    assert len(lists_with_expensive_items) == 1
    assert lists_with_expensive_items[0].id == list1.id
    assert not any(item.id == list2.id for item in lists_with_expensive_items)


def test_list_with_sorting(db):
    """Test listing with sorting."""
    # Arrange
    db.insert(Item, name="Item 1", price=30)
    db.insert(Item, name="Item 2", price=10)
    db.insert(Item, name="Item 3", price=20)

    # Act
    items_sorted_by_price = db.list(Item, sort=[{"field": "price", "order": "asc"}])

    # Assert
    assert len(items_sorted_by_price) == 3
    assert items_sorted_by_price[0].price == 10
    assert items_sorted_by_price[1].price == 20
    assert items_sorted_by_price[2].price == 30


def test_list_with_sorting_desc(db):
    """Test listing with descending sorting."""
    # Arrange
    db.insert(Item, name="Item 1", price=30)
    db.insert(Item, name="Item 2", price=10)
    db.insert(Item, name="Item 3", price=20)

    # Act
    items_sorted_by_price = db.list(Item, sort=[{"field": "price", "order": "desc"}])

    # Assert
    assert len(items_sorted_by_price) == 3
    assert items_sorted_by_price[0].price == 30
    assert items_sorted_by_price[1].price == 20
    assert items_sorted_by_price[2].price == 10


def test_list_with_multiple_sorting(db):
    """Test listing with multiple sort fields."""
    # Arrange
    db.insert(Item, name="Item A", color="red", price=10)
    db.insert(Item, name="Item B", color="red", price=20)
    db.insert(Item, name="Item C", color="blue", price=10)
    db.insert(Item, name="Item D", color="blue", price=20)

    # Act
    items_sorted = db.list(
        Item,
        sort=[{"field": "color", "order": "asc"}, {"field": "price", "order": "desc"}],
    )

    # Assert
    assert len(items_sorted) == 4
    # Should be sorted by color first (blue, red), then by price desc
    assert items_sorted[0].color == "blue" and items_sorted[0].price == 20
    assert items_sorted[1].color == "blue" and items_sorted[1].price == 10
    assert items_sorted[2].color == "red" and items_sorted[2].price == 20
    assert items_sorted[3].color == "red" and items_sorted[3].price == 10


def test_list_with_limit(db):
    """Test listing with limit."""
    # Arrange
    for i in range(5):
        db.insert(Item, name=f"Item {i + 1}", price=i * 10)

    # Act
    limited_items = db.list(Item, limit=3)

    # Assert
    assert len(limited_items) == 3


def test_list_with_skip(db):
    """Test listing with skip (offset)."""
    # Arrange
    for i in range(5):
        db.insert(Item, name=f"Item {i + 1}", price=i * 10)

    # Act
    skipped_items = db.list(Item, skip=2)

    # Assert
    assert len(skipped_items) == 3


def test_list_with_limit_and_skip(db):
    """Test listing with both limit and skip."""
    # Arrange
    for i in range(5):
        db.insert(Item, name=f"Item {i + 1}", price=i * 10)

    # Act
    paginated_items = db.list(Item, limit=2, skip=1)

    # Assert
    assert len(paginated_items) == 2


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


def test_list_with_relationship_filters_and_operators(db):
    """Test listing with relationship filters using operators."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    item3 = db.insert(Item, name="Item 3", color="green", price=30)

    list1 = db.insert(ItemList, name="List 1", items=[item2])
    list2 = db.insert(ItemList, name="List 2", items=[item3])

    # Act
    lists_with_expensive_items = db.list(ItemList, **{"items.price__gt": 15})

    # Assert
    assert len(lists_with_expensive_items) == 2
    assert list1 in lists_with_expensive_items  # has item2 with price=20
    assert list2 in lists_with_expensive_items  # has item3 with price=30


def test_list_with_select_fields(db):
    """Test listing with specific field selection."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    # Act
    items = db.list(Item, select=["name", "color"])

    # Assert
    assert len(items) == 3
    # When using select, we get dictionaries with field names as keys
    names = [item["name"] for item in items]
    colors = [item["color"] for item in items]

    assert "Item 1" in names
    assert "Item 2" in names
    assert "Item 3" in names
    assert "red" in colors
    assert "blue" in colors
    assert "green" in colors


def test_list_with_select_single_field(db):
    """Test listing with single field selection."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    items = db.list(Item, select=["name"])

    # Assert
    assert len(items) == 2
    names = [item["name"] for item in items]
    assert "Item 1" in names
    assert "Item 2" in names


def test_list_with_select_relationship_fields(db):
    """Test listing with relationship field selection."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")
    list1 = db.insert(ItemList, name="List 1", items=[item1, item2])

    # Act
    lists = db.list(ItemList, select=["name", "items.name", "items.color"])

    # Assert
    assert len(lists) == 1
    list_data = lists[0]
    assert list_data["name"] == "List 1"
    assert "items" in list_data
    assert len(list_data["items"]) == 2


def test_list_with_return_dict(db):
    """Test listing with return_dict option."""
    # Arrange
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    # Act
    items = db.list(Item, return_dict=True)

    # Assert
    assert len(items) == 2
    assert all(isinstance(item, dict) for item in items)
    assert all("name" in item for item in items)
    assert all("color" in item for item in items)
    assert all("price" in item for item in items)


def test_list_with_text_search_case_insensitive(db):
    """Test text search is case insensitive."""
    # Arrange
    item1 = db.insert(Item, name="Apple iPhone", color="red")
    item2 = db.insert(Item, name="Samsung Galaxy", color="blue")
    item3 = db.insert(Item, name="Google Pixel", color="green")

    # Act
    search_results = db.list(Item, name__q="apple")

    # Assert
    assert len(search_results) == 1
    assert item1 in search_results


def test_list_with_text_search_partial_match(db):
    """Test text search with partial matches."""
    # Arrange
    item1 = db.insert(Item, name="Apple iPhone 13", color="red")
    item2 = db.insert(Item, name="Apple MacBook", color="blue")
    item3 = db.insert(Item, name="Samsung Galaxy", color="green")

    # Act
    search_results = db.list(Item, name__q="Apple")

    # Assert
    assert len(search_results) == 2
    assert item1 in search_results
    assert item2 in search_results
    assert item3 not in search_results


def test_list_with_invalid_operator_raises(db):
    """Test that invalid operators raise like SQLAlchemy."""
    db.insert(Item, name="Item 1", color="red")

    with pytest.raises(Exception, match="Forbidden operator"):
        db.list(Item, color__invalid_op="red")


def test_list_default_limit_is_25(db):
    """Test README default list limit of 25."""
    for i in range(30):
        db.insert(Item, name=f"Item {i}", color="red", price=i)

    items = db.list(Item)
    assert len(items) == 25

    items_all = db.list(Item, limit=100)
    assert len(items_all) == 30


def test_list_with_distinct_on_fields(db):
    """Test distinct_on keeps first row per key after sort."""
    db.insert(Item, name="A", color="red", price=10)
    db.insert(Item, name="B", color="red", price=20)
    db.insert(Item, name="C", color="blue", price=30)

    items = db.list(
        Item,
        sort=[{"field": "price", "order": "asc"}],
        distinct_on=["color"],
        limit=100,
    )
    assert len(items) == 2
    colors = {item.color for item in items}
    assert colors == {"red", "blue"}


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
    item1 = db.insert(Item, name="Item 1", price=10)
    item2 = db.insert(Item, name="Item 2", price=20)

    # Act
    items = db.list(Item, price__gt="not_a_number")

    # Assert
    assert len(items) == 0  # Should return empty due to type mismatch


def test_list_with_sorting_and_pagination(db):
    """Test combining sorting with pagination."""
    # Arrange
    for i in range(10):
        db.insert(Item, name=f"Item {i + 1}", price=(i + 1) * 10)

    # Act
    items = db.list(Item, sort=[{"field": "price", "order": "desc"}], limit=3, skip=2)

    # Assert
    assert len(items) == 3
    # Should be sorted by price desc, then take items 3-5 (skip=2, limit=3)
    assert items[0].price == 80  # 10th item (100) - 2nd item (20) = 80
    assert items[1].price == 70
    assert items[2].price == 60
