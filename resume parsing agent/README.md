# Resume Parser Agent

Python 3.11+ resume parsing service for a modular job application pipeline.

The system will be built step by step:

1. Project foundation
2. Deterministic PDF/DOCX parser
3. Local resume file storage
4. Telegram bot interface
5. SQLite persistence
6. Qdrant duplicate prevention
7. Authenticated live dashboard
8. Gemini correction/reparse flow
9. Production hardening

## Current Status

Steps 1 through 9 are implemented: base project structure, pinned dependency
declarations, typed settings, schemas, structured errors, logging setup,
configurable local resume storage directory, stage timing utilities, and a
deterministic PDF/DOCX parser with safe local original-resume storage and a
Telegram bot upload/confirmation interface. SQLite persistence is now available
as the source of truth for parsed resume records, with Qdrant-ready duplicate
detection adapters, a basic authenticated live dashboard, and Gemini correction
support. Production hardening now includes health/readiness routes, startup
validation, pending vector retry support, and Docker Compose Qdrant wiring.

## Runtime

Start the dashboard and Telegram bot service:

```powershell
python -m resume_parser_agent.main
```

The dashboard runs on the configured host and port. When `TELEGRAM_BOT_TOKEN`
is set, the Telegram bot starts polling in the same process.

Run the full check command:

```powershell
./scripts/check.ps1
```

## Development

Install development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run tests:

```powershell
python -m pytest
```

Run coverage:

```powershell
python -m pytest --cov=resume_parser_agent --cov-report=term-missing
```

## Configuration

Copy `.env.example` to `.env` and fill in secrets before running bot, dashboard,
Gemini, or Qdrant-enabled steps.

Important settings:

- `TELEGRAM_BOT_TOKEN`: starts the Telegram bot when configured.
- `TELEGRAM_ALLOWED_CHAT_IDS`: leave empty to allow everyone, or set a
  comma-separated allowlist such as `123456,987654`.
- `ENABLE_VECTOR_DEDUP`: defaults to `false` so local testing does not stall on
  Qdrant or embedding model startup.
- `RESUME_STORAGE_DIR`: local directory where original PDF/DOCX uploads are
  stored with sanitized parsed name plus a UUID.

## Telegram Behavior

The bot accepts PDF and DOCX resume uploads. When a resume upload starts, it
immediately replies:

```text
Parsing your resume. Please wait until I finish.
```

While that chat is processing, extra messages or file uploads are rejected with
a busy message so overlapping parses do not collide. After parsing, the bot
returns a concise summary with name, email, phone, and skills. Full JSON is saved
in SQLite and visible in the authenticated dashboard.

If a user says details are wrong, the bot keeps the correction flow open. Simple
corrections like `My name is Jane Doe`, `Email: jane@example.com`, and
`Phone: +91 98765 43210` are applied locally. Vague feedback like
`my name is wrong and my phone no is incorrect` receives a targeted prompt asking
for the corrected fields.

## Dashboard

The authenticated dashboard lists parsed resumes, shows parsed JSON, timestamps,
version and duplicate status, and provides authenticated access to the stored
original resume file. PDF files open in-browser when supported; DOCX files are
served as downloads. Admin users can remove resume entries from the list or
detail page; removal deletes the SQLite record and the stored original file when
the file path can be safely resolved.
