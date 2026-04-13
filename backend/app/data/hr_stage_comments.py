"""
HR pipeline stage keys (shared by stage-comment API and models).
"""

from __future__ import annotations

from typing import Tuple

HR_STAGE_KEYS: Tuple[str, ...] = (
    "pre_screening",
    "technical_interview",
    "hr_interview",
    "offer_stage",
)
