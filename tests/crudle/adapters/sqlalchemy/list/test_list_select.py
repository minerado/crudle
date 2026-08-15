"""List field selection (`select`) and `return_dict`.

Default `list` returns ORM entities. Non-empty `select` or `return_dict=True`
switches the return shape to dictionaries.

SQLAlchemy contract for collection relationships (1:N / M:N): selecting a
relationship uses a join, so parent rows multiply (one dict per related row).
Nested relationship data is a single object (or None), not an aggregated list.
Memory aggregates nested collections into lists — do not treat those as twins.
"""

import pytest

from tests.models import Item, ItemList, ItemType, Tag


# ---------------------------------------------------------------------------
# Scalars
# ---------------------------------------------------------------------------


def test_list_with_select_fields(db):
    """Test listing with specific field selection."""
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)
    Item.insert(db, name="Item 3", color="green", price=30)

    items = Item.list(db, select=["name", "color"])

    assert len(items) == 3
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
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)

    items = Item.list(db, select=["name"])

    assert len(items) == 2
    names = [item["name"] for item in items]
    assert "Item 1" in names
    assert "Item 2" in names


def test_list_with_select_and_filters(db):
    """Test listing with field selection and filters."""
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)
    Item.insert(db, name="Item 3", color="red", price=30)

    red_items = Item.list(db, color="red", select=["name", "price"])

    assert len(red_items) == 2
    names = [item["name"] for item in red_items]
    prices = [item["price"] for item in red_items]
    assert "Item 1" in names
    assert "Item 3" in names
    assert 10 in prices
    assert 30 in prices


def test_list_with_complex_select_expression(db):
    """Test listing with multiple scalar select fields."""
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)

    items = Item.list(db, select=["name", "color", "price"])

    assert len(items) == 2
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
    """Empty select keeps default entity return shape."""
    Item.insert(db, name="Item 1", color="red")
    Item.insert(db, name="Item 2", color="blue")

    items = Item.list(db, select=[])

    assert len(items) == 2
    assert all(isinstance(item, Item) for item in items)


def test_list_with_select_single_record(db):
    """Test listing with select when only one record exists."""
    Item.insert(db, name="Item 1", color="red", price=10)

    items = Item.list(db, select=["name"])

    assert len(items) == 1
    assert items[0]["name"] == "Item 1"


def test_list_with_select_mixed_valid_invalid_fields(db):
    """Invalid select fields are skipped; valid fields (incl. rels) remain."""
    Item.insert(db, name="Item 1", color="red", price=10)

    items = Item.list(db, select=["name", "invalid_field", "price", "item_list"])

    assert len(items) == 1
    item = items[0]
    assert isinstance(item, dict)
    assert "name" in item
    assert "price" in item
    assert "item_list" in item
    assert "invalid_field" not in item
    assert item["name"] == "Item 1"
    assert item["price"] == 10
    assert item["item_list"] is None


# ---------------------------------------------------------------------------
# return_dict
# ---------------------------------------------------------------------------


def test_list_with_return_dict(db):
    """return_dict=True returns all scalar columns as dictionaries."""
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)

    items = Item.list(db, return_dict=True)

    assert len(items) == 2
    for item in items:
        assert isinstance(item, dict)
        assert "id" in item
        assert "name" in item
        assert "color" in item
        assert "price" in item
        assert "created_at" in item
        assert "item_list_id" in item
        assert "item_type_id" in item
        assert "item_list" not in item
        assert "tags" not in item
        assert "item_type" not in item


def test_list_with_return_dict_and_filters(db):
    """Test listing with return_dict=True and filters."""
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)
    Item.insert(db, name="Item 3", color="red", price=30)

    red_items = Item.list(db, color="red", return_dict=True)

    assert len(red_items) == 2
    for item in red_items:
        assert isinstance(item, dict)
        assert item["color"] == "red"
        assert "name" in item
        assert "price" in item


def test_list_with_return_dict_and_sorting(db):
    """Test listing with return_dict=True and sorting."""
    Item.insert(db, name="Item 1", color="red", price=30)
    Item.insert(db, name="Item 2", color="blue", price=10)
    Item.insert(db, name="Item 3", color="green", price=20)

    items = Item.list(db, return_dict=True, sort=[{"field": "price", "order": "asc"}])

    assert len(items) == 3
    assert items[0]["price"] == 10
    assert items[1]["price"] == 20
    assert items[2]["price"] == 30


def test_list_with_return_dict_and_limit(db):
    """Test listing with return_dict=True and limit."""
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="blue", price=20)
    Item.insert(db, name="Item 3", color="green", price=30)

    items = Item.list(db, return_dict=True, limit=2)

    assert len(items) == 2
    for item in items:
        assert isinstance(item, dict)
        assert "name" in item


def test_list_with_empty_select_and_return_dict(db):
    """Empty select + return_dict still returns full scalar dicts."""
    Item.insert(db, name="Item 1", color="red")

    items = Item.list(db, select=[], return_dict=True)

    assert len(items) == 1
    item = items[0]
    assert isinstance(item, dict)
    assert "name" in item
    assert "color" in item
    assert "id" in item


def test_list_with_return_dict_and_relationships(db):
    """return_dict=True must not include relationship objects."""
    item1 = Item.insert(db, name="Item 1", color="red")
    item2 = Item.insert(db, name="Item 2", color="blue")

    ItemList.insert(db, name="List 1", items=[item1, item2])

    items = Item.list(db, return_dict=True)

    assert len(items) == 2
    for item in items:
        assert isinstance(item, dict)
        assert "id" in item
        assert "name" in item
        assert "color" in item
        assert "item_list_id" in item
        assert "item_list" not in item
        assert "tags" not in item
        assert "item_type" not in item


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


def test_list_with_nested_select_relationship_fields(db):
    """Selecting a whole relationship nests related columns under the rel key."""
    item1 = Item.insert(db, name="Item 1", color="red")
    item2 = Item.insert(db, name="Item 2", color="blue")

    ItemList.insert(db, name="List 1", items=[item1, item2])

    items = Item.list(db, select=["name", "item_list", "color"])

    assert len(items) == 2
    for item in items:
        assert isinstance(item, dict)
        assert "name" in item
        assert "color" in item
        assert "item_list" in item
        assert isinstance(item["item_list"], dict)


def test_list_with_select_invalid_relationship_fields(db):
    """Invalid relationship names in select are skipped."""
    Item.insert(db, name="Item 1", color="red")

    items = Item.list(db, select=["name", "nonexistent_relationship", "color"])

    assert len(items) == 1
    for item in items:
        assert isinstance(item, dict)
        assert "name" in item
        assert "color" in item
        assert "nonexistent_relationship" not in item


def test_list_with_select_only_relationship_fields(db):
    """Select containing only relationship fields still returns dict rows."""
    Item.insert(db, name="Item 1", color="red")

    items = Item.list(db, select=["item_list", "tags", "item_type"])

    assert len(items) == 1
    item = items[0]
    assert isinstance(item, dict)
    assert "item_list" in item or "item_list_id" in item
    assert "tags" in item or "tags_id" in item
    assert "item_type" in item or "item_type_id" in item


def test_list_with_select_relationship_fields(db):
    """Selecting a 1:N relationship returns one row per related item."""
    Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    item3 = Item.insert(db, name="Item 3", color="green", price=30)

    ItemList.insert(db, name="List 1", items=[item2])
    ItemList.insert(db, name="List 2", items=[item3])

    lists_with_items = ItemList.list(db, select=["items"])

    assert lists_with_items[0]["items"]["id"] == item2.id
    assert lists_with_items[1]["items"]["id"] == item3.id


def test_list_with_select_one_to_one_relationship(db):
    """One-to-one select nests related columns; missing rel is None."""
    item_type = ItemType.insert(db, name="type_a")
    Item.insert(db, name="Test Item with Type", item_type=item_type)
    Item.insert(db, name="Test Item without Type")

    result = Item.list(db, select=["id", "name", "item_type"])

    assert len(result) == 2

    item_with_type_data = next(
        item for item in result if item["name"] == "Test Item with Type"
    )
    item_without_type_data = next(
        item for item in result if item["name"] == "Test Item without Type"
    )

    assert "item_type" in item_with_type_data
    assert isinstance(item_with_type_data["item_type"], dict)
    assert item_with_type_data["item_type"]["id"] == item_type.id
    assert item_with_type_data["item_type"]["name"] == "type_a"

    assert "item_type" in item_without_type_data
    assert item_without_type_data["item_type"] is None

    for item_data in result:
        assert "item_type_id" not in item_data
        assert "item_type_name" not in item_data
        assert "item_type_created_at" not in item_data


def test_list_with_select_one_to_many_relationship_with_nulls(db):
    """1:N select multiplies parent rows; empty collection is None."""
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    item3 = Item.insert(db, name="Item 3", color="green", price=30)

    ItemList.insert(db, name="List 1", items=[item1, item2])
    ItemList.insert(db, name="List 2", items=[item3])
    ItemList.insert(db, name="Empty List", items=[])

    lists = ItemList.list(db, select=["id", "name", "items"])

    assert len(lists) == 4

    list1_records = [item for item in lists if item["name"] == "List 1"]
    list2_data = next(item for item in lists if item["name"] == "List 2")
    empty_list_data = next(item for item in lists if item["name"] == "Empty List")

    assert len(list1_records) == 2
    for list1_data in list1_records:
        assert "items" in list1_data
        assert isinstance(list1_data["items"], dict)
        assert list1_data["items"]["id"] in [item1.id, item2.id]

    assert "items" in list2_data
    assert isinstance(list2_data["items"], dict)
    assert list2_data["items"]["id"] == item3.id

    assert "items" in empty_list_data
    assert empty_list_data["items"] is None


def test_list_with_super_deep_nested_assoc(db):
    """Dotted select on M:N nests selected related fields under the rel key."""
    item_type = ItemType.insert(db, name="type_a")
    item = Item.insert(db, color="red", item_type=item_type)
    ItemList.insert(db, name="list_1", items=[item])
    Tag.insert(db, name="tag_1", items=[item])

    result = Tag.list(db, select=["id", "items.color", "items.id"])

    assert len(result) == 1
    assert "items" in result[0]
    assert isinstance(result[0]["items"], dict)
    assert result[0]["items"]["color"] == "red"
    assert result[0]["items"]["id"] == item.id


# ---------------------------------------------------------------------------
# count-in-select
# ---------------------------------------------------------------------------


def test_list_with_select_count_fields(db):
    """count.* with other fields groups by those fields."""
    Item.insert(db, name="Item 1", color="red")
    Item.insert(db, name="Item 2", color="red")
    Item.insert(db, name="Item 3", color="blue")

    items = Item.list(db, select=["count.id", "color"])

    assert len(items) == 2
    for item in items:
        assert isinstance(item, dict)
        assert "count.id" in item
        assert "color" in item
        assert isinstance(item["count.id"], int)
        assert item["count.id"] > 0


def test_list_with_select_count_single_field(db):
    """Select containing only count returns a single aggregate row."""
    Item.insert(db, name="Item 1", color="red")
    Item.insert(db, name="Item 2", color="blue")

    items = Item.list(db, select=["count.id"])

    assert len(items) == 1
    item = items[0]
    assert isinstance(item, dict)
    assert "count.id" in item
    assert item["count.id"] == 2


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="DISTINCT ON is only supported by PostgreSQL, not SQLite")
def test_list_with_select_and_distinct_on(db):
    """Test listing with both select and distinct_on."""
    Item.insert(db, name="Item 1", color="red", price=10)
    Item.insert(db, name="Item 2", color="red", price=20)
    Item.insert(db, name="Item 3", color="blue", price=30)

    distinct_items = Item.list(db, distinct_on=["color"], select=["name", "color"])

    assert len(distinct_items) == 2
    colors = [item["color"] for item in distinct_items]
    assert "red" in colors
    assert "blue" in colors
