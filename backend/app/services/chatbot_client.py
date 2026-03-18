"""
HTTP client for the standalone chatbot service (classify, filters, aggregation detect).
"""

from typing import Any, Dict

import httpx


class ChatbotClient:
    """Thin wrapper around chatbot POST endpoints with status checks."""

    def __init__(self, base_url: str, client: httpx.AsyncClient) -> None:
        self._base = base_url.rstrip("/")
        self._client = client

    async def _post_json(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._base}{path}" if path.startswith("/") else f"{self._base}/{path}"
        response = await self._client.post(url, json=body)
        response.raise_for_status()
        return response.json()

    async def classify(self, message: str) -> Dict[str, Any]:
        return await self._post_json("/api/classify", {"message": message})

    async def extract_filters(self, message: str) -> Dict[str, Any]:
        return await self._post_json("/api/extract-filters", {"message": message})

    async def detect_aggregation(self, message: str) -> Dict[str, Any]:
        return await self._post_json("/api/detect-aggregation", {"message": message})
