from resume_parser_agent.errors import (
    ConfigurationError,
    EmptyResumeError,
    ExtractionError,
    LLMCorrectionError,
    ResumeParserError,
    ResumeStorageError,
    UnauthorizedUserError,
    UnsupportedFileTypeError,
)


def test_base_error_keeps_message_and_context() -> None:
    error = ResumeParserError("boom", context={"stage": "extract"})

    assert str(error) == "boom"
    assert error.code == "resume_parser_error"
    assert error.context == {"stage": "extract"}


def test_specific_errors_have_stable_codes_and_user_messages() -> None:
    errors = [
        ConfigurationError(),
        UnsupportedFileTypeError(),
        ExtractionError(),
        EmptyResumeError(),
        ResumeStorageError(),
        LLMCorrectionError(),
        UnauthorizedUserError(),
    ]

    assert [error.code for error in errors] == [
        "configuration_error",
        "unsupported_file_type",
        "extraction_error",
        "empty_resume",
        "resume_storage_error",
        "llm_correction_error",
        "unauthorized_user",
    ]
    assert all(error.user_message for error in errors)
