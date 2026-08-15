"""Tests for preload functionality in MemoryAdapter."""

from src.crudle.adapters.memory.adapter import NotLoaded

from .models import Item, ItemList, ItemType, Tag


class TestPreload:
    """Test preload functionality."""

    def test_relationships_default_to_notloaded(self, db):
        """Test that relationships default to NotLoaded."""
        # Create test data
        db.insert(ItemList, name="Test List")
        db.insert(ItemType, name="Test Type")

        # Create item without explicit relationships
        item = db.insert(Item, name="Test Item", color="red")

        # Check that relationships are NotLoaded
        assert isinstance(item.item_list, NotLoaded)
        assert isinstance(item.item_type, NotLoaded)
        assert isinstance(item.tags, NotLoaded)

        # Check that foreign keys are set
        assert item.item_list_id is None
        assert item.item_type_id is None

    def test_preload_one_to_one_relationship(self, db):
        """Test preloading one-to-one relationships."""
        # Create test data
        item_type = db.insert(ItemType, name="Test Type")
        item = db.insert(Item, name="Test Item", color="red", item_type_id=item_type.id)

        # Get item without preload
        item_no_preload = db.get(Item, item.id)
        assert isinstance(item_no_preload.item_type, NotLoaded)

        # Get item with preload
        item_with_preload = db.get(Item, item.id, preload=["item_type"])
        assert item_with_preload.item_type is not None
        assert item_with_preload.item_type.id == item_type.id
        assert item_with_preload.item_type.name == "Test Type"

    def test_preload_one_to_many_relationship(self, db):
        """Test preloading one-to-many relationships."""
        # Create test data
        item_list = db.insert(ItemList, name="Test List")
        db.insert(Item, name="Item 1", color="red", item_list_id=item_list.id)
        db.insert(Item, name="Item 2", color="blue", item_list_id=item_list.id)

        # Get item_list without preload
        list_no_preload = db.get(ItemList, item_list.id)
        assert isinstance(list_no_preload.items, NotLoaded)

        # Get item_list with preload
        list_with_preload = db.get(ItemList, item_list.id, preload=["items"])
        assert isinstance(list_with_preload.items, list)
        assert len(list_with_preload.items) == 2
        assert list_with_preload.items[0].name in ["Item 1", "Item 2"]
        assert list_with_preload.items[1].name in ["Item 1", "Item 2"]

    def test_preload_multiple_relationships(self, db):
        """Test preloading multiple relationships at once."""
        # Create test data
        item_type = db.insert(ItemType, name="Test Type")
        item_list = db.insert(ItemList, name="Test List")
        db.insert(Tag, name="tag1")
        db.insert(Tag, name="tag2")

        item = db.insert(
            Item,
            name="Test Item",
            color="red",
            item_type_id=item_type.id,
            item_list_id=item_list.id,
        )

        # Add tags to item (this would be done through a many-to-many relationship)
        # For now, we'll just test the one-to-one relationships

        # Get item with multiple preloads
        item_with_preload = db.get(Item, item.id, preload=["item_type", "item_list"])

        assert item_with_preload.item_type is not None
        assert item_with_preload.item_type.name == "Test Type"
        assert item_with_preload.item_list is not None
        assert item_with_preload.item_list.name == "Test List"

    def test_preload_with_list(self, db):
        """Test preloading relationships when using list method."""
        # Create test data
        item_type = db.insert(ItemType, name="Test Type")
        db.insert(Item, name="Item 1", color="red", item_type_id=item_type.id)
        db.insert(Item, name="Item 2", color="blue", item_type_id=item_type.id)

        # List items without preload
        items_no_preload = db.list(Item)
        for item in items_no_preload:
            assert isinstance(item.item_type, NotLoaded)

        # List items with preload
        items_with_preload = db.list(Item, preload=["item_type"])
        for item in items_with_preload:
            assert item.item_type is not None
            assert item.item_type.name == "Test Type"

    def test_preload_with_get_by(self, db):
        """Test preloading relationships when using get_by method."""
        # Create test data
        item_type = db.insert(ItemType, name="Test Type")
        db.insert(Item, name="Test Item", color="red", item_type_id=item_type.id)

        # Get by without preload
        item_no_preload = db.get_by(Item, name="Test Item")
        assert isinstance(item_no_preload.item_type, NotLoaded)

        # Get by with preload
        item_with_preload = db.get_by(Item, preload=["item_type"], name="Test Item")
        assert item_with_preload.item_type is not None
        assert item_with_preload.item_type.name == "Test Type"

    def test_preload_invalid_relationship(self, db):
        """Test that preloading invalid relationships is ignored."""
        item = db.insert(Item, name="Test Item", color="red")

        # Try to preload invalid relationship
        item_with_invalid = db.get(Item, item.id, preload=["invalid_relationship"])

        # Should not raise error, just ignore invalid relationship
        assert isinstance(item_with_invalid.item_type, NotLoaded)

    def test_notloaded_behavior(self):
        """Test NotLoaded object behavior."""
        not_loaded = NotLoaded()

        # Test string representation
        assert str(not_loaded) == "NotLoaded"
        assert repr(not_loaded) == "NotLoaded"

        # Test boolean behavior
        assert not not_loaded
        assert bool(not_loaded) is False

        # Test equality
        assert not_loaded == NotLoaded()
        assert not_loaded != "something else"
        assert not_loaded != None

    def test_preload_with_nested_relationships(self, db):
        """Test preloading nested relationships (future feature)."""
        # This test is for future nested relationship support
        # For now, we'll just test that it doesn't break
        item_type = db.insert(ItemType, name="Test Type")
        item = db.insert(Item, name="Test Item", color="red", item_type_id=item_type.id)

        # Try to preload nested relationship (should be ignored for now)
        item_with_nested = db.get(Item, item.id, preload=["item_type.name"])

        # Should still work, just ignore the nested part
        assert item_with_nested is not None
