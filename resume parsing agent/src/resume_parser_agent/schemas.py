"""Typed schemas for parsed resume output."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ContactInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    links: list[HttpUrl] = Field(default_factory=list)


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
    parser_version: str = "0.1.0"
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    stage_timings_ms: dict[str, float] = Field(default_factory=dict)
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ParsedResume(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact: ContactInfo = Field(default_factory=ContactInfo)
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    raw_text: str | None = None
    metadata: ParseMetadata = Field(default_factory=ParseMetadata)


class CorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_id: str
    correction_text: str
    current_resume: ParsedResume


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
