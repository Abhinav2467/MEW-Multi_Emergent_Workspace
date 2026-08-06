"""Pydantic schemas for API request/response and parsed profiles."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ContactInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    links: list[str] = Field(default_factory=list)


class ExperienceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    company: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ParseMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_filename: str | None = None
    source_file_type: str | None = None
    parser_version: str = "1.0.0"
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    parse_method: Literal["gemini", "deterministic"] = "deterministic"
    stage_timings_ms: dict[str, float] = Field(default_factory=dict)
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ParsedProfile(BaseModel):
    """Editable candidate profile extracted from a resume."""

    model_config = ConfigDict(extra="forbid")

    contact: ContactInfo = Field(default_factory=ContactInfo)
    skills: list[str] = Field(default_factory=list)
    experience_years: float | None = None
    current_role: str | None = None
    preferred_roles: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    raw_text: str | None = None
    metadata: ParseMetadata = Field(default_factory=ParseMetadata)


class ProfileUpdateRequest(BaseModel):
    contact: ContactInfo | None = None
    skills: list[str] | None = None
    experience_years: float | None = None
    current_role: str | None = None
    preferred_roles: list[str] | None = None


class UserOut(BaseModel):
    id: int
    email: str
    name: str | None = None
    has_gmail_token: bool = False


class JobMatchOut(BaseModel):
    id: int
    report_id: int
    company_name: str
    position: str
    apply_link: str
    matching_percentage: int
    relevant_skills: str
    hr_recruiter_name: str | None = None
    hr_recruiter_email: str | None = None
    location: str | None = None
    job_type: str | None = None
    created_at: str | None = None
    description: str | None = None


class ReportOut(BaseModel):
    id: int
    user_id: int
    profile_id: int
    status: str
    json_path: str | None = None
    excel_path: str | None = None
    created_at: str | None = None
    matches: list[JobMatchOut] = Field(default_factory=list)


class DraftCreateRequest(BaseModel):
    job_match_ids: list[int]


class SendDraftsRequest(BaseModel):
    draft_ids: list[int]


class DraftResponse(BaseModel):
    id: int
    job_match_id: int
    gmail_draft_id: str | None = None
    status: str
    hr_recruiter_name: str | None = None
    hr_recruiter_email: str | None = None
    error: str | None = None


class AuthUrlResponse(BaseModel):
    url: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    parse_method: str
    confirmed: bool
    resume_file_path: str | None = None
    version: int
    updated_at: str | None = None
    profile: ParsedProfile


class ConfirmResponse(BaseModel):
    profile_id: int
    report_id: int
    status: str
    match_count: int
    matches: list[JobMatchOut] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    code: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
