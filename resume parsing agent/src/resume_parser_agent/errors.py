"""Application error types."""

from collections.abc import Mapping
from typing import Any


class ResumeParserError(Exception):
    """Base error with a stable code, user-facing message, and safe context."""

    code = "resume_parser_error"
    user_message = "Something went wrong while processing the resume."

    def __init__(
        self,
        message: str | None = None,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        self.message = message or self.user_message
        self.context = dict(context or {})
        super().__init__(self.message)


class ConfigurationError(ResumeParserError):
    code = "configuration_error"
    user_message = "The service is not configured correctly."


class UnsupportedFileTypeError(ResumeParserError):
    code = "unsupported_file_type"
    user_message = "Please upload a PDF or DOCX resume."


class ExtractionError(ResumeParserError):
    code = "extraction_error"
    user_message = "I could not read text from that resume."


class EmptyResumeError(ResumeParserError):
    code = "empty_resume"
    user_message = "I could not find readable resume text in that file."


class ResumeStorageError(ResumeParserError):
    code = "resume_storage_error"
    user_message = "I could not store the uploaded resume."


class LLMCorrectionError(ResumeParserError):
    code = "llm_correction_error"
    user_message = "I kept the original parse, but the AI correction step failed."


class LLMCorrectionNoChangeError(LLMCorrectionError):
    code = "llm_correction_no_change"
    user_message = "I could not infer a correction from that message."


class UnauthorizedUserError(ResumeParserError):
    code = "unauthorized_user"
    user_message = "You are not authorized to use this bot."
