import json
from pathlib import Path
from typing import Type, TypeVar
from pydantic import BaseModel, Field, ValidationError

T = TypeVar("T", bound="AdvancedBaseModel")


class AdvancedBaseModel(BaseModel):
    """
    Advanced base class with:
    - Recursive updates
    - Strict validation (extra = forbid)
    - JSON file load/save
    """

    # 🔐 Strict: reject extra fields not defined in the model
    model_config = {
        "extra": "forbid"
    }

    def update(self: T, update_data: dict) -> T:
        """
        Recursively updates fields, validates types & structure.
        Raises ValidationError on unknown keys or invalid types.
        """
        updates = {}

        for key, value in update_data.items():
            if key not in self.model_fields:
                raise ValidationError(
                    f"Invalid key '{key}' for model '{self.__class__.__name__}'"
                )

            current = getattr(self, key)

            # 🔁 Recursively update nested models
            if isinstance(current, BaseModel) and isinstance(value, dict):
                # Validate using the nested model’s update logic
                updates[key] = current.update(value)

            else:
                # ✅ Validate this field value using Pydantic's model constructor
                try:
                    self.__class__(**{**self.model_dump(), key: value})
                except ValidationError as e:
                    raise e
                updates[key] = value

        return self.copy(update=updates)

    def save(self, path: str | Path, *, indent: int = 2) -> None:
        """
        Save the model to a JSON file.
        """
        path = Path(path)
        path.write_text(self.model_dump_json(indent=indent))

    @classmethod
    def load(cls: Type[T], path: str | Path, fallback: dict | None = None) -> T:
        """
        Load model from JSON file. If file not found, use fallback or raise.
        """
        path = Path(path)
        if not path.exists():
            if fallback is not None:
                return cls(**fallback)
            raise FileNotFoundError(f"Settings file not found: {path}")
        try:
            data = json.loads(path.read_text())
            return cls(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Invalid data in file: {e}")

    def update_and_save(self: T, update_data: dict, path: str | Path) -> T:
        """
        Recursively update model and save to file.
        """
        updated = self.update(update_data)
        updated.save(path)
        return updated
