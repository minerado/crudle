from typing import Any, Dict, List, Optional, Type, Union, get_origin, get_args
from datetime import datetime, timezone
import inspect
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError, MultipleResultsFound

from ...core.interface import AdapterInterface
from ...utils import flatten_dict


ALLOWED_OPERATORS = ["eq", "gt", "ge", "lt", "le", "ne", "in", "ni", "q"]
DEFAULT_QUERY_LIMIT = 25
ON_UPDATE_ASSOC_OPTIONS = {
    "raise": "raise",
    "nilify_all": "nilify_all",
    "delete_all": "delete_all",
}


class NotLoaded:
    """Represents a relationship that hasn't been loaded yet."""

    def __repr__(self):
        return "NotLoaded"

    def __bool__(self):
        return False

    def __eq__(self, other):
        return isinstance(other, NotLoaded)

    def __ne__(self, other):
        return not isinstance(other, NotLoaded)


class MemoryAdapter(AdapterInterface):
    """In-memory adapter that mimics SQLAlchemy adapter functionality.

    This adapter provides a complete in-memory implementation of all CRUD operations
    with support for relationships, complex queries, and advanced features.
    """

    def __init__(self):
        """Initialize the memory adapter with empty data stores."""
        # Main data storage: {model_class: {id: instance}}
        self._data = {}

        # Auto-incrementing ID counters: {model_class: next_id}
        self._counters = {}

        # Query history for debugging
        self._query_history = []

    def _get_next_id(self, model_class: Type) -> int:
        """Get the next available ID for a model class."""
        if model_class not in self._counters:
            self._counters[model_class] = 1
        else:
            self._counters[model_class] += 1
        return self._counters[model_class]

    def _infer_relationships(self, model_class: Type) -> Dict[str, Dict[str, Any]]:
        """Infer relationships from Pydantic model fields."""
        relationships = {}

        if not inspect.isclass(model_class) or not issubclass(model_class, BaseModel):
            return relationships

        # Get model fields from Pydantic
        if hasattr(model_class, "model_fields"):
            fields = model_class.model_fields
        elif hasattr(model_class, "__fields__"):
            fields = model_class.__fields__
        else:
            return relationships

        for field_name, field_info in fields.items():
            field_type = (
                field_info.annotation
                if hasattr(field_info, "annotation")
                else field_info
            )

            # Check if it's a relationship field
            if self._is_relationship_field(field_type):
                relationships[field_name] = {
                    "type": self._get_relationship_type(field_type),
                    "related_model": self._get_related_model(field_type),
                    "is_optional": self._is_optional_type(field_type),
                    "is_list": self._is_list_type(field_type),
                }

        return relationships

    def _is_relationship_field(self, field_type: Any) -> bool:
        """Check if a field represents a relationship."""
        # Check if it's a Pydantic model (not primitive types)
        if inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            return True

        # Check if it's a list of Pydantic models
        origin = get_origin(field_type)
        if origin is list:
            args = get_args(field_type)
            if args and inspect.isclass(args[0]) and issubclass(args[0], BaseModel):
                return True

        # Check if it's Optional[Model] or Union[None, Model]
        if origin is Union:
            args = get_args(field_type)
            for arg in args:
                if inspect.isclass(arg) and issubclass(arg, BaseModel):
                    return True

        return False

    def _get_relationship_type(self, field_type: Any) -> str:
        """Determine the relationship type."""
        origin = get_origin(field_type)

        if origin is list:
            # For now, assume all lists are one_to_many
            # In a more sophisticated implementation, we could check for bidirectional relationships
            return "one_to_many"
        elif origin is Union:
            # Optional[Model] - one_to_one
            return "one_to_one"
        elif inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            return "one_to_one"
        else:
            return "one_to_one"  # Default

    def _get_related_model(self, field_type: Any) -> Type[BaseModel]:
        """Extract the related model class."""
        if inspect.isclass(field_type) and issubclass(field_type, BaseModel):
            return field_type

        origin = get_origin(field_type)
        if origin is list:
            args = get_args(field_type)
            if args and inspect.isclass(args[0]) and issubclass(args[0], BaseModel):
                return args[0]

        if origin is Union:
            args = get_args(field_type)
            for arg in args:
                if inspect.isclass(arg) and issubclass(arg, BaseModel):
                    return arg

        return None

    def _is_optional_type(self, field_type: Any) -> bool:
        """Check if field type is optional (Union with None)."""
        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            return type(None) in args
        return False

    def _is_list_type(self, field_type: Any) -> bool:
        """Check if field type is a list."""
        return get_origin(field_type) is list

    def _ensure_model_data(self, model_class: Type) -> Dict[int, Any]:
        """Ensure data storage exists for a model class."""
        if model_class not in self._data:
            self._data[model_class] = {}
        return self._data[model_class]

    def _snapshot_store(self) -> Dict[str, Any]:
        """Freeze store + counters for insert/update rollback.

        Deep-copies Pydantic instances so in-place association mutations
        (e.g. ``nilify_all`` FK clears) can be undone on failure.
        """
        data: Dict[Any, Dict[Any, Any]] = {}
        for model, instances in self._data.items():
            frozen: Dict[Any, Any] = {}
            for instance_id, instance in instances.items():
                if isinstance(instance, BaseModel):
                    frozen[instance_id] = instance.model_copy(deep=True)
                else:
                    frozen[instance_id] = instance
            data[model] = frozen
        return {"data": data, "counters": dict(self._counters)}

    def _restore_store(self, snapshot: Dict[str, Any]) -> None:
        """Restore store + counters after a failed write graph."""
        self._data = {
            model: dict(instances) for model, instances in snapshot["data"].items()
        }
        self._counters = dict(snapshot["counters"])

    def _create_instance(self, model_class: Type, **kwargs) -> Any:
        """Create a model instance with auto-generated ID and metadata."""
        # Generate ID if not provided
        if "id" not in kwargs:
            kwargs["id"] = self._get_next_id(model_class)

        try:
            # Use Pydantic for model creation if it's a BaseModel
            if inspect.isclass(model_class) and issubclass(model_class, BaseModel):
                # Process nested relationships first
                processed_kwargs = self._process_nested_relationships(
                    model_class, kwargs
                )
                instance = model_class(**processed_kwargs)

                # Store in data using the ID
                instance_id = getattr(instance, "id", kwargs["id"])
                model_data = self._ensure_model_data(model_class)
                if instance_id in model_data:
                    raise IntegrityError(
                        f"Duplicate primary key for {model_class.__name__}: "
                        f"{instance_id}",
                        params=None,
                        orig=None,
                    )
                model_data[instance_id] = instance

                # Set foreign keys on related objects
                self._set_foreign_keys(instance, processed_kwargs)

                # For insert, we want to return the relationships as they were created
                # Only set unloaded relationships to NotLoaded for lazy loading on retrieval
                # Set unloaded relationships to NotLoaded for any relationships not explicitly provided
                self._set_unloaded_relationships_for_insert(instance, processed_kwargs)

                # Return a copy to prevent direct mutation
                return self._create_immutable_copy(instance)
            else:
                # Fallback to old method for non-Pydantic models
                return self._create_simple_instance(model_class, **kwargs)

        except ValidationError as e:
            raise ValueError(f"Validation error creating {model_class.__name__}: {e}")

    def _process_nested_relationships(
        self, model_class: Type, kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process nested relationships before creating the instance."""
        processed_kwargs = kwargs.copy()

        # Get relationship information
        relationships = self._infer_relationships(model_class)

        for field_name, rel_info in relationships.items():
            if field_name in processed_kwargs:
                value = processed_kwargs[field_name]
                processed_value = self._process_relationship_value(
                    field_name, value, rel_info
                )
                processed_kwargs[field_name] = processed_value

        return processed_kwargs

    def _process_relationship_value(
        self, field_name: str, value: Any, rel_info: Dict[str, Any]
    ) -> Any:
        """Process a relationship value, handling both existing objects and new data."""
        if value is None:
            return None

        related_model = rel_info["related_model"]
        is_list = rel_info["is_list"]

        if is_list:
            if not isinstance(value, list):
                value = [value]

            processed_items = []
            for item in value:
                processed_item = self._process_single_relationship_item(
                    item, related_model
                )
                processed_items.append(processed_item)
            return processed_items
        else:
            return self._process_single_relationship_item(value, related_model)

    def _process_single_relationship_item(self, item: Any, related_model: Type) -> Any:
        """Process a single relationship item."""
        if isinstance(item, dict):
            # Check if it's a reference to existing object by ID
            if "id" in item:
                existing_obj = self.get(related_model, item["id"])
                if existing_obj:
                    # Existing row: ignore other fields (no update-on-link).
                    return existing_obj
                raise ValueError(
                    f"No {related_model.__name__} found with id={item['id']}"
                )
            # New nested data
            return self._create_instance(related_model, **item)
        elif hasattr(item, "id") and item.id is not None:
            # It's an existing object
            return item
        else:
            # It's some other type, return as-is
            return item

    def _set_foreign_keys(
        self, instance: Any, processed_kwargs: Dict[str, Any]
    ) -> None:
        """Set foreign keys on related objects after creating the main instance."""
        relationships = self._infer_relationships(type(instance))

        for field_name, rel_info in relationships.items():
            if field_name in processed_kwargs:
                value = processed_kwargs[field_name]
                if value is not None:
                    self._set_foreign_key_on_related_objects(
                        instance, field_name, value, rel_info
                    )

                    # Handle bidirectional relationships by updating the reverse side
                    self._update_reverse_relationships(
                        instance, field_name, value, rel_info
                    )

    def _set_foreign_key_on_related_objects(
        self, instance: Any, field_name: str, value: Any, rel_info: Dict[str, Any]
    ) -> None:
        """Set foreign keys on related objects."""
        is_list = rel_info["is_list"]

        if is_list and isinstance(value, list):
            for item in value:
                self._set_foreign_key_on_single_object(
                    instance, field_name, item, rel_info
                )
        elif not is_list:
            self._set_foreign_key_on_single_object(
                instance, field_name, value, rel_info
            )

    def _set_foreign_key_on_single_object(
        self, instance: Any, field_name: str, related_obj: Any, rel_info: Dict[str, Any]
    ) -> None:
        """Set foreign key on a single related object."""
        if hasattr(related_obj, "id") and related_obj.id is not None:
            # Determine the foreign key field name
            foreign_key_field = self._get_foreign_key_field_name(
                field_name, type(instance)
            )

            if foreign_key_field:
                if rel_info["type"] == "one_to_many":
                    # Foreign key is on the related object - create a copy and update stored version
                    if hasattr(related_obj, foreign_key_field):
                        # Create a copy of the related object with updated foreign key
                        related_obj_copy = self._create_immutable_copy(related_obj)
                        setattr(related_obj_copy, foreign_key_field, instance.id)
                        # Update the stored object
                        self._ensure_model_data(type(related_obj))[related_obj.id] = (
                            related_obj_copy
                        )
                elif rel_info["type"] == "one_to_one":
                    # Foreign key is on the current instance — mutate it in place so
                    # callers that keep this object (and a later store overwrite)
                    # still see the FK.
                    if hasattr(instance, foreign_key_field):
                        setattr(instance, foreign_key_field, related_obj.id)

    def _get_foreign_key_field_name(
        self, relationship_field: str, parent_model_class: Type
    ) -> Optional[str]:
        """Get the foreign key field name for a relationship."""
        # Get the related model class
        relationships = self._infer_relationships(parent_model_class)
        if relationship_field not in relationships:
            return None

        related_model = relationships[relationship_field]["related_model"]
        if not related_model:
            return None

        # For one-to-many relationships, the foreign key is on the "many" side (related model)
        # For one-to-one relationships, the foreign key is on the side that "belongs to" the other
        # For many-to-many relationships, there's no direct foreign key

        if relationships[relationship_field]["type"] == "one_to_many":
            # Foreign key is on the related model (the "many" side)
            patterns = [
                f"{parent_model_class.__name__.lower()}_id",  # ItemList -> itemlist_id
            ]
            # Convert CamelCase to snake_case for foreign key naming
            parent_name = parent_model_class.__name__
            snake_case = "".join(
                [
                    "_" + c.lower() if c.isupper() and i > 0 else c.lower()
                    for i, c in enumerate(parent_name)
                ]
            )
            patterns.insert(0, f"{snake_case}_id")

            # Check if any of these patterns exist in the related model
            for pattern in patterns:
                if (
                    hasattr(related_model, "model_fields")
                    and pattern in related_model.model_fields
                ):
                    return pattern
                elif (
                    hasattr(related_model, "__fields__")
                    and pattern in related_model.__fields__
                ):
                    return pattern

        elif relationships[relationship_field]["type"] == "one_to_one":
            # Foreign key is on the current model (the side that "belongs to")
            patterns = [
                f"{relationship_field}_id",  # item_type -> item_type_id
            ]

            # Check if any of these patterns exist in the current model
            for pattern in patterns:
                if (
                    hasattr(parent_model_class, "model_fields")
                    and pattern in parent_model_class.model_fields
                ):
                    return pattern
                elif (
                    hasattr(parent_model_class, "__fields__")
                    and pattern in parent_model_class.__fields__
                ):
                    return pattern

        return None

    def _update_reverse_relationships(
        self, instance: Any, field_name: str, value: Any, rel_info: Dict[str, Any]
    ) -> None:
        """Update reverse relationships to maintain bidirectional consistency."""
        if isinstance(value, list):
            # One-to-many or many-to-many: update each related object
            for related_obj in value:
                if isinstance(related_obj, BaseModel):
                    self._update_reverse_relationship_for_object(
                        instance, field_name, related_obj
                    )
        elif isinstance(value, BaseModel):
            # One-to-one: update the single related object
            self._update_reverse_relationship_for_object(instance, field_name, value)

    def _update_reverse_relationship_for_object(
        self, instance: Any, field_name: str, related_obj: Any
    ) -> None:
        """Update the reverse relationship for a single related object.

        Always merges against the canonical store row when ``related_obj`` has
        an id. Payload copies may still carry ``NotLoaded`` / stale lists; those
        must not wipe existing reverse members.
        """
        reverse_field_name = self._get_reverse_relationship_field_name(
            field_name, type(instance), type(related_obj)
        )
        if not reverse_field_name:
            return

        related_model = type(related_obj)
        related_id = getattr(related_obj, "id", None)
        store = self._ensure_model_data(related_model)
        base = store.get(related_id) if related_id is not None else None
        if base is None:
            base = related_obj

        reverse_info = self._infer_relationships(related_model).get(
            reverse_field_name, {}
        )
        is_list = bool(reverse_info.get("is_list"))
        current_value = getattr(base, reverse_field_name, None)

        related_obj_copy = self._create_immutable_copy(base)

        if is_list:
            # Never assign a bare instance into a list field (Pydantic iterates
            # model fields). Merge with store state instead of replacing.
            if isinstance(current_value, list):
                current_list = list(current_value)
            else:
                current_list = []

            instance_id = getattr(instance, "id", None)

            def _same_member(existing: Any) -> bool:
                if instance_id is not None and getattr(existing, "id", None) == instance_id:
                    return True
                return existing is instance

            if not any(_same_member(existing) for existing in current_list):
                current_list.append(instance)
            setattr(related_obj_copy, reverse_field_name, current_list)
        else:
            setattr(related_obj_copy, reverse_field_name, instance)

        if related_id is not None:
            store[related_id] = related_obj_copy

    def _get_reverse_relationship_field_name(
        self, field_name: str, parent_model: Type, related_model: Type
    ) -> Optional[str]:
        """Get the reverse relationship field name."""
        # For now, use simple naming conventions
        # In a more sophisticated implementation, we could use metadata or annotations

        # Check if the related model has a field that matches the parent model name
        parent_name_lower = parent_model.__name__.lower()

        # Check for common patterns
        patterns = [
            parent_name_lower,  # "item" for Item
            f"{parent_name_lower}s",  # "items" for Item
        ]

        # Check if any of these patterns exist in the related model
        for pattern in patterns:
            if (
                hasattr(related_model, "model_fields")
                and pattern in related_model.model_fields
            ):
                return pattern
            elif (
                hasattr(related_model, "__fields__")
                and pattern in related_model.__fields__
            ):
                return pattern

        return None

    def _set_unloaded_relationships_for_insert(
        self, instance: Any, provided_kwargs: Dict[str, Any]
    ) -> None:
        """Set unloaded relationships to NotLoaded for insert, but only for relationships not explicitly provided."""
        relationships = self._infer_relationships(type(instance))

        for field_name, rel_info in relationships.items():
            # Only set to NotLoaded if the relationship was not explicitly provided during insert
            if field_name not in provided_kwargs:
                setattr(instance, field_name, NotLoaded())

    def _set_unloaded_relationships(self, instance: Any) -> None:
        """Set unloaded relationships to NotLoaded for lazy loading."""
        relationships = self._infer_relationships(type(instance))

        for field_name, rel_info in relationships.items():
            # Always set relationships to NotLoaded for lazy loading
            # This ensures that relationships are not preloaded unless explicitly requested
            setattr(instance, field_name, NotLoaded())

    def _set_unloaded_relationships_preserve_loaded(self, instance: Any) -> None:
        """Set unloaded relationships to NotLoaded for lazy loading, but preserve loaded relationships."""
        relationships = self._infer_relationships(type(instance))

        for field_name, rel_info in relationships.items():
            current_value = getattr(instance, field_name, None)

            # Only set to NotLoaded if the relationship is not already loaded
            # A relationship is considered loaded if it's not None, not NotLoaded, and not an empty list
            if current_value is None or isinstance(current_value, NotLoaded):
                setattr(instance, field_name, NotLoaded())
            elif isinstance(current_value, list) and len(current_value) == 0:
                # Empty list means no relationships, so set to NotLoaded
                setattr(instance, field_name, NotLoaded())
            # Otherwise, keep the loaded relationship as is

    def _preload_relationships(self, instance: Any, preload: List[str]) -> Any:
        """Preload specified relationships for an instance and return a copy with loaded relationships."""
        relationships = self._infer_relationships(type(instance))

        # Create a copy of the instance to avoid mutating the original
        if isinstance(instance, BaseModel):
            # For Pydantic models, use model_copy to create a copy
            instance_copy = instance.model_copy()

            for rel_name in preload:
                if rel_name not in relationships:
                    continue  # Skip invalid relationship names

                rel_info = relationships[rel_name]
                current_value = getattr(instance, rel_name, None)

                # Only preload if it's NotLoaded
                if isinstance(current_value, NotLoaded):
                    loaded_value = self._load_relationship(instance, rel_name, rel_info)
                    setattr(instance_copy, rel_name, loaded_value)

            return instance_copy
        else:
            # For non-Pydantic models, create a shallow copy
            import copy

            instance_copy = copy.copy(instance)

            for rel_name in preload:
                if rel_name not in relationships:
                    continue  # Skip invalid relationship names

                rel_info = relationships[rel_name]
                current_value = getattr(instance, rel_name, None)

                # Only preload if it's NotLoaded
                if isinstance(current_value, NotLoaded):
                    loaded_value = self._load_relationship(instance, rel_name, rel_info)
                    setattr(instance_copy, rel_name, loaded_value)

            return instance_copy

    def _load_relationship(
        self, instance: Any, rel_name: str, rel_info: Dict[str, Any]
    ) -> Any:
        """Load a specific relationship for an instance."""
        if rel_info["type"] == "one_to_one":
            return self._load_one_to_one_relationship(instance, rel_name, rel_info)
        elif rel_info["type"] == "one_to_many":
            return self._load_one_to_many_relationship(instance, rel_name, rel_info)
        else:
            return NotLoaded()  # Unknown relationship type

    def _load_one_to_one_relationship(
        self, instance: Any, rel_name: str, rel_info: Dict[str, Any]
    ) -> Any:
        """Load a one-to-one relationship."""
        related_model = rel_info["related_model"]
        foreign_key_field = self._get_foreign_key_field_name(rel_name, type(instance))

        if not foreign_key_field:
            # For relationships without foreign keys, return NotLoaded
            return NotLoaded()

        foreign_key_value = getattr(instance, foreign_key_field, None)
        if foreign_key_value is None:
            # If there's no foreign key value, return NotLoaded to indicate
            # that this relationship hasn't been loaded yet
            return NotLoaded()

        return self.get(related_model, foreign_key_value)

    def _load_one_to_many_relationship(
        self, instance: Any, rel_name: str, rel_info: Dict[str, Any]
    ) -> List[Any]:
        """Load a one-to-many relationship."""
        related_model = rel_info["related_model"]
        foreign_key_field = self._get_foreign_key_field_name(rel_name, type(instance))

        if not foreign_key_field:
            # For many-to-many relationships, look for reverse relationships
            # Find all related objects that have this instance in their reverse relationship
            related_objects = []
            related_data = self._ensure_model_data(related_model)

            # Get the reverse relationship field name
            reverse_field_name = self._get_reverse_relationship_field_name(
                rel_name, type(instance), related_model
            )

            if reverse_field_name:
                for related_instance in related_data.values():
                    reverse_value = getattr(related_instance, reverse_field_name, None)
                    if isinstance(reverse_value, list) and instance in reverse_value:
                        related_objects.append(related_instance)
                    elif reverse_value == instance:
                        related_objects.append(related_instance)

            return related_objects if related_objects else NotLoaded()

        # Find all related objects with matching foreign key
        related_objects = []
        related_data = self._ensure_model_data(related_model)

        for related_instance in related_data.values():
            if getattr(related_instance, foreign_key_field, None) == instance.id:
                related_objects.append(related_instance)

        return related_objects

    def _create_immutable_copy(self, instance: Any) -> Any:
        """Create a deep copy of an instance to prevent direct mutation."""
        if isinstance(instance, BaseModel):
            # For Pydantic models, use model_copy() which creates a deep copy
            # This preserves NotLoaded relationships as they are
            return instance.model_copy()
        else:
            # For non-Pydantic models, use deepcopy
            import copy

            return copy.deepcopy(instance)

    def _get_serializable_data(
        self, instance: Any, preserve_notloaded: bool = False
    ) -> Dict[str, Any]:
        """Get serializable data from an instance, optionally preserving NotLoaded relationships."""
        if isinstance(instance, BaseModel):
            # Get the model fields to know what to include
            model_fields = type(instance).model_fields
            relationships = self._infer_relationships(type(instance))

            filtered_data = {}

            for field_name in model_fields.keys():
                value = getattr(instance, field_name, None)

                if isinstance(value, NotLoaded):
                    if preserve_notloaded:
                        # Preserve NotLoaded for copying
                        filtered_data[field_name] = value
                    else:
                        # Handle NotLoaded relationships based on their type
                        if field_name in relationships:
                            rel_info = relationships[field_name]
                            if rel_info["is_list"]:
                                # For list relationships, use empty list
                                filtered_data[field_name] = []
                            else:
                                # For single relationships, use None
                                filtered_data[field_name] = None
                        else:
                            # Fallback to None
                            filtered_data[field_name] = None
                else:
                    # Include the actual value
                    filtered_data[field_name] = value

            return filtered_data
        else:
            # For non-Pydantic models, return a dict of attributes
            return {
                key: getattr(instance, key)
                for key in dir(instance)
                if not key.startswith("_") and not callable(getattr(instance, key))
            }

    def _create_simple_instance(self, model_class: Type, **kwargs) -> Any:
        """Create a simple instance for non-Pydantic models (fallback)."""
        # Generate ID
        instance_id = self._get_next_id(model_class)

        # Create instance data
        instance_data = {
            "id": instance_id,
            **kwargs,
            "_metadata": {
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
        }

        # Create a simple object to hold the data
        instance = type("ModelInstance", (), instance_data)()

        # Store in data
        self._ensure_model_data(model_class)[instance_id] = instance

        # Return a copy to prevent direct mutation
        return self._create_immutable_copy(instance)

    def _update_instance(
        self, instance: Any, on_update_assocs: str = "raise", **kwargs
    ) -> Any:
        """Update an instance with new data, applying association strategies."""
        if on_update_assocs not in ON_UPDATE_ASSOC_OPTIONS:
            raise ValueError(
                f"Invalid on_update_assocs '{on_update_assocs}'. "
                f"Expected one of {list(ON_UPDATE_ASSOC_OPTIONS)}"
            )

        if isinstance(instance, BaseModel):
            snapshot = self._snapshot_store()
            try:
                relationships = self._infer_relationships(type(instance))
                # Work on the stored instance (already the live object)
                live = self._ensure_model_data(type(instance))[instance.id]
                live = self._preload_all_relationships(live)

                for field_name, rel_info in relationships.items():
                    if field_name in kwargs:
                        self._apply_on_update_assocs(
                            live, field_name, kwargs[field_name], rel_info, on_update_assocs
                        )

                processed_kwargs = self._process_nested_relationships(
                    type(instance), kwargs
                )

                updated_instance = live.model_copy()

                for key, value in processed_kwargs.items():
                    if key != "id":
                        setattr(updated_instance, key, value)

                validation_data = self._get_serializable_data(
                    updated_instance, preserve_notloaded=False
                )
                type(instance)(**validation_data)

                self._set_foreign_keys(updated_instance, processed_kwargs)
                self._ensure_model_data(type(instance))[instance.id] = updated_instance

                return updated_instance
            except ValidationError as e:
                self._restore_store(snapshot)
                raise ValueError(
                    f"Validation error updating {type(instance).__name__}: {e}"
                )
            except Exception:
                self._restore_store(snapshot)
                raise
        else:
            for key, value in kwargs.items():
                if key != "id":
                    setattr(instance, key, value)

            if hasattr(instance, "_metadata"):
                instance._metadata["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

            return instance

    def _apply_on_update_assocs(
        self,
        instance: Any,
        field_name: str,
        values: Any,
        rel_info: Dict[str, Any],
        on_update: str,
    ) -> None:
        """Apply raise / delete_all / nilify_all before replacing a relationship."""
        related_model = rel_info["related_model"]
        is_list = rel_info["is_list"]
        current = getattr(instance, field_name, None)
        if isinstance(current, NotLoaded):
            current = self._load_relationship(instance, field_name, rel_info)
            setattr(instance, field_name, current)

        if is_list:
            if values is None:
                values = []
            if not isinstance(values, list):
                raise ValueError(
                    f"Invalid association value for '{field_name}': "
                    f"expected list, got {type(values).__name__}"
                )

            current_list = current if isinstance(current, list) else []
            existing_ids = {obj.id for obj in current_list if getattr(obj, "id", None)}
            new_ids = set()
            for item in values:
                if isinstance(item, dict) and item.get("id"):
                    new_ids.add(item["id"])
                elif hasattr(item, "id") and item.id:
                    new_ids.add(item.id)

            removing = existing_ids - new_ids

            if on_update == "raise" and removing:
                raise IntegrityError(
                    f"Cannot update {field_name} when on_update='raise'. "
                    f"Trying to remove existing associations. "
                    f"Use on_update='nilify_all' or 'delete_all' to allow updates.",
                    params=None,
                    orig=None,
                )

            if on_update == "delete_all":
                for obj in list(current_list):
                    if obj.id in removing:
                        related_store = self._ensure_model_data(related_model)
                        related_store.pop(obj.id, None)

            elif on_update == "nilify_all":
                fk_field = self._get_foreign_key_field_name(
                    field_name, type(instance)
                )
                if fk_field:
                    for obj in list(current_list):
                        if obj.id in removing:
                            stored = self._ensure_model_data(related_model).get(obj.id)
                            if stored is not None:
                                setattr(stored, fk_field, None)
        # Singular relationships: replace freely (FK update); strategies mainly
        # apply to collection associations per SQLAlchemy usage in README.

    def _normalize_filter_params(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested filter dicts to dotted keys (SQLAlchemy parity).

        Also unwraps ``filter={...}`` the same way ``list`` does.
        """
        if not filters:
            return {}
        merged = {k: v for k, v in filters.items() if k != "filter"}
        nested = filters.get("filter")
        if isinstance(nested, dict):
            merged.update(nested)
        return dict(flatten_dict(merged))

    def _split_field_operation(self, field: str) -> tuple[str, str]:
        """Split field__op; raise on forbidden operators (SQLAlchemy parity)."""
        parts = field.split("__")
        if len(parts) == 2:
            field_name, operator = parts
            if operator not in ALLOWED_OPERATORS:
                raise Exception(f"Forbidden operator: {operator}")
            return field_name, operator
        return parts[0], "eq"

    def _matches_filters(self, instance: Any, filters: Dict[str, Any]) -> bool:
        """Check if an instance matches the given filters.

        Nested filters that share a relationship prefix (e.g. ``items.color`` and
        ``items.price__gt``) must be satisfied by the **same** related row —
        SQLAlchemy join + WHERE semantics — not by different children independently.
        """
        if not filters:
            return True

        root_filters: Dict[str, Any] = {}
        nested_by_relationship: Dict[str, Dict[str, Any]] = {}

        for field, value in filters.items():
            if "." in field:
                relationship_field, nested_field = field.split(".", 1)
                nested_by_relationship.setdefault(relationship_field, {})[
                    nested_field
                ] = value
            else:
                root_filters[field] = value

        for field, value in root_filters.items():
            if not self._field_matches(instance, field, value):
                return False

        for relationship_field, nested_filters in nested_by_relationship.items():
            if not self._relationship_matches_filters(
                instance, relationship_field, nested_filters
            ):
                return False

        return True

    def _relationship_matches_filters(
        self,
        instance: Any,
        relationship_field: str,
        nested_filters: Dict[str, Any],
    ) -> bool:
        """Match nested filters under one relationship (any-match for collections)."""
        if not hasattr(instance, relationship_field):
            return False

        relationship_value = getattr(instance, relationship_field)

        if isinstance(relationship_value, NotLoaded):
            return False

        if relationship_value is None:
            return False

        if isinstance(relationship_value, list):
            if not relationship_value:
                return False
            return any(
                self._matches_filters(related_item, nested_filters)
                for related_item in relationship_value
            )

        return self._matches_filters(relationship_value, nested_filters)

    def _field_matches(self, instance: Any, field: str, value: Any) -> bool:
        """Check if a field matches a value using various operators."""
        # Handle nested fields (e.g., "author.name" or "author.name__gt")
        if "." in field:
            return self._nested_field_matches(instance, field, value)

        field_name, operator = self._split_field_operation(field)

        # Handle Pydantic models
        if isinstance(instance, BaseModel):
            if field_name not in type(instance).model_fields:
                return False
            instance_value = getattr(instance, field_name)
        else:
            # Handle basic field access for non-Pydantic models
            if not hasattr(instance, field_name):
                return False
            instance_value = getattr(instance, field_name)

        return self._apply_operator(instance_value, operator, value)

    def _apply_operator(
        self, instance_value: Any, operator: str, filter_value: Any
    ) -> bool:
        """Apply a filter operator to compare instance value with filter value."""
        if operator not in ALLOWED_OPERATORS:
            raise Exception(f"Forbidden operator: {operator}")

        try:
            if operator == "eq":
                return instance_value == filter_value
            elif operator == "ne":
                # SQLAlchemy/SQL parity:
                # - field__ne=None → IS NOT NULL
                # - field__ne=x with NULL column → row excluded (NULL comparisons are unknown)
                if filter_value is None:
                    return instance_value is not None
                if instance_value is None:
                    return False
                return instance_value != filter_value
            elif operator in ("gt", "ge", "lt", "le"):
                # SQLAlchemy/SQL parity:
                # - NULL column vs value → row excluded (unknown)
                # - comparison with None filter value is rejected
                if filter_value is None:
                    raise Exception(
                        "Only '=', '!=', 'is_()', 'is_not()', "
                        "'is_distinct_from()', 'is_not_distinct_from()' "
                        "operators can be used with None/True/False"
                    )
                if instance_value is None:
                    return False
                if operator == "gt":
                    return instance_value > filter_value
                if operator == "ge":
                    return instance_value >= filter_value
                if operator == "lt":
                    return instance_value < filter_value
                return instance_value <= filter_value
            elif operator == "in":
                # SQLAlchemy/SQL parity:
                # - filter must be an expression list (None rejected)
                # - NULL column never matches IN (...), even if None is in the list
                if filter_value is None:
                    raise Exception(
                        "IN expression list, SELECT construct, or bound "
                        "parameter object expected, got None."
                    )
                if instance_value is None:
                    return False
                return instance_value in filter_value
            elif operator == "ni":
                # SQLAlchemy/SQL parity:
                # - filter must be an expression list (None rejected)
                # - NOT IN (... NULL ...) is never true for any row
                # - NULL column NOT IN (non-null values) is unknown → exclude
                # - NULL column NOT IN () is true (empty set)
                if filter_value is None:
                    raise Exception(
                        "IN expression list, SELECT construct, or bound "
                        "parameter object expected, got None."
                    )
                if any(v is None for v in filter_value):
                    return False
                if instance_value is None:
                    return len(filter_value) == 0
                return instance_value not in filter_value
            elif operator == "q":
                return self._text_search(instance_value, filter_value)
            else:
                raise Exception(f"Forbidden operator: {operator}")
        except (TypeError, ValueError):
            # If comparison fails (e.g., string vs int), return False
            return False

    def _text_search(self, instance_value: Any, search_term: str) -> bool:
        """Perform text search on instance value."""
        if instance_value is None:
            return False

        # Convert to string for searching
        text_value = str(instance_value).lower()
        search_term = search_term.lower()

        # Simple contains search (can be enhanced with regex later)
        return search_term in text_value

    def _nested_field_matches(self, instance: Any, field_path: str, value: Any) -> bool:
        """Check if a nested field matches a value."""
        # Split the field path (e.g., "items.color" -> ["items", "color"])
        path_parts = field_path.split(".")

        if len(path_parts) < 2:
            return False

        # Get the relationship field name and nested field name
        relationship_field = path_parts[0]
        nested_field = ".".join(path_parts[1:])

        # Get the relationship value from the instance
        if not hasattr(instance, relationship_field):
            return False

        relationship_value = getattr(instance, relationship_field)

        # Handle NotLoaded relationships
        if isinstance(relationship_value, NotLoaded):
            return False

        # Handle different relationship types
        if isinstance(relationship_value, list):
            # One-to-many relationship - check if any item matches
            for related_item in relationship_value:
                if self._field_matches(related_item, nested_field, value):
                    return True
            return False
        else:
            # One-to-one relationship - check the single item
            return self._field_matches(relationship_value, nested_field, value)

    def insert(self, model: Type, **kwargs) -> Any:
        """Insert a new record.

        Nested association creates are applied eagerly while building the
        graph; on failure the store and id counters are restored so partial
        nested rows are not left behind (SQLAlchemy session rollback parity).

        Args:
            model: The model class to insert
            **kwargs: Attributes for the new record

        Returns:
            The created model instance
        """
        snapshot = self._snapshot_store()
        try:
            instance = self._create_instance(model, **kwargs)
        except Exception:
            self._restore_store(snapshot)
            raise

        self._query_history.append(
            {
                "operation": "insert",
                "model": model.__name__,
                "data": kwargs,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return instance

    def _normalize_id(self, id: Any) -> Optional[int]:
        """Normalize an ID to int, or return None if the value is not a usable ID.

        Rejects bools (since bool is a subclass of int), None, collections, and
        other non-numeric values. Accepts int, whole-number float, and numeric str.
        """
        if isinstance(id, bool) or id is None:
            return None
        if isinstance(id, int):
            return id
        if isinstance(id, float):
            return int(id) if id.is_integer() else None
        if isinstance(id, str):
            try:
                return int(id)
            except ValueError:
                return None
        return None

    def get(
        self, model: Type, id: Union[str, int], preload: List[str] = None
    ) -> Optional[Any]:
        """Get a record by ID.

        Args:
            model: The model class
            id: The record ID
            preload: List of relationships to preload

        Returns:
            The model instance or None if not found
        """
        normalized_id = self._normalize_id(id)
        if normalized_id is None:
            return None

        model_data = self._ensure_model_data(model)
        instance = model_data.get(normalized_id)

        if instance is None:
            return None

        # Always return a deep copy to prevent direct mutation
        instance_copy = self._create_immutable_copy(instance)

        # Set unloaded relationships to NotLoaded for lazy loading, but preserve loaded relationships
        self._set_unloaded_relationships_preserve_loaded(instance_copy)

        if preload:
            instance_copy = self._preload_relationships(instance_copy, preload)

        # Log query
        self._query_history.append(
            {
                "operation": "get",
                "model": model.__name__,
                "id": id,
                "preload": preload or [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return instance_copy

    def get_by(
        self, model: Type, preload: List[str] = None, **filters
    ) -> Optional[Any]:
        """Get exactly one record matching filters, or None.

        Shares the list filter / assoc dialect. Raises
        ``MultipleResultsFound`` if more than one record matches.

        ``limit`` / ``skip`` / ``sort`` / ``select`` / ``return_dict`` /
        ``distinct_on`` are ignored (same idea as ``count``).
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
            for key, value in filters.items()
            if key not in ignored_params
        }

        matches = self._query_instances(model, filter_params)
        if not matches:
            return None
        if len(matches) > 1:
            raise MultipleResultsFound(
                f"Multiple rows were found when one or none was required for {model.__name__}"
            )

        instance = matches[0]
        instance_copy = self._create_immutable_copy(instance)
        self._set_unloaded_relationships(instance_copy)

        if preload:
            instance_copy = self._preload_relationships(instance_copy, preload)

        self._query_history.append(
            {
                "operation": "get_by",
                "model": model.__name__,
                "filters": filter_params,
                "preload": preload or [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return instance_copy

    def _query_instances(
        self, model: Type, filters: Dict[str, Any] | None = None
    ) -> List[Any]:
        """Filter stored instances without pagination (used by get_by/count/list)."""
        filter_params = self._normalize_filter_params(filters or {})
        model_data = self._ensure_model_data(model)
        instances = list(model_data.values())

        if not filter_params:
            return instances

        needs_preload = self._needs_preload_for_filtering(filter_params)
        if needs_preload:
            instances = [self._preload_all_relationships(inst) for inst in instances]

        return [
            inst for inst in instances if self._matches_filters(inst, filter_params)
        ]

    def list(self, model: Type, preload: List[str] = None, **filters) -> List[Any]:
        """List records with optional filters.

        Args:
            model: The model class
            preload: List of relationships to preload
            **filters: Filter criteria and special parameters (sort, limit, skip, select, return_dict, distinct_on)

        Returns:
            List of model instances
        """
        special_params = {}
        filter_params = {}

        for key, value in filters.items():
            if key in ["sort", "limit", "skip", "select", "return_dict", "distinct_on"]:
                special_params[key] = value
            elif key == "filter" and isinstance(value, dict):
                # SQLAlchemy parity: filter={...} merges into filter params (then flattened)
                filter_params.update(value)
            else:
                filter_params[key] = value

        needs_preload = self._needs_preload_for_filtering(
            self._normalize_filter_params(filter_params)
        )
        instances = self._query_instances(model, filter_params)

        if "sort" in special_params:
            for spec in special_params["sort"] or []:
                field = spec.get("field", "")
                if "." in field:
                    for inst in instances:
                        self._preload_select_path(inst, field.split("."))
            instances = self._apply_sorting(instances, special_params["sort"])

        if "distinct_on" in special_params:
            instances = self._apply_distinct(instances, special_params["distinct_on"])

        skip = special_params.get("skip", 0)
        limit = special_params.get("limit", DEFAULT_QUERY_LIMIT)

        if skip is None:
            skip = 0
        if not isinstance(skip, int):
            raise ValueError("skip must be an int")
        if skip < 0:
            raise ValueError("skip must be >= 0")

        if limit is not None:
            if not isinstance(limit, int):
                raise ValueError("limit must be an int or None")
            if limit < 0:
                raise ValueError("limit must be >= 0")

        if skip:
            instances = instances[skip:]
        if limit is not None:
            instances = instances[:limit]

        if "select" in special_params or special_params.get("return_dict", False):
            select_fields = special_params.get("select") or []
            if any("." in field for field in select_fields):
                for inst in instances:
                    for field in select_fields:
                        if "." in field and not field.startswith("count"):
                            self._preload_select_path(inst, field.split("."))
            instances = self._apply_field_selection(instances, special_params)
        else:
            instances = [self._create_immutable_copy(inst) for inst in instances]

            if not needs_preload:
                for instance in instances:
                    self._set_unloaded_relationships(instance)

            if preload:
                instances = [
                    self._preload_relationships(instance, preload)
                    for instance in instances
                ]

        self._query_history.append(
            {
                "operation": "list",
                "model": model.__name__,
                "filters": filter_params,
                "special_params": special_params,
                "preload": preload or [],
                "result_count": len(instances),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return instances

    def _apply_distinct(
        self, instances: List[Any], distinct_on: Union[bool, List[str]]
    ) -> List[Any]:
        """Apply distinct_on semantics (SQLAlchemy/Postgres-style first-row wins)."""
        if distinct_on is True:
            seen = set()
            result = []
            for inst in instances:
                key = getattr(inst, "id", id(inst))
                if key in seen:
                    continue
                seen.add(key)
                result.append(inst)
            return result

        if not distinct_on:
            return instances

        seen = set()
        result = []
        for inst in instances:
            key_parts = []
            for field in distinct_on:
                if "." in field:
                    key_parts.append(self._get_nested_field_value(inst, field))
                else:
                    key_parts.append(getattr(inst, field, None))
            key = tuple(key_parts)
            if key in seen:
                continue
            seen.add(key)
            result.append(inst)
        return result

    def _apply_sorting(
        self, instances: List[Any], sort_specs: List[Dict[str, str]]
    ) -> List[Any]:
        """Apply sorting with SQLite-like NULLS (first on ASC, last on DESC).

        Uses stable multi-pass sorts so datetimes/strings/numbers and mixed
        ``order`` spellings all work without type-specific key hacks.
        """
        if not sort_specs:
            return instances

        def field_value(instance: Any, field: str) -> Any:
            if "." in field:
                value = self._get_nested_field_value(instance, field)
            elif hasattr(instance, field):
                value = getattr(instance, field)
            else:
                value = None

            if isinstance(value, NotLoaded):
                return None
            # Collection hops are undefined for Memory sort; treat as missing
            if isinstance(value, list):
                return None
            return value

        def sort_key(instance: Any, field: str):
            value = field_value(instance, field)
            # (0, ...) sorts before (1, ...) on ASC → NULLS first (SQLite-like)
            if value is None:
                return (0, None)
            return (1, value)

        ordered = list(instances)
        for spec in reversed(sort_specs):
            field = spec["field"]
            order = str(spec.get("order", "asc")).lower()
            reverse = order == "desc"
            ordered = sorted(
                ordered,
                key=lambda inst, f=field: sort_key(inst, f),
                reverse=reverse,
            )

        return ordered

    def _preload_select_path(self, instance: Any, parts: List[str]) -> None:
        """Load relationship hops along a select path (leaf scalar may remain).

        ``_preload_relationships`` returns a copy; we write loaded values back onto
        ``instance`` so projection sees them without re-querying.
        """
        if len(parts) <= 1 or instance is None or isinstance(instance, NotLoaded):
            return

        head, *rest = parts
        if not hasattr(instance, head):
            return

        value = getattr(instance, head)
        if isinstance(value, NotLoaded):
            loaded_copy = self._preload_relationships(instance, [head])
            value = getattr(loaded_copy, head)
            setattr(instance, head, value)

        if isinstance(value, NotLoaded) or value is None:
            return

        if isinstance(value, list):
            for item in value:
                self._preload_select_path(item, rest)
            return

        self._preload_select_path(value, rest)

    def _project_select_paths(
        self, instance: Any, paths: List[List[str]]
    ) -> Dict[str, Any]:
        """Project multi-hop select paths into a nested dict (lists at collections)."""
        if instance is None or isinstance(instance, NotLoaded):
            return None

        grouped: Dict[str, List[List[str]]] = {}
        for path in paths:
            if not path:
                continue
            head, *tail = path
            grouped.setdefault(head, []).append(tail)

        result: Dict[str, Any] = {}
        for head, tails in grouped.items():
            if not hasattr(instance, head):
                continue

            value = getattr(instance, head)
            if isinstance(value, NotLoaded):
                result[head] = None
                continue

            empty_tails = [tail for tail in tails if not tail]
            nested_tails = [tail for tail in tails if tail]

            if empty_tails and not nested_tails:
                # Whole relationship / object
                if isinstance(value, list):
                    result[head] = [
                        self._get_serializable_data(item, preserve_notloaded=False)
                        if isinstance(item, BaseModel)
                        else item
                        for item in value
                    ]
                elif isinstance(value, BaseModel):
                    result[head] = self._get_serializable_data(
                        value, preserve_notloaded=False
                    )
                else:
                    result[head] = value
                continue

            if nested_tails:
                if isinstance(value, list):
                    projected_items = []
                    for item in value:
                        projected = self._project_select_paths(item, nested_tails)
                        if projected is not None:
                            projected_items.append(projected)
                    result[head] = projected_items
                elif value is None:
                    result[head] = None
                else:
                    projected = self._project_select_paths(value, nested_tails)
                    result[head] = projected
                continue

            # Scalar / direct attr (empty_tails only already handled)
            if isinstance(value, NotLoaded):
                result[head] = None
            else:
                result[head] = value

        return result

    def _apply_field_selection(
        self, instances: List[Any], special_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply field selection and return format to instances."""
        select_fields = special_params.get("select", [])
        return_dict = special_params.get("return_dict", False)

        if not select_fields and not return_dict:
            return instances

        result = []

        for instance in instances:
            if isinstance(instance, BaseModel):
                if select_fields:
                    paths = [
                        field.split(".")
                        for field in select_fields
                        if not field.startswith("count")
                    ]
                    item_dict = self._project_select_paths(instance, paths) or {}
                else:
                    # Return all fields as dictionary
                    item_dict = self._get_serializable_data(
                        instance, preserve_notloaded=False
                    )

                result.append(item_dict)
            else:
                # For non-Pydantic models, create a simple dictionary
                if select_fields:
                    item_dict = {}
                    for field in select_fields:
                        if hasattr(instance, field):
                            item_dict[field] = getattr(instance, field)
                        else:
                            item_dict[field] = None
                else:
                    item_dict = {
                        key: getattr(instance, key)
                        for key in dir(instance)
                        if not key.startswith("_")
                        and not callable(getattr(instance, key))
                    }
                result.append(item_dict)

        return result

    def _needs_preload_for_filtering(self, filter_params: Dict[str, Any]) -> bool:
        """Check if we need to preload relationships for nested filtering."""
        for field in filter_params.keys():
            if "." in field:
                return True
        return False

    def _preload_all_relationships(self, instance: Any) -> Any:
        """Preload all relationships for an instance with limited depth to avoid circular references."""
        if isinstance(instance, BaseModel):
            relationships = self._infer_relationships(type(instance))
            preload_fields = list(relationships.keys())
            preloaded_instance = self._preload_relationships(instance, preload_fields)

            # Preload relationships of related objects (one level deep only to avoid circular references)
            for field_name in preload_fields:
                if hasattr(preloaded_instance, field_name):
                    related_value = getattr(preloaded_instance, field_name)
                    if isinstance(related_value, list):
                        # One-to-many: preload each item (one level deep)
                        preloaded_items = []
                        for item in related_value:
                            if isinstance(item, BaseModel):
                                # Preload only the direct relationships of the item
                                item_relationships = self._infer_relationships(
                                    type(item)
                                )
                                item_preload_fields = list(item_relationships.keys())
                                preloaded_item = self._preload_relationships(
                                    item, item_preload_fields
                                )
                                preloaded_items.append(preloaded_item)
                            else:
                                preloaded_items.append(item)
                        setattr(preloaded_instance, field_name, preloaded_items)
                    elif isinstance(related_value, BaseModel):
                        # One-to-one: preload the single item (one level deep)
                        item_relationships = self._infer_relationships(
                            type(related_value)
                        )
                        item_preload_fields = list(item_relationships.keys())
                        preloaded_item = self._preload_relationships(
                            related_value, item_preload_fields
                        )
                        setattr(preloaded_instance, field_name, preloaded_item)

            return preloaded_instance
        return instance

    def _get_nested_field_value(self, instance: Any, field_path: str) -> Any:
        """Get a nested field value from an instance (e.g., 'item_type.name')."""
        parts = field_path.split(".")
        current = instance

        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
                if isinstance(current, NotLoaded):
                    return None
            else:
                return None

        return current

    def update(self, model: Type, *args, **kwargs) -> Optional[Any]:
        """Update a record by ID.

        Args:
            model: The model class
            *args: Positional arguments (first one is treated as id)
            **kwargs: Attributes to update (including id if passed as keyword).
                Also accepts on_update_assocs and commit (commit ignored).

        Returns:
            The updated model instance or None if not found
        """
        on_update_assocs = kwargs.pop(
            "on_update_assocs", ON_UPDATE_ASSOC_OPTIONS["raise"]
        )
        kwargs.pop("commit", None)  # session concept; ignored for Memory

        if args:
            id = args[0]
        elif "id" in kwargs:
            id = kwargs.pop("id")
        else:
            return None

        stored = self._ensure_model_data(model).get(self._normalize_id(id))
        if stored is None:
            return None

        updated_instance = self._update_instance(
            stored, on_update_assocs=on_update_assocs, **kwargs
        )

        self._query_history.append(
            {
                "operation": "update",
                "model": model.__name__,
                "id": id,
                "data": kwargs,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        result = self._create_immutable_copy(updated_instance)

        relationships = self._infer_relationships(type(updated_instance))
        updated_relationships = {name for name in relationships if name in kwargs}

        for field_name in relationships:
            if field_name not in updated_relationships:
                setattr(result, field_name, NotLoaded())

        return result

    def update_by(
        self,
        model: Type,
        filters: Dict[str, Any],
        should_raise: bool = False,
        **kwargs,
    ) -> Optional[Any]:
        """Update a record by specified filters.

        Args:
            model: The model class
            filters: Filter criteria to find the record
            should_raise: Raise if no record found
            **kwargs: Attributes to update (on_update_assocs / commit supported)

        Returns:
            The updated model instance or None if not found
        """
        on_update_assocs = kwargs.pop(
            "on_update_assocs", ON_UPDATE_ASSOC_OPTIONS["raise"]
        )
        kwargs.pop("commit", None)

        try:
            instance = self.get_by(model, **filters)
        except MultipleResultsFound:
            raise

        if instance is None:
            if should_raise:
                raise ValueError(f"No {model.__name__} found matching filters: {filters}")
            return None

        stored = self._ensure_model_data(model).get(instance.id)
        updated_instance = self._update_instance(
            stored, on_update_assocs=on_update_assocs, **kwargs
        )

        self._query_history.append(
            {
                "operation": "update_by",
                "model": model.__name__,
                "filters": filters,
                "data": kwargs,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        result = self._create_immutable_copy(updated_instance)

        relationships = self._infer_relationships(type(updated_instance))
        updated_relationships = {name for name in relationships if name in kwargs}

        for field_name in relationships:
            if field_name not in updated_relationships:
                setattr(result, field_name, NotLoaded())

        return result

    @staticmethod
    def _attrs_for_upsert_insert(filters: Dict[str, Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build insert attrs for the upsert miss path.

        Strips update-only control keys so they are not written as fields.
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

        def merge_simple(src: Dict[str, Any]) -> None:
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

    def upsert_by(self, model: Type, filters: Dict[str, Any], **kwargs) -> Any:
        """Update exactly one match, or insert if none match.

        ``filters`` uses the ``get_by`` dialect (``MultipleResultsFound`` on
        ambiguity). On miss, simple equality filter keys merge into insert
        attrs when absent from ``**kwargs``. ``on_update_assocs`` /
        ``should_raise`` are not written as fields on insert;
        ``should_raise=True`` still raises on miss (never inserts).

        Args:
            model: The model class
            filters: Filter criteria to find the record
            **kwargs: Attributes for the record

        Returns:
            The updated or created model instance
        """
        updated = self.update_by(model, filters, **kwargs)
        if updated is not None:
            return updated

        return self.insert(model, **self._attrs_for_upsert_insert(filters, kwargs))

    def delete(self, model: Type, id: Union[str, int]) -> Optional[Any]:
        """Delete a record by ID (Ecto ``:nothing`` for related rows).

        Pops only the target from the store. Does not simulate SQLAlchemy /
        DB cascade, SET NULL, or RESTRICT.

        Args:
            model: The model class
            id: The record ID

        Returns:
            The deleted model instance or None if not found
        """
        normalized_id = self._normalize_id(id)
        if normalized_id is None:
            return None

        model_data = self._ensure_model_data(model)
        instance = model_data.pop(normalized_id, None)

        self._query_history.append(
            {
                "operation": "delete",
                "model": model.__name__,
                "id": id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return self._create_immutable_copy(instance) if instance else None

    def delete_by(self, model: Type, **filters) -> Optional[Any]:
        """Delete exactly one record matching filters, or None.

        Uses ``get_by`` (same filter dialect / MultipleResultsFound /
        ignored list options), then removes that row from the store.
        """
        instance = self.get_by(model, **filters)
        if instance is None:
            return None

        model_data = self._ensure_model_data(model)
        deleted_instance = model_data.pop(instance.id, None)

        self._query_history.append(
            {
                "operation": "delete_by",
                "model": model.__name__,
                "filters": filters,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return (
            self._create_immutable_copy(deleted_instance) if deleted_instance else None
        )

    def count(self, model: Type, **filters) -> int:
        """Count records matching filters.

        Shares the list filter / assoc / ``distinct_on`` dialect. Non-null
        checks use filters (e.g. ``price__ne=None``). ``limit`` / ``skip`` /
        ``sort`` / ``select`` / ``return_dict`` are ignored.
        """
        ignored_params = {
            "limit",
            "skip",
            "sort",
            "select",
            "return_dict",
        }

        distinct_on = filters.get("distinct_on", [])
        filter_params = {
            key: value
            for key, value in filters.items()
            if key not in ignored_params and key != "distinct_on"
        }

        instances = self._query_instances(model, filter_params)

        use_distinct = distinct_on is True or (
            isinstance(distinct_on, list) and len(distinct_on) > 0
        )
        if use_distinct:
            instances = self._apply_distinct(instances, distinct_on)

        result_count = len(instances)

        self._query_history.append(
            {
                "operation": "count",
                "model": model.__name__,
                "filters": filter_params,
                "special_params": {"distinct_on": distinct_on} if use_distinct else {},
                "result_count": result_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return result_count

    def get_query_history(self) -> List[Dict[str, Any]]:
        """Get the query history for debugging.

        Returns:
            List of query operations performed
        """
        return self._query_history.copy()

    def clear_data(self):
        """Clear all stored data (useful for testing)."""
        self._data.clear()
        self._counters.clear()
        self._query_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored data.

        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_models": len(self._data),
            "total_instances": sum(len(instances) for instances in self._data.values()),
            "queries_executed": len(self._query_history),
            "models": {},
        }

        for model_class, instances in self._data.items():
            stats["models"][model_class.__name__] = {
                "instance_count": len(instances),
                "next_id": self._counters.get(model_class, 1),
            }

        return stats
