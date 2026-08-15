"""List field selection (`select`) and `return_dict` — Memory adapter.

Default `list` returns Pydantic entities. Non-empty `select` or `return_dict=True`
switches the return shape to dictionaries.

Memory nests collection relationships as lists of partial dicts (not join-row
multiplication). See SQLAlchemy `test_list_select.py` for the join-shaped contract.
"""

from tests.crudle.adapters.memory.models import Item, ItemList


# ---------------------------------------------------------------------------
# Scalars
# ---------------------------------------------------------------------------


def test_list_with_select_fields(db):
    """Test listing with specific field selection."""
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Item, name="Item 3", color="green", price=30)

    items = db.list(Item, select=["name", "color"])

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
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    items = db.list(Item, select=["name"])

    assert len(items) == 2
    names = [item["name"] for item in items]
    assert "Item 1" in names
    assert "Item 2" in names


# ---------------------------------------------------------------------------
# Relationships (Memory: nested lists)
# ---------------------------------------------------------------------------


def test_list_with_select_relationship_fields(db):
    """Dotted select on 1:N nests a list of partial related dicts."""
    item1 = db.insert(Item, name="Item 1", color="red")
    item2 = db.insert(Item, name="Item 2", color="blue")
    db.insert(ItemList, name="List 1", items=[item1, item2])

    lists = db.list(ItemList, select=["name", "items.name", "items.color"])

    assert len(lists) == 1
    list_data = lists[0]
    assert list_data["name"] == "List 1"
    assert "items" in list_data
    assert len(list_data["items"]) == 2


# ---------------------------------------------------------------------------
# return_dict
# ---------------------------------------------------------------------------


def test_list_with_return_dict(db):
    """Test listing with return_dict option."""
    db.insert(Item, name="Item 1", color="red", price=10)
    db.insert(Item, name="Item 2", color="blue", price=20)

    items = db.list(Item, return_dict=True)

    assert len(items) == 2
    assert all(isinstance(item, dict) for item in items)
    assert all("name" in item for item in items)
    assert all("color" in item for item in items)
    assert all("price" in item for item in items)
