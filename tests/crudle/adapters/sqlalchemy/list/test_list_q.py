"""List filters: text-search operator (`q`) — SQLAlchemy / Postgres FTS.

Requires Postgres. Opt in with:

    CRUDLE_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/postgres \\
      pytest -m postgres

Without the env var, these tests are skipped.

SQLAlchemy contract: Postgres `to_tsvector` / `to_tsquery` via `unaccent_simple`
(bootstrapped by the postgres fixture). Not the same as Memory substring search.
"""

from contextlib import contextmanager

import pytest

from tests.models import Item, ItemList, ItemType, Tag

pytestmark = pytest.mark.postgres


@contextmanager
def search_fields(*fields: str):
    previous = getattr(Item.Queries, "search_fields", None)
    Item.Queries.search_fields = list(fields)
    try:
        yield
    finally:
        if previous is None:
            if hasattr(Item.Queries, "search_fields"):
                delattr(Item.Queries, "search_fields")
        else:
            Item.Queries.search_fields = previous


# ---------------------------------------------------------------------------
# Matches — field __q and bare search / q
# ---------------------------------------------------------------------------


class TestListQMatches:
    def test_field_q_token(self, postgres_db):
        item1 = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Samsung Galaxy", color="blue", price=20)

        items = Item.list(postgres_db, name__q="Apple")

        assert set(items) == {item1}

    def test_prefix_match(self, postgres_db):
        """tsquery uses word:* — Appl finds Apple."""
        item1 = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Samsung Galaxy", color="blue", price=20)

        assert Item.list(postgres_db, name__q="Appl") == [item1]

    def test_multi_word_and(self, postgres_db):
        item1 = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Apple MacBook", color="blue", price=20)
        Item.insert(postgres_db, name="iPhone case", color="green", price=30)

        assert Item.list(postgres_db, name__q="Apple iPhone") == [item1]

    def test_case_insensitive(self, postgres_db):
        item1 = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)

        assert Item.list(postgres_db, name__q="apple") == [item1]
        assert Item.list(postgres_db, name__q="APPLE") == [item1]

    def test_bare_search_over_search_fields(self, postgres_db):
        item1 = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Samsung Galaxy", color="blue", price=20)

        with search_fields("name"):
            assert Item.list(postgres_db, search="Apple") == [item1]

    def test_bare_q_alias_over_search_fields(self, postgres_db):
        item1 = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)

        with search_fields("name"):
            assert Item.list(postgres_db, q="Apple") == [item1]

    def test_search_fields_or_across_columns(self, postgres_db):
        Item.insert(postgres_db, name="Widget", color="blue", price=10)
        item_color = Item.insert(
            postgres_db, name="Gadget", color="crimson apple", price=20
        )
        item_name = Item.insert(
            postgres_db, name="Apple pie", color="green", price=30
        )

        with search_fields("name", "color"):
            results = set(Item.list(postgres_db, search="Apple"))
            assert results == {item_name, item_color}

    def test_multiple_filters_anded(self, postgres_db):
        item1 = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Apple MacBook", color="blue", price=20)

        assert Item.list(postgres_db, name__q="Apple", color="red") == [item1]


# ---------------------------------------------------------------------------
# Misses
# ---------------------------------------------------------------------------


class TestListQMisses:
    def test_no_token_hit(self, postgres_db):
        Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)

        assert Item.list(postgres_db, name__q="Nokia") == []

    def test_empty_search_with_search_fields_is_noop(self, postgres_db):
        item1 = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        item2 = Item.insert(postgres_db, name="Samsung", color="blue", price=20)

        with search_fields("name"):
            # filter_search returns query unchanged when value is falsy
            assert set(Item.list(postgres_db, search="")) == {item1, item2}

    def test_empty_search_fields_is_noop(self, postgres_db):
        item1 = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)

        with search_fields():
            assert set(Item.list(postgres_db, search="Apple")) == {item1}

    def test_partial_and_does_not_match(self, postgres_db):
        Item.insert(postgres_db, name="Apple iPhone", color="blue", price=10)

        assert Item.list(postgres_db, name__q="Apple", color="red") == []


# ---------------------------------------------------------------------------
# Spellings — nested forms
# ---------------------------------------------------------------------------


class TestListQSpellings:
    def test_nested_dotted_path(self, postgres_db):
        item_apple = Item.insert(postgres_db, name="Apple iPhone", color="red")
        item_samsung = Item.insert(postgres_db, name="Samsung Galaxy", color="blue")
        list1 = ItemList.insert(
            postgres_db, name="List 1", items=[item_apple, item_samsung]
        )
        ItemList.insert(postgres_db, name="List 2", items=[item_samsung])

        lists = ItemList.list(postgres_db, **{"items.name__q": "Apple"})

        assert lists == [list1]

    def test_nested_dict_filter(self, postgres_db):
        item_apple = Item.insert(postgres_db, name="Apple iPhone", color="red")
        item_samsung = Item.insert(postgres_db, name="Samsung Galaxy", color="blue")
        list1 = ItemList.insert(
            postgres_db, name="List 1", items=[item_apple, item_samsung]
        )
        ItemList.insert(postgres_db, name="List 2", items=[item_samsung])

        lists = ItemList.list(postgres_db, filter={"items": {"name__q": "Apple"}})

        assert lists == [list1]

    def test_nested_deep_dotted_path(self, postgres_db):
        item1 = Item.insert(postgres_db, name="Item 1", color="red")
        item2 = Item.insert(postgres_db, name="Item 2", color="blue")
        list1 = ItemList.insert(postgres_db, name="List 1", items=[item1])
        ItemList.insert(postgres_db, name="List 2", items=[item2])
        Tag.insert(postgres_db, name="python tips", items=[item1])
        Tag.insert(postgres_db, name="rust notes", items=[item2])

        lists = ItemList.list(postgres_db, **{"items.tags.name__q": "python"})

        assert lists == [list1]

    def test_belongs_to_relationship(self, postgres_db):
        electronics = ItemType.insert(postgres_db, name="Consumer Electronics")
        clothing = ItemType.insert(postgres_db, name="Clothing")
        phone = Item.insert(
            postgres_db, name="Phone", color="red", item_type=electronics
        )
        Item.insert(postgres_db, name="Shirt", color="blue", item_type=clothing)

        items = Item.list(postgres_db, **{"item_type.name__q": "Electro"})

        assert items == [phone]


# ---------------------------------------------------------------------------
# Value shapes / FTS-specific
# ---------------------------------------------------------------------------


class TestListQValueShapes:
    def test_unaccent_dictionary(self, postgres_db):
        """unaccent_simple: query without accent matches accented stored text."""
        item1 = Item.insert(postgres_db, name="café latte", color="red", price=10)
        Item.insert(postgres_db, name="tea", color="blue", price=20)

        assert Item.list(postgres_db, name__q="cafe") == [item1]

    def test_null_column_does_not_match(self, postgres_db):
        item1 = Item.insert(postgres_db, name="Apple", color="red", price=10)
        Item.insert(postgres_db, name=None, color="blue", price=20)

        assert Item.list(postgres_db, name__q="Apple") == [item1]

    def test_punctuation_sanitized_still_finds_token(self, postgres_db):
        item1 = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)

        assert Item.list(postgres_db, name__q="Apple!") == [item1]

    def test_empty_string_field(self, postgres_db):
        Item.insert(postgres_db, name="", color="red", price=10)
        item_named = Item.insert(postgres_db, name="Apple", color="blue", price=20)

        assert Item.list(postgres_db, name__q="Apple") == [item_named]
