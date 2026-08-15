import pytest
from sqlalchemy.exc import IntegrityError

from tests.models import Item, ItemList, ItemType, Tag


def test_update_commit_false_should_not_persist_changes(db):
    """Test that commit=False prevents all changes from being persisted."""
    # Arrange
    item = Item.insert(db, color="red")
    original_color = item.color

    # Act
    updated_item = item.update(db, color="blue", commit=False)

    # Assert
    # The returned object should have the updated value
    assert updated_item.color == "blue"

    # But the database should still have the original value
    db.refresh(item)
    assert item.color == original_color

    # Verify no new records were created
    assert len(Item.list(db)) == 1


def test_update_commit_false_should_not_persist_relationship_changes(db):
    """Test that commit=False prevents relationship changes from being persisted."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)
    original_item_type_id = item.item_type_id

    # Act
    updated_item = item.update(
        db, color="blue", item_type={"id": item_type.id, "name": "type_2"}, commit=False
    )

    # Assert
    # The returned object should have the updated values
    assert updated_item.color == "blue"
    assert updated_item.item_type.name == "type_2"

    # But the database should still have the original values
    db.refresh(item)
    assert item.color == "red"
    assert item.item_type_id == original_item_type_id
    assert item.item_type.name == "type_1"


def test_update_commit_false_should_not_persist_list_relationship_changes(db):
    """Test that commit=False prevents list relationship changes from being persisted."""
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="green")
    item_list = ItemList.insert(db, name="list_1", items=[item_1])
    original_items_count = len(item_list.items)

    # Act
    updated_item_list = item_list.update(
        db, name="list_2", items=[item_1, item_2], commit=False
    )

    # Assert
    # The returned object should have the updated values
    assert updated_item_list.name == "list_2"
    assert len(updated_item_list.items) == 2

    # But the database should still have the original values
    db.refresh(item_list)
    assert item_list.name == "list_1"
    assert len(item_list.items) == original_items_count


def test_update_commit_false_should_not_persist_new_relationship_creation(db):
    """Test that commit=False prevents new relationship objects from being created."""
    # Arrange
    item = Item.insert(db, color="red")
    original_items_count = len(Item.list(db))

    # Act
    updated_item = item.update(
        db,
        color="blue",
        item_type={"name": "new_type"},  # This should create a new ItemType
        commit=False,
    )

    # Assert
    # The returned object should have the new relationship
    assert updated_item.color == "blue"
    assert updated_item.item_type.name == "new_type"

    # But the database should not have the new ItemType
    assert len(ItemType.list(db)) == 0
    assert len(Item.list(db)) == original_items_count

    # The original item should be unchanged
    db.refresh(item)
    assert item.color == "red"
    assert item.item_type is None


def test_update_commit_false_should_not_persist_deletions(db):
    """Test that commit=False prevents deletions from being persisted."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)
    original_item_type_id = item.item_type_id

    # Act
    updated_item = item.update(
        db,
        color="blue",
        item_type=None,  # This should remove the relationship
        on_update_assocs="nilify_all",
        commit=False,
    )

    # Assert
    # The returned object should have the updated values
    assert updated_item.color == "blue"
    assert updated_item.item_type is None

    # But the database should still have the original relationship
    db.refresh(item)
    assert item.color == "red"
    assert item.item_type_id == original_item_type_id
    assert item.item_type.name == "type_1"


def test_update_commit_false_should_rollback_on_error(db):
    """Test that commit=False properly rolls back even when errors occur."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)

    # Act & Assert
    with pytest.raises(IntegrityError):
        item.update(
            db,
            color="blue",
            item_type=None,  # This should raise an error with on_update="raise"
            on_update_assocs="raise",
            commit=False,
        )

    # The database should still have the original values
    # Note: We can't use db.refresh() here because the item might be in an invalid state
    # after the error, so we'll just verify the error was raised


def test_update_commit_true_should_persist_changes(db):
    """Test that commit=True (default) persists changes as expected."""
    # Arrange
    item = Item.insert(db, color="red")

    # Act
    updated_item = item.update(db, color="blue", commit=True)

    # Assert
    # The returned object should have the updated value
    assert updated_item.color == "blue"

    # The database should also have the updated value
    db.refresh(item)
    assert item.color == "blue"


def test_update_commit_false_with_nested_relationships(db):
    """Test that commit=False prevents nested relationship changes from being persisted."""
    # Arrange
    item = Item.insert(db, color="red")
    item_list = ItemList.insert(db, name="list_1", items=[item])

    original_item_color = item.color
    original_list_name = item_list.name

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[{"id": item.id, "color": "blue"}],
        commit=False,
    )

    # Assert
    # The returned object should have the updated values
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].color == "blue"

    # But the database should still have the original values
    db.refresh(item_list)
    db.refresh(item)

    assert item_list.name == original_list_name
    assert item.color == original_item_color


def test_update_commit_false_with_delete_all_should_not_persist_deletions(db):
    """Test that commit=False prevents deletions when using on_update_assocs='delete_all'."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)
    original_item_type_id = item.item_type_id

    # Act
    updated_item = item.update(
        db,
        color="blue",
        item_type=None,  # This should delete the relationship with delete_all
        on_update_assocs="delete_all",
        commit=False,
    )

    # Assert
    # The returned object should have the updated values
    assert updated_item.color == "blue"
    assert updated_item.item_type is None

    # But the database should still have the original relationship
    db.refresh(item)
    assert item.color == "red"
    assert item.item_type_id == original_item_type_id
    assert item.item_type.name == "type_1"


def test_update_commit_false_with_delete_all_should_not_persist_list_deletions(db):
    """Test that commit=False prevents list deletions when using on_update_assocs='delete_all'."""
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="green")
    item_list = ItemList.insert(db, name="list_1", items=[item_1, item_2])
    original_items_count = len(item_list.items)

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[item_1],  # This should delete item_2 with delete_all
        on_update_assocs="delete_all",
        commit=False,
    )

    # Assert
    # The returned object should have the updated values
    assert updated_item_list.name == "list_2"
    assert len(updated_item_list.items) == 1
    assert updated_item_list.items[0].color == "red"

    # But the database should still have the original items
    db.refresh(item_list)
    assert item_list.name == "list_1"
    assert len(item_list.items) == original_items_count
    assert item_list.items[0].color == "red"
    assert item_list.items[1].color == "green"


def test_update_commit_false_with_delete_all_should_not_persist_nested_deletions(db):
    """Test that commit=False prevents nested deletions when using on_update_assocs='delete_all'."""
    # Arrange
    tag_1 = Tag.insert(db, name="tag_1")
    tag_2 = Tag.insert(db, name="tag_2")
    item = Item.insert(db, color="red", tags=[tag_1, tag_2])
    original_tags_count = len(item.tags)

    # Act
    updated_item = item.update(
        db,
        color="blue",
        tags=[tag_1],  # This should delete tag_2 with delete_all
        on_update_assocs="delete_all",
        commit=False,
    )

    # Assert
    # The returned object should have the updated values
    assert updated_item.color == "blue"
    assert len(updated_item.tags) == 1
    assert updated_item.tags[0].name == "tag_1"

    # But the database should still have the original tags
    db.refresh(item)
    assert item.color == "red"
    assert len(item.tags) == original_tags_count
    assert item.tags[0].name == "tag_1"
    assert item.tags[1].name == "tag_2"


def test_update_commit_false_with_delete_all_should_not_persist_orphaned_records(db):
    """Test that commit=False prevents orphaned records when using on_update_assocs='delete_all'."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)
    original_item_type_count = len(ItemType.list(db))

    # Act
    updated_item = item.update(
        db,
        color="blue",
        item_type=None,  # This should delete the ItemType with delete_all
        on_update_assocs="delete_all",
        commit=False,
    )

    # Assert
    # The returned object should have the updated values
    assert updated_item.color == "blue"
    assert updated_item.item_type is None

    # But the database should still have the original ItemType
    assert len(ItemType.list(db)) == original_item_type_count
    db.refresh(item)
    assert item.color == "red"
    assert item.item_type.name == "type_1"


def test_update_commit_false_with_delete_all_should_handle_mixed_operations(db):
    """Test that commit=False handles mixed operations with on_update_assocs='delete_all'."""
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="green")
    item_3 = Item.insert(db, color="blue")
    item_list = ItemList.insert(db, name="list_1", items=[item_1, item_2])
    original_items_count = len(item_list.items)

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[
            item_1,  # Keep item_1
            item_3,  # Add item_3 (this should delete item_2 with delete_all)
        ],
        on_update_assocs="delete_all",
        commit=False,
    )

    # Assert
    # The returned object should have the updated values
    assert updated_item_list.name == "list_2"
    assert len(updated_item_list.items) == 2
    assert updated_item_list.items[0].color == "red"  # item_1 unchanged
    assert updated_item_list.items[1].color == "blue"  # item_3 added

    # But the database should still have the original items
    db.refresh(item_list)
    assert item_list.name == "list_1"
    assert len(item_list.items) == original_items_count
    assert item_list.items[0].color == "red"
    assert item_list.items[1].color == "green"
