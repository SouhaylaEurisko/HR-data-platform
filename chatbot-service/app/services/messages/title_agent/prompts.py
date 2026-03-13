"""Prompts for Title Agent."""

TITLE_GENERATION_PROMPT = """
Generate a short, descriptive title (2-4 words max) for a chat conversation
based on the user's first message. The title should capture the core intent.

Rules:
- Maximum 4 words.
- Professional and concise.
- If it's a greeting, use "General Chat".
- If it's a search, summarise the search (e.g. "Lebanese Engineers Search").
- If it's statistics, summarise the stat (e.g. "Salary Statistics").

Return ONLY a JSON object:
{
  "title": "<2-4 word title>"
}
"""
