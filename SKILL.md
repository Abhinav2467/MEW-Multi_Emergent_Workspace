# Job Matching and Lead Pipeline

> **Preferred path:** use the unified FastAPI backend in [`backend/`](backend/).
> See [`backend/API.md`](backend/API.md) for the React frontend contract.

```bash
cd /path/to/job_applying_agent
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env   # fill API keys
uvicorn backend.main:app --reload --port 8000
```

### Streamlit test UI

With the backend running, start the tester in a second terminal:

```bash
streamlit run streamlit_app.py
```

Opens at http://localhost:8501. Use the sidebar to authenticate (Google OAuth code or pasted JWT), then walk through Resume → Jobs → Emails.

Pipeline:
1. **Resume upload** → Gemini Flash parse (deterministic fallback) → profile confirm
2. **Job matching** → CareerZenith + skill scoring → JSON + Excel under `backend/reports/`
3. **Cold email** → LangGraph recruiter discovery → Gmail draft → optional send

---

## Deprecated entry points

The following remain for reference but are **not** the supported integration path:

| Path | Status |
|---|---|
| `orchestrator.py` | Deprecated — logic ported to `backend/agents/job_search/` and `backend/services/` |
| `cold_email_agent/` | Deprecated — ported to `backend/agents/cold_email/` |
| `resume parsing agent/` | Deprecated — parser ported to `backend/agents/parser/` (Telegram bot removed from unified backend) |
| `match.rb` | Optional latest-jobs feed only; matching lives in Python |

### Legacy orchestrator (deprecated)

```bash
python3 orchestrator.py
```

### Legacy Ruby latest-jobs feed

```bash
ruby match.rb [API_FEED_URL]
```
