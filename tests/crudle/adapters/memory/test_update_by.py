"""
Test update_by operations for memory adapter.
"""

import pytest

from src.crudle.adapters.memory.adapter import NotLoaded
from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


def test_update_by_should_update_record(db):
    """Test updating record by filters."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=100)

    # Act
    updated_item = db.update_by(Item, {"name": "Test Item"}, color="blue", price=200)

    # Assert
    assert updated_item is not None
    assert updated_item.color == "blue"
    assert updated_item.price == 200
    assert updated_item.name == "Test Item"  # Filter field unchanged


def test_update_by_should_return_none_if_no_match(db):
    """Test updating non-existent record returns None."""
    # Arrange
    db.insert(Item, name="Test Item", color="red")

    # Act
    result = db.update_by(Item, {"name": "Non-existent Item"}, color="blue")

    # Assert
    assert result is None


def test_update_by_should_raise_on_multiple_matches(db):
    """Test that update_by raises when multiple records match."""
    from sqlalchemy.exc import MultipleResultsFound

    db.insert(Item, name="Test Item", color="red", price=100)
    db.insert(Item, name="Test Item", color="blue", price=200)

    with pytest.raises(MultipleResultsFound):
        db.update_by(Item, {"name": "Test Item"}, price=300)


def test_update_by_should_handle_multiple_filters(db):
    """Test updating with multiple filter criteria."""
    # Arrange
    item1 = db.insert(Item, name="Test Item", color="red", price=100)
    item2 = db.insert(Item, name="Test Item", color="blue", price=100)
    item3 = db.insert(Item, name="Other Item", color="red", price=100)

    # Act
    updated_item = db.update_by(Item, {"name": "Test Item", "color": "red"}, price=200)

    # Assert
    assert updated_item is not None
    assert updated_item.price == 200
    assert updated_item.name == "Test Item"
    assert updated_item.color == "red"


def test_update_by_should_handle_operator_filters(db):
    """Test updating with operator filters that uniquely match."""
    item1 = db.insert(Item, name="Item 1", price=100)
    item2 = db.insert(Item, name="Item 2", price=200)
    item3 = db.insert(Item, name="Item 3", price=300)

    updated_item = db.update_by(Item, {"price__gt": 250}, name="Expensive Item")

    assert updated_item is not None
    assert updated_item.id == item3.id
    assert updated_item.name == "Expensive Item"
    assert db.get(Item, item1.id).name == "Item 1"
    assert db.get(Item, item2.id).name == "Item 2"
    assert updated_item.name == "Expensive Item"
    assert updated_item.price > 150


def test_update_by_should_handle_complex_filters(db):
    """Test updating with complex filter combinations."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red", price=100)
    item2 = db.insert(Item, name="Item 2", color="blue", price=200)
    item3 = db.insert(Item, name="Item 3", color="red", price=300)
    item4 = db.insert(Item, name="Item 4", color="green", price=150)

    # Act
    updated_item = db.update_by(
        Item,
        {"color__in": ["red", "blue"], "price__ge": 150, "price__lt": 250},
        name="Selected Item",
    )

    # Assert
    assert updated_item is not None
    assert updated_item.name == "Selected Item"
    assert updated_item.color in ["red", "blue"]
    assert 150 <= updated_item.price < 250


def test_update_by_should_handle_relationship_filters(db):
    """Test updating with relationship filters."""
    # Arrange
    item_type1 = db.insert(ItemType, name="Electronics")
    item_type2 = db.insert(ItemType, name="Clothing")

    item1 = db.insert(Item, name="Item 1", item_type=item_type1)
    item2 = db.insert(Item, name="Item 2", item_type=item_type2)

    # Act
    updated_item = db.update_by(Item, {"item_type.name": "Electronics"}, price=100)

    # Assert
    assert updated_item is not None
    assert updated_item.price == 100
    # Relationships are NotLoaded by default, need to preload to access them
    assert isinstance(updated_item.item_type, NotLoaded)
    # Verify the relationship by preloading it
    loaded_item = db.get(Item, updated_item.id, preload=["item_type"])
    assert loaded_item.item_type.name == "Electronics"


def test_update_by_should_handle_nested_relationship_updates(db):
    """Test updating with nested relationship data."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red")

    # Act
    updated_item = db.update_by(
        Item,
        {"name": "Test Item"},
        item_type={"name": "Electronics"},
        tags=[{"name": "expensive"}, {"name": "popular"}],
    )

    # Assert
    assert updated_item is not None
    assert updated_item.item_type.name == "Electronics"
    assert len(updated_item.tags) == 2
    assert updated_item.tags[0].name == "expensive"
    assert updated_item.tags[1].name == "popular"


def test_update_by_should_handle_list_relationship_updates(db):
    """Test updating list relationships."""
    # Arrange
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")
    item_list = db.insert(ItemList, name="Test List", items=[item1])

    # Act
    updated_list = db.update_by(ItemList, {"name": "Test List"}, items=[item1, item2])

    # Assert
    assert updated_list is not None
    assert len(updated_list.items) == 2
    assert updated_list.items[0].id == item1.id
    assert updated_list.items[1].id == item2.id


def test_update_by_should_handle_mixed_relationship_updates(db):
    """Test updating with mixed existing and new relationships."""
    # Arrange
    item_list = db.insert(ItemList, name="Test List")
    existing_item = db.insert(Item, name="Existing Item", color="red")

    # Act
    updated_list = db.update_by(
        ItemList,
        {"name": "Test List"},
        items=[existing_item, {"name": "New Item", "color": "blue"}],
    )

    # Assert
    assert updated_list is not None
    assert len(updated_list.items) == 2
    assert updated_list.items[0].id == existing_item.id
    assert updated_list.items[1].name == "New Item"
    assert updated_list.items[1].color == "blue"


def test_update_by_should_handle_validation_errors(db):
    """Test that validation errors are handled gracefully."""
    # Arrange
    item = db.insert(Item, name="Test Item", price=100)

    # Test invalid type
    try:
        db.update_by(Item, {"name": "Test Item"}, price="not_a_number")
        assert False, "Should have raised validation error"
    except ValueError as e:
        assert "validation error" in str(e)

    # Test valid update
    updated_item = db.update_by(Item, {"name": "Test Item"}, price=200)
    assert updated_item.price == 200


def test_update_by_should_handle_empty_filters(db):
    """Test updating with empty filters."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red")

    # Act
    updated_item = db.update_by(Item, {}, color="blue")

    # Assert
    assert updated_item is not None
    assert updated_item.color == "blue"


def test_update_by_should_handle_none_values(db):
    """Test updating with None values."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red", price=100)

    # Act
    updated_item = db.update_by(Item, {"name": "Test Item"}, color=None, price=None)

    # Assert
    assert updated_item is not None
    assert updated_item.color is None
    assert updated_item.price is None
    assert updated_item.name == "Test Item"  # Unchanged


def test_update_by_should_handle_text_search_filters(db):
    """Test updating with text search filters."""
    # Arrange
    item1 = db.insert(Item, name="Apple iPhone", color="red")
    item2 = db.insert(Item, name="Samsung Galaxy", color="blue")

    # Act
    updated_item = db.update_by(Item, {"name__q": "Apple"}, price=1000)

    # Assert
    assert updated_item is not None
    assert updated_item.price == 1000
    assert "Apple" in updated_item.name


def test_update_by_should_handle_case_insensitive_filters(db):
    """Test that filters are case insensitive where appropriate."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red")

    # Act
    updated_item = db.update_by(Item, {"name__q": "test"}, price=200)

    # Assert
    assert updated_item is not None
    assert updated_item.price == 200


def test_update_by_should_handle_partial_matches(db):
    """Test updating with partial text matches that uniquely identify a row."""
    item1 = db.insert(Item, name="Apple iPhone 13", color="red")
    item2 = db.insert(Item, name="Samsung Galaxy", color="green")

    updated_item = db.update_by(Item, {"name__q": "Apple"}, price=1000)

    assert updated_item is not None
    assert updated_item.id == item1.id
    assert updated_item.price == 1000
    assert db.get(Item, item2.id).price is None


def test_update_by_should_handle_invalid_operators(db):
    """Test that invalid operators raise like SQLAlchemy."""
    db.insert(Item, name="Test Item", color="red")

    with pytest.raises(Exception, match="Forbidden operator"):
        db.update_by(Item, {"color__invalid_op": "red"}, price=200)


def test_update_by_should_handle_type_mismatches(db):
    """Test that type mismatches in filters are handled gracefully."""
    # Arrange
    item = db.insert(Item, name="Test Item", price=100)

    # Act
    updated_item = db.update_by(Item, {"price__gt": "not_a_number"}, name="Updated")

    # Assert
    assert updated_item is None  # No match due to type mismatch


def test_update_by_should_raise_on_multiple_matches_same_name(db):
    """Test that when multiple records match, update_by raises."""
    from sqlalchemy.exc import MultipleResultsFound

    db.insert(Item, name="Test Item", color="red", price=100)
    db.insert(Item, name="Test Item", color="red", price=200)
    db.insert(Item, name="Test Item", color="red", price=300)

    with pytest.raises(MultipleResultsFound):
        db.update_by(Item, {"name": "Test Item", "color": "red"}, price=999)


def test_update_by_should_handle_should_raise(db):
    """Test should_raise when no record matches."""
    with pytest.raises(ValueError, match="No Item found"):
        db.update_by(Item, {"name": "missing"}, should_raise=True, price=1)


def test_update_by_should_handle_relationship_replacement(db):
    """Test replacing relationships through update_by."""
    # Arrange
    item = db.insert(Item, name="Test Item")
    old_type = db.insert(ItemType, name="Old Type")
    new_type = db.insert(ItemType, name="New Type")

    # Set initial relationship
    item = db.update(Item, item.id, item_type=old_type)
    assert item.item_type.name == "Old Type"

    # Act - replace relationship
    updated_item = db.update_by(Item, {"name": "Test Item"}, item_type=new_type)

    # Assert
    assert updated_item is not None
    assert updated_item.item_type.name == "New Type"
    assert updated_item.item_type.id == new_type.id


def test_update_by_should_handle_relationship_removal(db):
    """Test removing relationships by setting to None."""
    # Arrange
    item_type = db.insert(ItemType, name="Test Type")
    item = db.insert(Item, name="Test Item", item_type=item_type)
    assert item.item_type is not None

    # Act
    updated_item = db.update_by(Item, {"name": "Test Item"}, item_type=None)

    # Assert
    assert updated_item is not None
    assert updated_item.item_type is None


def test_update_by_should_handle_complex_nested_updates(db):
    """Test complex nested relationship updates."""
    # Arrange
    item = db.insert(Item, name="Test Item", color="red")

    # Act
    updated_item = db.update_by(
        Item,
        {"name": "Test Item"},
        item_type={"name": "Electronics"},
        tags=[{"name": "expensive"}, {"name": "popular"}],
    )

    # Assert
    assert updated_item is not None
    assert updated_item.item_type.name == "Electronics"
    assert len(updated_item.tags) == 2
    assert updated_item.tags[0].name == "expensive"
    assert updated_item.tags[1].name == "popular"


def test_update_by_should_maintain_referential_integrity(db):
    """Test that relationships maintain referential integrity."""
    # Arrange
    item_type = db.insert(ItemType, name="Test Type")
    item = db.insert(Item, name="Test Item", item_type=item_type)

    # Act
    updated_item = db.update_by(Item, {"name": "Test Item"}, name="Updated Item")

    # Assert
    assert updated_item is not None
    assert updated_item.name == "Updated Item"
    # Relationships are NotLoaded by default, need to preload to access them
    assert isinstance(updated_item.item_type, NotLoaded)
    # Verify the relationship by preloading it
    loaded_item = db.get(Item, updated_item.id, preload=["item_type"])
    assert loaded_item.item_type.id == item_type.id
    assert loaded_item.item_type.name == "Test Type"
