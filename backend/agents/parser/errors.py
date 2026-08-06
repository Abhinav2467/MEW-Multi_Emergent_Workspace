"""Parser package errors."""

from collections.abc import Mapping
from typing import Any


class ParserError(Exception):
    code = "parser_error"
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


class UnsupportedFileTypeError(ParserError):
    code = "unsupported_file_type"
    user_message = "Please upload a PDF or DOCX resume."


class ExtractionError(ParserError):
    code = "extraction_error"
    user_message = "Could not read text from that resume."


class EmptyResumeError(ParserError):
    code = "empty_resume"
    user_message = "Could not find readable resume text in that file."


class LLMParseError(ParserError):
    code = "llm_parse_error"
    user_message = "Gemini parsing failed; falling back to deterministic parser."
