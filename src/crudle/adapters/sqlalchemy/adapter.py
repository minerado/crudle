from sqlalchemy.exc import NoResultFound, SQLAlchemyError
from sqlalchemy.orm.session import Session
from typing import List

from .helpers import (
    ON_UPDATE_ASSOC_OPTIONS,
    handle_relationship,
    set_attributes_from_dict,
)
from .query_builder import SQLAlchemyQueryBuilder


class SQLAlchemyAdapter:
    """Extends a SQLAlchemy model with CRUD operations.

    You can define extra filters by declaring a `Queries` class inside the
    model definition:

    ```python
    class MyTable(Base, Crudle):
        id = Column(int)

        class Queries:
            def filter_role(self, query, value):
                return query.filter(Entities.roles.any(EntityRoles.slug == value))

    MyTable.list(db, {'role': 'issuer'})
    ```

    Now, everytime we pass "role" as a filter parameter for the `list` method,
    the `filter_role` query will be added to our base query.
    """

    DEFAULT_ON_UPDATE_ASSOC = ON_UPDATE_ASSOC_OPTIONS["raise"]

    class Queries:
        search_fields = []

    def update(
        self,
        db: Session,
        on_update_assocs=DEFAULT_ON_UPDATE_ASSOC,
        commit=True,
        **kwargs,
    ):
        """Update an instance in the database."""
        return self.__update(
            db, self, on_update_assocs=on_update_assocs, commit=commit, **kwargs
        )

    def delete(self, db: Session, commit=True):
        """Delete an instance from the database."""
        return self.__delete(db, self, commit=commit)

    @classmethod
    def build_query(cls, search_fields: List[str] = [], **kwargs):
        """Build a query with optional search fields."""

        class Q(SQLAlchemyQueryBuilder, cls.Queries): ...

        search_fields = search_fields or getattr(cls.Queries, "search_fields", [])

        return Q(model=cls, search_fields=search_fields).build_query(**kwargs)

    @classmethod
    def insert(cls, db: Session, commit=True, **kwargs):
        """Insert a new instance into the database."""
        model = cls.__call__()
        relationship_map = {k: v for k, v in model.__mapper__.relationships.items()}

        _params = {k: v for k, v in kwargs.items() if v is not None}

        for k, v in _params.items():
            if k in relationship_map and isinstance(v, dict):
                model_entity = relationship_map[k].entity.entity

                if v.get("id"):
                    association = model_entity.get(db, v.get("id"))
                else:
                    association = relationship_map[k].entity.entity(**v)

                setattr(model, k, association)

            elif k in relationship_map and isinstance(v, list):
                model_entity = relationship_map[k].entity.entity

                association = []
                for item in v:
                    if hasattr(item, "id") and item.id:
                        association.append(item)
                    elif isinstance(item, dict) and item.get("id"):
                        association.append(model_entity.get(db, item.get("id")))
                    else:
                        if isinstance(item, dict):
                            # Create the model instance and handle nested relationships
                            nested_model = relationship_map[k].entity.entity()
                            set_attributes_from_dict(
                                nested_model, item, db, "nilify_all"
                            )
                            association.append(nested_model)
                        else:
                            association.append(item)

                setattr(model, k, association)

            else:
                setattr(model, k, v)

        db.add(model)

        if commit:
            db.commit()

        return model

    @classmethod
    def get(cls, db: Session, id: str | int):
        """Retrieve an instance by its ID."""
        return db.get(cls, id)

    @classmethod
    def get_by(cls, db: Session, **kwargs):
        """Retrieve an instance by specified filters."""
        q = cls.build_query(**kwargs)

        return db.execute(q).scalar_one_or_none()

    @classmethod
    def list(cls, db: Session, **kwargs):
        """List instances based on specified filters."""
        # Extract special parameters that shouldn't be passed to build_query
        return_dict = kwargs.pop("return_dict", False)

        # Check if select is being used
        select_fields = kwargs.get("select", [])

        if select_fields:
            # Build query with select fields
            q = cls.build_query(**kwargs)
            result = db.execute(q).all()

            # Get column names from the query result
            if result:
                # Get column names from the first row's keys (if it's a Row object)
                # or from the query's selected columns
                if hasattr(result[0], "_mapping"):
                    # SQLAlchemy Row object
                    column_names = list(result[0]._mapping.keys())
                else:
                    # Fallback: get column names from query
                    column_names = [str(col) for col in q.column_descriptions]

                # Convert tuples to dictionaries and structure relationship data
                structured_results = []
                for row in result:
                    row_dict = dict(zip(column_names, row))

                    # Group relationship fields into nested objects
                    structured_row = {}
                    relationship_data = {}

                    for key, value in row_dict.items():
                        # Check if this is a relationship field (has underscore prefix and rel_name is a relationship)
                        is_relationship_field = False
                        if "_" in key:
                            # Check if this key starts with any relationship name from select_fields
                            for field in select_fields:
                                # Handle both direct relationship fields ("items") and nested fields ("items.color")
                                if "." in field:
                                    rel_name = field.split(".")[0]
                                else:
                                    rel_name = field

                                if hasattr(cls, rel_name):
                                    attr = getattr(cls, rel_name)
                                    if hasattr(attr, "property") and hasattr(
                                        attr.property, "mapper"
                                    ):
                                        # Check if this key starts with the relationship name + underscore
                                        prefix = rel_name + "_"
                                        if key.startswith(prefix):
                                            field_name = key[
                                                len(prefix) :
                                            ]  # Remove the prefix

                                            if rel_name not in relationship_data:
                                                relationship_data[rel_name] = {}
                                            relationship_data[rel_name][field_name] = (
                                                value
                                            )
                                            is_relationship_field = True
                                            break

                        # Only add to structured_row if it's not a relationship field
                        if not is_relationship_field:
                            structured_row[key] = value

                    # Add relationship data to the structured row, but only if there's actual data
                    for rel_name, rel_data in relationship_data.items():
                        # Check if all values in the relationship are None
                        if all(value is None for value in rel_data.values()):
                            structured_row[rel_name] = None
                        else:
                            structured_row[rel_name] = rel_data

                    structured_results.append(structured_row)

                return structured_results
            else:
                return []
        elif return_dict:
            # When return_dict=True, return all fields as dictionaries (excluding relationships)
            # Get all column names (excluding relationships)
            column_names = [column.name for column in cls.__table__.columns]

            # Remove select from kwargs if it exists to avoid conflict
            kwargs_copy = kwargs.copy()
            kwargs_copy.pop("select", None)

            # Build query with all columns selected
            q = cls.build_query(**kwargs_copy, select=column_names)
            result = db.execute(q).all()

            # Convert tuples to dictionaries
            return [dict(zip(column_names, row)) for row in result]
        else:
            # Normal behavior: return model instances
            q = cls.build_query(**kwargs)
            return db.execute(q).scalars().all()

    @classmethod
    def update_by(
        cls,
        db: Session,
        filters,
        /,
        should_raise=False,
        **kwargs,
    ):
        """Update an instance based on specified filters."""
        item = cls.get_by(db, **filters)

        if not item and should_raise:
            raise NoResultFound()

        if not item:
            return None

        return cls.__update(db, item, **kwargs)

    @classmethod
    def delete_by(cls, db: Session, **kwargs):
        """Delete an instance based on specified filters."""
        item = cls.get_by(db, **kwargs)

        return cls.__delete(db, item) if item else None

    @classmethod
    def count(cls, db: Session, field: str | None = None, **kwargs) -> int:
        """Count instances based on specified filters."""
        # Extract only filter-related parameters, ignore pagination and other parameters
        filter_params = {}
        ignored_params = {
            "limit",
            "skip",
            "sort",
            "select",
            "return_dict",
            "distinct_on",
        }

        for key, value in kwargs.items():
            if key not in ignored_params:
                filter_params[key] = value

        # Handle field parameter - if field is invalid, just count all records
        select_field = "count"
        if field:
            try:
                # Check if field exists on the model
                if hasattr(cls, field):
                    select_field = f"count.{field}"
                elif "." in field:
                    # Handle nested fields like "item_type.name"
                    parts = field.split(".", 1)
                    rel_name = parts[0]
                    nested_field = parts[1]
                    if hasattr(cls, rel_name):
                        attr = getattr(cls, rel_name)
                        if hasattr(attr, "property") and hasattr(
                            attr.property, "mapper"
                        ):
                            related_model = attr.property.mapper.class_
                            if hasattr(related_model, nested_field):
                                select_field = f"count.{field}"
                # If field doesn't exist, just use "count" (count all records)
            except Exception:
                # If there's any error with the field, just count all records
                pass

        q = cls.build_query(select=[select_field], **filter_params)
        return db.scalar(q) or 0

    @classmethod
    def upsert_by(cls, db: Session, filters, **kwargs):
        """Update or insert an instance based on specified filters."""
        return cls.update_by(db, filters, **kwargs) or cls.insert(db, **kwargs)

    @staticmethod
    def __delete(db: Session, model, commit=True):
        db.delete(model)

        if commit:
            db.commit()

        return model

    @staticmethod
    def __update(
        db: Session,
        model,
        /,
        on_update_assocs=DEFAULT_ON_UPDATE_ASSOC,
        commit=True,
        **kwargs,
    ):
        """Update a row in a `model` table.

        Args:
            db (Session): The database session.
            model: The database model instance to update the row.
            commit (bool): Whether to commit the changes to the database.
            kwargs: Params used to update the row.

        Returns:
            BaseModel: The updated row.
        """
        if not commit:
            # For commit=False, work on a copy to avoid modifying the original
            # and then rollback all database changes
            savepoint = db.begin_nested()

            # Create a copy of the model to work with
            model_copy = type(model)()
            for key in model.__mapper__.columns.keys():
                if hasattr(model, key):
                    setattr(model_copy, key, getattr(model, key))

            # Ensure the copy has the same id for foreign key relationships
            if hasattr(model, "id") and model.id:
                model_copy.id = model.id

            # Copy relationships - start with empty collections for list relationships
            for key in model.__mapper__.relationships.keys():
                if hasattr(model, key):
                    rel_value = getattr(model, key)
                    if rel_value is not None:
                        if hasattr(rel_value, "__iter__") and not isinstance(
                            rel_value, str
                        ):
                            # It's a collection - start with empty list
                            setattr(model_copy, key, [])
                        else:
                            # It's a single relationship - copy the reference
                            setattr(model_copy, key, rel_value)
                    else:
                        # Set to None if the original was None
                        setattr(model_copy, key, None)

            # Work with the copy
            working_model = model_copy
        else:
            working_model = model
            savepoint = None

        try:
            # Don't filter None values since we want to validate them
            params = kwargs
            relationship_map = working_model.__mapper__.relationships

            # Apply all changes to the working model
            for key, value in params.items():
                if key in relationship_map:
                    updated_relationship = handle_relationship(
                        db,
                        working_model,
                        key,
                        value,
                        on_update=on_update_assocs,
                        commit=commit,
                    )
                    setattr(working_model, key, updated_relationship)
                else:
                    setattr(working_model, key, value)

            if commit:
                db.commit()
            else:
                # Rollback to savepoint, undoing all database changes
                savepoint.rollback()
        except SQLAlchemyError as e:
            if not commit and savepoint:
                savepoint.rollback()
            db.rollback()
            raise e

        return working_model
