"""Dashboard routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
import shutil
import tempfile

from resume_parser_agent.dashboard.auth import require_admin
from resume_parser_agent.dashboard.events import DashboardEventBus
from resume_parser_agent.logging_config import get_logger
from resume_parser_agent.storage.repositories import ResumeRepository
from resume_parser_agent.storage.resume_files import resolve_stored_resume_path, store_resume_file
from resume_parser_agent.parser.service import ResumeParserService

logger = get_logger(__name__)


def create_dashboard_router(
    *,
    repository: ResumeRepository,
    storage_dir: Path,
    event_bus: DashboardEventBus,
    admin_username: str,
    admin_password: str,
) -> APIRouter:
    """Create authenticated dashboard routes."""

    router = APIRouter()
    admin = require_admin(username=admin_username, password=admin_password)

    @router.post("/api/parse")
    async def parse_resume(file: UploadFile = File(...), _: str = Depends(admin)):
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)
            
        try:
            parser_service = ResumeParserService()
            parsed = parser_service.parse_file(tmp_path)
            stored = store_resume_file(
                tmp_path,
                person_name=parsed.contact.name,
                storage_dir=storage_dir,
            )
            record = await repository.create(
                telegram_user_id=0,
                parsed_resume=parsed,
                original_filename=stored.original_filename,
                local_file_path=stored.relative_path,
            )
            return {"skills": parsed.skills}
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @router.get("/api/resumes/{record_id}")
    async def resume_json(record_id: int, _: str = Depends(admin)):
        record = await repository.get(record_id)
        return {
            "id": record.id,
            "person_name": record.person_name,
            "target_role": record.target_role,
            "version_number": record.version_number,
            "duplicate_status": record.duplicate_status,
            "parsed_json": record.parsed_json,
        }

    @router.post("/api/resumes/{record_id}/delete")
    async def delete_resume(record_id: int, _: str = Depends(admin)):
        try:
            record = await repository.get(record_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Resume record not found") from exc

        await repository.delete(record_id)
        try:
            path = resolve_stored_resume_path(record.local_file_path, storage_dir)
            if path.is_file():
                path.unlink()
        except Exception:
            logger.warning(
                "Could not remove stored resume file during dashboard delete",
                extra={"record_id": record_id, "local_file_path": record.local_file_path},
            )
        await event_bus.publish_resume_deleted(record_id)
        return {"status": "deleted"}

    @router.get("/api/resumes/{record_id}/file")
    async def resume_file(record_id: int, _: str = Depends(admin)):
        record = await repository.get(record_id)
        try:
            path = resolve_stored_resume_path(record.local_file_path, storage_dir)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid stored resume path") from exc
        media_type = (
            "application/pdf"
            if path.suffix.lower() == ".pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        return FileResponse(
            path,
            media_type=media_type,
            filename=record.original_filename,
        )

    return router
