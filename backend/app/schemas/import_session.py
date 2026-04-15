"""Import session HTTP request bodies."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class ConfirmImportRequest(BaseModel):
    session_id: int
    confirmed_mappings: Dict[str, str]
    new_custom_fields: List[Dict[str, Any]] = []
    skip_columns: List[str] = []
    sheet_names: List[str]
    org_id: int


class DuplicateCheckRequest(BaseModel):
    filename: str
    sheet_names: List[str]
    org_id: int = 1
