from datetime import UTC

import pytest
from pydantic import ValidationError

from resume_parser_agent.schemas import (
    ContactInfo,
    CorrectionRequest,
    EducationItem,
    ErrorResponse,
    ExperienceItem,
    ParseMetadata,
    ParsedResume,
)


def test_parsed_resume_defaults_are_json_ready() -> None:
    resume = ParsedResume(
        contact=ContactInfo(
            name="Jane Doe",
            email="jane@example.com",
            links=["https://example.com/jane"],
        ),
        skills=["Python", "FastAPI"],
        experience=[ExperienceItem(title="Engineer", company="Acme")],
        education=[EducationItem(institution="State University")],
        raw_text="Jane Doe\nPython",
        metadata=ParseMetadata(
            source_filename="jane.pdf",
            source_file_type="pdf",
            confidence_score=0.8,
            stage_timings_ms={"extract": 1.0},
        ),
    )

    dumped = resume.model_dump(mode="json")

    assert dumped["contact"]["name"] == "Jane Doe"
    assert dumped["contact"]["links"] == ["https://example.com/jane"]
    assert dumped["metadata"]["confidence_score"] == 0.8
    assert resume.metadata.parsed_at.tzinfo == UTC


def test_schemas_reject_extra_fields_and_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        ContactInfo(name="Jane", unknown=True)

    with pytest.raises(ValidationError):
        ParseMetadata(confidence_score=1.5)


def test_correction_request_and_error_response() -> None:
    resume = ParsedResume(contact=ContactInfo(name="Jane Doe"))
    correction = CorrectionRequest(
        resume_id="resume-1",
        correction_text="Email should be jane@example.com",
        current_resume=resume,
    )
    error = ErrorResponse(code="bad_request", message="Nope", context={"field": "x"})

    assert correction.current_resume.contact.name == "Jane Doe"
    assert error.context == {"field": "x"}
