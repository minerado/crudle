from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.sql.elements import BinaryExpression

from ...utils import filter_none_values


ON_UPDATE_ASSOC_OPTIONS = {
    "raise": "raise",
    "nilify_all": "nilify_all",
    "delete_all": "delete_all",
}


def validate_association_value(item, relationship_name):
    """Validate that an association value is of a valid type.

    Args:
        item: The value to validate
        relationship_name (str): The name of the relationship for error messages

    Raises:
        ValueError: If the item is not a valid association type
    """
    # Valid types: dict or model instance
    if item is None:
        raise ValueError(
            f"Invalid association value for '{relationship_name}': "
            f"expected dict or model instance, got None"
        )

    # Check if it's a model instance (has id attribute and is not a basic type)
    if hasattr(item, "id") and not isinstance(
        item, (str, int, float, bool, list, tuple, set)
    ):
        return  # Valid model instance

    # Check if it's a dict
    if isinstance(item, dict):
        return  # Valid dict

    # If we get here, it's an invalid type
    raise ValueError(
        f"Invalid association value for '{relationship_name}': "
        f"expected dict or model instance, got {type(item).__name__} ({item})"
    )


def get_foreign_key_column(model, relationship_name):
    """Get the foreign key column name for a given relationship.

    Args:
        model: The SQLAlchemy model.
        relationship_name (str): The name of the relationship.

    Returns:
        str: The foreign key column name.
    """
    relationship = getattr(model.__mapper__.relationships, relationship_name)
    if callable(relationship):
        # The callable returns a list of tuples, get the relationship from the tuple
        relationships = relationship()
        for name, rel in relationships:
            if name == relationship_name:
                relationship = rel
                break
        else:
            raise ValueError(f"Could not find relationship {relationship_name}")

    if isinstance(relationship, RelationshipProperty):
        # For many-to-many relationships, there's no direct foreign key on the related model
        if relationship.direction.name == "MANYTOMANY":
            return None  # No foreign key on the related model for many-to-many
        # For one-to-many relationships, the foreign key is on the related model
        elif relationship.direction.name == "ONETOMANY":
            # Get the foreign key column from the related model
            related_model = relationship.mapper.class_
            for column in related_model.__table__.columns:
                if column.foreign_keys:
                    for fk in column.foreign_keys:
                        if fk.column.table == model.__table__:
                            return column.name
            raise ValueError(
                f"Could not find foreign key column for {relationship_name}"
            )
        else:
            # For many-to-one relationships, the foreign key is on the current model
            primaryjoin = relationship.primaryjoin
            if isinstance(primaryjoin, BinaryExpression):
                return primaryjoin.right.name
            else:
                raise ValueError(
                    f"Primary join for {relationship_name} is not a binary expression"
                )
    else:
        raise ValueError(f"{relationship_name} is not a valid relationship")


def validate_conflicting_operations(
    values, relationship_name, db, model, on_update="nilify_all"
):
    """Validate that there are no conflicting operations on the same objects.

    Args:
        values (list): List of values to process
        relationship_name (str): Name of the relationship for error messages
        db (Session): Database session to check current state
        model: The model instance being updated
        on_update (str): The update strategy ("nilify_all", "delete_all", "raise")

    Raises:
        IntegrityError: If conflicting operations are detected
    """
    if not isinstance(values, list):
        return

    # Skip validation for nilify_all since it doesn't actually delete objects
    if on_update == "nilify_all":
        return

    # Get the related model class from the relationship
    relationship = model.__mapper__.relationships[relationship_name]
    related_model_class = relationship.entity.entity

    # Track operations on nested objects across all items
    # {object_id: {'update': bool, 'delete': bool, 'relationship_name': str}}
    nested_operations = {}

    # First pass: collect all update operations
    for item in values:
        if not isinstance(item, dict):
            continue

        for key, value in item.items():
            if key == "id":
                continue

            if isinstance(value, dict) and "id" in value and value.get("id"):
                obj_id = value["id"]
                if obj_id not in nested_operations:
                    nested_operations[obj_id] = {
                        "update": False,
                        "delete": False,
                        "relationship_name": key,
                    }
                nested_operations[obj_id]["update"] = True

    # Second pass: collect all delete operations and check for conflicts
    for item in values:
        if not isinstance(item, dict) or "id" not in item:
            continue

        # Get the current object to check its relationships
        current_obj_id = item["id"]
        current_obj = db.get(related_model_class, current_obj_id)
        if not current_obj:
            continue

        for key, value in item.items():
            if key == "id":
                continue

            if value is None:
                # This is a delete operation - check if this specific object is being updated
                # Get the current value of this relationship
                current_relationship = getattr(current_obj, key, None)
                if current_relationship and hasattr(current_relationship, "id"):
                    obj_id = current_relationship.id
                    if (
                        obj_id in nested_operations
                        and nested_operations[obj_id]["update"]
                    ):
                        raise IntegrityError(
                            f"Conflicting operations on {key}: "
                            f"trying to both update and delete the same association (ID: {obj_id}). "
                            f"Resolve conflicts before updating.",
                            params=None,
                            orig=None,
                        )


def handle_relationship(
    db,
    model,
    relationship_name,
    values,
    on_update: str = "nilify_all",
    commit: bool = True,
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
    foreign_key = get_foreign_key_column(model, relationship_name)

    if isinstance(relationship, list):
        # First validate that values is a list
        if not isinstance(values, list):
            raise ValueError(
                f"Invalid association value for '{relationship_name}': "
                f"expected list, got {type(values).__name__} ({values})"
            )

        # Validate for conflicting operations before processing
        validate_conflicting_operations(values, relationship_name, db, model, on_update)

        # Validate all association values (including None)
        for item in values:
            validate_association_value(item, relationship_name)

        existing_ids = {assoc.id for assoc in relationship}
        new_ids = set()
        for item in values:
            if isinstance(item, dict) and "id" in item and item["id"]:
                new_ids.add(item["id"])
            elif hasattr(item, "id") and item.id:
                new_ids.add(item.id)

        if on_update == "delete_all":
            # For many-to-many relationships, clear the relationship and add new ones
            # For one-to-many relationships, delete the association objects
            if foreign_key is None:  # Many-to-many relationship
                # Clear the relationship (removes all associations)
                relationship.clear()
                if commit:
                    db.flush()
            else:  # One-to-many relationship
                # Delete association objects not in the new payload
                for assoc in relationship:
                    if assoc.id not in new_ids:
                        db.delete(assoc)
                        if commit:
                            db.flush()  # Ensure the deletion is flushed to the database
        elif on_update == "raise":
            # Raise error only if trying to remove existing associations
            # Allow updating properties of existing associations
            # Allow adding new associations
            if existing_ids and new_ids:
                # Check if we're trying to remove existing associations
                # This happens when existing_ids contains IDs not in new_ids
                removing_existing = bool(existing_ids - new_ids)
                if removing_existing:
                    raise IntegrityError(
                        f"Cannot update {relationship_name} when on_update='raise'. "
                        f"Trying to remove existing associations. "
                        f"Use on_update='nilify_all' or 'delete_all' to allow updates.",
                        params=None,
                        orig=None,
                    )
            # If new_ids is empty, it means we're only adding new items (no IDs), which is allowed

            # For "raise", preserve existing associations and only add new ones
            associations = list(relationship)  # Start with existing associations
            for item in values:
                if isinstance(item, dict):
                    item = filter_none_values(item)

                    if "id" in item and item["id"]:
                        # This should not happen due to the check above, but just in case
                        stmt = select(model_entity).filter_by(id=item["id"])
                        association = db.execute(stmt).scalar_one()

                        if not commit:
                            # For commit=False, create a copy of the association to avoid modifying the original
                            association_copy = type(association)()
                            for key in association.__mapper__.columns.keys():
                                if hasattr(association, key):
                                    setattr(
                                        association_copy,
                                        key,
                                        getattr(association, key),
                                    )
                            association = association_copy

                        # Set the foreign key to associate with the current model
                        if foreign_key and hasattr(association, foreign_key):
                            setattr(association, foreign_key, model.id)
                        update_association(
                            association, item, foreign_key, on_update, commit, db
                        )
                        associations.append(association)
                    else:
                        # Add new association
                        item[foreign_key] = model.id
                        new_assoc = model_entity(**item)
                        db.add(new_assoc)
                        if commit:
                            db.flush()
                        associations.append(new_assoc)
                else:
                    # Handle model instances directly
                    if hasattr(item, "id") and item.id:
                        # Existing model instance - set foreign key and add to associations
                        if foreign_key and hasattr(item, foreign_key):
                            setattr(item, foreign_key, model.id)
                        associations.append(item)
                    else:
                        # New model instance - set foreign key and add to database
                        if foreign_key and hasattr(item, foreign_key):
                            setattr(item, foreign_key, model.id)
                        db.add(item)
                        if commit:
                            db.flush()
                        associations.append(item)
            return associations

        associations = []
        for item in values:
            if isinstance(item, dict):
                if "id" in item and item["id"]:
                    stmt = select(model_entity).filter_by(id=item["id"])
                    association = db.execute(stmt).scalar_one()
                    # For one-to-many relationships, we need to set the foreign key on the related object
                    if foreign_key and hasattr(association, foreign_key):
                        setattr(association, foreign_key, model.id)
                    # Always update the association with the provided data
                    update_association(
                        association, item, foreign_key, on_update, commit
                    )
                    associations.append(association)
                else:
                    # Only set foreign key if it exists (not for many-to-many relationships)
                    if foreign_key:
                        item[foreign_key] = model.id
                    new_assoc = model_entity(**item)
                    db.add(new_assoc)
                    if commit:
                        db.flush()
                    associations.append(new_assoc)
            else:
                # Handle model instances directly
                if hasattr(item, "id") and item.id:
                    # Existing model instance - set foreign key and add to associations
                    if foreign_key and hasattr(item, foreign_key):
                        setattr(item, foreign_key, model.id)
                    associations.append(item)
                else:
                    # New model instance - set foreign key and add to database
                    if foreign_key and hasattr(item, foreign_key):
                        setattr(item, foreign_key, model.id)
                    db.add(item)
                    if commit:
                        db.flush()
                    associations.append(item)
        return associations
    else:
        # Handle single relationship (one-to-one or many-to-one)
        if values is None:
            # Handle None value for single relationships
            if on_update == "delete_all":
                # Delete the existing association if it exists
                if (
                    hasattr(model, relationship_name)
                    and getattr(model, relationship_name) is not None
                ):
                    existing_assoc = getattr(model, relationship_name)
                    db.delete(existing_assoc)
                    if commit:
                        db.flush()
                return None
            elif on_update == "raise":
                # Raise error if trying to set to None when on_update=raise
                if (
                    hasattr(model, relationship_name)
                    and getattr(model, relationship_name) is not None
                ):
                    raise IntegrityError(
                        f"Cannot update {relationship_name} when on_update='raise'. "
                        f"Trying to remove existing association. "
                        f"Use on_update='nilify_all' or 'delete_all' to allow updates.",
                        params=None,
                        orig=None,
                    )
                return None
            else:  # nilify_all
                # Just set to None without deleting
                return None
        else:
            # Validate non-None single relationship value
            validate_association_value(values, relationship_name)

            if isinstance(values, dict) and "id" in values and values["id"]:
                stmt = select(model_entity).filter_by(id=values["id"])
                association = db.execute(stmt).scalar_one()

                if not commit:
                    # For commit=False, create a copy of the association to avoid modifying the original
                    association_copy = type(association)()
                    for key in association.__mapper__.columns.keys():
                        if hasattr(association, key):
                            setattr(association_copy, key, getattr(association, key))
                    # Ensure the copy has the proper session context
                    association_copy._sa_instance_state = association._sa_instance_state
                    association = association_copy

                update_association(
                    association, values, foreign_key, on_update, commit, db
                )
                return association
            else:
                if isinstance(values, dict):
                    # Only set foreign key if it exists (not for many-to-many relationships)
                    if foreign_key and hasattr(model_entity, foreign_key):
                        values[foreign_key] = model.id
                    new_assoc = model_entity(**values)
                else:
                    # Handle model instances directly
                    if foreign_key and hasattr(values, foreign_key):
                        setattr(values, foreign_key, model.id)
                    new_assoc = values
                db.add(new_assoc)
                if commit:
                    if commit:
                        db.flush()
                return new_assoc


def update_association(
    association, data, foreign_key, on_update="nilify_all", commit=True, db=None
):
    """Update an association with data, handling nested relationships."""
    relationship_map = {k: v for k, v in association.__mapper__.relationships.items()}

    # Use the passed db session or fall back to the association's session
    session = db or (
        association._sa_instance_state.session
        if association._sa_instance_state
        else None
    )

    for key, value in data.items():
        if key == foreign_key:
            continue

        if key in relationship_map and isinstance(value, dict):
            # Handle single relationship
            model_entity = relationship_map[key].entity.entity

            if value.get("id"):
                # Update existing relationship
                stmt = select(model_entity).filter_by(id=value["id"])
                related_obj = session.execute(stmt).scalar_one()
                update_association(related_obj, value, "id", on_update, commit, db)
                setattr(association, key, related_obj)
            else:
                # Create new relationship
                related_obj = model_entity()
                set_attributes_from_dict(
                    related_obj,
                    value,
                    session,
                    on_update,
                )
                setattr(association, key, related_obj)
        elif key in relationship_map and value is None:
            # Handle None value for single relationship
            existing_assoc = getattr(association, key)
            if existing_assoc is not None:
                if on_update == "delete_all":
                    # Delete the existing association
                    session.delete(existing_assoc)
                    if commit:
                        session.flush()
                elif on_update == "raise":
                    # Raise error if trying to set to None when on_update=raise
                    raise IntegrityError(
                        f"Cannot update {key} when on_update='raise'. "
                        f"Trying to remove existing association. "
                        f"Use on_update='nilify_all' or 'delete_all' to allow updates.",
                        params=None,
                        orig=None,
                    )
                # For "nilify_all", just set to None without deleting
            setattr(association, key, None)

        elif key in relationship_map and isinstance(value, list):
            # Handle list of relationships
            model_entity = relationship_map[key].entity.entity

            new_associations = []
            for item in value:
                if hasattr(item, "id") and item.id:
                    new_associations.append(item)
                elif isinstance(item, dict) and item.get("id"):
                    stmt = select(model_entity).filter_by(id=item["id"])
                    related_obj = session.execute(stmt).scalar_one()
                    update_association(related_obj, item, "id", on_update, commit, db)
                    new_associations.append(related_obj)
                else:
                    if isinstance(item, dict):
                        related_obj = model_entity()
                        set_attributes_from_dict(
                            related_obj,
                            item,
                            association._sa_instance_state.session,
                            on_update,
                        )
                        new_associations.append(related_obj)
                    else:
                        new_associations.append(item)

            setattr(association, key, new_associations)
        else:
            # Handle regular attributes
            if getattr(association, key) != value:
                setattr(association, key, value)


def set_attributes_from_dict(
    model, data_dict, db, on_update=ON_UPDATE_ASSOC_OPTIONS["raise"]
):
    """Recursively set attributes on a model from a dictionary, handling nested relationships."""
    relationship_map = {k: v for k, v in model.__mapper__.relationships.items()}

    for k, v in data_dict.items():
        if v is None:
            # Handle None value for single relationship
            if k in relationship_map:
                existing_assoc = getattr(model, k)
                if existing_assoc is not None and on_update == "raise":
                    # Raise error if trying to set to None when on_update=raise
                    raise IntegrityError(
                        f"Cannot update {k} when on_update='raise'. "
                        f"Trying to remove existing association. "
                        f"Use on_update='nilify_all' or 'delete_all' to allow updates.",
                        params=None,
                        orig=None,
                    )
            continue

        if k in relationship_map and isinstance(v, dict):
            # Handle single relationship
            model_entity = relationship_map[k].entity.entity

            if v.get("id"):
                association = model_entity.get(db, v.get("id"))
            else:
                association = model_entity()
                set_attributes_from_dict(association, v, db, on_update)

            setattr(model, k, association)

        elif k in relationship_map and isinstance(v, list):
            # Handle list of relationships
            model_entity = relationship_map[k].entity.entity

            association = []
            for item in v:
                if hasattr(item, "id") and item.id:
                    association.append(item)
                elif isinstance(item, dict) and item.get("id"):
                    association.append(model_entity.get(db, item.get("id")))
                else:
                    if isinstance(item, dict):
                        nested_model = model_entity()
                        set_attributes_from_dict(nested_model, item, db, on_update)
                        association.append(nested_model)
                    else:
                        association.append(item)

            setattr(model, k, association)
        else:
            # Handle regular attributes
            setattr(model, k, v)
