from sqlalchemy import func, select
from sqlalchemy.exc import NoResultFound, SQLAlchemyError
from sqlalchemy.orm.session import Session
from typing import List

from .helpers import (
    ON_UPDATE_ASSOC_OPTIONS,
    get_related_or_raise,
    handle_relationship,
    set_attributes_from_dict,
    structure_select_row,
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
        """Insert a new instance, optionally with nested associations.

        Relationship values may be model instances, ``{"id": ...}`` links
        (existing rows are not updated), or create dicts / nested lists.
        ``None`` kwargs are skipped. Missing ``{"id": ...}`` targets raise
        ``NoResultFound``. ``commit=False`` adds the graph to the session
        without ``commit``; primary keys appear after flush (often via
        ``db.commit()`` when autoflush is off).
        """
        model = cls.__call__()
        relationship_map = {k: v for k, v in model.__mapper__.relationships.items()}

        _params = {k: v for k, v in kwargs.items() if v is not None}

        for k, v in _params.items():
            if k in relationship_map and isinstance(v, dict):
                model_entity = relationship_map[k].entity.entity

                if v.get("id"):
                    association = get_related_or_raise(model_entity, db, v.get("id"))
                else:
                    # Same recursive path as list members (nested dicts allowed).
                    association = model_entity()
                    set_attributes_from_dict(association, v, db, "nilify_all")

                setattr(model, k, association)

            elif k in relationship_map and isinstance(v, list):
                model_entity = relationship_map[k].entity.entity

                association = []
                for item in v:
                    if hasattr(item, "id") and item.id:
                        association.append(item)
                    elif isinstance(item, dict) and item.get("id"):
                        association.append(
                            get_related_or_raise(model_entity, db, item.get("id"))
                        )
                    else:
                        if isinstance(item, dict):
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
        """Retrieve exactly one instance matching filters, or None.

        Shares the list filter / assoc dialect. Raises
        ``MultipleResultsFound`` if more than one row matches.

        ``limit`` / ``skip`` / ``sort`` / ``select`` / ``return_dict`` /
        ``distinct_on`` are ignored (same idea as ``count``) so pagination
        cannot hide duplicates or drop the only match.
        """
        ignored_params = {
            "limit",
            "skip",
            "sort",
            "select",
            "return_dict",
            "distinct_on",
        }
        filter_params = {
            key: value
            for key, value in kwargs.items()
            if key not in ignored_params
        }
        q = cls.build_query(
            limit=None, skip=0, distinct_on=[], **filter_params
        )
        # Joins can fan out parent rows; unique() keeps entity identity once.
        return db.execute(q).scalars().unique().one_or_none()

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

            if not result:
                return []

            if hasattr(result[0], "_mapping"):
                column_names = list(result[0]._mapping.keys())
            else:
                column_names = [str(col) for col in q.column_descriptions]

            structured_results = []
            for row in result:
                row_dict = dict(zip(column_names, row))
                structured_results.append(
                    structure_select_row(row_dict, select_fields)
                )

            return structured_results
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
        """Update exactly one instance matching ``filters``, or None.

        ``filters`` is a dict spread into ``get_by`` (same dialect /
        MultipleResultsFound / ignored list options). Update attrs and
        ``on_update_assocs`` / ``commit`` live in ``**kwargs``.
        """
        item = cls.get_by(db, **filters)

        if not item and should_raise:
            raise NoResultFound()

        if not item:
            return None

        return cls.__update(db, item, **kwargs)

    @classmethod
    def delete_by(cls, db: Session, **kwargs):
        """Delete exactly one instance matching filters, or None.

        Uses ``get_by`` (same filter dialect / MultipleResultsFound /
        ignored list options), then deletes that row.
        """
        item = cls.get_by(db, **kwargs)

        return cls.__delete(db, item) if item else None

    @classmethod
    def count(cls, db: Session, **kwargs) -> int:
        """Count instances based on specified filters.

        Shares the list filter / assoc / ``distinct_on`` dialect; returns an
        int. Non-null checks use filters (e.g. ``price__ne=None``).

        ``limit`` / ``skip`` / ``sort`` / ``select`` / ``return_dict`` are
        ignored. ``distinct_on`` matches list cardinality (one per group)
        via ``COUNT(*)`` over a distinct subquery (no row materialization).
        """
        ignored_params = {
            "limit",
            "skip",
            "sort",
            "select",
            "return_dict",
        }

        distinct_on = kwargs.get("distinct_on", [])
        filter_params = {
            key: value
            for key, value in kwargs.items()
            if key not in ignored_params and key != "distinct_on"
        }

        use_list_shaped_distinct = distinct_on is True or (
            isinstance(distinct_on, list) and len(distinct_on) > 0
        )

        if use_list_shaped_distinct:
            # Same distinct row set as list(limit=None), counted in SQL.
            inner = cls.build_query(
                distinct_on=distinct_on,
                limit=None,
                skip=0,
                **filter_params,
            )
            count_q = select(func.count()).select_from(inner.subquery())
            return db.scalar(count_q) or 0

        q = cls.build_query(select=["count"], distinct_on=[], **filter_params)
        return db.scalar(q) or 0

    @staticmethod
    def _attrs_for_upsert_insert(filters, kwargs):
        """Build insert attrs for the upsert miss path.

        Strips update-only control keys so they are not written as columns.
        Merges simple equality keys from ``filters`` (and nested
        ``filter={...}``) when absent from ``kwargs``. Operator keys,
        dotted association hops, nested / list values, and list-option
        keys are not merged.
        """
        control = {"on_update_assocs", "should_raise"}
        attrs = {k: v for k, v in kwargs.items() if k not in control}
        skip = {
            "filter",
            "q",
            "or_",
            "and_",
            "not_",
            "select",
            "sort",
            "order_by",
            "limit",
            "skip",
            "preload",
            "return_dict",
            "distinct_on",
            *control,
        }

        def merge_simple(src):
            for key, value in src.items():
                if key == "filter" and isinstance(value, dict):
                    merge_simple(value)
                    continue
                if (
                    key in skip
                    or "__" in key
                    or "." in key
                    or isinstance(value, (dict, list))
                ):
                    continue
                attrs.setdefault(key, value)

        merge_simple(filters or {})
        return attrs

    @classmethod
    def upsert_by(cls, db: Session, filters, **kwargs):
        """Update exactly one match, or insert if none match.

        ``filters`` uses the ``get_by`` dialect (``MultipleResultsFound`` on
        ambiguity). On miss, simple equality filter keys merge into insert
        attrs when absent from ``**kwargs``. ``on_update_assocs`` /
        ``should_raise`` are not written as columns on insert;
        ``should_raise=True`` still raises on miss (never inserts).
        """
        updated = cls.update_by(db, filters, **kwargs)
        if updated is not None:
            return updated

        return cls.insert(db, **cls._attrs_for_upsert_insert(filters, kwargs))

    @staticmethod
    def __delete(db: Session, model, commit=True):
        if model is None:
            return None

        # Dual ``secondary=`` + association-object mappings (e.g. ``tags``
        # and ``item_tags``) conflict on flush if both are cleared. Clear only
        # the ``secondary=`` collections, then flush (sessions often use
        # ``autoflush=False``).
        cleared = False
        for rel in model.__mapper__.relationships:
            if rel.uselist and rel.secondary is not None:
                setattr(model, rel.key, [])
                cleared = True
        if cleared:
            db.flush()

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
