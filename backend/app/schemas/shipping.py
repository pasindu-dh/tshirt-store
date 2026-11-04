from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ShippingMethodCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    fee_lkr: int = Field(ge=0, le=10000000)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0, le=100000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()

        if not stripped:
            raise ValueError("Name cannot be blank")

        return stripped

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()


class ShippingMethodUpdate(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=80
    )
    description: str | None = Field(
        default=None, max_length=500
    )
    fee_lkr: int | None = Field(
        default=None, ge=0, le=10000000
    )
    is_active: bool | None = None
    sort_order: int | None = Field(
        default=None, ge=0, le=100000
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return value

        stripped = value.strip()

        if not stripped:
            raise ValueError("Name cannot be blank")

        return stripped

    @field_validator("description")
    @classmethod
    def strip_description(
        cls, value: str | None
    ) -> str | None:
        return value.strip() if value is not None else value

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one field to update"
            )

        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        return self


class ShippingMethodOut(BaseModel):
    id: int
    name: str
    description: str
    fee_lkr: int
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
