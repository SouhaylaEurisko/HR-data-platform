"""
Lightweight OpenAI chat-completions wrapper for the backend.
Used exclusively for the single column-normalization call during import.
"""

import json
import logging
from typing import Any, Dict, Optional

import httpx

from ..config.config import config

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0


async def call_llm(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.0,
) -> Optional[Dict[str, Any]]:
    """
    Send a single chat-completion request and parse the JSON response.
    Returns the parsed dict, or None on failure.
    """
    headers = {
        "Authorization": f"Bearer {config.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.openai_model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return None
