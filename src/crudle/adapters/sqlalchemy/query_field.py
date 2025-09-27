import operator as o
from pydantic import BaseModel, computed_field
from sqlalchemy import Select, text
from sqlalchemy.sql import func
from typing import Any, ClassVar

from ...utils import build_tsquery_string


OPERATORS = ["eq", "gt", "ge", "lt", "le", "ne", "in", "ni", "q"]


class SQLAlchemyQueryField(BaseModel):
    """
    `SQLAlchemyQueryField` helps build and manipulate SQLAlchemy queries with ease.

    ### Attributes:
    - `name` (str): The name of the field to be queried.
    - `operator` (str): The operator to be used for the query (e.g., "eq", "gt").
    - `parents` (list[str]): Parent relationships to join in the query.
    - `model` (Any): The SQLAlchemy model associated with the query field.

    ### Methods:

    #### `__init__(self, value: str, model: Any)`
    Initializes the `SQLAlchemyQueryField` with a value and model.

    - **Parameters**:
      - `value` (str): The field and operator string (e.g., "age__gt").
      - `model` (Any): The SQLAlchemy model associated with the query field.
      - `override_operator` (str): Optional operator to override the value's operator.

    - **Example**:
      ```python
      qf = SQLAlchemyQueryField(value="age__gt", model=SomeModel)
      query.where(qf.operation(20))
      ```
    """

    ALLOWED_OPERATORS: ClassVar[list[str]] = OPERATORS
    DEFAULT_OPERATOR: ClassVar[str] = "eq"
    OPERATOR_SPLITTER: ClassVar[str] = "__"

    name: str
    operator: str
    parents: list[str]

    model: Any = None

    def __init__(self, value, model, override_operator=None):
        (field, operator) = self.split_field_operation(value)
        fields = field.split(".")
        name = fields[-1]
        parents = fields[:-1]
        op = override_operator or operator

        super().__init__(model=model, name=name, operator=op, parents=parents)

    def join_query(self, query: Select, join_opts={}):
        """
        Joins a query with the necessary relationships to filter by a field.

        This method traverses the parent relationships specified in the `parents` attribute
        and joins them to the provided SQLAlchemy query. This is useful for filtering
        fields that are part of related models.

        ### Parameters:
        - `query` (Select): The SQLAlchemy `Select` query to be joined.
        - `join_opts` (dict): Optional dictionary of join options. These options are passed
        to the SQLAlchemy `join` method.

        ### Returns:
        - `Select`: The modified query with the necessary joins.

        ### Example:
        ```python
        # Initialize QueryField with a related field
        qf = QueryField("related_field", SomeModel)

        # Join the necessary relationships
        query = qf.join_query(query)

        # The query now includes the necessary joins to filter by 'related_field'
        query.where(qf.operation("some_value"))
        ```
        """
        model = self.model

        for parent in self.parents:
            parent_model = getattr(model, parent).property.mapper.class_
            query = query.join(getattr(model, parent), **join_opts)
            model = parent_model

        return query

    def operation(self, value):
        """Returns a SQLAlchemy operation based on the operator and value."""

        special_operators_fns = {
            "in": self.parent_model_field.in_,
            "ni": self.parent_model_field.not_in,
            "q": self.__to_tsvector,
        }

        if self.operator in special_operators_fns:
            return special_operators_fns[self.operator](value)

        return getattr(o, self.operator)(self.parent_model_field, value)

    def __to_tsvector(self, value, dictionary="unaccent_simple"):
        """Returns a tsvector operation to search for a term in a field."""

        term = build_tsquery_string(value)

        return func.to_tsvector(
            text(f"'{dictionary}'"),
            func.coalesce(getattr(self.parent_model, self.name), text("' '")),
        ).op("@@")(text(f"to_tsquery('{dictionary}', '%s')" % term))

    @computed_field
    @property
    def parent_model(self) -> Any:
        """Returns the direct model that contains the field."""

        return self.parent_models[-1] if self.parent_models else self.model

    @computed_field
    @property
    def parent_models(self) -> list[Any]:
        """Returns a list of models used to access the field."""

        return self.__parent_models(self.model, self.parents, [])

    @computed_field
    @property
    def parent_model_field(self) -> Any:
        """Returns the field from the parent model."""

        return getattr(self.parent_model, self.name)

    @classmethod
    def __parent_models(cls, base_model, parents, models):
        if not parents:
            return models

        parent, *rest = parents

        new_model = getattr(base_model, parent).property.mapper.class_

        return cls.__parent_models(new_model, rest, models + [new_model])

    @classmethod
    def split_field_operation(cls, key: str) -> tuple[str, str]:
        """Returns a Python operation by splitting a string and getting the
        operation name after '__'.

        Defaults to 'eq'.

        Examples:
            >>> split_field_operation("date__gt")
            >>> ("date", "gt")

            >>> split_field_operation("name__eq")
            >>> ("name", "eq")

            >>> split_field_operation("name")
            >>> ("name", "eq")
        """

        key_op_pair = key.split(cls.OPERATOR_SPLITTER)
        operation_name = (
            key_op_pair[1] if len(key_op_pair) == 2 else cls.DEFAULT_OPERATOR
        )

        if operation_name not in cls.ALLOWED_OPERATORS:
            raise Exception(f"Forbidden operator: {operation_name}")

        return (key_op_pair[0], operation_name)
