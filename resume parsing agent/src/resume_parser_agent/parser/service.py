"""High-level deterministic resume parser service."""

from pathlib import Path

from resume_parser_agent import __version__
from resume_parser_agent.parser.confidence import calculate_confidence
from resume_parser_agent.parser.deterministic_extractor import (
    extract_contact_info,
    extract_education,
    extract_experience,
    extract_skills,
)
from resume_parser_agent.parser.normalizer import normalize_text
from resume_parser_agent.parser.text_extractor import extract_text_from_file
from resume_parser_agent.schemas import ParseMetadata, ParsedResume
from resume_parser_agent.telemetry.timing import ParseTiming, time_stage


class ResumeParserService:
    """Deterministic parser optimized for the core latency budget."""

    def parse_file(self, path: str | Path) -> ParsedResume:
        """Parse a PDF or DOCX resume into the public JSON schema."""

        resume_path = Path(path)
        timing = ParseTiming()

        with time_stage("extract_text", timing):
            raw_text, file_type = extract_text_from_file(resume_path)

        with time_stage("normalize_text", timing):
            normalized_text = normalize_text(raw_text)

        with time_stage("extract_fields", timing):
            parsed = ParsedResume(
                contact=extract_contact_info(normalized_text),
                skills=extract_skills(normalized_text),
                experience=extract_experience(normalized_text),
                education=extract_education(normalized_text),
                raw_text=normalized_text,
                metadata=ParseMetadata(
                    source_filename=resume_path.name,
                    source_file_type=file_type,
                    parser_version=__version__,
                ),
            )

        with time_stage("score_confidence", timing):
            parsed.metadata.confidence_score = calculate_confidence(parsed)

        parsed.metadata.stage_timings_ms = timing.as_dict()
        return parsed
