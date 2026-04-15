"""
Resume Parser Agent — converts PDF pages to images, sends to GPT-4o vision,
and returns structured ResumeInfo validated by Pydantic.
"""

import base64
import json
import logging
from typing import Any, Dict, List

import httpx

from ...config.config import config
from ...constants import ResumeParser
from ...dtos.resume_parser import ResumeInfo
from .prompts import RESUME_EXTRACT_PROMPT

logger = logging.getLogger(__name__)

_VISION_MODEL = "gpt-4o"


def _pdf_pages_to_base64_images(pdf_bytes: bytes) -> List[str]:
    """Convert each PDF page to a base64-encoded PNG using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF is required for resume parsing. Install with: pip install PyMuPDF"
        ) from exc

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images: List[str] = []
    for page_num in range(min(len(doc), ResumeParser.MAX_PDF_PAGES)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=ResumeParser.RENDER_DPI)
        img_bytes = pix.tobytes("png")
        images.append(base64.b64encode(img_bytes).decode("utf-8"))
    doc.close()
    return images


class ResumeParserAgent:
    """Standalone agent that extracts structured resume data via GPT-4o vision."""

    def __init__(self) -> None:
        self.api_key = config.openai_api_key

    async def parse(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Parse a PDF resume and return validated ResumeInfo as a dict."""
        images = _pdf_pages_to_base64_images(pdf_bytes)
        if not images:
            logger.warning("No pages extracted from PDF")
            return {}

        content_parts: List[Dict[str, Any]] = [
            {"type": "text", "text": "Extract all information from this resume:"},
        ]
        for img_b64 in images:
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}",
                    "detail": "high",
                },
            })

        messages = [
            {"role": "system", "content": RESUME_EXTRACT_PROMPT},
            {"role": "user", "content": content_parts},
        ]

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": _VISION_MODEL,
                        "messages": messages,
                        "response_format": {"type": "json_object"},
                        "temperature": 0.1,
                        "max_tokens": 4096,
                    },
                )

            if response.status_code != 200:
                logger.error("OpenAI vision returned %d: %s", response.status_code, response.text)
                raise RuntimeError(f"OpenAI vision API error: {response.status_code}")

            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_content)
            validated = ResumeInfo.model_validate(parsed)
            return validated.model_dump()

        except json.JSONDecodeError as exc:
            logger.error("Failed to parse GPT response as JSON: %s", exc)
            raise RuntimeError(f"Resume parsing JSON error: {exc}") from exc
        except httpx.RequestError as exc:
            logger.error("Network error calling OpenAI vision: %s", exc)
            raise RuntimeError(f"Resume parsing network error: {exc}") from exc
