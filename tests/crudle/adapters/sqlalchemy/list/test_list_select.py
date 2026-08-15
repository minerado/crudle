"""List field selection (`select`) and `return_dict`.

Default `list` returns ORM entities. Non-empty `select` or `return_dict=True`
switches the return shape to dictionaries.

SQLAlchemy contract for collection relationships (1:N / M:N): selecting a
relationship uses a join, so parent rows multiply (one dict per related row).
Nested relationship data is a single object (or None), not an aggregated list.
Memory aggregates nested collections into lists — do not treat those as twins.

Deep select supports multi-hop paths (e.g. ``items.item_type.name``) via
deduplicated outer joins in a single query; see the Deep select section.
"""

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
# Deep select (multi-hop)
#
# SQLAlchemy shape: join-row multiplication; each hop nests as a single object
# (or None), never an aggregated list. Same idea as one-hop collection select.
# ---------------------------------------------------------------------------


def test_deep_select_two_hop_to_one(db):
    """Two-hop path through 1:N then 1:1 nests as items.item_type."""
    item_type = ItemType.insert(db, name="electronics")
    item = Item.insert(db, name="Laptop", color="silver", item_type=item_type)
    ItemList.insert(db, name="Wishlist", items=[item])

    rows = ItemList.list(db, select=["name", "items.item_type.name"])

    assert len(rows) == 1
    assert rows[0]["name"] == "Wishlist"
    assert rows[0]["items"]["item_type"]["name"] == "electronics"
    # No flat / partially nested leftovers
    assert "items_item_type_name" not in rows[0]
    assert "item_type" not in rows[0]


def test_deep_select_two_hop_collection_multiplies_rows(db):
    """1:N then M:N multiplies parent × item × tag; each row is one leaf."""
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    Tag.insert(db, name="expensive", items=[item1])
    Tag.insert(db, name="sale", items=[item1])
    Tag.insert(db, name="cheap", items=[item2])
    ItemList.insert(db, name="List 1", items=[item1, item2])

    rows = ItemList.list(db, select=["name", "items.id", "items.tags.name"])

    assert len(rows) == 3  # item1×2 tags + item2×1 tag

    triples = {
        (row["name"], row["items"]["id"], row["items"]["tags"]["name"]) for row in rows
    }
    assert triples == {
        ("List 1", item1.id, "expensive"),
        ("List 1", item1.id, "sale"),
        ("List 1", item2.id, "cheap"),
    }


def test_deep_select_merges_sibling_fields_on_same_path(db):
    """Shallow and deep fields on the same relationship merge into one tree."""
    item_type = ItemType.insert(db, name="type_a")
    item = Item.insert(db, name="Gadget", color="red", price=99, item_type=item_type)
    ItemList.insert(db, name="Box", items=[item])

    rows = ItemList.list(
        db,
        select=["name", "items.name", "items.color", "items.item_type.name"],
    )

    assert len(rows) == 1
    nested = rows[0]["items"]
    assert nested["name"] == "Gadget"
    assert nested["color"] == "red"
    assert nested["item_type"]["name"] == "type_a"


def test_deep_select_missing_intermediate_is_none(db):
    """Missing hop yields None at that nesting level (outer join semantics)."""
    item = Item.insert(db, name="Orphan", color="grey")  # no item_type
    ItemList.insert(db, name="Lonely", items=[item])

    rows = ItemList.list(db, select=["name", "items.item_type.name"])

    assert len(rows) == 1
    assert rows[0]["name"] == "Lonely"
    assert rows[0]["items"]["item_type"] is None


def test_deep_select_empty_collection_parent_still_returned(db):
    """Parent with empty collection still appears; deep path is None."""
    ItemList.insert(db, name="Empty", items=[])

    rows = ItemList.list(db, select=["name", "items.tags.name"])

    assert len(rows) == 1
    assert rows[0]["name"] == "Empty"
    assert rows[0]["items"] is None


def test_deep_select_from_many_to_many_root(db):
    """Deep select starting from M:N root: tags → items → item_type."""
    item_type = ItemType.insert(db, name="type_b")
    item = Item.insert(db, name="Tagged", color="green", item_type=item_type)
    Tag.insert(db, name="featured", items=[item])

    rows = Tag.list(db, select=["name", "items.item_type.name"])

    assert len(rows) == 1
    assert rows[0]["name"] == "featured"
    assert rows[0]["items"]["item_type"]["name"] == "type_b"


def test_deep_select_with_filter_on_deep_path(db):
    """Deep select coexists with deep filters (filters already work)."""
    type_a = ItemType.insert(db, name="keep")
    type_b = ItemType.insert(db, name="drop")
    item_a = Item.insert(db, name="A", color="red", item_type=type_a)
    item_b = Item.insert(db, name="B", color="blue", item_type=type_b)
    ItemList.insert(db, name="Mixed", items=[item_a, item_b])

    rows = ItemList.list(
        db,
        select=["name", "items.name", "items.item_type.name"],
        **{"items.item_type.name": "keep"},
    )

    # Filter may still join-multiply; every returned row should be the keep path
    assert len(rows) >= 1
    assert all(row["items"]["item_type"]["name"] == "keep" for row in rows)
    assert all(row["items"]["name"] == "A" for row in rows)


def test_deep_select_invalid_deep_path_is_skipped(db):
    """Unknown deep segment is skipped; valid siblings remain."""
    item = Item.insert(db, name="X", color="red")
    ItemList.insert(db, name="L", items=[item])

    rows = ItemList.list(
        db,
        select=["name", "items.color", "items.nope.name", "items.missing"],
    )

    assert len(rows) == 1
    assert rows[0]["name"] == "L"
    assert rows[0]["items"]["color"] == "red"
    assert "nope" not in rows[0]["items"]
    assert "missing" not in rows[0]["items"]


def test_deep_select_three_hop_path(db):
    """Three hops: ItemList → items → tags → (scalar on Tag via items.tags.name).

    Same depth as two relationship hops + leaf column; stresses path walking.
    """
    item = Item.insert(db, name="Phone", color="black", price=500)
    Tag.insert(db, name="mobile", items=[item])
    list_row = ItemList.insert(db, name="Cart", items=[item])

    # Also project list id to prove root scalars survive deep projection
    rows = ItemList.list(db, select=["id", "name", "items.tags.name"])

    assert len(rows) == 1
    assert rows[0]["id"] == list_row.id
    assert rows[0]["name"] == "Cart"
    assert rows[0]["items"]["tags"]["name"] == "mobile"


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
# Combos — select with sort / limit / skip / filters (shared SQL pipeline)
# ---------------------------------------------------------------------------


def test_select_with_sort_asc(db):
    """Scalar select keeps sort order from the same query."""
    Item.insert(db, name="c", color="red", price=30)
    Item.insert(db, name="a", color="blue", price=10)
    Item.insert(db, name="b", color="green", price=20)

    rows = Item.list(
        db,
        select=["name", "price"],
        sort=[{"field": "price", "order": "asc"}],
    )

    assert [row["price"] for row in rows] == [10, 20, 30]
    assert [row["name"] for row in rows] == ["a", "b", "c"]


def test_select_with_sort_desc_and_filter(db):
    """Select + filter + sort share one query without dropping order."""
    Item.insert(db, name="keep-low", color="red", price=10)
    Item.insert(db, name="drop", color="blue", price=99)
    Item.insert(db, name="keep-high", color="red", price=40)
    Item.insert(db, name="keep-mid", color="red", price=25)

    rows = Item.list(
        db,
        color="red",
        select=["name", "price"],
        sort=[{"field": "price", "order": "desc"}],
    )

    assert [row["name"] for row in rows] == ["keep-high", "keep-mid", "keep-low"]
    assert all(row["price"] in (10, 25, 40) for row in rows)


def test_select_with_limit(db):
    """Limit applies after select projection columns are set."""
    for i in range(5):
        Item.insert(db, name=f"Item {i}", color="red", price=i * 10)

    rows = Item.list(
        db,
        select=["name", "price"],
        sort=[{"field": "price", "order": "asc"}],
        limit=2,
    )

    assert len(rows) == 2
    assert [row["price"] for row in rows] == [0, 10]


def test_select_with_skip(db):
    """Skip/offset works with select."""
    for i in range(5):
        Item.insert(db, name=f"Item {i}", color="red", price=i * 10)

    rows = Item.list(
        db,
        select=["name", "price"],
        sort=[{"field": "price", "order": "asc"}],
        skip=2,
    )

    assert [row["price"] for row in rows] == [20, 30, 40]


def test_select_with_limit_and_skip(db):
    """Pagination window is stable with select + sort."""
    for i in range(6):
        Item.insert(db, name=f"Item {i}", color="red", price=i * 10)

    rows = Item.list(
        db,
        select=["name", "price"],
        sort=[{"field": "price", "order": "asc"}],
        skip=2,
        limit=2,
    )

    assert [row["price"] for row in rows] == [20, 30]
    assert [row["name"] for row in rows] == ["Item 2", "Item 3"]


def test_select_sort_by_field_not_in_select(db):
    """ORDER BY a column that is not projected must still work."""
    Item.insert(db, name="late", color="red", price=30)
    Item.insert(db, name="early", color="blue", price=10)
    Item.insert(db, name="mid", color="green", price=20)

    rows = Item.list(
        db,
        select=["name"],
        sort=[{"field": "price", "order": "asc"}],
    )

    assert [row["name"] for row in rows] == ["early", "mid", "late"]
    assert all(set(row.keys()) == {"name"} for row in rows)


def test_deep_select_with_sort_limit_skip(db):
    """Deep select coexists with sort/limit/skip on the root model."""
    type_a = ItemType.insert(db, name="type_a")
    type_b = ItemType.insert(db, name="type_b")
    ItemList.insert(
        db,
        name="L1",
        items=[Item.insert(db, name="i1", color="red", price=10, item_type=type_a)],
    )
    ItemList.insert(
        db,
        name="L2",
        items=[Item.insert(db, name="i2", color="blue", price=20, item_type=type_b)],
    )
    ItemList.insert(
        db,
        name="L3",
        items=[Item.insert(db, name="i3", color="green", price=30, item_type=type_a)],
    )

    rows = ItemList.list(
        db,
        select=["name", "items.item_type.name"],
        sort=[{"field": "name", "order": "asc"}],
        skip=1,
        limit=1,
    )

    assert len(rows) == 1
    assert rows[0]["name"] == "L2"
    assert rows[0]["items"]["item_type"]["name"] == "type_b"


def test_select_relationship_with_limit_counts_joined_rows(db):
    """Limit applies to SQL rows after joins (1:N multiplies before limit)."""
    item1 = Item.insert(db, name="Item 1", color="red", price=10)
    item2 = Item.insert(db, name="Item 2", color="blue", price=20)
    ItemList.insert(db, name="List 1", items=[item1, item2])
    ItemList.insert(
        db,
        name="List 2",
        items=[Item.insert(db, name="Item 3", color="green", price=30)],
    )

    rows = ItemList.list(
        db,
        select=["name", "items.id"],
        sort=[{"field": "name", "order": "asc"}],
        limit=2,
    )

    # List 1 alone yields 2 joined rows; limit=2 can be satisfied by List 1 only
    assert len(rows) == 2
    assert all(row["name"] == "List 1" for row in rows)
    assert {row["items"]["id"] for row in rows} == {item1.id, item2.id}


def test_return_dict_with_sort_limit_skip(db):
    """return_dict path also respects sort + pagination."""
    Item.insert(db, name="a", color="red", price=30)
    Item.insert(db, name="b", color="blue", price=10)
    Item.insert(db, name="c", color="green", price=20)

    rows = Item.list(
        db,
        return_dict=True,
        sort=[{"field": "price", "order": "asc"}],
        skip=1,
        limit=1,
    )

    assert len(rows) == 1
    assert rows[0]["name"] == "c"
    assert rows[0]["price"] == 20
    assert "item_list" not in rows[0]
