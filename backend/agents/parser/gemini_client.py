"""Gemini Flash client for resume parsing."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.agents.parser.errors import LLMParseError
from backend.agents.parser.prompts import build_parse_prompt, build_rescan_prompt
from backend.models.schemas import (
    ContactInfo,
    EducationItem,
    ExperienceItem,
    ParseMetadata,
    ParsedProfile,
)

logger = logging.getLogger(__name__)


class GeminiContactOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    links: list[str] = Field(default_factory=list)


class GeminiExperienceOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    company: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: list[str] = Field(default_factory=list)


class GeminiEducationOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class GeminiProfileOut(BaseModel):
    """Simplified schema for Gemini structured output (no datetime metadata)."""

    model_config = ConfigDict(extra="ignore")

    contact: GeminiContactOut = Field(default_factory=GeminiContactOut)
    skills: list[str] = Field(default_factory=list)
    experience_years: float | None = None
    current_role: str | None = None
    preferred_roles: list[str] = Field(default_factory=list)
    experience: list[GeminiExperienceOut] = Field(default_factory=list)
    education: list[GeminiEducationOut] = Field(default_factory=list)


def _to_parsed_profile(
    out: GeminiProfileOut,
    *,
    raw_text: str,
    filename: str | None = None,
    file_type: str | None = None,
) -> ParsedProfile:
    return ParsedProfile(
        contact=ContactInfo(
            name=out.contact.name,
            email=out.contact.email,
            phone=out.contact.phone,
            location=out.contact.location,
            linkedin=out.contact.linkedin,
            links=list(out.contact.links or []),
        ),
        skills=[s.strip() for s in out.skills if s and s.strip()],
        experience_years=out.experience_years,
        current_role=out.current_role,
        preferred_roles=[r.strip() for r in out.preferred_roles if r and r.strip()],
        experience=[
            ExperienceItem(
                title=e.title,
                company=e.company,
                location=e.location,
                start_date=e.start_date,
                end_date=e.end_date,
                description=list(e.description or []),
            )
            for e in out.experience
        ],
        education=[
            EducationItem(
                institution=e.institution,
                degree=e.degree,
                field_of_study=e.field_of_study,
                start_date=e.start_date,
                end_date=e.end_date,
            )
            for e in out.education
        ],
        raw_text=raw_text,
        metadata=ParseMetadata(
            source_filename=filename,
            source_file_type=file_type,
            parse_method="gemini",
            confidence_score=0.9,
        ),
    )


class GeminiParseClient:
    """Schema-validated Gemini adapter for initial parse and rescan with multi-key failover."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str = "gemini-2.5-flash",
        client: Any | None = None,
    ) -> None:
        if client is None and not api_key:
            raise LLMParseError("GEMINI_API_KEY or GOOGLE_API_KEY is required for Gemini parsing.")
        self.api_key = api_key
        self.model = model
        self._client = client or self._build_client(api_key)

    async def parse_text(
        self,
        raw_text: str,
        *,
        filename: str | None = None,
        file_type: str | None = None,
    ) -> ParsedProfile:
        prompt = build_parse_prompt(raw_text, filename=filename)
        try:
            response_text = await asyncio.to_thread(self._generate, prompt)
            out = GeminiProfileOut.model_validate_json(response_text)
            return _to_parsed_profile(
                out, raw_text=raw_text, filename=filename, file_type=file_type
            )
        except Exception as exc:
            logger.warning("Gemini parse failed: %s", exc)
            raise LLMParseError(
                "Gemini parse failed.",
                context={"error": str(exc)},
            ) from exc

    async def rescan(self, current: ParsedProfile) -> ParsedProfile:
        prompt = build_rescan_prompt(current)
        try:
            response_text = await asyncio.to_thread(self._generate, prompt)
            out = GeminiProfileOut.model_validate_json(response_text)
            return _to_parsed_profile(
                out,
                raw_text=current.raw_text or "",
                filename=current.metadata.source_filename,
                file_type=current.metadata.source_file_type,
            )
        except Exception as exc:
            logger.warning("Gemini rescan failed: %s", exc)
            raise LLMParseError(
                "Gemini rescan failed.",
                context={"error": str(exc)},
            ) from exc

    def _generate(self, prompt: str) -> str:
        from backend.config import get_settings

        settings = get_settings()
        keys_to_try = [
            k.strip() for k in [
                self.api_key,
                settings.gemini_backup_key,
                settings.gemini_email_key,
                settings.gemini_api_key,
                settings.google_api_key,
            ] if k and k.strip()
        ]
        unique_keys = list(dict.fromkeys(keys_to_try))

        last_exc = None
        for key in unique_keys:
            try:
                client = self._build_client(key)
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_json_schema": GeminiProfileOut.model_json_schema(),
                    },
                )
                text = getattr(response, "text", None)
                if text:
                    return str(text)
            except Exception as exc:
                last_exc = exc
                masked = f"...{key[-4:]}" if len(key) >= 4 else "***"
                logger.warning("Gemini API call failed with key ending in %s: %s", masked, exc)
                continue

        raise LLMParseError(f"Gemini generation failed across all keys: {last_exc}")

    @staticmethod
    def _build_client(api_key: str | None) -> Any:
        from google import genai

        return genai.Client(api_key=api_key)
