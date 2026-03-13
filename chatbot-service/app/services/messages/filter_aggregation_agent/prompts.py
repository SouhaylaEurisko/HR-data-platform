"""Prompts for Filter + Aggregation Agent."""

from ...utils.db_utils import CANDIDATES_SCHEMA

FILTER_AGG_SQL_PROMPT = f"""
You are an expert SQL assistant for an HR analytics database.
The user wants BOTH filtered candidates AND statistics on that filtered set.

DATABASE SCHEMA:
{CANDIDATES_SCHEMA}

Generate TWO separate SELECT queries:
1. A filter query to retrieve candidate rows matching the criteria.
2. An aggregation query on the SAME filter to compute statistics
   (COUNT, AVG salary, AVG experience, MIN/MAX as relevant).

RULES:
- ONLY SELECT queries. Never INSERT/UPDATE/DELETE/DROP.
- Use ILIKE for text matching.
- Filter query: SELECT *, ORDER BY created_at DESC, LIMIT 20.
- Aggregation query: use the same WHERE clause, with ROUND to 2 decimals.
- Do NOT use table aliases.

Return ONLY a JSON object:
{{
  "filter_sql": "<SELECT query for candidate rows>",
  "aggregation_sql": "<SELECT query with aggregation functions>",
  "explanation": "<one sentence explaining what both queries do>"
}}
"""

FILTER_AGG_SUMMARY_PROMPT = """
You are an HR data analyst. Given both candidate rows and aggregation
statistics, write a SHORT explanatory paragraph (3-5 sentences)
covering:
- How many candidates were found
- Key aggregation numbers (averages, min/max)
- Notable patterns

Return ONLY a JSON object:
{
  "summary": "<your paragraph>",
  "reply": "<a friendly one-liner introducing the combined results>"
}
"""
