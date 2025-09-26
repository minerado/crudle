import pytest
from sqlalchemy.exc import IntegrityError

from tests.models import Item, ItemList, ItemTag, ItemType, Tag


def test_update_on_delete_all_should_add_assoc_with_existing_record(db):
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="green")
    item_list = ItemList.insert(db, name="list_1")

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[{"id": item_1.id}, item_2],
        on_update_assocs="delete_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert len(updated_item_list.items) == 2
    assert any(
        item.id == item_1.id and item.color == "red" for item in updated_item_list.items
    )
    assert any(
        item.id == item_2.id and item.color == "green"
        for item in updated_item_list.items
    )
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 2


def test_update_on_delete_all_should_add_assoc_with_new_record(db):
    # Arrange
    item_list = ItemList.insert(db, name="list_1")

    # Act
    updated_item_list = item_list.update(
        db, name="list_2", items=[{"color": "blue"}], on_update_assocs="delete_all"
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].color == "blue"
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 1


def test_update_on_delete_all_should_add_and_update_assoc_with_existing_record(db):
    # Arrange
    item = Item.insert(db, color="red")
    item_list = ItemList.insert(db, name="list_1")

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[{"id": item.id, "color": "blue"}],
        on_update_assocs="delete_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].id == item.id
    assert updated_item_list.items[0].color == "blue"
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 1


def test_update_on_delete_all_should_update_assoc(db):
    # Arrange
    item = Item.insert(db, color="red")
    item_list = ItemList.insert(db, name="list_1", items=[item])

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[{"id": item.id, "color": "blue"}],
        on_update_assocs="delete_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].id == item.id
    assert updated_item_list.items[0].color == "blue"
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 1


def test_update_on_delete_all_should_update_assoc_and_add_new_assoc(
    db,
):
    # Arrange
    item = Item.insert(db, color="red")
    item_list = ItemList.insert(db, name="list_1", items=[item])

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[{"id": item.id, "color": "blue"}, {"color": "green"}],
        on_update_assocs="delete_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].id == item.id
    assert updated_item_list.items[0].color == "blue"
    assert updated_item_list.items[1].color == "green"
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 2


def test_update_on_delete_all_should_delete_assoc(db):
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)
    item_list = ItemList.insert(db, name="list_1", items=[item])

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[],
        on_update_assocs="delete_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 0
    assert len(updated_item_list.items) == 0
    # ItemType should still exist since it's not managed by ItemList and db doesn't cascade delete it
    assert len(ItemType.list(db)) == 1


def test_update_on_delete_all_should_delete_single_assoc(db):
    """Test that setting a single relationship to None with delete_all removes the association."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)

    # Act
    updated_item = item.update(
        db,
        color="blue",
        item_type=None,
        on_update_assocs="delete_all",
    )

    # Assert
    assert updated_item.color == "blue"
    assert updated_item.item_type is None
    assert len(ItemType.list(db)) == 0  # ItemType should be deleted


def test_update_on_delete_all_should_update_assoc_with_nested_assoc(db):
    # Arrange
    tag = Tag.insert(db, name="tag_1")
    item = Item.insert(db, color="red", tags=[tag])
    item_list = ItemList.insert(db, name="list_1", items=[item])

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[
            {"id": item.id, "color": "blue", "tags": [{"id": tag.id, "name": "tag_2"}]}
        ],
        on_update_assocs="delete_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].color == "blue"
    assert updated_item_list.items[0].tags[0].name == "tag_2"
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 1
    assert len(Tag.list(db)) == 1


def test_update_on_delete_all_should_delete_assoc_and_add_new_assoc(
    db,
):
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="green")
    item_3 = Item.insert(db, color="blue")
    item_4 = Item.insert(db, color="yellow")
    item_list = ItemList.insert(db, name="list_1", items=[item_1, item_2, item_3])

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[{"id": item_1.id, "color": "magenta"}, {"color": "yellow"}, item_4],
        on_update_assocs="delete_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].id == item_1.id
    assert updated_item_list.items[0].color == "magenta"
    assert updated_item_list.items[1].color == "yellow"
    assert updated_item_list.items[2].id == item_4.id
    assert updated_item_list.items[2].color == "yellow"
    assert len(updated_item_list.items) == 3
    assert len(Item.list(db)) == 3


def test_update_on_delete_all_should_handle_new_model_instance_without_id(db):
    """Test handling a new model instance that doesn't have an ID yet."""
    # Arrange
    item_list = ItemList.insert(db, name="list_1")
    new_item = Item(color="blue")  # Not saved to DB yet

    # Act
    updated_item_list = item_list.update(
        db, name="list_2", items=[new_item], on_update_assocs="delete_all"
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert len(updated_item_list.items) == 1
    assert updated_item_list.items[0].color == "blue"
    assert updated_item_list.items[0].id is not None
    assert len(Item.list(db)) == 1


def test_update_on_delete_all_should_handle_mixed_dict_and_model_instances(db):
    """Test handling a mix of dictionaries and model instances."""
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item(color="green")  # New instance
    item_list = ItemList.insert(db, name="list_1")

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[{"id": item_1.id, "color": "blue"}, item_2, {"color": "yellow"}],
        on_update_assocs="delete_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert len(updated_item_list.items) == 3
    assert any(
        item.id == item_1.id and item.color == "blue"
        for item in updated_item_list.items
    )
    assert any(item.color == "green" for item in updated_item_list.items)
    assert any(item.color == "yellow" for item in updated_item_list.items)
    assert len(Item.list(db)) == 3


def test_update_on_delete_all_should_handle_deep_nested_assoc(db):
    # Arrange
    item_type_1 = ItemType.insert(db, name="type_1")
    item_type_2 = ItemType.insert(db, name="type_2")
    item_1 = Item.insert(db, color="red", item_type=item_type_1)
    item_2 = Item.insert(db, color="green", item_type=item_type_2)

    tag = Tag.insert(db, name="tag_1", items=[item_1, item_2])

    # Act
    updated_tag = tag.update(
        db,
        items=[
            {
                "id": item_1.id,
                "color": "blue",
                "item_type": {"id": item_type_1.id, "name": "type_a"},
            },
            {
                "id": item_2.id,
                "color": "magenta",
                "item_type": None,
            },
            {"color": "green"},
        ],
        on_update_assocs="delete_all",
    )

    # Assert
    assert len(updated_tag.items) == 3
    assert any(
        item.id == item_1.id and item.color == "blue" for item in updated_tag.items
    )
    assert any(
        item.id == item_2.id and item.color == "magenta" for item in updated_tag.items
    )
    assert any(item.color == "green" for item in updated_tag.items)
    assert len(Tag.list(db)) == 1
    assert len(Item.list(db)) == 3
    assert len(ItemType.list(db)) == 1


def test_update_on_delete_all_should_raise_error_when_deleting_conflicting_associations(
    db,
):
    """Test that update raises IntegrityError when trying to both update and delete the same object."""
    # Arrange
    item_type_1 = ItemType.insert(db, name="type_1")
    item_1 = Item.insert(db, color="red", item_type=item_type_1)
    item_2 = Item.insert(db, color="green", item_type=item_type_1)

    tag = Tag.insert(db, name="tag_1", items=[item_1, item_2])

    # Act & Assert - This should raise an IntegrityError because we're trying to
    # both update item_type_1 (in item_1) and delete it (in item_2)
    with pytest.raises(IntegrityError, match="Conflicting operations on item_type"):
        tag.update(
            db,
            items=[
                {
                    "id": item_1.id,
                    "color": "blue",
                    "item_type": {"id": item_type_1.id, "name": "type_a"},
                },
                {
                    "id": item_2.id,
                    "color": "magenta",
                    "item_type": None,
                },
                {"color": "green"},
            ],
            on_update_assocs="delete_all",
        )
