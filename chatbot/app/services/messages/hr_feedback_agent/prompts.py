"""Prompts for HR feedback (stage comments) lookup."""

HR_FEEDBACK_EXTRACT_PROMPT = """
You extract structured data from a user message about HR pipeline feedback / comments
for a specific candidate.

The database stores comments per stage in keys:
- pre_screening  (also: pre-screening, prescreening, initial screening)
- technical_interview
- hr_interview
- offer_stage

Rules:
- "candidate_name": substring to match against full_name (e.g. "Charbel Tarabay" → "Charbel Tarabay" or "Charbel").
- "stage": one of exactly: "pre_screening", "technical_interview", "hr_interview", "offer_stage".
  If the user does not name a stage but asks for "feedback", "comment", "notes", default to "pre_screening".
- If you cannot identify a person name, set "candidate_name" to "".

Return ONLY a JSON object:
{
  "candidate_name": "<string>",
  "stage": "pre_screening" | "technical_interview" | "hr_interview" | "offer_stage"
}
"""
