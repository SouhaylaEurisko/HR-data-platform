"""Utilities for CV Info Agent."""
from typing import Any, Dict, List


def format_resume_info(ri: Any) -> str:
    """Produce a compact text summary of resume_info JSONB for the LLM."""
    if not ri or not isinstance(ri, dict):
        return ""
    parts: List[str] = []
    if ri.get("summary"):
        parts.append(f"CV Summary: {ri['summary']}")
    if ri.get("skills"):
        parts.append(f"CV Skills: {', '.join(ri['skills'][:15])}")
    if ri.get("languages"):
        parts.append(f"CV Languages: {', '.join(ri['languages'])}")
    if ri.get("work_experience"):
        jobs = []
        for w in ri["work_experience"][:3]:
            title = w.get("title") or "?"
            company = w.get("company") or ""
            period = ""
            if w.get("start_date") or w.get("end_date"):
                period = f" ({w.get('start_date', '?')}–{w.get('end_date', 'Present')})"
            jobs.append(f"{title} at {company}{period}" if company else f"{title}{period}")
        parts.append(f"CV Work: {'; '.join(jobs)}")
    if ri.get("education"):
        edus = []
        for e in ri["education"][:3]:
            deg = e.get("degree") or "?"
            inst = e.get("institution") or ""
            edus.append(f"{deg} — {inst}" if inst else deg)
        parts.append(f"CV Education: {'; '.join(edus)}")
    if ri.get("certifications"):
        parts.append(f"CV Certifications: {', '.join(ri['certifications'][:5])}")
    return " | ".join(parts)


def cv_rows_to_display(rows: List[Dict[str, Any]], max_rows: int = 10) -> str:
    """
    Convert query result rows to a compact text representation
    for the LLM summariser, with emphasis on CV/resume data.
    """
    if not rows:
        return "No candidates found."

    lines = []
    for i, row in enumerate(rows[:max_rows]):
        parts = []
        name = row.get("full_name")
        if name:
            parts.append(name)
        if row.get("applied_position"):
            parts.append(f"Position: {row['applied_position']}")
        if row.get("nationality"):
            parts.append(f"Nationality: {row['nationality']}")
        if row.get("years_of_experience") is not None:
            parts.append(f"Experience: {row['years_of_experience']} yrs")
        if row.get("current_salary") is not None:
            parts.append(f"Salary: ${float(row['current_salary']):,.0f}")
        if row.get("current_address"):
            parts.append(f"Location: {row['current_address']}")

        resume_text = format_resume_info(row.get("resume_info"))
        if resume_text:
            parts.append(resume_text)

        lines.append(f"{i+1}. " + " | ".join(parts))

    text = "\n".join(lines)
    if len(rows) > max_rows:
        text += f"\n... and {len(rows) - max_rows} more candidates."
    return text
