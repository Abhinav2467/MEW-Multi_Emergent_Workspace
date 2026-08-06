"""Route resume files to the right text extractor."""

from pathlib import Path

from resume_parser_agent.errors import EmptyResumeError, UnsupportedFileTypeError
from resume_parser_agent.parser.docx_extractor import extract_docx_text
from resume_parser_agent.parser.pdf_extractor import extract_pdf_text


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def detect_file_type(path: Path) -> str:
    """Return a normalized file type for supported resume files."""

    extension = path.suffix.lower()
    if extension == ".pdf":
        return "pdf"
    if extension == ".docx":
        return "docx"
    raise UnsupportedFileTypeError(
        context={"filename": path.name, "extension": extension or "<none>"}
    )


def extract_text_from_file(path: Path) -> tuple[str, str]:
    """Extract text and return it with the detected file type."""

    file_type = detect_file_type(path)
    text = extract_pdf_text(path) if file_type == "pdf" else extract_docx_text(path)
    if not text.strip():
        raise EmptyResumeError(context={"filename": path.name, "file_type": file_type})
    return text, file_type
