import copy
from typing import Type

from pydantic import Field, create_model

from nekro_agent.core.config import CoreConfig
from nekro_agent.core.core_utils import ConfigBase


def create_overridable_config_model(model_name: str, source_model: Type[ConfigBase]) -> Type[ConfigBase]:
    """
    Dynamically creates a Pydantic model class containing all overridable fields
    from a source model.

    For each overridable field `field_name: T` in the source model, two fields are created:
    - `enable_field_name: bool`: A toggle to enable/disable the override.
    - `field_name: T`: The field for the override value, inheriting properties from the source.
    """
    new_fields = {}
    for name, field in source_model.model_fields.items():
        is_overridable = isinstance(field.json_schema_extra, dict) and field.json_schema_extra.get("overridable")

        if is_overridable:
            # Create a copy of the field to avoid modifying the original
            value_field = copy.deepcopy(field)

            # The title for the enable toggle
            enable_title = f"覆盖: {field.title or name}"
            new_fields[f"enable_{name}"] = (
                bool,
                Field(default=False, title=enable_title),
            )

            # The value field itself
            # Update description to clarify it's an override value
            value_field.description = f"覆盖值: {field.description}" if field.description else "此配置项的覆盖值"
            # Add a reference to the enable toggle for the frontend
            extra = value_field.json_schema_extra.copy() if isinstance(value_field.json_schema_extra, dict) else {}
            extra["enable_toggle"] = f"enable_{name}"
            value_field.json_schema_extra = extra
            new_fields[name] = (field.annotation, value_field)

    # Create the new Pydantic model
    model = create_model(model_name, **new_fields, __base__=ConfigBase)

    # Set a default config key for this new model type, although it will be overridden
    model.set_config_key("overrides")

    return model


# Create the single OverridableConfig class to be used by adapters and channels
OverridableConfig = create_overridable_config_model("OverridableConfig", CoreConfig)
