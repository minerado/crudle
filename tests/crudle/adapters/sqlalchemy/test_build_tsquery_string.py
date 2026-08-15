"""Unit stress tests for SQLAlchemy build_tsquery_string (no database required)."""

from crudle.adapters.sqlalchemy.helpers import build_tsquery_string


class TestBuildTsqueryString:
    def test_single_word(self):
        assert build_tsquery_string("Apple") == "Apple:*"

    def test_multi_word_anded_with_prefix(self):
        assert build_tsquery_string("John Doe") == "John:* & Doe:*"

    def test_trims_via_split_collapses_whitespace(self):
        assert build_tsquery_string("  John   Doe  ") == "John:* & Doe:*"

    def test_strips_special_characters(self):
        assert build_tsquery_string("Apple-iPhone!") == "AppleiPhone:*"

    def test_escapes_single_quotes_then_sanitizes(self):
        # quotes duplicated first, then non-word chars stripped → apostrophe gone
        assert build_tsquery_string("O'Brien") == "OBrien:*"

    def test_empty_string(self):
        assert build_tsquery_string("") == ""

    def test_whitespace_only(self):
        assert build_tsquery_string("   ") == ""

    def test_unicode_word_characters_kept(self):
        assert build_tsquery_string("café") == "café:*"

    def test_multiple_tokens_after_sanitize(self):
        assert build_tsquery_string("foo, bar; baz") == "foo:* & bar:* & baz:*"
