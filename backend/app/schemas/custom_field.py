"""Custom field HTTP schemas."""

from __future__ import annotations

from pydantic import BaseModel


class CustomFieldDefinitionOut(BaseModel):
    id: int
    field_key: str
    label: str
    field_type: str

    class Config:
        from_attributes = True
