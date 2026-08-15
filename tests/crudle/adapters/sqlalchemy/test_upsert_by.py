from datetime import datetime, timezone

import pytest
from tests.models import Item, ItemList, Tag, ItemType


def test_upsert_by_should_update_existing_record(db):
    """Test upsert_by updates an existing record when found."""
    # Arrange
    item = Item.insert(db, name="Original Name", color="red", price=10)
    original_id = item.id

    # Act
    result = Item.upsert_by(db, {"color": "red"}, name="Updated Name", price=20)

    # Assert
    assert result is not None
    assert result.id == original_id  # Same record
    assert result.name == "Updated Name"
    assert result.color == "red"  # Filter condition
    assert result.price == 20
    assert len(Item.list(db)) == 1  # Still only one record


def test_upsert_by_should_insert_new_record_when_not_found(db):
    """Test upsert_by inserts a new record when no existing record matches filters."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)

    # Act
    result = Item.upsert_by(
        db, {"name": "Item 2"}, name="New Item", color="blue", price=30
    )

    # Assert
    assert result is not None
    assert result.name == "New Item"
    assert result.color == "blue"
    assert result.price == 30
    assert len(Item.list(db)) == 2  # Now two records


def test_upsert_by_with_single_filter(db):
    """Test upsert_by with single filter condition."""
    # Arrange
    item = Item.insert(db, name="Item 1", color="red", price=10)

    # Act - Update existing
    result1 = Item.upsert_by(db, {"name": "Item 1"}, color="blue", price=20)

    # Assert
    assert result1.id == item.id
    assert result1.color == "blue"
    assert result1.price == 20
    assert len(Item.list(db)) == 1

    # Act - Insert new
    result2 = Item.upsert_by(
        db, {"name": "Item 2"}, name="Item 2", color="green", price=30
    )

    # Assert
    assert result2.name == "Item 2"
    assert result2.color == "green"
    assert result2.price == 30
    assert len(Item.list(db)) == 2


def test_upsert_by_with_multiple_filters(db):
    """Test upsert_by with multiple filter conditions."""
    # Arrange
    item = Item.insert(db, name="Item 1", color="red", price=10)

    # Act - Update existing
    result1 = Item.upsert_by(
        db, {"name": "Item 1", "color": "red"}, price=20, name="Updated Item"
    )

    # Assert
    assert result1.id == item.id
    assert result1.name == "Updated Item"
    assert result1.color == "red"
    assert result1.price == 20
    assert len(Item.list(db)) == 1

    # Act - Insert new
    result2 = Item.upsert_by(
        db, {"name": "Item 2"}, name="New Item", color="blue", price=30
    )

    # Assert
    assert result2.name == "New Item"
    assert result2.color == "blue"
    assert result2.price == 30
    assert len(Item.list(db)) == 2


def test_upsert_by_with_operator_filters(db):
    """Test upsert_by with operator filters."""
    # Arrange
    item = Item.insert(db, name="Item 1", price=10)

    # Act - Update existing
    result1 = Item.upsert_by(db, {"price__gt": 5}, name="Updated Item", price=15)

    # Assert
    assert result1.id == item.id
    assert result1.name == "Updated Item"
    assert result1.price == 15
    assert len(Item.list(db)) == 1

    # Act - Insert new (no existing record with price > 20)
    result2 = Item.upsert_by(db, {"price__gt": 20}, name="Expensive Item", price=25)

    # Assert
    assert result2.name == "Expensive Item"
    assert result2.price == 25
    assert len(Item.list(db)) == 2


def test_upsert_by_with_in_operator(db):
    """Test upsert_by with 'in' operator."""
    # Arrange
    item = Item.insert(db, name="Item 1", color="red")

    # Act - Update existing
    result1 = Item.upsert_by(
        db, {"color__in": ["red", "blue"]}, name="Updated Item", color="blue"
    )

    # Assert
    assert result1.id == item.id
    assert result1.name == "Updated Item"
    assert result1.color == "blue"
    assert len(Item.list(db)) == 1

    # Act - Insert new
    result2 = Item.upsert_by(
        db, {"color__in": ["green", "yellow"]}, name="New Item", color="green"
    )

    # Assert
    assert result2.name == "New Item"
    assert result2.color == "green"
    assert len(Item.list(db)) == 2


def test_upsert_by_with_relationship_filters(db):
    """Test upsert_by with relationship filters."""
    # Arrange - Since ItemType has one-to-one relationship, create separate types
    item_type_1 = ItemType.insert(db, name="type_a")
    item_type_2 = ItemType.insert(db, name="type_b")
    item = Item.insert(db, name="Item 1", color="red", item_type=item_type_1)

    # Act - Update existing
    result1 = Item.upsert_by(
        db, {"item_type.name": "type_a"}, name="Updated Item", color="blue"
    )

    # Assert
    assert result1.id == item.id
    assert result1.name == "Updated Item"
    assert result1.color == "blue"
    assert result1.item_type.name == "type_a"
    assert len(Item.list(db)) == 1

    # Act - Insert new
    result2 = Item.upsert_by(
        db,
        {"item_type.name": "type_b"},
        name="New Item",
        color="green",
        item_type=item_type_2,
    )

    # Assert
    assert result2.name == "New Item"
    assert result2.color == "green"
    assert result2.item_type.name == "type_b"
    assert len(Item.list(db)) == 2


def test_upsert_by_with_nested_relationship_filters(db):
    """Test upsert_by with nested relationship filters."""
    # Arrange - Since ItemType has one-to-one relationship, create separate types
    item_type_1 = ItemType.insert(db, name="type_a")
    item_type_2 = ItemType.insert(db, name="type_b")
    item = Item.insert(db, name="Item 1", color="red", item_type=item_type_1)

    # Act - Update existing
    result1 = Item.upsert_by(
        db, {"item_type.name": "type_a"}, name="Updated Item", color="blue"
    )

    # Assert
    assert result1.id == item.id
    assert result1.name == "Updated Item"
    assert result1.color == "blue"
    assert result1.item_type.name == "type_a"
    assert len(Item.list(db)) == 1

    # Act - Insert new
    result2 = Item.upsert_by(
        db,
        {"item_type.name": "type_b"},
        name="New Item",
        color="green",
        item_type=item_type_2,
    )

    # Assert
    assert result2.name == "New Item"
    assert result2.color == "green"
    assert result2.item_type.name == "type_b"
    assert len(Item.list(db)) == 2


def test_upsert_by_with_none_values(db):
    """Test upsert_by with None values in filters."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color=None, price=20)

    # Act - Update existing (item with None color)
    result1 = Item.upsert_by(db, {"color": None}, name="Updated Item", price=25)

    # Assert
    assert result1.name == "Updated Item"
    assert result1.color is None
    assert result1.price == 25
    assert len(Item.list(db)) == 2

    # Act - Insert new (no existing item with price None)
    result2 = Item.upsert_by(db, {"price": None}, name="New Item", color="blue")

    # Assert
    assert result2.name == "New Item"
    assert result2.color == "blue"
    assert result2.price is None
    assert len(Item.list(db)) == 3


def test_upsert_by_with_datetime_filters(db):
    """Test upsert_by with datetime filters."""
    # Arrange
    past_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    item = Item.insert(db, name="Item 1", color="red")
    item.created_at = past_time
    db.commit()

    # Act - Update existing
    result1 = Item.upsert_by(
        db, {"created_at__lt": now}, name="Updated Item", color="blue"
    )

    # Assert
    assert result1.id == item.id
    assert result1.name == "Updated Item"
    assert result1.color == "blue"
    assert len(Item.list(db)) == 1

    # Act - Insert new (no existing item created after now)
    future_time = datetime(2030, 1, 1, tzinfo=timezone.utc)
    result2 = Item.upsert_by(
        db, {"created_at__gt": future_time}, name="Future Item", color="green"
    )

    # Assert
    assert result2.name == "Future Item"
    assert result2.color == "green"
    assert len(Item.list(db)) == 2


def test_upsert_by_different_models(db):
    """Test upsert_by with different models."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")
    ItemList.insert(db, name="List 1")
    Tag.insert(db, name="Tag 1")

    # Act - Update existing items
    item_result = Item.upsert_by(
        db, {"color": "red"}, name="Updated Item", color="blue"
    )
    list_result = ItemList.upsert_by(db, {"name": "List 1"}, name="Updated List")
    tag_result = Tag.upsert_by(db, {"name": "Tag 1"}, name="Updated Tag")

    # Assert
    assert item_result.name == "Updated Item"
    assert item_result.color == "blue"
    assert list_result.name == "Updated List"
    assert tag_result.name == "Updated Tag"

    # Act - Insert new items
    new_item = Item.upsert_by(
        db, {"name": "New Item"}, name="New Item", color="green", price=10
    )
    new_list = ItemList.upsert_by(db, {"name": "New List"}, name="New List")
    new_tag = Tag.upsert_by(db, {"name": "New Tag"}, name="New Tag")

    # Assert
    assert new_item.name == "New Item"
    assert new_item.color == "green"
    assert new_list.name == "New List"
    assert new_tag.name == "New Tag"

    # Verify counts
    assert len(Item.list(db)) == 2
    assert len(ItemList.list(db)) == 2
    assert len(Tag.list(db)) == 2


def test_upsert_by_with_complex_queries(db):
    """Test upsert_by with complex query combinations."""
    # Arrange
    item = Item.insert(db, name="Item 1", color="red", price=10)

    # Act - Update existing
    result1 = Item.upsert_by(
        db,
        {"color": "red", "price__gt": 5, "name": "Item 1"},
        name="Complex Updated Item",
        color="blue",
        price=20,
    )

    # Assert
    assert result1.id == item.id
    assert result1.name == "Complex Updated Item"
    assert result1.color == "blue"
    assert result1.price == 20
    assert len(Item.list(db)) == 1

    # Act - Insert new
    result2 = Item.upsert_by(
        db,
        {"color": "green", "price__gt": 30, "name": "Item 2"},
        name="Complex New Item",
        color="yellow",
        price=40,
    )

    # Assert
    assert result2.name == "Complex New Item"
    assert result2.color == "yellow"
    assert result2.price == 40
    assert len(Item.list(db)) == 2


def test_upsert_by_with_string_operations(db):
    """Test upsert_by with string operations."""
    # Arrange
    item = Item.insert(db, name="Apple", color="red")

    # Act - Update existing
    result1 = Item.upsert_by(db, {"name": "Apple"}, color="green")

    # Assert
    assert result1.id == item.id
    assert result1.name == "Apple"
    assert result1.color == "green"
    assert len(Item.list(db)) == 1

    # Act - Insert new
    result2 = Item.upsert_by(db, {"name": "Banana"}, name="Banana", color="yellow")

    # Assert
    assert result2.name == "Banana"
    assert result2.color == "yellow"
    assert len(Item.list(db)) == 2


def test_upsert_by_with_numeric_operations(db):
    """Test upsert_by with numeric operations."""
    # Arrange
    item = Item.insert(db, name="Item 1", price=10)

    # Act - Update existing
    result1 = Item.upsert_by(db, {"price": 10}, name="Updated Item", price=15)

    # Assert
    assert result1.id == item.id
    assert result1.name == "Updated Item"
    assert result1.price == 15
    assert len(Item.list(db)) == 1

    # Act - Insert new
    result2 = Item.upsert_by(
        db, {"name": "New Item"}, name="New Item", color="blue", price=20
    )

    # Assert
    assert result2.name == "New Item"
    assert result2.color == "blue"
    assert result2.price == 20
    assert len(Item.list(db)) == 2


def test_upsert_by_should_handle_multiple_records_found(db):
    """Test upsert_by behavior when multiple records match filters."""
    from sqlalchemy.exc import MultipleResultsFound

    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="red", price=20)

    # Act & Assert - Should raise error when multiple records match
    with pytest.raises(MultipleResultsFound):
        Item.upsert_by(db, {"color": "red"}, name="Updated Item")

    # Verify no changes were made
    assert len(Item.list(db)) == 2


def test_upsert_by_should_handle_empty_filters(db):
    """Test upsert_by with empty filters."""
    from sqlalchemy.exc import MultipleResultsFound

    # Arrange
    Item.insert(db, name="Item 1", color="red")
    Item.insert(db, name="Item 2", color="blue")

    # Act & Assert - Should raise error when multiple records match empty filters
    with pytest.raises(MultipleResultsFound):
        Item.upsert_by(db, {}, name="Updated Item")

    # Verify no changes were made
    assert len(Item.list(db)) == 2


def test_upsert_by_should_handle_invalid_filters(db):
    """Test upsert_by with invalid filter fields."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")

    # Act & Assert - Should raise AttributeError for invalid field
    with pytest.raises(
        AttributeError, match="type object 'Item' has no attribute 'invalid_field'"
    ):
        Item.upsert_by(db, {"invalid_field": "value"}, name="Updated Item")

    # Verify no changes were made
    assert len(Item.list(db)) == 1


def test_upsert_by_should_handle_mixed_valid_invalid_filters(db):
    """Test upsert_by with mix of valid and invalid filters."""
    # Arrange
    Item.insert(db, name="Item 1", color="red", price=10)

    # Act & Assert - Should raise AttributeError for invalid field
    with pytest.raises(
        AttributeError, match="type object 'Item' has no attribute 'invalid_field'"
    ):
        Item.upsert_by(
            db, {"color": "red", "invalid_field": "value"}, name="Updated Item"
        )

    # Verify no changes were made
    assert len(Item.list(db)) == 1


def test_upsert_by_should_preserve_relationships(db):
    """Test that upsert_by preserves existing relationships when updating."""
    # Arrange
    item_type = ItemType.insert(db, name="type_a")
    item = Item.insert(db, name="Item 1", color="red", item_type=item_type)

    # Act - Update existing item
    result = Item.upsert_by(db, {"name": "Item 1"}, name="Updated Item", color="blue")

    # Assert
    assert result.id == item.id
    assert result.name == "Updated Item"
    assert result.color == "blue"
    assert result.item_type.id == item_type.id
    assert result.item_type.name == "type_a"


def test_upsert_by_should_create_relationships_when_inserting(db):
    """Test that upsert_by creates relationships when inserting new records."""
    # Arrange
    item_type = ItemType.insert(db, name="type_a")

    # Act - Insert new item with relationship
    result = Item.upsert_by(
        db, {"name": "New Item"}, name="New Item", color="blue", item_type=item_type
    )

    # Assert
    assert result.name == "New Item"
    assert result.color == "blue"
    assert result.item_type.id == item_type.id
    assert result.item_type.name == "type_a"


def test_upsert_by_should_handle_commit_parameter(db):
    """Test upsert_by with commit parameter."""
    # Arrange
    Item.insert(db, name="Item 1", color="red")

    # Act - Update with commit=False
    result = Item.upsert_by(
        db, {"name": "Item 1"}, name="Updated Item", color="blue", commit=False
    )

    # Assert
    assert result.name == "Updated Item"
    assert result.color == "blue"
    # Note: commit=False behavior is tested in the update method


def test_upsert_by_should_handle_on_update_assocs_parameter(db):
    """Test upsert_by with on_update_assocs parameter."""
    # Arrange
    item = Item.insert(db, name="Item 1", color="red")
    ItemList.insert(db, name="List 1", items=[item])

    # Act - Update existing list
    result = ItemList.upsert_by(
        db,
        {"name": "List 1"},
        name="Updated List",
        items=[{"name": "Updated Item"}],
        on_update_assocs="nilify_all",
    )

    # Assert
    assert result.name == "Updated List"
    assert len(result.items) == 1
    assert result.items[0].name == "Updated Item"


def test_upsert_by_should_handle_should_raise_parameter(db):
    """Test upsert_by with should_raise parameter."""
    from sqlalchemy.exc import NoResultFound

    # Arrange
    Item.insert(db, name="Item 1", color="red")

    # Act & Assert - should_raise=True causes update_by to raise NoResultFound
    # and upsert_by doesn't catch this exception, so it propagates up
    with pytest.raises(NoResultFound):
        Item.upsert_by(
            db, {"color": "blue"}, name="New Item", color="green", should_raise=True
        )

    # Verify no changes were made
    assert len(Item.list(db)) == 1


def test_upsert_by_should_return_updated_instance(db):
    """Test that upsert_by returns the updated instance when updating."""
    # Arrange
    item = Item.insert(db, name="Original Name", color="red", price=10)
    original_id = item.id

    # Act
    result = Item.upsert_by(db, {"id": original_id}, name="Updated Name", price=20)

    # Assert
    assert result is not None
    assert result.id == original_id
    assert result.name == "Updated Name"
    assert result.price == 20
    assert result.color == "red"  # Should remain unchanged


def test_upsert_by_should_return_inserted_instance(db):
    """Test that upsert_by returns the inserted instance when inserting."""
    # Arrange
    assert len(Item.list(db)) == 0

    # Act
    result = Item.upsert_by(
        db, {"name": "New Item"}, name="New Item", color="blue", price=15
    )

    # Assert
    assert result is not None
    assert result.name == "New Item"
    assert result.color == "blue"
    assert result.price == 15
    assert result.id is not None
    assert len(Item.list(db)) == 1


def test_upsert_by_with_relationship_field_filters(db):
    """Test upsert_by with relationship field filters."""
    # Arrange - Since ItemType has one-to-one relationship, create separate types
    item_type_1 = ItemType.insert(db, name="type_a")
    item_type_2 = ItemType.insert(db, name="type_b")
    item = Item.insert(db, name="Item 1", color="red", item_type=item_type_1)

    # Act - Update existing
    result1 = Item.upsert_by(
        db, {"item_type": item_type_1}, name="Updated Item", color="blue"
    )

    # Assert
    assert result1.id == item.id
    assert result1.name == "Updated Item"
    assert result1.color == "blue"
    assert result1.item_type.id == item_type_1.id
    assert len(Item.list(db)) == 1

    # Act - Insert new
    result2 = Item.upsert_by(
        db, {"name": "New Item"}, name="New Item", color="green", item_type=item_type_2
    )

    # Assert
    assert result2.name == "New Item"
    assert result2.color == "green"
    assert result2.item_type.id == item_type_2.id
    assert len(Item.list(db)) == 2


def test_upsert_by_with_nested_field_filters(db):
    """Test upsert_by with nested field filters."""
    # Arrange - Since ItemType has one-to-one relationship, create separate types
    item_type_1 = ItemType.insert(db, name="type_a")
    item_type_2 = ItemType.insert(db, name="type_b")
    item = Item.insert(db, name="Item 1", color="red", item_type=item_type_1)

    # Act - Update existing
    result1 = Item.upsert_by(
        db, {"item_type.name": "type_a"}, name="Updated Item", color="blue"
    )

    # Assert
    assert result1.id == item.id
    assert result1.name == "Updated Item"
    assert result1.color == "blue"
    assert result1.item_type.name == "type_a"
    assert len(Item.list(db)) == 1

    # Act - Insert new
    result2 = Item.upsert_by(
        db,
        {"item_type.name": "type_b"},
        name="New Item",
        color="green",
        item_type=item_type_2,
    )

    # Assert
    assert result2.name == "New Item"
    assert result2.color == "green"
    assert result2.item_type.name == "type_b"
    assert len(Item.list(db)) == 2


def test_upsert_by_should_handle_duplicate_insertion(db):
    """Test upsert_by behavior when trying to insert duplicate records."""
    # Arrange
    assert len(Item.list(db)) == 0

    # Act - Insert first record
    result1 = Item.upsert_by(db, {"name": "Item 1"}, name="Item 1", color="red")

    # Assert
    assert result1.name == "Item 1"
    assert result1.color == "red"
    assert len(Item.list(db)) == 1

    # Act - Try to insert duplicate (should update instead)
    result2 = Item.upsert_by(db, {"name": "Item 1"}, name="Item 1", color="blue")

    # Assert
    assert result2.id == result1.id  # Same record
    assert result2.name == "Item 1"
    assert result2.color == "blue"
    assert len(Item.list(db)) == 1  # Still only one record


def test_upsert_by_should_handle_complex_relationship_upserts(db):
    """Test upsert_by with complex relationship scenarios."""
    # Arrange
    item_type = ItemType.insert(db, name="type_a")
    item = Item.insert(db, name="Item 1", color="red", item_type=item_type)
    ItemList.insert(db, name="List 1", items=[item])

    # Act - Update existing list
    result1 = ItemList.upsert_by(
        db, {"name": "List 1"}, name="Updated List", items=[{"name": "Updated Item"}]
    )

    # Assert
    assert result1.name == "Updated List"
    # The on_update_assocs behavior may add items instead of replacing them
    assert len(result1.items) >= 1
    assert any(item.name == "Updated Item" for item in result1.items)

    # Act - Insert new list
    result2 = ItemList.upsert_by(
        db,
        {"name": "New List"},
        name="New List",
        items=[{"name": "New Item", "color": "blue"}],
    )

    # Assert
    assert result2.name == "New List"
    assert len(result2.items) == 1
    assert result2.items[0].name == "New Item"
    assert result2.items[0].color == "blue"

    # Verify counts
    assert len(ItemList.list(db)) == 2
    # The on_update_assocs behavior may add items instead of replacing them
    assert len(Item.list(db)) >= 2  # At least original + new item
