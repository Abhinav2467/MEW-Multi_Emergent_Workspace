"""Simple Streamlit UI for testing the unified Job Applying Agent backend."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import streamlit as st

DEFAULT_BASE_URL = "http://localhost:8000"
TIMEOUT = 120.0


def init_state() -> None:
    defaults = {
        "base_url": DEFAULT_BASE_URL,
        "jwt": None,
        "user": None,
        "profile_id": None,
        "profile": None,
        "report_id": None,
        "matches": [],
        "drafts": [],
        "google_auth_url": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def headers() -> dict[str, str]:
    h = {"Accept": "application/json"}
    if st.session_state.jwt:
        h["Authorization"] = f"Bearer {st.session_state.jwt}"
    return h


def base() -> str:
    return st.session_state.base_url.rstrip("/")


def show_error(exc: Exception) -> None:
    if isinstance(exc, httpx.HTTPStatusError):
        detail = exc.response.text
        try:
            detail = exc.response.json()
        except Exception:
            pass
        st.error(f"HTTP {exc.response.status_code}: {detail}")
    else:
        st.error(str(exc))


def api_get(path: str, **kwargs: Any) -> Any:
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.get(f"{base()}{path}", headers=headers(), **kwargs)
        resp.raise_for_status()
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.content


def api_post(path: str, *, json_body: dict | None = None, files=None, **kwargs: Any) -> Any:
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(
            f"{base()}{path}",
            headers=headers(),
            json=json_body,
            files=files,
            **kwargs,
        )
        resp.raise_for_status()
        if not resp.content:
            return None
        if resp.headers.get("content-type", "").startswith("application/json"):
            return resp.json()
        return resp.content


def api_put(path: str, json_body: dict) -> Any:
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.put(f"{base()}{path}", headers=headers(), json=json_body)
        resp.raise_for_status()
        return resp.json()


def extract_oauth_code(text: str) -> str:
    """Accept a raw code or a full callback URL containing ?code=."""
    text = text.strip()
    if text.startswith("http"):
        qs = parse_qs(urlparse(text).query)
        if "code" in qs:
            return qs["code"][0]
    return text


def render_sidebar() -> None:
    st.sidebar.title("Backend Tester")
    st.session_state.base_url = st.sidebar.text_input(
        "Backend URL",
        value=st.session_state.base_url,
    )

    if st.sidebar.button("Health check"):
        try:
            data = api_get("/health")
            st.sidebar.success(f"OK: {data}")
        except Exception as exc:
            show_error(exc)

    st.sidebar.divider()
    st.sidebar.subheader("Auth")

    if st.sidebar.button("Get Google OAuth URL"):
        try:
            data = api_get("/auth/google")
            st.session_state.google_auth_url = data.get("url")
            st.sidebar.success("OAuth URL ready below")
        except Exception as exc:
            show_error(exc)

    if st.session_state.google_auth_url:
        st.sidebar.markdown(f"[Open Google login]({st.session_state.google_auth_url})")
        st.sidebar.caption(
            "After Google consent, copy the **authorization code** shown on the page "
            "(out-of-band / Desktop client flow — same as cold_email_agent). "
            "Paste it below. Or paste an existing JWT."
        )

    oauth_input = st.sidebar.text_area(
        "OAuth authorization code",
        height=80,
        placeholder="Paste the code Google shows after you approve access",
    )
    if st.sidebar.button("Exchange code for JWT"):
        if not oauth_input.strip():
            st.sidebar.warning("Paste an OAuth code first")
        else:
            try:
                code = extract_oauth_code(oauth_input)
                with httpx.Client(timeout=TIMEOUT) as client:
                    resp = client.get(
                        f"{base()}/auth/callback",
                        params={"code": code},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                st.session_state.jwt = data["access_token"]
                st.session_state.user = data.get("user")
                st.sidebar.success(f"Logged in as {data.get('user', {}).get('email')}")
                st.rerun()
            except Exception as exc:
                show_error(exc)

    jwt_paste = st.sidebar.text_input("Or paste existing JWT", type="password")
    if st.sidebar.button("Use pasted JWT"):
        if not jwt_paste.strip():
            st.sidebar.warning("Paste a JWT first")
        else:
            st.session_state.jwt = jwt_paste.strip()
            try:
                st.session_state.user = api_get("/auth/me")
                st.sidebar.success(f"Using JWT for {st.session_state.user.get('email')}")
                st.rerun()
            except Exception as exc:
                st.session_state.jwt = None
                st.session_state.user = None
                show_error(exc)

    if st.session_state.jwt:
        st.sidebar.success("Authenticated")
        if st.session_state.user:
            st.sidebar.json(st.session_state.user)
        if st.sidebar.button("Refresh /auth/me"):
            try:
                st.session_state.user = api_get("/auth/me")
                st.rerun()
            except Exception as exc:
                show_error(exc)
        if st.sidebar.button("Log out"):
            st.session_state.jwt = None
            st.session_state.user = None
            st.rerun()
    else:
        st.sidebar.info("Not logged in")


def require_auth() -> bool:
    if not st.session_state.jwt:
        st.warning("Log in from the sidebar first (OAuth code or JWT).")
        return False
    return True


def render_resume_tab() -> None:
    st.subheader("1. Resume")
    if not require_auth():
        return

    uploaded = st.file_uploader("Upload resume (PDF or DOCX)", type=["pdf", "docx"])
    if uploaded and st.button("Upload & parse"):
        try:
            files = {
                "file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")
            }
            with st.spinner("Parsing resume..."):
                data = api_post("/upload-resume", files=files)
            st.session_state.profile_id = data["id"]
            st.session_state.profile = data
            st.success(f"Profile #{data['id']} parsed via {data.get('parse_method')}")
        except Exception as exc:
            show_error(exc)

    if not st.session_state.profile:
        st.info("Upload a resume to continue.")
        return

    profile_wrap = st.session_state.profile
    profile = profile_wrap.get("profile") or {}
    contact = profile.get("contact") or {}

    try:
        st.components.v1.html(
            f"""
            <script>
                try {{
                    const payload = {json.dumps(profile)};
                    window.parent.postMessage({{ type: "MEW_PROFILE_SYNC", profile: payload }}, "*");
                }} catch (e) {{}}
            </script>
            """,
            height=0,
        )
    except Exception:
        pass

    st.markdown(f"**Profile ID:** `{st.session_state.profile_id}` · confirmed: `{profile_wrap.get('confirmed')}`")

    with st.form("edit_profile"):
        name = st.text_input("Name", value=contact.get("name") or "")
        email = st.text_input("Email", value=contact.get("email") or "")
        phone = st.text_input("Phone", value=contact.get("phone") or "")
        location = st.text_input("Location", value=contact.get("location") or "")
        linkedin = st.text_input("LinkedIn", value=contact.get("linkedin") or "")
        skills_raw = st.text_area(
            "Skills (comma-separated)",
            value=", ".join(profile.get("skills") or []),
        )
        current_role = st.text_input("Current role", value=profile.get("current_role") or "")
        preferred_raw = st.text_area(
            "Preferred roles (comma-separated)",
            value=", ".join(profile.get("preferred_roles") or []),
        )
        experience_years = st.number_input(
            "Experience years",
            min_value=0.0,
            value=float(profile.get("experience_years") or 0),
            step=0.5,
        )
        save = st.form_submit_button("Save edits (PUT)")
        if save:
            body = {
                "contact": {
                    "name": name or None,
                    "email": email or None,
                    "phone": phone or None,
                    "location": location or None,
                    "linkedin": linkedin or None,
                    "links": contact.get("links") or [],
                },
                "skills": [s.strip() for s in skills_raw.split(",") if s.strip()],
                "current_role": current_role or None,
                "preferred_roles": [s.strip() for s in preferred_raw.split(",") if s.strip()],
                "experience_years": experience_years,
            }
            try:
                data = api_put(f"/resume/{st.session_state.profile_id}", body)
                st.session_state.profile = data
                st.success("Profile updated")
                st.rerun()
            except Exception as exc:
                show_error(exc)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Rescan with Gemini"):
            try:
                with st.spinner("Rescanning..."):
                    data = api_post(f"/resume/{st.session_state.profile_id}/rescan")
                st.session_state.profile = data
                st.success("Rescan complete")
                st.rerun()
            except Exception as exc:
                show_error(exc)
    with col2:
        if st.button("Confirm & run job search", type="primary"):
            try:
                with st.spinner("Confirming and matching jobs (may take a while)..."):
                    data = api_post(f"/resume/{st.session_state.profile_id}/confirm")
                st.session_state.report_id = data["report_id"]
                st.session_state.matches = data.get("matches") or []
                st.session_state.profile = api_get(f"/resume/{st.session_state.profile_id}")
                st.success(
                    f"Report #{data['report_id']} ready with {data.get('match_count', 0)} matches"
                )
            except Exception as exc:
                show_error(exc)

    with st.expander("Raw profile JSON"):
        st.json(st.session_state.profile)


def render_jobs_tab() -> None:
    st.subheader("2. Jobs & Reports")
    if not require_auth():
        return

    if st.button("List my reports"):
        try:
            reports = api_get("/reports")
            st.session_state["_reports"] = reports
        except Exception as exc:
            show_error(exc)

    reports = st.session_state.get("_reports") or []
    if reports:
        st.write("Reports:")
        for r in reports:
            st.caption(
                f"#{r['id']} status={r['status']} profile={r['profile_id']} created={r.get('created_at')}"
            )

    report_id = st.number_input(
        "Report ID",
        min_value=0,
        value=int(st.session_state.report_id or 0),
        step=1,
    )
    if st.button("Load report"):
        if not report_id:
            st.warning("Enter a report ID (or confirm a resume first)")
        else:
            try:
                data = api_get(f"/reports/{int(report_id)}")
                st.session_state.report_id = data["id"]
                st.session_state.matches = data.get("matches") or []
                st.success(f"Loaded report #{data['id']} ({data.get('status')})")
            except Exception as exc:
                show_error(exc)

    matches = st.session_state.matches or []
    if not matches:
        st.info("No matches loaded. Confirm a resume or load a report.")
        return

    st.write(f"**{len(matches)}** job matches")
    rows = [
        {
            "ID": m.get("id"),
            "Company": m.get("company_name"),
            "Position": m.get("position"),
            "Match %": m.get("matching_percentage"),
            "Skills": m.get("relevant_skills"),
            "HR Name": m.get("hr_recruiter_name") or "",
            "HR Email": m.get("hr_recruiter_email") or "",
            "Apply": m.get("apply_link"),
        }
        for m in matches
    ]
    st.dataframe(rows, use_container_width=True)

    if st.session_state.report_id and st.button("Download Excel"):
        try:
            content = api_get(f"/reports/{st.session_state.report_id}/excel")
            st.download_button(
                "Save report.xlsx",
                data=content,
                file_name=f"job_matches_report_{st.session_state.report_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as exc:
            show_error(exc)


def render_emails_tab() -> None:
    st.subheader("3. Cold Emails")
    if not require_auth():
        return

    matches = st.session_state.matches or []
    if not matches:
        st.info("Load job matches from the Jobs tab first.")
    else:
        options = {
            f"#{m['id']} — {m.get('company_name')} / {m.get('position')} ({m.get('matching_percentage')}%)": m["id"]
            for m in matches
        }
        selected_labels = st.multiselect("Select jobs for drafts", list(options.keys()))
        selected_ids = [options[label] for label in selected_labels]

        if st.button("Create Gmail drafts", type="primary"):
            if not selected_ids:
                st.warning("Select at least one job")
            else:
                try:
                    with st.spinner("Discovering recruiters and creating drafts..."):
                        drafts = api_post("/emails/drafts", json_body={"job_match_ids": selected_ids})
                    st.session_state.drafts = drafts
                    # Refresh matches so HR fields update
                    if st.session_state.report_id:
                        report = api_get(f"/reports/{st.session_state.report_id}")
                        st.session_state.matches = report.get("matches") or []
                    st.success(f"Created {len(drafts)} draft record(s)")
                except Exception as exc:
                    show_error(exc)

    if st.button("Refresh drafts list"):
        try:
            st.session_state.drafts = api_get("/emails/drafts")
        except Exception as exc:
            show_error(exc)

    drafts = st.session_state.drafts or []
    if drafts:
        st.write("Drafts:")
        draft_rows = [
            {
                "Draft ID": d.get("id"),
                "Job Match": d.get("job_match_id"),
                "Status": d.get("status"),
                "Gmail ID": d.get("gmail_draft_id") or "",
                "HR Name": d.get("hr_recruiter_name") or "",
                "HR Email": d.get("hr_recruiter_email") or "",
                "Error": d.get("error") or "",
            }
            for d in drafts
        ]
        st.dataframe(draft_rows, use_container_width=True)

        sendable = [d for d in drafts if d.get("status") == "draft"]
        send_options = {
            f"#{d['id']} → {d.get('hr_recruiter_email') or 'no email'} (job {d.get('job_match_id')})": d["id"]
            for d in sendable
        }
        if send_options:
            to_send_labels = st.multiselect("Drafts to send", list(send_options.keys()))
            to_send_ids = [send_options[label] for label in to_send_labels]
            if st.button("Send selected drafts", type="primary"):
                if not to_send_ids:
                    st.warning("Select drafts to send")
                else:
                    try:
                        with st.spinner("Sending..."):
                            result = api_post("/emails/send", json_body={"draft_ids": to_send_ids})
                        st.session_state.drafts = api_get("/emails/drafts")
                        st.success("Send completed")
                        st.json(result)
                    except Exception as exc:
                        show_error(exc)
        else:
            st.caption("No drafts in `draft` status ready to send.")
    else:
        st.caption("No drafts yet.")


def main() -> None:
    st.set_page_config(page_title="Job Applying Agent Tester", layout="wide")
    init_state()
    st.title("Job Applying Agent — Backend Tester")
    st.caption("Streamlit client for the FastAPI backend. Keep uvicorn running on the backend URL.")

    render_sidebar()

    tab_resume, tab_jobs, tab_emails = st.tabs(["Resume", "Jobs", "Emails"])
    with tab_resume:
        render_resume_tab()
    with tab_jobs:
        render_jobs_tab()
    with tab_emails:
        render_emails_tab()


if __name__ == "__main__":
    main()
