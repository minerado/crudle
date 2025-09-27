from tests.models import Item, ItemList, Tag


def test_insert_should_create_record(db):
    # Act
    item = Item.insert(db, color="red")

    # Assert
    assert item.id is not None
    assert item.color == "red"


def test_insert_should_create_record_with_existing_relationship(db):
    # Arrange
    item_list = ItemList.insert(db, name="list_1")

    # Act
    item = Item.insert(db, color="red", item_list=item_list)

    # Assert
    assert item.id is not None
    assert item.color == "red"
    assert item.item_list == item_list


def test_insert_should_create_record_with_new_relationship(db):
    # Act
    item = Item.insert(db, color="red", item_list={"name": "list_1"})

    # Assert
    assert item.id is not None
    assert item.color == "red"
    assert item.item_list.name == "list_1"


def test_insert_should_create_record_with_list_of_nested_new_relationships(db):
    # Act
    item_list = ItemList.insert(
        db,
        items=[
            {"color": "red", "tags": [{"name": "tag_1"}]},
            {"color": "blue", "tags": [{"name": "tag_2"}]},
        ],
        name="list_1",
    )

    # Assert
    assert item_list.id is not None
    assert item_list.items[0].color == "red"
    assert item_list.items[0].tags[0].name == "tag_1"
    assert item_list.items[1].color == "blue"
    assert item_list.items[1].tags[0].name == "tag_2"


def test_insert_should_create_record_with_list_of_nested_existing_relationships(db):
    # Arrange
    tag_1 = Tag.insert(db, name="tag_1")
    tag_2 = Tag.insert(db, name="tag_2")

    # Act
    item_list = ItemList.insert(
        db,
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
    # Arrange
    tag_1 = Tag.insert(db, name="tag_1")
    tag_2 = Tag.insert(db, name="tag_2")

    # Act
    item_list = ItemList.insert(
        db,
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
    assert len(Tag.list(db)) == 3


def test_insert_should_create_record_with_nested_relationship_and_not_update_existing_relationship(
    db,
):
    # Arrange
    tag = Tag.insert(db, name="tag_1")

    # Act
    item_list = ItemList.insert(
        db,
        items=[{"color": "red", "tags": [{"id": tag.id, "name": "tag_2"}]}],
        name="list_1",
    )

    # Assert
    assert item_list.id is not None
    assert item_list.items[0].color == "red"
    assert not item_list.items[0].tags[0].name == "tag_2"
    assert len(Tag.list(db)) == 1


def test_insert_should_not_create_when_commit_is_false(db):
    # Act
    item_list = ItemList.insert(db, name="list_1", commit=False)

    # Assert
    assert item_list.id is None
    assert len(ItemList.list(db)) == 0

    # Commit
    db.commit()

    # Assert
    assert item_list.id is not None
    assert len(ItemList.list(db)) == 1
