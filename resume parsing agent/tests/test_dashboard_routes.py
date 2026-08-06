from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from resume_parser_agent.config import Settings
from resume_parser_agent.dashboard.app import build_dashboard_app
from resume_parser_agent.errors import ConfigurationError
from resume_parser_agent.schemas import ContactInfo, ParsedResume
from resume_parser_agent.storage.database import connect
from resume_parser_agent.storage.migrations import initialize_database
from resume_parser_agent.storage.repositories import ResumeRepository


AUTH = ("admin", "secret")


def make_settings(storage_dir: Path) -> Settings:
    return Settings(
        dashboard_admin_username="admin",
        dashboard_admin_password="secret",
        resume_storage_dir=storage_dir,
        _env_file=None,
    )


async def make_repository(tmp_path: Path) -> tuple[ResumeRepository, object]:
    connection = await connect(f"sqlite+aiosqlite:///{tmp_path / 'resume.db'}")
    await initialize_database(connection)
    return ResumeRepository(connection), connection


async def create_record(repository: ResumeRepository, storage_dir: Path, filename: str = "Jane.pdf"):
    (storage_dir / filename).write_bytes(b"%PDF-1.4")
    return await repository.create(
        telegram_user_id=123,
        parsed_resume=ParsedResume(
            contact=ContactInfo(name="Jane Doe", email="jane@example.com"),
            raw_text="Jane Doe",
        ),
        original_filename="upload.pdf",
        local_file_path=filename,
    )


def test_dashboard_requires_admin_password(tmp_path: Path) -> None:
    repository = object()

    with pytest.raises(ConfigurationError):
        build_dashboard_app(
            repository=repository,  # type: ignore[arg-type]
            settings=Settings(dashboard_admin_password=None, _env_file=None),
        )


@pytest.mark.asyncio
async def test_dashboard_requires_auth(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        client = TestClient(build_dashboard_app(repository=repository, settings=make_settings(tmp_path)))

        response = client.get("/")

        assert response.status_code == 401
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_health_and_ready_endpoints(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        client = TestClient(build_dashboard_app(repository=repository, settings=make_settings(tmp_path)))

        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/ready").json() == {
            "status": "ok",
            "storage": True,
            "database": True,
        }
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_dashboard_lists_resumes_and_shows_detail_json(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        await create_record(repository, tmp_path)
        client = TestClient(build_dashboard_app(repository=repository, settings=make_settings(tmp_path)))

        list_response = client.get("/", auth=AUTH)
        detail_response = client.get("/resumes/1", auth=AUTH)
        json_response = client.get("/api/resumes/1", auth=AUTH)

        assert list_response.status_code == 200
        assert "Jane Doe" in list_response.text
        assert "/resumes/1/delete" in list_response.text
        assert detail_response.status_code == 200
        assert "jane@example.com" in detail_response.text
        assert "/resumes/1/delete" in detail_response.text
        assert json_response.json()["parsed_json"]["contact"]["name"] == "Jane Doe"
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_dashboard_delete_requires_auth(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        await create_record(repository, tmp_path)
        client = TestClient(build_dashboard_app(repository=repository, settings=make_settings(tmp_path)))

        response = client.post("/resumes/1/delete", follow_redirects=False)

        assert response.status_code == 401
        assert len(await repository.list_all()) == 1
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_dashboard_delete_removes_record_and_stored_file(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        await create_record(repository, tmp_path, "Jane.pdf")
        client = TestClient(build_dashboard_app(repository=repository, settings=make_settings(tmp_path)))

        response = client.post("/resumes/1/delete", auth=AUTH, follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/"
        assert await repository.list_all() == []
        assert not (tmp_path / "Jane.pdf").exists()
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_dashboard_delete_missing_record_returns_404(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        client = TestClient(build_dashboard_app(repository=repository, settings=make_settings(tmp_path)))

        response = client.post("/resumes/999/delete", auth=AUTH, follow_redirects=False)

        assert response.status_code == 404
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_stored_resume_file_route_requires_auth_and_serves_file(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        await create_record(repository, tmp_path, "Jane.docx")
        client = TestClient(build_dashboard_app(repository=repository, settings=make_settings(tmp_path)))

        unauthorized = client.get("/resumes/1/file")
        authorized = client.get("/resumes/1/file", auth=AUTH)

        assert unauthorized.status_code == 401
        assert authorized.status_code == 200
        assert authorized.content == b"%PDF-1.4"
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_file_route_cannot_escape_storage_dir(tmp_path: Path) -> None:
    repository, connection = await make_repository(tmp_path)
    try:
        await repository.create(
            telegram_user_id=123,
            parsed_resume=ParsedResume(contact=ContactInfo(name="Jane Doe"), raw_text="Jane"),
            original_filename="upload.pdf",
            local_file_path="../secret.pdf",
        )
        client = TestClient(build_dashboard_app(repository=repository, settings=make_settings(tmp_path)))

        response = client.get("/resumes/1/file", auth=AUTH)

        assert response.status_code == 400
    finally:
        await connection.close()
