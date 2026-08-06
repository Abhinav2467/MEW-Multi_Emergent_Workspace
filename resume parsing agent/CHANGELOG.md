# Changelog

All notable project changes are recorded here. Before fixing bugs or making changes,
check this file for similar prior errors and reuse the documented fix when possible.

## 2026-05-24

### Changed
- Routed configured Telegram correction feedback through Gemini before local
  fallback correction handling.
- Updated the Gemini correction prompt so vague feedback like `the name is wrong`
  can be resolved from resume `raw_text` when the correct value is clearly
  present.
- Added no-change detection for Gemini corrections. If Gemini returns unchanged
  resume content, the bot asks for the corrected field value instead of claiming
  the saved JSON was updated.
- Changed successful AI correction replies to include the updated resume summary.

### Why
- Users can report that a field is wrong without knowing the exact correction
  format. Gemini should attempt the reparse/correction when configured, but the
  bot must not say a correction was applied when nothing changed.

### Errors Fixed
- Fixed misleading Telegram reply:
  `Thanks, I applied the correction and updated the saved JSON.`
  after vague feedback such as `The name is wrong` when no actual JSON change
  was made.

### Changed
- Added authenticated dashboard remove actions on the resume list and detail
  pages.
- Added a POST-only `/resumes/{record_id}/delete` route that deletes the SQLite
  record and removes the stored original resume file when it can be safely
  resolved.
- Added dashboard live-refresh support for resume deletion events.
- Updated `README.md` to document dashboard removal behavior.

### Why
- Admin users need a way to remove incorrect, test, or stale parsed resume
  entries directly from the dashboard without editing SQLite manually.

### Errors Fixed
- None.

### Changed
- Updated `README.md` with the current runtime command, Telegram polling
  behavior, empty allowlist behavior, vector dedupe default, processing/busy
  messages, targeted correction flow, and dashboard capabilities.

### Why
- The README lagged behind the latest tested Telegram behavior and configuration
  semantics.

### Errors Fixed
- None.

### Changed
- Added targeted Telegram correction prompts for vague feedback such as
  `name is wrong` and `phone no is incorrect`.
- Allowed concrete correction messages sent directly after parse confirmation,
  such as `My name is Jane Doe`, to update the parsed result immediately.
- Tightened local name correction parsing so vague phrases like
  `my name is wrong` are not treated as the corrected name value.

### Why
- Testers naturally describe which fields are wrong before providing corrected
  values. The bot should ask for the exact missing corrected fields and should
  not accidentally save words like `wrong` as resume data.

### Errors Fixed
- Fixed the correction flow shown in Telegram where
  `My name is wrong and my phone no is incorrect` only received a generic
  correction prompt.
- Fixed a parser edge case where `My name is wrong ...` could be interpreted as
  a concrete name correction.

### Changed
- Added a Telegram `processing` session state.
- The bot now immediately replies `Parsing your resume. Please wait until I finish.`
  when a resume upload starts.
- While a chat is processing a resume, extra file uploads or text replies receive
  a busy message instead of entering confirmation or correction handling.
- Parser failures now reset the Telegram session back to idle after surfacing the
  friendly error message.

### Why
- Telegram cannot disable the user's input box, so the bot needs to make the
  active parsing state clear and reject overlapping work while parsing is in
  progress.

### Errors Fixed
- Fixed a race-prone chat flow where users could send corrections or additional
  resumes during an active parse and collide with the current processing state.

### Changed
- Added local correction handling for Telegram messages such as
  `My name is ...`, `Email: ...`, and `Phone: ...` when Gemini is not
  configured.
- Kept the bot in correction mode when a user says something is wrong but does
  not provide a concrete corrected field.
- Made vector duplicate detection optional with `ENABLE_VECTOR_DEDUP=false` by
  default so normal Telegram uploads do not stall while loading local embedding
  models or contacting Qdrant.
- Restored `.env.example`.

### Why
- The chat showed the tester expected a follow-up correction like
  `My name is regandla sai yasvitha` to update the parsed record. Previously the
  first vague complaint ended the correction flow without applying anything.
- Uploads should keep working even when Qdrant or the local embedding model is
  not running yet.

### Errors Fixed
- Fixed correction flow where a vague first correction consumed the correction
  state and the concrete second correction was ignored.
- Fixed likely upload stalls caused by eager vector duplicate detection when
  running the app locally without Qdrant/embedding readiness.

### Changed
- Changed Telegram parse-complete replies to a concise summary format with name,
  email, phone, and skills instead of sending JSON in chat.

### Why
- The Telegram response should be readable and close to the desired UX shown by
  the user, while full JSON remains available in the dashboard and database.

### Errors Fixed
- None.

### Changed
- Omitted full `raw_text` from Telegram JSON replies and bounded Telegram JSON
  output length while keeping full parsed data in SQLite/dashboard storage.
- Added exception logging around Telegram upload and correction handling.

### Why
- Real resumes can produce JSON responses larger than Telegram's message limit,
  especially when `raw_text` contains the full extracted resume. Telegram then
  raises an unexpected API error and the bot falls back to the generic
  "Something went wrong" message.

### Errors Fixed
- Fixed likely Telegram upload failure where sending a real PDF response returned:
  `Something went wrong while processing the resume. Please try again.`

### Changed
- Wired Telegram uploads into SQLite persistence, duplicate detection, dashboard
  live-update publishing, and optional Gemini correction save-back.
- Updated the runtime entrypoint so `python -m resume_parser_agent.main` starts
  the dashboard and also starts Telegram polling when `TELEGRAM_BOT_TOKEN` is
  configured.
- Fixed Telegram text handling so correction messages are routed after a user
  says parsed details are wrong.

### Why
- Completes the end-to-end pipeline: Telegram upload -> parse -> local file
  storage -> duplicate decision -> SQLite record -> dashboard visibility ->
  optional correction update.

### Errors Fixed
- Fixed incomplete integration where bot uploads were only kept in memory and
  did not appear in the dashboard or SQLite store.
- Fixed unreachable correction flow caused by both confirmation and correction
  handlers using the same Telegram text filter.
- Fixed duplicate confirmation fallthrough where `same role` or `different role`
  saved the duplicate decision and then incorrectly prompted for corrections.

### Changed
- Updated `TELEGRAM_ALLOWED_CHAT_IDS` settings parsing so an empty value means
  all Telegram users are allowed, and comma-separated IDs still work.

### Why
- `pydantic-settings` attempted to JSON-decode the tuple field before the custom
  CSV validator ran, so `TELEGRAM_ALLOWED_CHAT_IDS=` crashed startup instead of
  becoming an empty allowlist.

### Errors Fixed
- Fixed startup failure:
  `pydantic_settings.exceptions.SettingsError: error parsing value for field "telegram_allowed_chat_ids" from source "DotEnvSettingsSource"`.
- Original nested error:
  `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`.

### Added
- Added Step 9 production hardening with dashboard runtime entrypoint, startup
  setting validation, unauthenticated `/health` and `/ready` endpoints,
  repository health checks, pending vector-index retry support, Docker Compose
  Qdrant service wiring, and a local check script.
- Updated Docker to run `python -m resume_parser_agent.main`.
- Added tests for startup validation, health/readiness endpoints, repository
  readiness, pending vector index listing, and retrying pending vector indexes.

### Why
- Provides operational checks and a runnable service entrypoint while preserving
  SQLite as the source of truth and keeping vector indexing retryable.
- Makes deployment setup more realistic for local/VM Docker usage.

### Errors Fixed
- None.

### Added
- Added Step 8 Gemini correction/reparse adapter with structured JSON output,
  schema validation, correction prompts, and SQLite save-back helper.
- Updated the default Gemini model from `gemini-3.5-flash` to
  `gemini-2.5-flash` based on current official Gemini API examples.
- Added tests for prompt construction, valid correction, malformed Gemini
  response handling, Gemini outage behavior, and saving corrected JSON back to
  SQLite.

### Why
- Keeps Gemini outside the deterministic 300ms parser path while allowing user
  corrections to update stored parsed JSON.
- Shields the bot/dashboard from LLM failures by raising a typed correction
  error and leaving the original deterministic parse intact.

### Errors Fixed
- None.

### Known Warnings
- Local environment warning during install:
  `langchain-google-genai 4.2.2 requires google-genai<2.0.0,>=1.65.0, but you have google-genai 2.6.0 which is incompatible.`
  The project tests pass with the pinned project dependency; future work should
  avoid relying on the globally installed conflicting LangChain package.

### Added
- Added Step 7 authenticated FastAPI dashboard with person list, resume detail,
  parsed JSON endpoint, secured original resume file route, static assets,
  Jinja templates, and server-sent event support.
- Added repository list-all support for dashboard views.
- Added tests for dashboard auth, list/detail JSON rendering, secured file
  access, path traversal protection, and live event payloads.

### Why
- Lets an admin view parsed resumes so far, inspect JSON output, and open or
  download stored originals from the authenticated dashboard.
- Adds live refresh plumbing for new parse events without exposing unauthenticated
  JSON or file endpoints.

### Errors Fixed
- Fixed dashboard test failures:
  `TypeError: cannot use 'tuple' as a dict key (unhashable type: 'dict')`
  caused by Starlette's newer `TemplateResponse` call signature.
- Fixed unsafe dashboard file-path handling:
  `resume_parser_agent.errors.ResumeStorageError: Stored resume path must be relative to the resume storage directory.`
- Fixed SSE test ordering failure:
  `TimeoutError` when publishing before the async subscriber was active. The
  test now yields to the event loop so the subscription is registered before
  publishing.

### Added
- Added Step 6 duplicate detection with exact same-user text-hash matching,
  local embedding provider, Qdrant vector store adapter, and duplicate-aware
  persistence policy.
- Added best-effort vector indexing that leaves SQLite records saved with
  `pending` status if Qdrant or embeddings fail.
- Added tests for exact duplicates, mocked near-vector duplicates, same-user
  scoping, same-role update replacement, different-role new-version storage, and
  Qdrant failure fallback.

### Why
- Prevents duplicate resume creation unless the user confirms the resume is an
  update or for a different role.
- Keeps Qdrant replaceable and non-canonical; SQLite remains the source of
  truth.

### Errors Fixed
- None.

### Added
- Added Step 5 SQLite persistence with async connection helpers, schema
  bootstrap, schema version tracking, dataclass record models, and parsed resume
  repository methods.
- Stored parsed JSON, Telegram user ID, person name, target role, version number,
  duplicate status, text hash, vector indexing status, original filename, local
  file path, and timestamps.
- Added tests for database URL parsing, repeatable schema initialization,
  create/fetch, version tracking, latest-version replacement, user-scoped
  listing, exact hash lookup, and missing records.

### Why
- Makes SQLite the canonical source of truth before adding Qdrant duplicate
  detection and the dashboard.
- Keeps original file paths relative and ties future vector records back to
  stable SQLite IDs.

### Errors Fixed
- None.

### Added
- Added Step 4 Telegram bot interface with allowlist checks, upload handling,
  parser integration, local original-resume storage, summary plus JSON replies,
  confirmation handling, and correction collection.
- Added bot session store and Telegram message formatting helpers.
- Added application factory for python-telegram-bot v22.7.
- Added async tests for authorization, upload parsing/storage, friendly parser
  errors, confirmation state, correction collection, formatters, session store,
  and app wiring.

### Why
- Provides the real-time user interface while keeping bot logic testable without
  Telegram network calls.
- Prepares correction text for the later Gemini reparse step without coupling
  Step 4 to an LLM.

### Errors Fixed
- None.

### Added
- Added Step 3 local resume file storage under the configured storage directory.
- Added sanitized person-name filenames with UUID collision protection.
- Added path resolution safeguards for future authenticated dashboard file
  serving.
- Added storage tests for filename sanitization, repeated names, missing names,
  unsafe extensions, missing source files, and path traversal.

### Why
- Preserves original uploaded PDF/DOCX resumes locally so the dashboard can
  later open or download them.
- Prevents duplicate names from overwriting files and keeps stored paths safely
  constrained to the resume storage directory.

### Errors Fixed
- None.

### Added
- Copied the project scaffold to
  `C:\Users\nites\OneDrive\Documents\videsh Stuff\resume parsing agent` and
  continued development there.
- Added the Step 2 deterministic parser for PDF and DOCX resumes.
- Added direct PDF extraction with PyMuPDF and DOCX extraction with python-docx.
- Added deterministic contact, skills, experience, education, normalization, and
  confidence helpers.
- Added parser tests for PDF, DOCX, unsupported files, empty resumes, core field
  extraction, and stage timing.

### Why
- Moves the working project into the user-requested final folder.
- Establishes the 300ms core parser before adding Telegram, storage, dashboard,
  vectors, or Gemini.
- Keeps parsing deterministic and locally testable before external services are
  introduced.

### Errors Fixed
- None.

### Added
- Created the Step 1 project foundation for the resume parsing agent.
- Added explicit telemetry package initialization for stable imports.
- Added tests for settings, schemas, structured errors, logging, and timing.
- Ignored Python editable-install metadata generated during local test setup.

### Why
- Establishes the approved greenfield structure, pinned dependency policy, typed
  configuration, schemas, structured errors, logging setup, resume storage
  directory, and timing utilities before implementing parser behavior.
- Keeps telemetry utilities importable as the package grows in later steps.
- Keeps the foundation aligned with the required 80% test coverage gate instead
  of weakening the coverage configuration.
- Prevents generated packaging artifacts from polluting future source changes.

### Errors Fixed
- Fixed coverage gate failure:
  `Coverage failure: total of 25 is less than fail-under=80`.
