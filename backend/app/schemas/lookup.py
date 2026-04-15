"""Lookup HTTP schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LookupOptionOut(BaseModel):
    id: int
    code: str
    label: str
    display_order: int
    is_active: bool

    class Config:
        from_attributes = True


class LookupCategoryOut(BaseModel):
    id: int
    code: str
    label: str
    description: Optional[str] = None
    is_system: bool

    class Config:
        from_attributes = True


class CreateLookupOptionRequest(BaseModel):
    code: str
    label: str
    display_order: int = 0
