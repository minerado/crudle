from sqlalchemy.exc import (
    IntegrityError,
    NoResultFound,
    SQLAlchemyError,
)
from sqlalchemy import select
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.elements import BinaryExpression
from typing import List

from .query.builder import QueryBuilder


class CRUDMixin:
    """Extends a SQLAlchemy model with CRUD operations.

    You can define extra filters by declaring a `Queries` class inside the
    model definition:

    ```python
    class MyTable(Base, CRUDMixin):
        id = Column(int)

        class Queries:
            def filter_role(self, query, value):
                return query.filter(Entities.roles.any(EntityRoles.slug == value))

    MyTable.list(db, {'role': 'issuer'})
    ```

    Now, everytime we pass "role" as a filter parameter for the `list` method,
    the `filter_role` query will be added to our base query.
    """

    DEFAULT_ON_UPDATE_ASSOC = "raise"

    class Queries:
        search_fields = []

    def delete(self, db: Session, **kwargs):
        """Delete an instance from the database."""
        return self.__delete(db, self, **kwargs)

    def update(self, db: Session, **kwargs):
        """Update an instance in the database."""
        return self.__update(db, self, **kwargs)

    @classmethod
    def build_query(cls, search_fields: List[str] = [], **kwargs):
        """Build a query with optional search fields."""

        class Q(QueryBuilder, cls.Queries): ...

        search_fields = search_fields or getattr(cls.Queries, "search_fields", [])
        return Q(model=cls, search_fields=search_fields).build_query(**kwargs)

    @classmethod
    def count(cls, db: Session, field: str | None = None, **kwargs) -> int:
        """Count instances based on specified filters."""
        select_field = f"count.{field}" if field else "count"
        q = cls.build_query(select=[select_field], **kwargs)
        return db.scalar(q) or 0

    @classmethod
    def delete_by(cls, db: Session, **kwargs):
        """Delete an instance based on specified filters."""
        item = cls.get_by(db, **kwargs)
        return cls.__delete(db, item) if item else None

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
                    if item.get("id"):
                        association.append(model_entity.get(db, item.get("id")))
                    else:
                        association.append(relationship_map[k].entity.entity(**item))

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
        try:
            params = CRUDMixinHelper.filter_none_values(kwargs)
            relationship_map = model.__mapper__.relationships

            for key, value in params.items():
                if key in relationship_map:
                    updated_relationship = CRUDMixinHelper.handle_relationship(
                        db, model, key, value, on_update=on_update_assocs
                    )
                    setattr(model, key, updated_relationship)
                else:
                    setattr(model, key, value)

            if commit:
                db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise e

        return model


class CRUDMixinHelper:
    @staticmethod
    def filter_none_values(data):
        return {k: v for k, v in data.items() if v is not None}

    @staticmethod
    def get_foreign_key_column(model, relationship_name):
        """Get the foreign key column name for a given relationship.

        Args:
            model: The SQLAlchemy model.
            relationship_name (str): The name of the relationship.

        Returns:
            str: The foreign key column name.
        """
        relationship = getattr(model.__mapper__.relationships, relationship_name)
        if isinstance(relationship, RelationshipProperty):
            primaryjoin = relationship.primaryjoin
            if isinstance(primaryjoin, BinaryExpression):
                return primaryjoin.right.name
            else:
                raise ValueError(
                    f"Primary join for {relationship_name} is not a binary expression"
                )
        else:
            raise ValueError(f"{relationship_name} is not a valid relationship")

    @staticmethod
    def handle_relationship(
        db, model, relationship_name, values, on_update: str = "nilify_all"
    ):
        """Handle updating or creating relationships.

        Args:
            db (Session): The database session.
            model: The database model instance.
            relationship_name (str): The name of the relationship.
            values (list or dict): The values to update or create.

        Returns:
            list or object: The updated or created relationship(s).
        """
        relationship = getattr(model, relationship_name)
        model_entity = model.__mapper__.relationships[relationship_name].entity.entity
        foreign_key = CRUDMixinHelper.get_foreign_key_column(model, relationship_name)

        if isinstance(relationship, list):
            existing_ids = {assoc.id for assoc in relationship}
            new_ids = {item["id"] for item in values if "id" in item and item["id"]}

            if on_update == "delete_all":
                # Delete associations not in the new payload
                for assoc in relationship:
                    if assoc.id not in new_ids:
                        db.delete(assoc)
                        db.flush()  # Ensure the deletion is flushed to the database
            elif on_update == "raise":
                if not new_ids.issubset(existing_ids):
                    raise IntegrityError(
                        "Some associations are missing in the payload",
                        params=None,
                        orig=None,
                    )

            associations = []
            for item in values:
                item = CRUDMixinHelper.filter_none_values(item)

                if "id" in item and item["id"]:
                    stmt = select(model_entity).filter_by(id=item["id"])
                    association = db.execute(stmt).scalar_one()
                    CRUDMixinHelper.update_association(association, item, foreign_key)
                    associations.append(association)
                else:
                    item[foreign_key] = model.id
                    new_assoc = model_entity(**item)
                    db.add(new_assoc)
                    db.flush()
                    associations.append(new_assoc)
            return associations
        else:
            values = CRUDMixinHelper.filter_none_values(values)
            if "id" in values and values["id"]:
                stmt = select(model_entity).filter_by(id=values["id"])
                association = db.execute(stmt).scalar_one()
                CRUDMixinHelper.update_association(association, values, foreign_key)
                return association
            else:
                values[foreign_key] = model.id
                new_assoc = model_entity(**values)
                db.add(new_assoc)
                db.flush()
                return new_assoc

    @staticmethod
    def update_association(association, data, foreign_key):
        for key, value in data.items():
            if key != foreign_key and getattr(association, key) != value:
                setattr(association, key, value)
