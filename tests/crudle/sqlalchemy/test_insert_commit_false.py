from tests.models import Item, ItemList, ItemType, Tag


def test_insert_commit_false_should_not_persist_basic_record(db):
    """Test that commit=False prevents basic record creation from being persisted."""
    # Act
    item = Item.insert(db, color="red", commit=False)

    # Assert
    # The returned object should have the values
    assert item.color == "red"
    assert item.id is None  # No ID assigned yet

    # But the database should not have the record
    assert len(Item.list(db)) == 0

    # After manual commit, it should be persisted
    db.commit()
    assert item.id is not None
    assert len(Item.list(db)) == 1


def test_insert_commit_false_should_not_persist_single_relationship(db):
    """Test that commit=False prevents single relationship creation from being persisted."""
    # Act
    item = Item.insert(db, color="red", item_type={"name": "type_1"}, commit=False)

    # Assert
    # The returned object should have the relationship
    assert item.color == "red"
    assert item.item_type.name == "type_1"
    assert item.id is None
    assert item.item_type.id is None

    # But the database should not have either record
    assert len(Item.list(db)) == 0
    assert len(ItemType.list(db)) == 0

    # After manual commit, both should be persisted
    db.commit()
    assert item.id is not None
    assert item.item_type.id is not None
    assert len(Item.list(db)) == 1
    assert len(ItemType.list(db)) == 1


def test_insert_commit_false_should_not_persist_list_relationship(db):
    """Test that commit=False prevents list relationship creation from being persisted."""
    # Act
    item_list = ItemList.insert(
        db, name="list_1", items=[{"color": "red"}, {"color": "blue"}], commit=False
    )

    # Assert
    # The returned object should have the relationships
    assert item_list.name == "list_1"
    assert len(item_list.items) == 2
    assert item_list.items[0].color == "red"
    assert item_list.items[1].color == "blue"
    assert item_list.id is None
    assert item_list.items[0].id is None
    assert item_list.items[1].id is None

    # But the database should not have any records
    assert len(ItemList.list(db)) == 0
    assert len(Item.list(db)) == 0

    # After manual commit, all should be persisted
    db.commit()
    assert item_list.id is not None
    assert item_list.items[0].id is not None
    assert item_list.items[1].id is not None
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 2


def test_insert_commit_false_should_not_persist_nested_relationships(db):
    """Test that commit=False prevents nested relationship creation from being persisted."""
    # Act
    item = Item.insert(
        db, color="red", tags=[{"name": "tag_1"}, {"name": "tag_2"}], commit=False
    )

    # Assert
    # The returned object should have the nested relationships
    assert item.color == "red"
    assert len(item.tags) == 2
    assert item.tags[0].name == "tag_1"
    assert item.tags[1].name == "tag_2"
    assert item.id is None
    assert item.tags[0].id is None
    assert item.tags[1].id is None

    # But the database should not have any records
    assert len(Item.list(db)) == 0
    assert len(Tag.list(db)) == 0

    # After manual commit, all should be persisted
    db.commit()
    assert item.id is not None
    assert item.tags[0].id is not None
    assert item.tags[1].id is not None
    assert len(Item.list(db)) == 1
    assert len(Tag.list(db)) == 2


def test_insert_commit_false_should_not_persist_mixed_relationships(db):
    """Test that commit=False prevents mixed relationship creation from being persisted."""
    # Act
    item = Item.insert(
        db,
        color="red",
        item_type={"name": "type_1"},  # Single relationship
        tags=[{"name": "tag_1"}, {"name": "tag_2"}],  # List relationship
        commit=False,
    )

    # Assert
    # The returned object should have all relationships
    assert item.color == "red"
    assert item.item_type.name == "type_1"
    assert len(item.tags) == 2
    assert item.tags[0].name == "tag_1"
    assert item.tags[1].name == "tag_2"
    assert item.id is None
    assert item.item_type.id is None
    assert item.tags[0].id is None
    assert item.tags[1].id is None

    # But the database should not have any records
    assert len(Item.list(db)) == 0
    assert len(ItemType.list(db)) == 0
    assert len(Tag.list(db)) == 0

    # After manual commit, all should be persisted
    db.commit()
    assert item.id is not None
    assert item.item_type.id is not None
    assert item.tags[0].id is not None
    assert item.tags[1].id is not None
    assert len(Item.list(db)) == 1
    assert len(ItemType.list(db)) == 1
    assert len(Tag.list(db)) == 2


def test_insert_commit_false_should_not_persist_deep_nested_relationships(db):
    """Test that commit=False prevents deep nested relationship creation from being persisted."""
    # Act
    item_list = ItemList.insert(
        db,
        name="list_1",
        items=[
            {
                "color": "red",
                "item_type": {"name": "type_1"},
                "tags": [{"name": "tag_1"}, {"name": "tag_2"}],
            },
            {
                "color": "blue",
                "item_type": {"name": "type_2"},
                "tags": [{"name": "tag_3"}],
            },
        ],
        commit=False,
    )

    # Assert
    # The returned object should have all nested relationships
    assert item_list.name == "list_1"
    assert len(item_list.items) == 2

    # First item
    assert item_list.items[0].color == "red"
    assert item_list.items[0].item_type.name == "type_1"
    assert len(item_list.items[0].tags) == 2
    assert item_list.items[0].tags[0].name == "tag_1"
    assert item_list.items[0].tags[1].name == "tag_2"

    # Second item
    assert item_list.items[1].color == "blue"
    assert item_list.items[1].item_type.name == "type_2"
    assert len(item_list.items[1].tags) == 1
    assert item_list.items[1].tags[0].name == "tag_3"

    # All should have no IDs
    assert item_list.id is None
    assert item_list.items[0].id is None
    assert item_list.items[1].id is None
    assert item_list.items[0].item_type.id is None
    assert item_list.items[1].item_type.id is None
    assert item_list.items[0].tags[0].id is None
    assert item_list.items[0].tags[1].id is None
    assert item_list.items[1].tags[0].id is None

    # But the database should not have any records
    assert len(ItemList.list(db)) == 0
    assert len(Item.list(db)) == 0
    assert len(ItemType.list(db)) == 0
    assert len(Tag.list(db)) == 0

    # After manual commit, all should be persisted
    db.commit()
    assert item_list.id is not None
    assert item_list.items[0].id is not None
    assert item_list.items[1].id is not None
    assert item_list.items[0].item_type.id is not None
    assert item_list.items[1].item_type.id is not None
    assert item_list.items[0].tags[0].id is not None
    assert item_list.items[0].tags[1].id is not None
    assert item_list.items[1].tags[0].id is not None
    assert len(ItemList.list(db)) == 1
    assert len(Item.list(db)) == 2
    assert len(ItemType.list(db)) == 2
    assert len(Tag.list(db)) == 3


def test_insert_commit_false_should_handle_existing_relationships(db):
    """Test that commit=False works with existing relationships."""
    # Arrange
    existing_type = ItemType.insert(db, name="existing_type")
    existing_tag = Tag.insert(db, name="existing_tag")

    # Act
    item = Item.insert(
        db,
        color="red",
        item_type={"id": existing_type.id},  # Existing relationship
        tags=[
            {"id": existing_tag.id},  # Existing relationship
            {"name": "new_tag"},  # New relationship
        ],
        commit=False,
    )

    # Assert
    # The returned object should have the relationships
    assert item.color == "red"
    assert item.item_type.name == "existing_type"
    assert len(item.tags) == 2
    assert item.tags[0].name == "existing_tag"
    assert item.tags[1].name == "new_tag"
    assert item.id is None
    assert item.item_type.id == existing_type.id  # Existing relationship should have ID
    assert item.tags[0].id == existing_tag.id  # Existing relationship should have ID
    assert item.tags[1].id is None  # New relationship should not have ID

    # The database should only have the original records
    assert len(Item.list(db)) == 0
    assert len(ItemType.list(db)) == 1
    assert len(Tag.list(db)) == 1

    # After manual commit, the new records should be persisted
    db.commit()
    assert item.id is not None
    assert item.tags[1].id is not None
    assert len(Item.list(db)) == 1
    assert len(ItemType.list(db)) == 1
    assert len(Tag.list(db)) == 2


def test_insert_commit_false_should_handle_duplicate_names_in_memory(db):
    """Test that commit=False handles duplicate names in memory without database constraints."""
    # Act
    item = Item.insert(
        db,
        color="red",
        tags=[
            {"name": "tag_1"},
            {"name": "tag_1"},  # Duplicate name in memory
            {"name": "tag_2"},
        ],
        commit=False,
    )

    # Assert
    # The returned object should have all relationships (including duplicates)
    assert item.color == "red"
    assert len(item.tags) == 3
    assert item.tags[0].name == "tag_1"
    assert item.tags[1].name == "tag_1"
    assert item.tags[2].name == "tag_2"
    assert item.id is None
    assert item.tags[0].id is None
    assert item.tags[1].id is None
    assert item.tags[2].id is None

    # The database should not have any records
    assert len(Item.list(db)) == 0
    assert len(Tag.list(db)) == 0

    # Note: We don't commit this because it would fail due to unique constraint
    # This test demonstrates that commit=False allows duplicate names in memory


def test_insert_commit_true_should_persist_changes(db):
    """Test that commit=True (default) persists changes as expected."""
    # Act
    item = Item.insert(db, color="red", item_type={"name": "type_1"})

    # Assert
    # The returned object should have the values
    assert item.color == "red"
    assert item.item_type.name == "type_1"
    assert item.id is not None
    assert item.item_type.id is not None

    # The database should also have the records
    assert len(Item.list(db)) == 1
    assert len(ItemType.list(db)) == 1


def test_insert_commit_false_should_work_with_empty_relationships(db):
    """Test that commit=False works with empty relationships."""
    # Act
    item = Item.insert(
        db,
        color="red",
        item_type=None,  # None single relationship
        tags=[],  # Empty list relationship
        commit=False,
    )

    # Assert
    # The returned object should have the values
    assert item.color == "red"
    assert item.item_type is None
    assert len(item.tags) == 0
    assert item.id is None

    # The database should not have any records
    assert len(Item.list(db)) == 0

    # After manual commit, only the main record should be persisted
    db.commit()
    assert item.id is not None
    assert len(Item.list(db)) == 1


def test_insert_commit_false_should_handle_duplicate_relationships(db):
    """Test that commit=False handles duplicate relationships correctly."""
    # Act
    item = Item.insert(
        db,
        color="red",
        tags=[{"name": "tag_1"}, {"name": "tag_2"}, {"name": "tag_3"}],
        commit=False,
    )

    # Assert
    # The returned object should have all relationships
    assert item.color == "red"
    assert len(item.tags) == 3
    assert item.tags[0].name == "tag_1"
    assert item.tags[1].name == "tag_2"
    assert item.tags[2].name == "tag_3"
    assert item.id is None
    assert item.tags[0].id is None
    assert item.tags[1].id is None
    assert item.tags[2].id is None

    # The database should not have any records
    assert len(Item.list(db)) == 0
    assert len(Tag.list(db)) == 0

    # After manual commit, all should be persisted
    db.commit()
    assert item.id is not None
    assert item.tags[0].id is not None
    assert item.tags[1].id is not None
    assert item.tags[2].id is not None
    assert len(Item.list(db)) == 1
    assert len(Tag.list(db)) == 3
