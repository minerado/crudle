import pytest
from datetime import datetime, timezone


from tests.models import Item, ItemList, Tag, ItemType


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


@pytest.mark.skip(
    reason="Search functionality requires PostgreSQL tsvector support, not available in SQLite"
)
def test_list_with_search_fields(db):
    """Test listing with search functionality."""
    # Arrange
    item1 = Item.insert(db, name="Apple iPhone", color="red")
    item2 = Item.insert(db, name="Samsung Galaxy", color="blue")
    item3 = Item.insert(db, name="Google Pixel", color="green")

    # Create a custom model with search fields configured
    class SearchableItem(Item):
        class Queries:
            search_fields = ["name"]

    # Act
    search_results = SearchableItem.list(db, search="Apple")

    # Assert
    assert len(search_results) == 1
    assert item1 in search_results
    assert item2 not in search_results
    assert item3 not in search_results


@pytest.mark.skip(
    reason="Search functionality requires PostgreSQL tsvector support, not available in SQLite"
)
def test_list_with_q_operator(db):
    """Test listing with q (search) operator."""
    # Arrange
    item1 = Item.insert(db, name="Apple iPhone", color="red")
    item2 = Item.insert(db, name="Samsung Galaxy", color="blue")
    item3 = Item.insert(db, name="Google Pixel", color="green")

    # Create a custom model with search fields configured
    class SearchableItem(Item):
        class Queries:
            search_fields = ["name"]

    # Act
    search_results = SearchableItem.list(db, name__q="Apple")

    # Assert
    assert len(search_results) == 1
    assert item1 in search_results
    assert item2 not in search_results
    assert item3 not in search_results


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


def test_list_with_select_fields(db):
    """Test listing with specific field selection."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)
    Item.insert(db, name="Item 3", color="green", price=30)

    # Act
    items = Item.list(db, select=["name", "color"])

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
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)

    # Act
    items = Item.list(db, select=["name"])

    # Assert
    assert len(items) == 2
    # When using select, we get dictionaries with field names as keys
    names = [item["name"] for item in items]
    assert "Item 1" in names
    assert "Item 2" in names


def test_list_with_select_and_filters(db):
    """Test listing with field selection and filters."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)
    Item.insert(db, name="Item 3", color="red", price=30)

    # Act
    red_items = Item.list(db, color="red", select=["name", "price"])

    # Assert
    assert len(red_items) == 2
    # When using select, we get dictionaries with field names as keys
    names = [item["name"] for item in red_items]
    prices = [item["price"] for item in red_items]
    assert "Item 1" in names
    assert "Item 3" in names
    assert 10 in prices
    assert 30 in prices


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
def test_list_with_select_and_distinct_on(db):
    """Test listing with both select and distinct_on."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="red", price=20)
    Item.insert(db, name="Item 3", color="blue", price=30)

    # Act
    distinct_items = Item.list(db, distinct_on=["color"], select=["name", "color"])

    # Assert
    assert len(distinct_items) == 2
    # When using select, we get dictionaries with field names as keys
    colors = [item["color"] for item in distinct_items]
    assert "red" in colors
    assert "blue" in colors


def test_list_with_complex_select_expression(db):
    """Test listing with complex select expressions."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)

    # Act
    items = Item.list(db, select=["name", "color", "price"])

    # Assert
    assert len(items) == 2
    # When using select, we get dictionaries with field names as keys
    names = [item["name"] for item in items]
    colors = [item["color"] for item in items]
    prices = [item["price"] for item in items]
    assert "Item 1" in names
    assert "Item 2" in names
    assert "red" in colors
    assert "blue" in colors
    assert 10 in prices
    assert 20 in prices


def test_list_with_empty_select(db):
    """Test listing with empty select array."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")
    Item.insert(db, name="Item 2", color="blue")

    # Act
    items = Item.list(db, select=[])

    # Assert
    assert len(items) == 2
    # Should return all items with all fields (default behavior)


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


def test_list_with_select_single_record(db):
    """Test listing with select when only one record exists."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)

    # Act
    items = Item.list(db, select=["name"])

    # Assert
    assert len(items) == 1
    # When using select, we get dictionaries with field names as keys
    assert items[0]["name"] == "Item 1"


def test_list_with_return_dict(db):
    """Test listing with return_dict=True to get all fields as dictionaries."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)

    # Act
    items = Item.list(db, return_dict=True)

    # Assert
    assert len(items) == 2
    # Should return dictionaries with all column fields
    for item in items:
        assert isinstance(item, dict)
        assert "id" in item
        assert "name" in item
        assert "color" in item
        assert "price" in item
        assert "created_at" in item
        assert "item_list_id" in item
        assert "item_type_id" in item
        # Should not include relationship fields
        assert "item_list" not in item
        assert "tags" not in item
        assert "item_type" not in item


def test_list_with_return_dict_and_filters(db):
    """Test listing with return_dict=True and filters."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)
    Item.insert(db, name="Item 3", color="red", price=30)

    # Act
    red_items = Item.list(db, color="red", return_dict=True)

    # Assert
    assert len(red_items) == 2
    for item in red_items:
        assert isinstance(item, dict)
        assert item["color"] == "red"
        assert "name" in item
        assert "price" in item


def test_list_with_return_dict_and_sorting(db):
    """Test listing with return_dict=True and sorting."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=30)
    Item.insert(db, name="Item 2", color="blue", price=10)
    Item.insert(db, name="Item 3", color="green", price=20)

    # Act
    items = Item.list(db, return_dict=True, sort=[{"field": "price", "order": "asc"}])

    # Assert
    assert len(items) == 3
    assert items[0]["price"] == 10
    assert items[1]["price"] == 20
    assert items[2]["price"] == 30


def test_list_with_return_dict_and_limit(db):
    """Test listing with return_dict=True and limit."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)
    Item.insert(db, name="Item 3", color="green", price=30)

    # Act
    items = Item.list(db, return_dict=True, limit=2)

    # Assert
    assert len(items) == 2
    for item in items:
        assert isinstance(item, dict)
        assert "name" in item


def test_list_with_nested_select_relationship_fields(db):
    """Test listing with select on relationship fields."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red")
    item2 = Item.insert(db, name="Item 2", color="blue")

    ItemList.insert(db, name="List 1", items=[item1, item2])

    # Act
    # This should include the relationship field
    items = Item.list(db, select=["name", "item_list", "color"])

    # Assert
    assert len(items) == 2
    # Should have both regular fields and relationship field
    for item in items:
        assert isinstance(item, dict)
        assert "name" in item
        assert "color" in item
        assert "item_list" in item  # Relationship field should be included
        assert isinstance(item["item_list"], dict)


def test_list_with_select_invalid_relationship_fields(db):
    """Test listing with select on invalid relationship fields."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")

    # Act
    # This should skip the invalid relationship field
    items = Item.list(db, select=["name", "nonexistent_relationship", "color"])

    # Assert
    assert len(items) == 1
    # Should only have the valid fields
    for item in items:
        assert isinstance(item, dict)
        assert "name" in item
        assert "color" in item
        assert "nonexistent_relationship" not in item


def test_list_with_select_only_relationship_fields(db):
    """Test listing with select containing only relationship fields."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")

    # Act
    # This should return data with relationship fields
    items = Item.list(db, select=["item_list", "tags", "item_type"])

    # Assert
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, dict)
    # Should have relationship data (even if None for this item)
    assert "item_list" in item or "item_list_id" in item
    assert "tags" in item or "tags_id" in item
    assert "item_type" in item or "item_type_id" in item


def test_list_with_select_mixed_valid_invalid_fields(db):
    """Test listing with select containing mix of valid and invalid fields."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)

    # Act
    items = Item.list(db, select=["name", "invalid_field", "price", "item_list"])

    # Assert
    assert len(items) == 1
    # Should have the valid fields (including relationship field)
    item = items[0]
    assert isinstance(item, dict)
    assert "name" in item
    assert "price" in item
    assert "item_list" in item  # Relationship field should be included
    assert "invalid_field" not in item
    assert item["name"] == "Item 1"
    assert item["price"] == 10
    assert item["item_list"] is None  # No relationship, so should be None


def test_list_with_empty_select_and_return_dict(db):
    """Test listing with empty select and return_dict=True."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")

    # Act
    items = Item.list(db, select=[], return_dict=True)

    # Assert
    assert len(items) == 1
    # Should return all fields as dictionaries
    item = items[0]
    assert isinstance(item, dict)
    assert "name" in item
    assert "color" in item
    assert "id" in item


def test_list_with_return_dict_and_relationships(db):
    """Test listing with return_dict=True should not include relationship data."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red")
    item2 = Item.insert(db, name="Item 2", color="blue")

    ItemList.insert(db, name="List 1", items=[item1, item2])

    # Act
    items = Item.list(db, return_dict=True)

    # Assert
    assert len(items) == 2
    for item in items:
        assert isinstance(item, dict)
        # Should have all column fields
        assert "id" in item
        assert "name" in item
        assert "color" in item
        assert "item_list_id" in item
        # Should not have relationship objects
        assert "item_list" not in item
        assert "tags" not in item
        assert "item_type" not in item


def test_list_with_select_count_fields(db):
    """Test listing with select containing count fields."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")
    Item.insert(db, name="Item 2", color="red")
    Item.insert(db, name="Item 3", color="blue")

    # Act
    items = Item.list(db, select=["count.id", "color"])

    # Assert
    assert len(items) == 2  # Should group by color
    for item in items:
        assert isinstance(item, dict)
        assert "count.id" in item
        assert "color" in item
        assert isinstance(item["count.id"], int)
        assert item["count.id"] > 0


def test_list_with_select_count_single_field(db):
    """Test listing with select containing only count field."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")
    Item.insert(db, name="Item 2", color="blue")

    # Act
    items = Item.list(db, select=["count.id"])

    # Assert
    assert len(items) == 1  # Should return single count
    item = items[0]
    assert isinstance(item, dict)
    assert "count.id" in item
    assert item["count.id"] == 2


def test_list_with_select_relationship_fields(db):
    """Test listing with relationship filters using operators."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    item3 = Item.insert(db, name="Item 3", color="green", price=30)

    ItemList.insert(db, name="List 1", items=[item2])
    ItemList.insert(db, name="List 2", items=[item3])

    # Act
    lists_with_expensive_items = ItemList.list(db, select=["items"])

    # Assert
    assert lists_with_expensive_items[0]["items"]["id"] == item2.id
    assert lists_with_expensive_items[1]["items"]["id"] == item3.id


def test_list_with_select_one_to_one_relationship(db):
    """Test listing with one-to-one relationship selection."""
    # Arrange
    item_type = ItemType.insert(db, name="type_a")
    Item.insert(db, name="Test Item with Type", item_type=item_type)
    Item.insert(db, name="Test Item without Type")

    # Act
    result = Item.list(db, select=["id", "name", "item_type"])

    # Assert
    assert len(result) == 2

    # Find the items by name
    item_with_type_data = next(
        item for item in result if item["name"] == "Test Item with Type"
    )
    item_without_type_data = next(
        item for item in result if item["name"] == "Test Item without Type"
    )

    # Item with relationship should have nested data
    assert "item_type" in item_with_type_data
    assert isinstance(item_with_type_data["item_type"], dict)
    assert item_with_type_data["item_type"]["id"] == item_type.id
    assert item_with_type_data["item_type"]["name"] == "type_a"

    # Item without relationship should have None
    assert "item_type" in item_without_type_data
    assert item_without_type_data["item_type"] is None

    # Should NOT have prefixed fields
    for item_data in result:
        assert "item_type_id" not in item_data
        assert "item_type_name" not in item_data
        assert "item_type_created_at" not in item_data


def test_list_with_select_one_to_many_relationship_with_nulls(db):
    """Test listing with one-to-many relationship selection including null relationships."""
    # Arrange
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    item3 = Item.insert(db, name="Item 3", color="green", price=30)

    ItemList.insert(db, name="List 1", items=[item1, item2])
    ItemList.insert(db, name="List 2", items=[item3])
    ItemList.insert(db, name="Empty List", items=[])  # Empty list

    # Act
    lists = ItemList.list(db, select=["id", "name", "items"])

    # Assert - one-to-many relationships return multiple rows (one per related item)
    assert (
        len(lists) == 4
    )  # List 1 appears twice (2 items), List 2 once, Empty List once

    # Find lists by name
    list1_records = [item for item in lists if item["name"] == "List 1"]
    list2_data = next(item for item in lists if item["name"] == "List 2")
    empty_list_data = next(item for item in lists if item["name"] == "Empty List")

    # List 1 should have 2 records (one for each item)
    assert len(list1_records) == 2
    for list1_data in list1_records:
        assert "items" in list1_data
        assert isinstance(list1_data["items"], dict)
        assert list1_data["items"]["id"] in [item1.id, item2.id]

    # List 2 should have nested data
    assert "items" in list2_data
    assert isinstance(list2_data["items"], dict)
    assert list2_data["items"]["id"] == item3.id

    # Empty list should have None
    assert "items" in empty_list_data
    assert empty_list_data["items"] is None


def test_list_with_super_deep_nested_assoc(db):
    """Test listing with super deep nested associations."""
    # Arrange
    item_type = ItemType.insert(db, name="type_a")
    item = Item.insert(db, color="red", item_type=item_type)
    ItemList.insert(db, name="list_1", items=[item])
    Tag.insert(db, name="tag_1", items=[item])

    # Act
    result = Tag.list(db, select=["id", "items.color", "items.id"])

    # Assert - Tag has many-to-many relationship with Item
    assert len(result) == 1
    assert "items" in result[0]
    assert isinstance(
        result[0]["items"], dict
    )  # Returns single item dict for this case
    assert result[0]["items"]["color"] == "red"
    assert result[0]["items"]["id"] == item.id


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
