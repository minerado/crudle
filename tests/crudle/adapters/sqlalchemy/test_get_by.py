import pytest
from sqlalchemy.exc import MultipleResultsFound

from tests.models import Item, ItemList, Tag


def test_get_by_should_return_record(db):
    """Test getting a record by ID."""
    # Arrange
    new_item = Item.insert(db, color="red")

    # Act
    item = Item.get_by(db, color="red")

    # Assert
    assert item.id == new_item.id


def test_get_by_should_return_none_if_record_does_not_exist(db):
    # Arrange
    item = Item.get_by(db, color="red")

    # Assert
    assert item is None


def test_get_by_should_raise_if_it_finds_multiple_records(db):
    # Arrange
    Item.insert(db, color="red")
    Item.insert(db, color="red")

    # Act
    with pytest.raises(MultipleResultsFound):
        Item.get_by(db, color="red")


def test_get_by_should_return_record_with_suffix_filters(db):
    # Arrange
    item_1 = Item.insert(db, color="red", price=10)
    item_2 = Item.insert(db, color="blue", price=10)
    item_3 = Item.insert(db, color="red", price=20)

    # Act
    assert item_1.id == Item.get_by(db, color="red", price__lt=20).id
    assert item_2.id == Item.get_by(db, color="blue", price__eq=10).id
    assert item_3.id == Item.get_by(db, color="red", price__gt=10).id


def test_get_by_should_return_record_with_nested_filters(db):
    # Arrange
    item_1 = Item.insert(db, color="red", price=10)
    item_2 = Item.insert(db, color="blue", price=10)
    item_3 = Item.insert(db, color="red", price=20)

    red_list = ItemList.insert(db, name="list_1", items=[item_1, item_3])
    blue_list = ItemList.insert(db, name="list_2", items=[item_2])

    expensive_tag = Tag.insert(db, items=[item_3], name="expensive")
    cheap_tag = Tag.insert(db, items=[item_2], name="cheap")

    # Assert
    assert red_list.id == ItemList.get_by(db, **{"items.tags.name": "expensive"}).id
    assert blue_list.id == ItemList.get_by(db, **{"items.tags.name": "cheap"}).id
    assert expensive_tag.id == Tag.get_by(db, **{"items.item_list.name": "list_1"}).id
    assert cheap_tag.id == Tag.get_by(db, **{"items.item_list.name": "list_2"}).id
