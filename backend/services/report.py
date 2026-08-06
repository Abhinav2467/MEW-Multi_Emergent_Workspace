"""Write job match reports as JSON and Excel."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from backend.config import get_settings

REPORT_COLUMNS = [
    "Company Name",
    "Position",
    "Apply Link",
    "Matching Percentage",
    "Relevant Skilled Match",
    "HR Recruiter Name",
    "HR Recruiter Email",
]


def report_dir(user_id: int, report_id: int) -> Path:
    settings = get_settings()
    path = Path(settings.reports_dir) / str(user_id) / str(report_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def matches_to_rows(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for m in matches:
        rows.append(
            {
                "Company Name": m.get("company_name", ""),
                "Position": m.get("position", ""),
                "Apply Link": m.get("apply_link", ""),
                "Matching Percentage": f"{m.get('matching_percentage', 0)}%",
                "Relevant Skilled Match": m.get("relevant_skills", ""),
                "HR Recruiter Name": m.get("hr_recruiter_name") or "",
                "HR Recruiter Email": m.get("hr_recruiter_email") or "",
            }
        )
    return rows


def write_report_files(
    *,
    user_id: int,
    report_id: int,
    matches: list[dict[str, Any]],
    profile_id: int,
) -> tuple[str, str]:
    out_dir = report_dir(user_id, report_id)
    rows = matches_to_rows(matches)

    json_path = out_dir / "report.json"
    excel_path = out_dir / "report.xlsx"

    payload = {
        "report_id": report_id,
        "user_id": user_id,
        "profile_id": profile_id,
        "matches": matches,
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    df = pd.DataFrame(rows, columns=REPORT_COLUMNS)
    df.to_excel(excel_path, index=False)

    return str(json_path), str(excel_path)


def refresh_report_files(
    *,
    user_id: int,
    report_id: int,
    matches: list[dict[str, Any]],
    profile_id: int,
) -> tuple[str, str]:
    return write_report_files(
        user_id=user_id,
        report_id=report_id,
        matches=matches,
        profile_id=profile_id,
    )
