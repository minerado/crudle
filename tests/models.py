from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.crudle import SQLAlchemyAdapter
from tests.conftest import Base


# Define the models
class Item(Base, SQLAlchemyAdapter):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    color = Column(String(100))
    price = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Foreign key to link items to item lists
    item_list_id = Column(Integer, ForeignKey("item_lists.id"))

    # Foreign key to link items to item types
    item_type_id = Column(Integer, ForeignKey("item_types.id"))

    # Relationship back to the item list
    item_list = relationship("ItemList", back_populates="items")

    # Many-to-many relationship with tags
    tags = relationship("Tag", secondary="item_tags", back_populates="items")

    # Direct relationship to item_tags (for the association table)
    item_tags = relationship("ItemTag", back_populates="item", overlaps="tags")

    # One-to-one relationship: one Item has one ItemType
    item_type = relationship("ItemType", back_populates="item")

    class Queries:
        def filter_is_expensive(self, query, value):
            if value:
                return query.filter(Item.price > 10)

            if value is False:
                return query.filter(Item.price <= 10)

            return query


class ItemList(Base, SQLAlchemyAdapter):
    __tablename__ = "item_lists"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    # One-to-many relationship: one ItemList has many Items
    items = relationship("Item", back_populates="item_list")


class ItemTag(Base, SQLAlchemyAdapter):
    __tablename__ = "item_tags"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    item_id = Column(Integer, ForeignKey("items.id"))
    tag_id = Column(Integer, ForeignKey("tags.id"))

    # Direct relationship to item (for the association table)
    item = relationship("Item", back_populates="item_tags", overlaps="tags")

    # Direct relationship to tag (for the association table)
    tag = relationship("Tag", back_populates="item_tags", overlaps="items,tags")


class Tag(Base, SQLAlchemyAdapter):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Many-to-many relationship with items
    items = relationship(
        "Item", secondary="item_tags", back_populates="tags", overlaps="item,item_tags"
    )

    # Direct relationship to item_tags (for the association table)
    item_tags = relationship("ItemTag", back_populates="tag", overlaps="items,tags")


class ItemType(Base, SQLAlchemyAdapter):
    __tablename__ = "item_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # One-to-one relationship: one ItemType has one Item
    item = relationship("Item", back_populates="item_type", uselist=False)
