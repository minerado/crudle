from tests.models import Item, ItemList, ItemTag, ItemType, Tag


def test_update_on_nilify_all_should_add_assoc_with_existing_record(db):
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="green")
    item_list = ItemList.insert(db, name="list_1")

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[{"id": item_1.id}, item_2],
        on_update_assocs="nilify_all",
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


def test_update_on_nilify_all_should_add_assoc_with_new_record(db):
    # Arrange
    item_list = ItemList.insert(db, name="list_1")

    # Act
    updated_item_list = item_list.update(
        db, name="list_2", items=[{"color": "blue"}], on_update_assocs="nilify_all"
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].color == "blue"
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 1


def test_update_on_nilify_all_should_add_and_update_assoc_with_existing_record(db):
    # Arrange
    item = Item.insert(db, color="red")
    item_list = ItemList.insert(db, name="list_1")

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[{"id": item.id, "color": "blue"}],
        on_update_assocs="nilify_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].id == item.id
    assert updated_item_list.items[0].color == "blue"
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 1


def test_update_on_nilify_all_should_update_assoc(db):
    # Arrange
    item = Item.insert(db, color="red")
    item_list = ItemList.insert(db, name="list_1", items=[item])

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[{"id": item.id, "color": "blue"}],
        on_update_assocs="nilify_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].id == item.id
    assert updated_item_list.items[0].color == "blue"
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 1


def test_update_on_nilify_all_should_update_assoc_and_add_new_assoc(
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
        on_update_assocs="nilify_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].id == item.id
    assert updated_item_list.items[0].color == "blue"
    assert updated_item_list.items[1].color == "green"
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 2


def test_update_on_nilify_all_should_nilify_assoc(db):
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)
    item_list = ItemList.insert(db, name="list_1", items=[item])

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[],
        on_update_assocs="nilify_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert len(ItemList.list(db)) == 1
    # Items should still exist but not be associated with the list
    assert len(Item.list(db)) == 1
    assert len(updated_item_list.items) == 0
    # ItemType should still exist since it's not managed by ItemList
    assert len(ItemType.list(db)) == 1


def test_update_on_nilify_all_should_nilify_single_assoc(db):
    """Test that setting a single relationship to None with nilify_all removes the association without deleting the object."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)

    # Act
    updated_item = item.update(
        db,
        color="blue",
        item_type=None,
        on_update_assocs="nilify_all",
    )

    # Assert
    assert updated_item.color == "blue"
    assert updated_item.item_type is None
    # ItemType should still exist (not deleted like in delete_all)
    assert len(ItemType.list(db)) == 1


def test_update_on_nilify_all_should_update_assoc_with_nested_assoc(db):
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
        on_update_assocs="nilify_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].color == "blue"
    assert updated_item_list.items[0].tags[0].name == "tag_2"
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 1
    assert len(Tag.list(db)) == 1


def test_update_on_nilify_all_should_nilify_assoc_and_add_new_assoc(
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
        on_update_assocs="nilify_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert updated_item_list.items[0].id == item_1.id
    assert updated_item_list.items[0].color == "magenta"
    assert updated_item_list.items[1].color == "yellow"
    assert updated_item_list.items[2].id == item_4.id
    assert updated_item_list.items[2].color == "yellow"
    assert len(updated_item_list.items) == 3
    # All items should still exist (item_2 and item_3 are just not associated anymore)
    assert len(Item.list(db)) == 5


def test_update_on_nilify_all_should_handle_new_model_instance_without_id(db):
    """Test handling a new model instance that doesn't have an ID yet."""
    # Arrange
    item_list = ItemList.insert(db, name="list_1")
    new_item = Item(color="blue")  # Not saved to DB yet

    # Act
    updated_item_list = item_list.update(
        db, name="list_2", items=[new_item], on_update_assocs="nilify_all"
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert len(updated_item_list.items) == 1
    assert updated_item_list.items[0].color == "blue"
    assert updated_item_list.items[0].id is not None
    assert len(Item.list(db)) == 1


def test_update_on_nilify_all_should_handle_mixed_dict_and_model_instances(db):
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
        on_update_assocs="nilify_all",
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


def test_update_on_nilify_all_should_handle_deep_nested_assoc(db):
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
        on_update_assocs="nilify_all",
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
    # Both item types should still exist (not deleted like in delete_all)
    assert len(ItemType.list(db)) == 2


def test_update_on_nilify_all_should_not_raise_error_when_nilifying_conflicting_associations(
    db,
):
    """Test that update does not raise IntegrityError when nilifying conflicting associations."""
    # Arrange
    item_type_1 = ItemType.insert(db, name="type_1")
    item_1 = Item.insert(db, color="red", item_type=item_type_1)
    item_2 = Item.insert(db, color="green", item_type=item_type_1)

    tag = Tag.insert(db, name="tag_1", items=[item_1, item_2])

    # Act - This should NOT raise an IntegrityError because nilify_all doesn't delete
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
        on_update_assocs="nilify_all",
    )

    # Assert
    assert len(updated_tag.items) == 3
    assert len(Tag.list(db)) == 1
    assert len(Item.list(db)) == 3
    # ItemType should still exist (not deleted)
    assert len(ItemType.list(db)) == 1


def test_update_on_nilify_all_should_nilify_through_association_table(db):
    # Arrange
    item_type_1 = ItemType.insert(db, name="type_1")
    item_1 = Item.insert(db, color="red", item_type=item_type_1)
    item_2 = Item.insert(db, color="green", item_type=item_type_1)

    tag = Tag.insert(db, name="tag_1", items=[item_1, item_2])

    updated_tag = tag.update(
        db, items=[{"id": item_1.id}], on_update_assocs="nilify_all"
    )

    # Assert
    assert len(updated_tag.items) == 1
    assert updated_tag.items[0].id == item_1.id
    assert len(Tag.list(db)) == 1
    # All items should still exist (item_2 is just not associated anymore)
    assert len(Item.list(db)) == 2
    # Association table should only have one entry (same as delete_all for many-to-many)
    assert len(ItemTag.list(db)) == 1
    assert len(ItemType.list(db)) == 1


def test_update_on_nilify_all_should_preserve_orphaned_records(db):
    """Test that nilify_all preserves orphaned records instead of deleting them."""
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="green")
    item_3 = Item.insert(db, color="blue")
    item_list = ItemList.insert(db, name="list_1", items=[item_1, item_2, item_3])

    # Act - Only keep item_1, nilify item_2 and item_3
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[{"id": item_1.id, "color": "magenta"}],
        on_update_assocs="nilify_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert len(updated_item_list.items) == 1
    assert updated_item_list.items[0].id == item_1.id
    assert updated_item_list.items[0].color == "magenta"

    # All items should still exist in the database (not deleted)
    assert len(Item.list(db)) == 3

    # Verify the orphaned items still exist
    all_items = Item.list(db)
    item_colors = [item.color for item in all_items]
    assert "magenta" in item_colors
    assert "green" in item_colors  # Orphaned but not deleted
    assert "blue" in item_colors  # Orphaned but not deleted


def test_update_on_nilify_all_should_handle_empty_list_associations(db):
    """Test that providing an empty list nilifies all associations."""
    # Arrange
    item_1 = Item.insert(db, color="red")
    item_2 = Item.insert(db, color="green")
    item_list = ItemList.insert(db, name="list_1", items=[item_1, item_2])

    # Act
    updated_item_list = item_list.update(
        db,
        name="list_2",
        items=[],
        on_update_assocs="nilify_all",
    )

    # Assert
    assert updated_item_list.name == "list_2"
    assert len(updated_item_list.items) == 0

    # Items should still exist but not be associated
    assert len(Item.list(db)) == 2

    # Verify items are orphaned but not deleted
    all_items = Item.list(db)
    item_colors = [item.color for item in all_items]
    assert "red" in item_colors
    assert "green" in item_colors


def test_update_on_nilify_all_should_handle_none_single_relationship(db):
    """Test nilify_all behavior when setting a single relationship to None."""
    # Arrange
    item_type = ItemType.insert(db, name="type_1")
    item = Item.insert(db, color="red", item_type=item_type)

    # Act
    updated_item = item.update(
        db,
        color="blue",
        item_type=None,
        on_update_assocs="nilify_all",
    )

    # Assert
    assert updated_item.color == "blue"
    assert updated_item.item_type is None

    # ItemType should still exist (not deleted)
    assert len(ItemType.list(db)) == 1

    # Verify the ItemType is orphaned but not deleted
    item_type = ItemType.list(db)[0]
    assert item_type.name == "type_1"
    assert item_type.item is None  # No item associated with it
