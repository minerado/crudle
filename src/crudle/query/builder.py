# query_builder.py

from functools import reduce
from sqlalchemy import Select, distinct, or_, select
from sqlalchemy.sql import func
from typing import Any

from .field import QueryField
from ..utils import flatten_dict


class QueryBuilder:
    """
    QueryBuilder is a class that helps you build queries based on a model and a set of filters.

    It allows you to filter, sort, and search for data in a database using a declarative way.

    ## Building a basic query
    >>> builder = QueryBuilder(model=Transactions)
    >>> query = builder.build_query()

    With the code above, you will get a query that fetches all transactions from the database.

    ## Filtering data
    >>> query = builder.build_query(filters={"name": "John Doe"}) # Filter by name
    >>> query = builder.build_query(filters={"age__lt": 20}) # Filter by age less than 20

    You can also filter by multiple fields at once:
    >>> query = builder.build_query(filters={"name": "John Doe", "age_lt": 20})

    As we see in the example above, you can use operators by using the '__' suffix. The default
    operator is 'eq' (equals), but you can use other operators like 'lt' (less than), 'gt' (greater
    than), 'le' (less or equal), 'ge' (greater or equal), 'ne' (not equals), 'in' (in a list),
    'not_in' (not in a list) and 'q' (search using tsvectors).

    ## Sorting data
    >>> query = builder.build_query(sort=[{"field": "name", "order": "asc"}]) # Sort by name in ascending order
    >>> query = builder.build_query(sort=[{"field": "name", "order": "desc"}]) # Sort by name in descending order

    You can set multiple sort fields at once. The order defaults to 'asc'.

    ## Searching data
    The QueryBuilder class also supports a search filter that allows you to search for a term in
    multiple fields at once.

    >>> builder = QueryBuilder(model=Transactions, search_fields=["name"])
    >>> query = builder.build_query(search="Finn") # Search for 'Finn' in the 'name' field

    The search filter uses the PostgreSQL `tsvector` and `tsquery` functions to search for a term in
    a field. It also supports multiple fields and nested relationships that you can define like
    'entities.roles.name'.

    ## Custom filters
    The QueryBuilder class is designed to be inherited by other classes to extend its functionality.

    When you create a class that inherits from QueryBuilder, you can declare custom filters to
    apply custom behaviour to your queries. To do that, you must declare a method that starts with
    `filter_` and receives a query and a value as arguments.

    For example, to create a filter called 'filter_something', you must declare a method like this:

    ```python
    class TransactionsQueryBuilder(QueryBuilder):
        def filter_something(self, query, value):
            return query.filter(...) # Do whatever you want here, just remember to return a query
    ```

    Then you can just use the `something` filter in your queries:

    >>> query = builder.build_query(filters={"something": "value"})
    """

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
            field = QueryField(f, self.model, override_operator="q")
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
            query_field = QueryField(f, self.model)
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

        field = QueryField(key, self.model)
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

        for f in fields:
            if f.startswith("count"):
                splitted_field = f.split(".", 1)
                field = splitted_field[1] if len(splitted_field) > 1 else "id"
                query_field = QueryField(field, self.model)
                query = query_field.join_query(query)
                query_fields.append(
                    func.count(distinct(query_field.parent_model_field))
                )
            else:
                query_fields.append(QueryField(f, self.model).parent_model_field)

        for f in query_fields:
            if isinstance(f, QueryField):
                query = f.join_query(query)

        return query.with_only_columns(*query_fields)

    def __apply_sort(self, query: Select, params: dict[str, str]) -> Select:
        """Applies a sort to a query
        If the field is a relationship, it joins the relationship before sorting
        and returns the query with the order applied. It also supports nested
        relationships as well as hybrid properties.
        """
        if not params:
            return query

        field = QueryField(params["field"], self.model)

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
