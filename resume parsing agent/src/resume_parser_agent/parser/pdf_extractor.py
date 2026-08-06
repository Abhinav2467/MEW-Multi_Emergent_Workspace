"""PDF text extraction."""

from pathlib import Path

import fitz

from resume_parser_agent.errors import ExtractionError


def extract_pdf_text(path: Path) -> str:
    """Extract readable text from a PDF file."""

    try:
        document = fitz.open(path)
    except Exception as exc:  # pragma: no cover - exact PyMuPDF errors vary
        raise ExtractionError(
            "Could not open PDF file.",
            context={"path": str(path), "error": str(exc)},
        ) from exc

    try:
        pages = [page.get_text("text") for page in document]
    except Exception as exc:  # pragma: no cover - exact PyMuPDF errors vary
        raise ExtractionError(
            "Could not extract PDF text.",
            context={"path": str(path), "error": str(exc)},
        ) from exc
    finally:
        document.close()

    return "\n".join(page.strip() for page in pages if page.strip()).strip()
