"""
Test insert operations for memory adapter.
"""

from tests.crudle.adapters.memory.models import Item, ItemList, Tag


def test_insert_should_create_record(db):
    """Test basic record creation."""
    # Act
    item = db.insert(Item, color="red")

    # Assert
    assert item.id is not None
    assert item.color == "red"


def test_insert_should_create_record_with_existing_relationship(db):
    """Test creating record with existing relationship."""
    # Arrange
    item_list = db.insert(ItemList, name="list_1")

    # Act
    item = db.insert(Item, color="red", item_list=item_list)

    # Assert
    assert item.id is not None
    assert item.color == "red"
    assert item.item_list.id == item_list.id
    assert item.item_list.name == "list_1"


def test_insert_should_create_record_with_new_relationship(db):
    """Test creating record with new nested relationship."""
    # Act
    item = db.insert(Item, color="red", item_list={"name": "list_1"})

    # Assert
    assert item.id is not None
    assert item.color == "red"
    assert item.item_list.name == "list_1"
    assert item.item_list.id is not None


def test_insert_should_create_record_with_list_of_nested_new_relationships(db):
    """Test creating record with list of nested relationships."""

    # Act
    item_list = db.insert(
        ItemList,
        items=[
            {"color": "red", "tags": [{"name": "tag_1"}]},
            {"color": "blue", "tags": [{"name": "tag_2"}]},
        ],
        name="list_1",
    )

    # Assert
    assert item_list.id is not None
    assert len(item_list.items) == 2
    assert item_list.items[0].color == "red"
    assert item_list.items[0].tags[0].name == "tag_1"
    assert item_list.items[1].color == "blue"
    assert item_list.items[1].tags[0].name == "tag_2"


def test_insert_should_create_record_with_list_of_nested_existing_relationships(db):
    """Test creating record with list of existing relationships."""
    # Arrange
    tag_1 = db.insert(Tag, name="tag_1")
    tag_2 = db.insert(Tag, name="tag_2")

    # Act
    item_list = db.insert(
        ItemList,
        items=[
            {"color": "red", "tags": [tag_1]},
            {"color": "blue", "tags": [tag_2]},
        ],
        name="list_1",
    )

    # Assert
    assert item_list.id is not None
    assert item_list.items[0].color == "red"
    assert item_list.items[0].tags[0].id == tag_1.id
    assert item_list.items[1].color == "blue"
    assert item_list.items[1].tags[0].id == tag_2.id


def test_insert_should_create_record_with_list_of_nested_mixed_relationships(db):
    """Test creating record with mixed existing and new relationships."""
    # Arrange
    tag_1 = db.insert(Tag, name="tag_1")
    tag_2 = db.insert(Tag, name="tag_2")

    # Act
    item_list = db.insert(
        ItemList,
        items=[
            {"color": "red", "tags": [tag_1]},
            {"color": "blue", "tags": [{"id": tag_2.id}, {"name": "tag_3"}]},
        ],
        name="list_1",
    )

    # Assert
    assert item_list.id is not None
    assert item_list.items[0].color == "red"
    assert item_list.items[0].tags[0].id == tag_1.id
    assert item_list.items[1].color == "blue"
    assert item_list.items[1].tags[0].id == tag_2.id
    assert item_list.items[1].tags[0].name == tag_2.name
    assert item_list.items[1].tags[1].name == "tag_3"
    assert len(db.list(Tag)) == 3


def test_insert_should_create_record_with_nested_relationship_and_not_update_existing_relationship(
    db,
):
    """Test that nested relationships don't update existing ones."""
    # Arrange
    tag = db.insert(Tag, name="tag_1")

    # Act
    item_list = db.insert(
        ItemList,
        items=[{"color": "red", "tags": [{"id": tag.id, "name": "tag_2"}]}],
        name="list_1",
    )

    # Assert
    assert item_list.id is not None
    assert item_list.items[0].color == "red"
    # The existing tag should not be updated
    assert item_list.items[0].tags[0].name == "tag_1"  # Original name, not "tag_2"
    assert len(db.list(Tag)) == 1


def test_insert_should_validate_required_fields(db):
    """Test that Pydantic validation works for required fields."""
    # Test missing required field
    try:
        db.insert(Tag)  # Missing required 'name' field
        assert False, "Should have raised validation error"
    except ValueError as e:
        assert "Field required" in str(e)

    # Test valid data
    tag = db.insert(Tag, name="valid_tag")
    assert tag.name == "valid_tag"


def test_insert_should_validate_field_types(db):
    """Test that Pydantic validation works for field types."""
    # Test invalid type
    try:
        db.insert(Item, price="not_a_number")
        assert False, "Should have raised validation error"
    except ValueError as e:
        assert "validation error" in str(e)

    # Test valid data
    item = db.insert(Item, price=100)
    assert item.price == 100


def test_insert_should_handle_optional_fields(db):
    """Test that optional fields work correctly."""
    # Test with None values
    item = db.insert(Item, name="Test Item", color=None, price=None)
    assert item.name == "Test Item"
    assert item.color is None
    assert item.price is None

    # Test with values
    item = db.insert(Item, name="Test Item", color="red", price=100)
    assert item.color == "red"
    assert item.price == 100
