"""Gemini correction/reparse adapter."""

from __future__ import annotations

import asyncio
from typing import Any

from resume_parser_agent.errors import LLMCorrectionError, LLMCorrectionNoChangeError
from resume_parser_agent.llm.prompts import build_correction_prompt
from resume_parser_agent.schemas import CorrectionRequest, ParsedResume
from resume_parser_agent.storage.repositories import ResumeRepository


class GeminiCorrectionClient:
    """Schema-validated Gemini adapter for correction flows."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str = "gemini-2.5-flash",
        client: Any | None = None,
    ) -> None:
        if client is None and not api_key:
            raise LLMCorrectionError("GEMINI_API_KEY is required for Gemini corrections.")
        self.model = model
        self._client = client or self._build_client(api_key)

    async def apply_user_correction(self, request: CorrectionRequest) -> ParsedResume:
        """Ask Gemini to apply user correction and validate the returned JSON."""

        prompt = build_correction_prompt(request)
        try:
            response_text = await asyncio.to_thread(self._generate, prompt)
            return ParsedResume.model_validate_json(response_text)
        except Exception as exc:
            raise LLMCorrectionError(
                "Gemini correction failed.",
                context={"resume_id": request.resume_id, "error": str(exc)},
            ) from exc

    def _generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": ParsedResume.model_json_schema(),
            },
        )
        return str(response.text)

    @staticmethod
    def _build_client(api_key: str | None) -> Any:
        from google import genai

        return genai.Client(api_key=api_key)


async def apply_correction_to_record(
    *,
    repository: ResumeRepository,
    record_id: int,
    correction_text: str,
    client: GeminiCorrectionClient,
) -> ParsedResume:
    """Apply a correction through Gemini and save the corrected JSON to SQLite."""

    record = await repository.get(record_id)
    current_resume = ParsedResume.model_validate(record.parsed_json)
    corrected = await client.apply_user_correction(
        CorrectionRequest(
            resume_id=str(record_id),
            correction_text=correction_text,
            current_resume=current_resume,
        )
    )
    if _resume_content_dump(corrected) == _resume_content_dump(current_resume):
        raise LLMCorrectionNoChangeError(
            "Gemini returned unchanged parsed resume JSON.",
            context={"resume_id": str(record_id)},
        )
    await repository.replace_latest_version(
        record_id=record.id,
        parsed_resume=corrected,
        original_filename=record.original_filename,
        local_file_path=record.local_file_path,
        duplicate_status="corrected",
        vector_indexing_status="pending",
    )
    return corrected


def _resume_content_dump(resume: ParsedResume) -> dict[str, Any]:
    return resume.model_dump(
        mode="json",
        include={"contact", "skills", "experience", "education", "raw_text"},
    )
