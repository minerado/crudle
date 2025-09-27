# query_builder.py

from functools import reduce
from sqlalchemy import Select, distinct, or_, select
from sqlalchemy.sql import func
from typing import Any


from ...utils import flatten_dict
from .query_field import SQLAlchemyQueryField


class SQLAlchemyQueryBuilder:
    DEFAULT_QUERY_LIMIT = 25

    def __init__(
        self,
        model,
        search_fields: list[str] = [],
        model_dump_kwargs={"exclude_none": True},
    ):
        self.model = model
        self.base_query = select(model)
        self.custom_filters = self.__custom_filters()
        self.model_dump_kwargs = model_dump_kwargs
        self.search_fields = search_fields

    def build_query(
        self,
        distinct_on: list[str] | bool = True,
        limit: int = DEFAULT_QUERY_LIMIT,
        skip: int = 0,
        sort: list[dict] | None = None,
        select: list = [],
        filter: dict | None = None,
        **kwargs,
    ) -> Select:
        """Builds a query based on a `filters` model.

        If custom filters were declared, it removes them from the `filters`
        dict and apply their custom behaviour.
        """
        # You can either pass a dict with filters or use kwargs
        filters = filter or kwargs or {}

        query = reduce(self.__apply_filter, flatten_dict(filters), self.base_query)
        query = reduce(self.__apply_sort, sort or [], query)
        query = self.__apply_select(query, select)
        query = self.__apply_distinct(query, distinct_on)
        query = self.__apply_limit(query, limit)
        query = self.__apply_offset(query, skip)

        return query

    def filter_search(self, query: Select, value: str) -> Select:
        """
        Applies a search filter to a query.

        It uses the `tsvector` and `tsquery` functions from PostgreSQL to search for a term in a
        field. It also supports multiple fields and nested relationships.

        To use this filter, you must declare the fields you want to search in the `search_fields`
        attribute of the class. It will search for the term in all declared fields.

        Example:
            >>> query = Transactions.list(db, search="John Doe")
        """
        if not value or not self.search_fields:
            return query

        filters = []

        for f in self.search_fields:
            field = SQLAlchemyQueryField(f, self.model, override_operator="q")
            query = field.join_query(query, join_opts={"isouter": True})
            filters.append(field.operation(value))

        return query.filter(or_(*filters))

    def filter_q(self, query: Select, value: str) -> Select:
        """
        Just calls self.filter_search to keep compatibility with the custom filters.
        """
        return self.filter_search(query, value)

    def __apply_distinct(
        self, query: Select, fields: list[str] | bool = True
    ) -> Select:
        if fields is True:
            return query.distinct()

        if not fields:
            return query

        query_fields = []

        for f in fields:
            query_field = SQLAlchemyQueryField(f, self.model)
            query = query_field.join_query(query)
            query_fields.append(query_field.parent_model_field)

        return query.distinct(*query_fields)

    def __apply_filter(self, query: Select, key_value: tuple[str, Any]) -> Select:
        """
        Looks for a custom filter defined in the `self.custom_filters` dict and
        applies it to the query. If the filter is not found, it applies a basic
        operation filter like 'eq', 'gt', 'lt', etc.
        """

        key, value = key_value

        custom_filter = self.custom_filters.get(key)

        if custom_filter:
            return getattr(self, custom_filter)(query, value)

        field = SQLAlchemyQueryField(key, self.model)
        query = field.join_query(query, join_opts={"isouter": True})

        return query.where(field.operation(value))

    def __apply_limit(self, query: Select, limit: int) -> Select:
        return query.limit(limit)

    def __apply_offset(self, query: Select, skip: int) -> Select:
        return query.offset(skip)

    def __apply_select(self, query: Select, fields: list) -> Select:
        """Applies a select to a query"""

        if not fields:
            return query

        query_fields = []

        # Track which fields are relationship fields
        relationship_fields = set()

        for f in fields:
            if f.startswith("count"):
                splitted_field = f.split(".", 1)
                field = splitted_field[1] if len(splitted_field) > 1 else "id"

                # Handle nested relationship fields in count
                if "." in field:
                    parts = field.split(".", 1)
                    rel_name = parts[0]
                    nested_field = parts[1]

                    # Check if the first part is a relationship
                    if hasattr(self.model, rel_name):
                        attr = getattr(self.model, rel_name)
                        if hasattr(attr, "property") and hasattr(
                            attr.property, "mapper"
                        ):
                            # This is a nested relationship field for count
                            relationship_fields.add(rel_name)
                            related_model = attr.property.mapper.class_

                            # Join the relationship if not already joined
                            if rel_name not in [
                                field.split("_")[0]
                                for field in [
                                    str(field)
                                    for field in query_fields
                                    if hasattr(field, "name")
                                ]
                            ]:
                                query = query.join(
                                    getattr(self.model, rel_name), **{"isouter": True}
                                )

                            # Select the specific nested field for count
                            if hasattr(related_model, nested_field):
                                nested_column = getattr(related_model, nested_field)
                                query_fields.append(
                                    func.count(distinct(nested_column)).label(f)
                                )
                            else:
                                # Field doesn't exist in related model, count all records
                                query_fields.append(
                                    func.count(distinct(self.model.id)).label(f)
                                )
                        else:
                            # Not a relationship, count all records
                            query_fields.append(
                                func.count(distinct(self.model.id)).label(f)
                            )
                    else:
                        # Relationship doesn't exist, count all records
                        query_fields.append(
                            func.count(distinct(self.model.id)).label(f)
                        )
                else:
                    # Regular field for count
                    query_field = SQLAlchemyQueryField(field, self.model)
                    query = query_field.join_query(query)
                    query_fields.append(
                        func.count(distinct(query_field.parent_model_field)).label(f)
                    )
            else:
                # Check if this is a nested field (e.g., "items.color")
                if "." in f:
                    parts = f.split(".", 1)
                    rel_name = parts[0]
                    nested_field = parts[1]

                    # Check if the first part is a relationship
                    if hasattr(self.model, rel_name):
                        attr = getattr(self.model, rel_name)
                        if hasattr(attr, "property") and hasattr(
                            attr.property, "mapper"
                        ):
                            # This is a nested relationship field
                            relationship_fields.add(rel_name)
                            related_model = attr.property.mapper.class_

                            # Join the relationship if not already joined
                            if rel_name not in [
                                field.split("_")[0]
                                for field in [
                                    str(field)
                                    for field in query_fields
                                    if hasattr(field, "name")
                                ]
                            ]:
                                query = query.join(
                                    getattr(self.model, rel_name), **{"isouter": True}
                                )

                            # Select only the specific nested field
                            if hasattr(related_model, nested_field):
                                nested_column = getattr(related_model, nested_field)
                                aliased_column = nested_column.label(
                                    f"{rel_name}_{nested_field}"
                                )
                                query_fields.append(aliased_column)
                            else:
                                # Field doesn't exist in related model, skip it
                                continue
                        else:
                            # Not a relationship, skip it
                            continue
                    else:
                        # Relationship doesn't exist, skip it
                        continue
                else:
                    # Direct field (not nested)
                    query_field = SQLAlchemyQueryField(f, self.model)
                    # Check if this is a relationship field
                    if hasattr(self.model, f):
                        attr = getattr(self.model, f)
                        # Check if it's a SQLAlchemy relationship property
                        if hasattr(attr, "property") and hasattr(
                            attr.property, "mapper"
                        ):
                            # This is a relationship field - we need to join and select the related model
                            relationship_fields.add(f)
                            # Manually join the relationship since SQLAlchemyQueryField.join_query won't work for direct relationships
                            related_model = attr.property.mapper.class_
                            query = query.join(
                                getattr(self.model, f), **{"isouter": True}
                            )
                            # Select all columns from the related model with a prefix
                            for column in related_model.__table__.columns:
                                # Add the relationship name as a prefix to avoid column name conflicts
                                aliased_column = column.label(f"{f}_{column.name}")
                                query_fields.append(aliased_column)
                        else:
                            # This is a regular column field
                            query_fields.append(query_field.parent_model_field)
                    else:
                        # Field doesn't exist, skip it
                        continue

        # If we have relationship fields, we need to include main model columns
        # But only include the specific columns that are requested (non-relationship fields)
        if relationship_fields:
            # Get the field names that were already added
            added_fields = set()
            for field in query_fields:
                if hasattr(field, "name"):
                    added_fields.add(field.name)
                elif hasattr(field, "key"):
                    added_fields.add(field.key)

            for f in fields:
                if (
                    not f.startswith("count")
                    and f not in relationship_fields
                    and f not in added_fields
                ):
                    if hasattr(self.model, f):
                        attr = getattr(self.model, f)
                        # Only add if it's not a relationship field
                        if not (
                            hasattr(attr, "property")
                            and hasattr(attr.property, "mapper")
                        ):
                            query_fields.append(getattr(self.model, f))

        for f in query_fields:
            if isinstance(f, SQLAlchemyQueryField):
                query = f.join_query(query)

        # If we have count fields and other fields, we need to group by the other fields
        has_count = any(field.startswith("count") for field in fields)
        has_other_fields = any(not field.startswith("count") for field in fields)

        if has_count and has_other_fields:
            # Add GROUP BY for non-count fields
            group_by_fields = []
            for field in fields:
                if not field.startswith("count"):
                    query_field = SQLAlchemyQueryField(field, self.model)
                    if hasattr(self.model, field):
                        attr = getattr(self.model, field)
                        if not (
                            hasattr(attr, "property")
                            and hasattr(attr.property, "mapper")
                        ):
                            group_by_fields.append(query_field.parent_model_field)

            if group_by_fields:
                query = query.group_by(*group_by_fields)

        return query.with_only_columns(*query_fields)

    def __apply_sort(self, query: Select, params: dict[str, str]) -> Select:
        """Applies a sort to a query
        If the field is a relationship, it joins the relationship before sorting
        and returns the query with the order applied. It also supports nested
        relationships as well as hybrid properties.
        """
        if not params:
            return query

        field = SQLAlchemyQueryField(params["field"], self.model)

        order = params.get("order", "asc").lower()
        query = query.add_columns(field.parent_model_field)
        query = field.join_query(query)
        query = query.order_by(getattr(field.parent_model_field, order)())
        return query

    @classmethod
    def __custom_filters(cls) -> dict[str, str]:
        """Returns a dict containing all declared custom functions and their
        respective filter keys.

        For example, if you declare a 'filter_name' method,
        it returns `{'name': 'filter_name'}`
        """
        return {f.split("_", 1)[1]: f for f in dir(cls) if "filter_" in f}
