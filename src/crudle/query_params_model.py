# query_params.py

from datetime import date, datetime
from pydantic import BaseModel
from typing import (
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
)
from uuid import UUID


class QueryParamsModel(BaseModel):
    suffixes: ClassVar[Dict[str, List[Type]]] = {
        "eq": [int, float, str, date, datetime, UUID, list],
        "ne": [int, float, str, date, datetime, UUID, list],
        "gt": [int, float, date, datetime],
        "ge": [int, float, date, datetime],
        "lt": [int, float, date, datetime],
        "le": [int, float, date, datetime],
        "in": [int, float, str, date, datetime, UUID],
        "ni": [int, float, str, date, datetime, UUID],
        "q": [str],
    }

    ignored_keys: ClassVar[List[str]] = ["q", "search"]

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.add_suffix_fields()

    @classmethod
    def add_suffix_fields(cls):
        annotations_copy = list(cls.__annotations__.items())
        for attr_name, attr_type in annotations_copy:
            # Skip ignored keys
            if attr_name in cls.ignored_keys:
                continue

            # Extract types, even if they are wrapped in Optional or Union
            attr_types = cls._get_attr_types(attr_type)

            # Process each type and add suffix fields if applicable
            for atype in attr_types:
                cls._process_type(attr_name, atype)

    @classmethod
    def _get_attr_types(cls, attr_type):
        """Extract types, even if they are wrapped in Optional or Union."""
        origin = get_origin(attr_type)
        if origin is Union:
            attr_types = get_args(attr_type)
            return [t for t in attr_types if t is not type(None)]  # Remove NoneType
        return [attr_type]

    @classmethod
    def _process_type(cls, attr_name, atype):
        """Process each type and add suffix fields if applicable."""
        if get_origin(atype) is list:
            element_type = get_args(atype)[0]
            cls._add_suffix_fields_for_list(attr_name, element_type)
        elif isinstance(atype, type) and issubclass(atype, BaseModel):
            # Skip nested models
            return
        else:
            cls._add_suffix_fields_for_type(attr_name, atype)

    @classmethod
    def _add_suffix_fields_for_list(cls, attr_name, element_type):
        """Add suffix fields for list types."""
        for suffix, types in cls.suffixes.items():
            if list in types:
                cls.add_suffix_field(attr_name, List[element_type], suffix)

    @classmethod
    def _add_suffix_fields_for_type(cls, attr_name, atype):
        """Add suffix fields for non-list types."""
        for suffix, types in cls.suffixes.items():
            if atype in types:
                cls.add_suffix_field(attr_name, atype, suffix)

    @classmethod
    def add_suffix_field(cls, attr_name, attr_type, suffix):
        """Add a suffix field to the class annotations."""
        if suffix in ["in", "ni"]:
            cls.__annotations__[f"{attr_name}__{suffix}"] = Optional[List[attr_type]]
        else:
            cls.__annotations__[f"{attr_name}__{suffix}"] = Optional[attr_type]
        setattr(cls, f"{attr_name}__{suffix}", None)
