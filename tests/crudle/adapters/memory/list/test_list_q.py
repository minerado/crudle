"""List filters: text-search operator (`q`) — Memory adapter.

Memory contract: case-insensitive substring match on the field value
(str(value).lower() contains needle.lower()). This is intentionally NOT
Postgres FTS — see README Memory-only differences.

High-level sections:

- Matches — substring finds expected rows
- Misses — correctly returns no rows
- Spellings — field__q, nested path / nested dict
- Value shapes — None, empty string, numbers, unicode, etc.
"""

from datetime import datetime, timezone

from tests.crudle.adapters.memory.models import Item, ItemList, ItemType, Tag


def _ids(rows):
    return {row.id for row in rows}


# ---------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------


class TestListQMatches:
    def test_single_token_substring(self, db):
        item1 = db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Samsung Galaxy", color="blue", price=20)
        db.insert(Item, name="Google Pixel", color="green", price=30)

        items = db.list(Item, name__q="Apple")

        assert _ids(items) == {item1.id}

    def test_case_insensitive(self, db):
        item1 = db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Samsung Galaxy", color="blue", price=20)

        assert _ids(db.list(Item, name__q="apple")) == {item1.id}
        assert _ids(db.list(Item, name__q="APPLE")) == {item1.id}

    def test_mid_string_partial(self, db):
        item1 = db.insert(Item, name="Apple iPhone", color="red", price=10)
        item2 = db.insert(Item, name="Google Pixel Phone", color="green", price=30)
        db.insert(Item, name="Samsung Galaxy", color="blue", price=20)

        assert _ids(db.list(Item, name__q="Phone")) == {item1.id, item2.id}

    def test_multi_word_as_whole_substring(self, db):
        """Memory matches the entire needle as one substring, not FTS tokens."""
        item1 = db.insert(Item, name="Apple iPhone 13", color="red", price=10)
        db.insert(Item, name="Apple MacBook", color="blue", price=20)
        db.insert(Item, name="iPhone case", color="green", price=30)

        assert _ids(db.list(Item, name__q="Apple iPhone")) == {item1.id}

    def test_multiple_fields_anded(self, db):
        item1 = db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Apple MacBook", color="blue", price=20)
        db.insert(Item, name="Samsung Galaxy", color="red", price=30)

        items = db.list(Item, name__q="Apple", color="red")

        assert _ids(items) == {item1.id}


# ---------------------------------------------------------------------------
# Misses
# ---------------------------------------------------------------------------


class TestListQMisses:
    def test_no_substring_hit(self, db):
        db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Samsung Galaxy", color="blue", price=20)

        assert db.list(Item, name__q="Nokia") == []

    def test_empty_search_term(self, db):
        """Empty needle is a substring of every non-null string."""
        item1 = db.insert(Item, name="Apple", color="red", price=10)
        item2 = db.insert(Item, name="Samsung", color="blue", price=20)

        assert _ids(db.list(Item, name__q="")) == {item1.id, item2.id}

    def test_whitespace_only_search_term(self, db):
        item1 = db.insert(Item, name="Apple iPhone", color="red", price=10)
        db.insert(Item, name="Samsung", color="blue", price=20)

        # needle is spaces; only values containing those spaces match
        assert _ids(db.list(Item, name__q=" ")) == {item1.id}

    def test_partial_and_does_not_match(self, db):
        db.insert(Item, name="Apple iPhone", color="blue", price=10)

        assert db.list(Item, name__q="Apple", color="red") == []


# ---------------------------------------------------------------------------
# Spellings
# ---------------------------------------------------------------------------


class TestListQSpellings:
    def test_nested_dotted_path(self, db):
        item_apple = db.insert(Item, name="Apple iPhone", color="red")
        item_samsung = db.insert(Item, name="Samsung Galaxy", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item_apple, item_samsung])
        db.insert(ItemList, name="List 2", items=[item_samsung])

        lists = db.list(ItemList, **{"items.name__q": "Apple"})

        assert _ids(lists) == {list1.id}

    def test_nested_dict_filter(self, db):
        item_apple = db.insert(Item, name="Apple iPhone", color="red")
        item_samsung = db.insert(Item, name="Samsung Galaxy", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item_apple, item_samsung])
        db.insert(ItemList, name="List 2", items=[item_samsung])

        lists = db.list(ItemList, filter={"items": {"name__q": "Apple"}})

        assert _ids(lists) == {list1.id}

    def test_nested_deep_dotted_path(self, db):
        item1 = db.insert(Item, name="Item 1", color="red")
        item2 = db.insert(Item, name="Item 2", color="blue")
        list1 = db.insert(ItemList, name="List 1", items=[item1])
        db.insert(ItemList, name="List 2", items=[item2])
        db.insert(Tag, name="python-tips", items=[item1])
        db.insert(Tag, name="rust-notes", items=[item2])

        lists = db.list(ItemList, **{"items.tags.name__q": "python"})

        assert _ids(lists) == {list1.id}

    def test_belongs_to_relationship(self, db):
        electronics = db.insert(ItemType, name="Consumer Electronics")
        clothing = db.insert(ItemType, name="Clothing")
        phone = db.insert(Item, name="Phone", color="red", item_type=electronics)
        db.insert(Item, name="Shirt", color="blue", item_type=clothing)

        items = db.list(Item, **{"item_type.name__q": "Electro"})

        assert _ids(items) == {phone.id}

    def test_bare_search_is_not_a_memory_feature(self, db):
        """Memory has no Queries.search_fields / bare search= multi-field FTS."""
        db.insert(Item, name="Apple iPhone", color="red", price=10)

        # treated as unknown bare field eq on attribute "search" → no match / ignored path
        assert db.list(Item, search="Apple") == []


# ---------------------------------------------------------------------------
# Value shapes
# ---------------------------------------------------------------------------


class TestListQValueShapes:
    def test_null_column_excluded(self, db):
        item_named = db.insert(Item, name="Apple", color="red", price=10)
        db.insert(Item, name=None, color="blue", price=20)

        assert _ids(db.list(Item, name__q="Apple")) == {item_named.id}

    def test_empty_string_field(self, db):
        item_empty = db.insert(Item, name="", color="red", price=10)
        item_named = db.insert(Item, name="Apple", color="blue", price=20)

        assert _ids(db.list(Item, name__q="")) == {item_empty.id, item_named.id}
        assert _ids(db.list(Item, name__q="Apple")) == {item_named.id}

    def test_integer_field_via_str(self, db):
        item1 = db.insert(Item, name="A", color="red", price=100)
        item2 = db.insert(Item, name="B", color="blue", price=200)

        assert _ids(db.list(Item, price__q="10")) == {item1.id}
        assert item2.id not in _ids(db.list(Item, price__q="10"))

    def test_datetime_via_str(self, db):
        moment = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        other = datetime(2024, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        item1 = db.insert(Item, name="A", color="red", created_at=moment)
        db.insert(Item, name="B", color="blue", created_at=other)

        assert _ids(db.list(Item, created_at__q="2024-01-15")) == {item1.id}

    def test_special_characters_in_needle(self, db):
        item1 = db.insert(Item, name="C++ Primer", color="red", price=10)
        db.insert(Item, name="Java Guide", color="blue", price=20)

        assert _ids(db.list(Item, name__q="C++")) == {item1.id}

    def test_unicode_no_unaccent(self, db):
        """Memory does not unaccent — cafe does not match café."""
        item_accent = db.insert(Item, name="café latte", color="red", price=10)
        db.insert(Item, name="tea", color="blue", price=20)

        assert _ids(db.list(Item, name__q="café")) == {item_accent.id}
        assert db.list(Item, name__q="cafe") == []
