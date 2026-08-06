"""Resume parser service: Gemini-first with deterministic fallback."""

from __future__ import annotations

import logging
from pathlib import Path

from backend.agents.parser.deterministic import (
    calculate_confidence,
    extract_contact_info,
    extract_current_role,
    extract_education,
    extract_experience,
    extract_skills,
)
from backend.agents.parser.errors import LLMParseError
from backend.agents.parser.extractors import extract_text_from_file
from backend.agents.parser.gemini_client import GeminiParseClient
from backend.agents.parser.normalizer import normalize_text
from backend.config import get_settings
from backend.models.schemas import ParseMetadata, ParsedProfile

logger = logging.getLogger(__name__)


class ParserService:
    """Parse resumes with Gemini Flash; fall back to deterministic extraction."""

    def __init__(self, gemini_client: GeminiParseClient | None = None) -> None:
        self._gemini = gemini_client

    def _get_gemini(self) -> GeminiParseClient | None:
        if self._gemini is not None:
            return self._gemini
        settings = get_settings()
        api_key = settings.resolved_parser_gemini_key
        if not api_key:
            logger.warning(
                "No GEMINI_PARSER_KEY, GEMINI_API_KEY, or GOOGLE_API_KEY configured; using deterministic parser."
            )
            return None
        try:
            return GeminiParseClient(
                api_key=api_key,
                model=settings.gemini_model,
            )
        except LLMParseError as exc:
            logger.warning("Could not create Gemini client: %s", exc)
            return None

    def parse_deterministic(
        self,
        path: Path,
        raw_text: str | None = None,
        file_type: str | None = None,
    ) -> ParsedResumeResult:
        if raw_text is None or file_type is None:
            raw_text, file_type = extract_text_from_file(path)
        normalized = normalize_text(raw_text)
        contact = extract_contact_info(normalized)
        skills = extract_skills(normalized)
        experience = extract_experience(normalized)
        education = extract_education(normalized)
        profile = ParsedProfile(
            contact=contact,
            skills=skills,
            experience=experience,
            education=education,
            current_role=extract_current_role(experience),
            preferred_roles=[],
            experience_years=None,
            raw_text=normalized,
            metadata=ParseMetadata(
                source_filename=path.name,
                source_file_type=file_type,
                confidence_score=calculate_confidence(
                    contact, skills, experience, education
                ),
                parse_method="deterministic",
            ),
        )
        return ParsedResumeResult(profile=profile, parse_method="deterministic")

    async def parse_file(self, path: str | Path) -> ParsedResumeResult:
        resume_path = Path(path)
        raw_text, file_type = extract_text_from_file(resume_path)
        normalized = normalize_text(raw_text)

        gemini = self._get_gemini()
        if gemini is not None:
            try:
                profile = await gemini.parse_text(
                    normalized,
                    filename=resume_path.name,
                    file_type=file_type,
                )
                profile.metadata.source_filename = resume_path.name
                profile.metadata.source_file_type = file_type
                profile.metadata.parse_method = "gemini"
                if not profile.raw_text:
                    profile.raw_text = normalized
                return ParsedResumeResult(profile=profile, parse_method="gemini")
            except LLMParseError as exc:
                logger.warning(
                    "Gemini parse encountered rate limit/error for %s: %s. Using deterministic fallback.",
                    resume_path.name,
                    exc,
                )

        return self.parse_deterministic(resume_path, raw_text=normalized, file_type=file_type)

    async def rescan(self, current: ParsedProfile) -> ParsedResumeResult:
        gemini = self._get_gemini()
        if gemini is None:
            raise LLMParseError(
                "GEMINI_API_KEY or GOOGLE_API_KEY is required for rescan."
            )
        profile = await gemini.rescan(current)
        return ParsedResumeResult(profile=profile, parse_method="gemini")


class ParsedResumeResult:
    def __init__(self, *, profile: ParsedProfile, parse_method: str) -> None:
        self.profile = profile
        self.parse_method = parse_method
