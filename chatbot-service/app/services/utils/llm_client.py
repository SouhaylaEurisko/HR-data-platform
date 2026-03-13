"""
Shared LLM client — every agent uses this for OpenAI calls.
All calls return parsed JSON dicts.
"""
import json
import logging
import httpx

from ...config import config

logger = logging.getLogger(__name__)


class LLMClient:
    """Stateless helper that wraps the OpenAI chat-completions API."""

    def __init__(self):
        self.api_key = config.openai_api_key
        self.model = config.openai_model or "gpt-4o-mini"

    async def call(
        self,
        system_prompt: str,
        user_message: str,
        context: str = "LLM call",
        temperature: float = 0.2,
    ) -> dict:
        """
        Send a system+user prompt to the LLM and return parsed JSON.

        Args:
            system_prompt: Instructions for the LLM.
            user_message:  The user's text / query.
            context:       Label used in error messages.
            temperature:   Sampling temperature (low = deterministic).

        Returns:
            Parsed JSON dict from the LLM response.

        Raises:
            RuntimeError on network / parse errors.
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": temperature,
                    },
                )

                if response.status_code != 200:
                    raise RuntimeError(
                        f"{context}: OpenAI returned {response.status_code} — {response.text}"
                    )

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if not content:
                    raise RuntimeError(f"{context}: empty LLM response")

                return json.loads(content)

        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{context}: failed to parse JSON — {exc}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"{context}: network error — {exc}") from exc
