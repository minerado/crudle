"""
Pydantic models for memory adapter testing.
These models mirror the SQLAlchemy models but use Pydantic for validation.
"""

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class ItemType(BaseModel):
    """Item type model - one-to-one with Item."""

    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=50)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Tag(BaseModel):
    """Tag model - many-to-many with Item."""

    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=50)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    items: List["Item"] = []  # Many-to-many


class Item(BaseModel):
    """Item model - main entity with various relationships."""

    id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=100)
    price: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Foreign key references
    item_list_id: Optional[int] = None
    item_type_id: Optional[int] = None

    # Relationships
    item_list: Optional["ItemList"] = None  # Many-to-one
    item_type: Optional[ItemType] = None  # One-to-one
    tags: List[Tag] = []  # Many-to-many


class ItemList(BaseModel):
    """Item list model - one-to-many with Item."""

    id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=100)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    items: List[Item] = []  # One-to-many


class ItemTag(BaseModel):
    """Association model for many-to-many relationship between Item and Tag."""

    id: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Foreign key references
    item_id: Optional[int] = None
    tag_id: Optional[int] = None

    # Relationships
    item: Optional[Item] = None
    tag: Optional[Tag] = None


# Update forward references
Item.model_rebuild()
ItemList.model_rebuild()
Tag.model_rebuild()
ItemTag.model_rebuild()
