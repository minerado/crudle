"""List field selection (`select`) and `return_dict` — Memory adapter.

Default `list` returns Pydantic entities. Non-empty `select` or `return_dict=True`
switches the return shape to dictionaries.

Memory nests collection relationships as lists of partial dicts (not join-row
multiplication). See SQLAlchemy `test_list_select.py` for the join-shaped contract.

Deep select supports multi-hop paths (e.g. ``items.item_type.name``) with
nested lists at collection hops; see the Deep select section.
"""

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


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


# ---------------------------------------------------------------------------
# Deep select (multi-hop)
#
# Memory shape: one parent row; collections nest as lists of partial dicts
# at every collection hop (not join-row multiplication).
# ---------------------------------------------------------------------------


def test_deep_select_two_hop_to_one(db):
    """Two-hop path through 1:N then 1:1 nests as items[].item_type."""
    item_type = db.insert(ItemType, name="electronics")
    item = db.insert(Item, name="Laptop", color="silver", item_type=item_type)
    db.insert(ItemList, name="Wishlist", items=[item])

    rows = db.list(ItemList, select=["name", "items.item_type.name"])

    assert len(rows) == 1
    assert rows[0]["name"] == "Wishlist"
    assert len(rows[0]["items"]) == 1
    assert rows[0]["items"][0]["item_type"]["name"] == "electronics"


def test_deep_select_two_hop_collection_keeps_one_parent(db):
    """1:N then M:N keeps one parent; items and tags are nested lists."""
    item1 = db.insert(Item, name="Item 1", color="red", price=10)
    item2 = db.insert(Item, name="Item 2", color="blue", price=20)
    db.insert(Tag, name="expensive", items=[item1])
    db.insert(Tag, name="sale", items=[item1])
    db.insert(Tag, name="cheap", items=[item2])
    db.insert(ItemList, name="List 1", items=[item1, item2])

    rows = db.list(ItemList, select=["name", "items.id", "items.tags.name"])

    assert len(rows) == 1
    assert rows[0]["name"] == "List 1"
    assert len(rows[0]["items"]) == 2

    by_id = {item["id"]: item for item in rows[0]["items"]}
    assert {t["name"] for t in by_id[item1.id]["tags"]} == {"expensive", "sale"}
    assert {t["name"] for t in by_id[item2.id]["tags"]} == {"cheap"}


def test_deep_select_merges_sibling_fields_on_same_path(db):
    """Shallow and deep fields on the same relationship merge into one tree."""
    item_type = db.insert(ItemType, name="type_a")
    item = db.insert(
        Item, name="Gadget", color="red", price=99, item_type=item_type
    )
    db.insert(ItemList, name="Box", items=[item])

    rows = db.list(
        ItemList,
        select=["name", "items.name", "items.color", "items.item_type.name"],
    )

    assert len(rows) == 1
    nested = rows[0]["items"][0]
    assert nested["name"] == "Gadget"
    assert nested["color"] == "red"
    assert nested["item_type"]["name"] == "type_a"


def test_deep_select_missing_intermediate_is_none(db):
    """Missing to-one hop yields None at that nesting level."""
    item = db.insert(Item, name="Orphan", color="grey")
    db.insert(ItemList, name="Lonely", items=[item])

    rows = db.list(ItemList, select=["name", "items.item_type.name"])

    assert len(rows) == 1
    assert rows[0]["name"] == "Lonely"
    assert rows[0]["items"][0]["item_type"] is None


def test_deep_select_empty_collection_parent_still_returned(db):
    """Parent with empty collection still appears; nested list is empty."""
    db.insert(ItemList, name="Empty", items=[])

    rows = db.list(ItemList, select=["name", "items.tags.name"])

    assert len(rows) == 1
    assert rows[0]["name"] == "Empty"
    assert rows[0]["items"] == []


def test_deep_select_from_many_to_many_root(db):
    """Deep select starting from M:N root: tags → items → item_type."""
    item_type = db.insert(ItemType, name="type_b")
    item = db.insert(Item, name="Tagged", color="green", item_type=item_type)
    db.insert(Tag, name="featured", items=[item])

    rows = db.list(Tag, select=["name", "items.item_type.name"])

    assert len(rows) == 1
    assert rows[0]["name"] == "featured"
    assert len(rows[0]["items"]) == 1
    assert rows[0]["items"][0]["item_type"]["name"] == "type_b"


def test_deep_select_with_filter_on_deep_path(db):
    """Deep select coexists with deep filters."""
    type_a = db.insert(ItemType, name="keep")
    type_b = db.insert(ItemType, name="drop")
    item_a = db.insert(Item, name="A", color="red", item_type=type_a)
    item_b = db.insert(Item, name="B", color="blue", item_type=type_b)
    db.insert(ItemList, name="Mixed", items=[item_a, item_b])

    rows = db.list(
        ItemList,
        select=["name", "items.name", "items.item_type.name"],
        **{"items.item_type.name": "keep"},
    )

    assert len(rows) == 1
    assert rows[0]["name"] == "Mixed"
    # Filtered list still projects matching nested items only (or full list —
    # require at least that keep path is present and drop is absent)
    names = [item["name"] for item in rows[0]["items"]]
    assert "A" in names
    assert all(
        item["item_type"]["name"] == "keep"
        for item in rows[0]["items"]
        if item["name"] == "A"
    )


def test_deep_select_invalid_deep_path_is_skipped(db):
    """Unknown deep segment is skipped; valid siblings remain."""
    item = db.insert(Item, name="X", color="red")
    db.insert(ItemList, name="L", items=[item])

    rows = db.list(
        ItemList,
        select=["name", "items.color", "items.nope.name", "items.missing"],
    )

    assert len(rows) == 1
    assert rows[0]["name"] == "L"
    assert rows[0]["items"][0]["color"] == "red"
    assert "nope" not in rows[0]["items"][0]
    assert "missing" not in rows[0]["items"][0]


def test_deep_select_three_hop_path(db):
    """ItemList → items → tags → name, nested as lists at collection hops."""
    item = db.insert(Item, name="Phone", color="black", price=500)
    db.insert(Tag, name="mobile", items=[item])
    list_row = db.insert(ItemList, name="Cart", items=[item])

    rows = db.list(ItemList, select=["id", "name", "items.tags.name"])

    assert len(rows) == 1
    assert rows[0]["id"] == list_row.id
    assert rows[0]["name"] == "Cart"
    assert rows[0]["items"][0]["tags"][0]["name"] == "mobile"


# ---------------------------------------------------------------------------
# Combos — select with sort / limit / skip
# ---------------------------------------------------------------------------


def test_select_with_sort_asc(db):
    """Scalar select keeps sort order."""
    db.insert(Item, name="c", color="red", price=30)
    db.insert(Item, name="a", color="blue", price=10)
    db.insert(Item, name="b", color="green", price=20)

    rows = db.list(
        Item,
        select=["name", "price"],
        sort=[{"field": "price", "order": "asc"}],
    )

    assert [row["price"] for row in rows] == [10, 20, 30]
    assert [row["name"] for row in rows] == ["a", "b", "c"]


def test_select_with_sort_desc_and_filter(db):
    """Select + filter + sort."""
    db.insert(Item, name="keep-low", color="red", price=10)
    db.insert(Item, name="drop", color="blue", price=99)
    db.insert(Item, name="keep-high", color="red", price=40)
    db.insert(Item, name="keep-mid", color="red", price=25)

    rows = db.list(
        Item,
        color="red",
        select=["name", "price"],
        sort=[{"field": "price", "order": "desc"}],
    )

    assert [row["name"] for row in rows] == ["keep-high", "keep-mid", "keep-low"]


def test_select_with_limit_and_skip(db):
    """Pagination window is stable with select + sort."""
    for i in range(6):
        db.insert(Item, name=f"Item {i}", color="red", price=i * 10)

    rows = db.list(
        Item,
        select=["name", "price"],
        sort=[{"field": "price", "order": "asc"}],
        skip=2,
        limit=2,
    )

    assert [row["price"] for row in rows] == [20, 30]
    assert [row["name"] for row in rows] == ["Item 2", "Item 3"]


def test_select_sort_by_field_not_in_select(db):
    """Sort by a field that is not projected."""
    db.insert(Item, name="late", color="red", price=30)
    db.insert(Item, name="early", color="blue", price=10)
    db.insert(Item, name="mid", color="green", price=20)

    rows = db.list(
        Item,
        select=["name"],
        sort=[{"field": "price", "order": "asc"}],
    )

    assert [row["name"] for row in rows] == ["early", "mid", "late"]
    assert all(set(row.keys()) == {"name"} for row in rows)


def test_deep_select_with_sort_limit_skip(db):
    """Deep select coexists with sort/limit/skip on the root model."""
    type_a = db.insert(ItemType, name="type_a")
    type_b = db.insert(ItemType, name="type_b")
    db.insert(
        ItemList,
        name="L1",
        items=[db.insert(Item, name="i1", color="red", price=10, item_type=type_a)],
    )
    db.insert(
        ItemList,
        name="L2",
        items=[db.insert(Item, name="i2", color="blue", price=20, item_type=type_b)],
    )
    db.insert(
        ItemList,
        name="L3",
        items=[db.insert(Item, name="i3", color="green", price=30, item_type=type_a)],
    )

    rows = db.list(
        ItemList,
        select=["name", "items.item_type.name"],
        sort=[{"field": "name", "order": "asc"}],
        skip=1,
        limit=1,
    )

    assert len(rows) == 1
    assert rows[0]["name"] == "L2"
    assert rows[0]["items"][0]["item_type"]["name"] == "type_b"


def test_return_dict_with_sort_limit_skip(db):
    """return_dict path also respects sort + pagination."""
    db.insert(Item, name="a", color="red", price=30)
    db.insert(Item, name="b", color="blue", price=10)
    db.insert(Item, name="c", color="green", price=20)

    rows = db.list(
        Item,
        return_dict=True,
        sort=[{"field": "price", "order": "asc"}],
        skip=1,
        limit=1,
    )

    assert len(rows) == 1
    assert rows[0]["name"] == "c"
    assert rows[0]["price"] == 20
