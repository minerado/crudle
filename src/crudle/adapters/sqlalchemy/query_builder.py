# query_builder.py

from functools import reduce
from sqlalchemy import Select, case, distinct, or_, select
from sqlalchemy.sql import func
from typing import Any


from ...utils import flatten_dict
from .helpers import is_sa_relationship
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
        limit: int | None = DEFAULT_QUERY_LIMIT,
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
            query = query_field.join_query(query, join_opts={"isouter": True})
            query_fields.append(query_field.parent_model_field)

        # Postgres: DISTINCT ON (a, b) requires ORDER BY to start with a, b.
        # Keep any earlier sort clauses after the distinct_on leading keys.
        existing_order_by = tuple(query._order_by_clauses or ())
        query = query.order_by(None)
        query = query.order_by(*query_fields, *existing_order_by)

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
        if limit is None:
            return query
        if limit < 0:
            raise ValueError("limit must be >= 0")
        return query.limit(limit)

    def __apply_offset(self, query: Select, skip: int) -> Select:
        if skip is None:
            skip = 0
        if skip < 0:
            raise ValueError("skip must be >= 0")
        return query.offset(skip)

    def __apply_select(self, query: Select, fields: list) -> Select:
        """Applies a select to a query.

        Relationship paths may be multi-hop (``items.item_type.name``). Joins are
        outer and deduplicated per path prefix so one ``list`` call stays a single
        SQL statement (no N+1). Selected relationship columns are labeled with
        dotted paths for nested result shaping.
        """

        if not fields:
            return query

        query_fields = []
        relationship_fields = set()
        joined_paths: set[tuple[str, ...]] = set()
        selected_labels: set[str] = set()
        rel_path_prefixes: set[tuple[str, ...]] = set()

        def ensure_joins(rel_path: list[str]):
            """Outer-join each relationship along ``rel_path`` at most once."""
            nonlocal query
            model = self.model
            for index, rel_name in enumerate(rel_path):
                path_key = tuple(rel_path[: index + 1])
                if path_key not in joined_paths:
                    query = query.join(getattr(model, rel_name), isouter=True)
                    joined_paths.add(path_key)
                model = getattr(model, rel_name).property.mapper.class_
            return model

        def add_column(column, label: str):
            if label in selected_labels:
                return
            query_fields.append(column.label(label))
            selected_labels.add(label)

        for f in fields:
            if f.startswith("count"):
                splitted_field = f.split(".", 1)
                field = splitted_field[1] if len(splitted_field) > 1 else "id"

                if "." in field:
                    query_field = SQLAlchemyQueryField(field, self.model)
                    if query_field.parents:
                        relationship_fields.add(query_field.parents[0])
                        for index in range(len(query_field.parents)):
                            rel_path_prefixes.add(
                                tuple(query_field.parents[: index + 1])
                            )
                    query = query_field.join_query(
                        query, join_opts={"isouter": True}
                    )
                    for index in range(len(query_field.parents)):
                        joined_paths.add(tuple(query_field.parents[: index + 1]))
                    # Non-null related scalar → count distinct parent rows
                    # (Memory parity; avoids distinct-value collapse).
                    related_col = query_field.parent_model_field
                    parent_id = getattr(self.model, "id")
                    query_fields.append(
                        func.count(
                            distinct(
                                case((related_col.isnot(None), parent_id))
                            )
                        ).label(f)
                    )
                    selected_labels.add(f)
                else:
                    query_field = SQLAlchemyQueryField(field, self.model)
                    query = query_field.join_query(query)
                    # Root scalar: COUNT(col) = non-null rows (not distinct values).
                    # Bare count / id: distinct parent ids (join-safe).
                    if field == "id":
                        query_fields.append(
                            func.count(
                                distinct(query_field.parent_model_field)
                            ).label(f)
                        )
                    else:
                        query_fields.append(
                            func.count(query_field.parent_model_field).label(f)
                        )
                    selected_labels.add(f)
                continue

            parts = f.split(".")
            model = self.model
            rel_path: list[str] = []
            skipped = False

            for index, part in enumerate(parts):
                is_last = index == len(parts) - 1

                if is_sa_relationship(model, part):
                    rel_path.append(part)
                    relationship_fields.add(rel_path[0])
                    rel_path_prefixes.add(tuple(rel_path))
                    model = getattr(model, part).property.mapper.class_

                    if is_last:
                        ensure_joins(rel_path)
                        path_prefix = ".".join(rel_path)
                        for column in model.__table__.columns:
                            add_column(column, f"{path_prefix}.{column.name}")
                    continue

                if not is_last:
                    # Column (or unknown) in the middle of a path — invalid
                    skipped = True
                    break

                if not hasattr(model, part):
                    skipped = True
                    break

                if rel_path:
                    ensure_joins(rel_path)
                    column = getattr(model, part)
                    add_column(column, f)
                else:
                    # Root scalar column
                    query_fields.append(getattr(self.model, part))
                    selected_labels.add(part)

            if skipped:
                continue

        # Intermediate PKs so outer-join nulls can distinguish missing collections
        # vs missing nested to-ones (stripped from output if not requested).
        for prefix in sorted(rel_path_prefixes, key=len):
            leaf_model = ensure_joins(list(prefix))
            if hasattr(leaf_model, "id"):
                add_column(getattr(leaf_model, "id"), f"{'.'.join(prefix)}.id")

        # Keep explicitly requested root scalars when relationships are present
        if relationship_fields:
            for f in fields:
                if f.startswith("count") or "." in f or f in relationship_fields:
                    continue
                if f in selected_labels:
                    continue
                if hasattr(self.model, f) and not is_sa_relationship(self.model, f):
                    query_fields.append(getattr(self.model, f))
                    selected_labels.add(f)

        has_count = any(field.startswith("count") for field in fields)
        has_other_fields = any(not field.startswith("count") for field in fields)

        if has_count and has_other_fields:
            group_by_fields = []
            for field in fields:
                if field.startswith("count"):
                    continue
                if "." in field or is_sa_relationship(self.model, field):
                    continue
                if hasattr(self.model, field):
                    group_by_fields.append(getattr(self.model, field))

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
        # Outer join so sorting by a relationship field does not filter out
        # parents with a missing association (matches filter join semantics).
        query = field.join_query(query, join_opts={"isouter": True})
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
