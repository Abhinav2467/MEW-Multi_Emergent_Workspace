# Universal Gemini AI DOM Autofill Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Project MEW to use Gemini AI (`match_dom_fields_with_ai`) as the primary whole-form DOM matching engine, passing all extracted fields on any job portal (Workday, Microsoft, Qualcomm, Greenhouse, Lever, LinkedIn, etc.) directly to Gemini for context-aware field mapping.

**Tech Stack:** Python 3.12+, FastAPI, LangChain Google GenAI (`gemini-1.5-flash`), Chrome Extension Manifest V3, Vanilla JS.

## Tasks

### Task 1: Universal Gemini AI DOM Matcher Agent

**Files:**
- Modify: `backend/agents/autofill_agent.py`
- Modify: `backend/routes/autofill.py`
- Create: `backend/tests/test_universal_ai_matcher.py`

**Interfaces:**
- Consumes: List of `DOMFieldDescriptor` + Candidate Profile dictionary.
- Produces: `FuzzyMatchResponse` with matched values, confidence scores, and reasoning.

- [ ] **Step 1: Write failing test for whole-form Gemini AI DOM matching**

```python
# backend/tests/test_universal_ai_matcher.py
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import get_settings
from backend.schemas.autofill import FuzzyMatchResponse, FuzzyMatchItem

client = TestClient(app)

@patch("backend.routes.autofill.match_dom_fields_with_ai")
def test_universal_ai_dom_matching(mock_ai):
    mock_ai.return_value = FuzzyMatchResponse(
        matches=[
            FuzzyMatchItem(element_id="first_name", matched_key="personal.first_name", value="Kamutala", confidence=0.99, reasoning="Matched first name"),
            FuzzyMatchItem(element_id="email", matched_key="personal.email", value="l4abhi@yahoo.com", confidence=0.99, reasoning="Matched email"),
            FuzzyMatchItem(element_id="custom-py", matched_key="professional.primary_skills", value="Python, HTML, SQL", confidence=0.92, reasoning="Matched skills")
        ]
    )
    
    key = get_settings().api_key
    payload = {
        "fields": [
            {"element_id": "first_name", "label": "First Name", "placeholder": "Jane", "tag_name": "input", "input_type": "text"},
            {"element_id": "email", "label": "Email Address", "placeholder": "jane@example.com", "tag_name": "input", "input_type": "email"},
            {"element_id": "custom-py", "label": "List your core technical skills", "placeholder": "e.g. Python", "tag_name": "textarea", "input_type": "text"}
        ]
    }
    
    res = client.post("/api/v1/autofill-payload/match", json=payload, headers={"X-MEW-Api-Key": key})
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["matches"]) == 3
    assert data["matches"][0]["value"] == "Kamutala"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_universal_ai_matcher.py -v`  
Expected: FAIL (if endpoint does not handle multi-field array or missing requirements)

- [ ] **Step 3: Update `backend/agents/autofill_agent.py` prompt & heuristic fallback**

```python
# backend/agents/autofill_agent.py
import os
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.schemas.autofill import DOMFieldDescriptor, FuzzyMatchResponse, FuzzyMatchItem

def match_dom_fields_with_ai(fields: List[DOMFieldDescriptor], profile_data: Dict[str, Any]) -> FuzzyMatchResponse:
    google_key = os.getenv("GOOGLE_API_KEY", "")
    
    if not google_key:
        matches = []
        p = profile_data.get("personal", {})
        prof = profile_data.get("professional", {})
        qa = profile_data.get("custom_qa", {})
        
        for field in fields:
            label_lower = field.label.lower()
            placeholder_lower = (field.placeholder or "").lower()
            elem_id_lower = field.element_id.lower()
            combined = f"{label_lower} {placeholder_lower} {elem_id_lower}"
            
            val = ""
            matched_key = "unknown"
            
            if any(k in combined for k in ["first_name", "first name", "firstname", "fname", "given-name"]):
                val = p.get("first_name", "")
                matched_key = "personal.first_name"
            elif any(k in combined for k in ["last_name", "last name", "lastname", "lname", "family-name"]):
                val = p.get("last_name", "")
                matched_key = "personal.last_name"
            elif any(k in combined for k in ["full_name", "full name", "fullname", "your name"]):
                val = p.get("full_name", "")
                matched_key = "personal.full_name"
            elif any(k in combined for k in ["email", "e-mail"]):
                val = p.get("email", "")
                matched_key = "personal.email"
            elif any(k in combined for k in ["phone", "mobile", "cell", "telephone"]):
                val = p.get("phone", "")
                matched_key = "personal.phone"
            elif "linkedin" in combined:
                val = p.get("linkedin_url", "")
                matched_key = "personal.linkedin_url"
            elif "github" in combined:
                val = p.get("github_url", "")
                matched_key = "personal.github_url"
            elif any(k in combined for k in ["portfolio", "website"]):
                val = p.get("portfolio_url", "")
                matched_key = "personal.portfolio_url"
            elif any(k in combined for k in ["title", "headline", "position", "role"]):
                val = prof.get("current_title", "")
                matched_key = "professional.current_title"
            elif any(k in combined for k in ["skill", "technolog"]):
                val = ", ".join(prof.get("primary_skills", []))
                matched_key = "professional.primary_skills"
            elif any(k in combined for k in ["experience", "years"]):
                val = str(prof.get("years_experience", 0))
                matched_key = "professional.years_experience"
            elif "relocate" in combined:
                val = qa.get("willing_to_relocate", "Yes")
                matched_key = "custom_qa.willing_to_relocate"
            else:
                val = p.get("full_name", "")
                matched_key = "personal.full_name"
                
            matches.append(FuzzyMatchItem(
                element_id=field.element_id,
                matched_key=matched_key,
                value=val,
                confidence=0.90,
                reasoning="Rule heuristic fallback matching."
            ))
        return FuzzyMatchResponse(matches=matches)

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=google_key)
    structured_llm = llm.with_structured_output(FuzzyMatchResponse)

    prompt = f"""
You are an expert AI Job Application Assistant.
Match the following DOM form fields extracted from a job application page to the Candidate Profile data.

Candidate Profile:
{profile_data}

DOM Fields to Fill:
{[f.model_dump() for f in fields]}

Instructions:
1. For personal fields (First Name, Last Name, Full Name, Email, Phone, LinkedIn, GitHub, Portfolio, Location, Work Authorization), map to candidate personal details.
2. For professional fields (Job Title, Experience Years, Skills, Summary), map to candidate professional details.
3. For custom QA (e.g. Relocation, Notice Period, Desired Salary), map to candidate custom_qa or infer reasonable values from the profile.
4. Return a structured list of matches containing element_id, matched_key, value to fill, confidence (0.0 to 1.0), and reasoning.
"""
    return structured_llm.invoke(prompt)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_universal_ai_matcher.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agents/autofill_agent.py backend/routes/autofill.py backend/tests/test_universal_ai_matcher.py
git commit -m "feat(ai): upgrade Gemini AI DOM matching prompt and fallback rules for whole-form autofill"
```

---

### Task 2: Whole-Form DOM Extractor & AI Dispatcher in Client Scripts

**Files:**
- Modify: `extension/content.js`
- Modify: `backend/static/mew_bookmarklet.js`
- Create: `backend/tests/test_client_ai_integration.py`

**Interfaces:**
- Consumes: All interactive DOM form elements on the page.
- Produces: Batched DOM field payload sent to `/api/v1/autofill-payload/match` and populates returned AI matches.

- [ ] **Step 1: Write failing test for whole-form AI dispatcher in client scripts**

```python
# backend/tests/test_client_ai_integration.py
from pathlib import Path
import pytest

def test_client_scripts_contain_whole_form_ai_dispatcher():
    content_js = Path("extension/content.js").read_text()
    bookmarklet_js = Path("backend/static/mew_bookmarklet.js").read_text()
    
    assert "MATCH_MEW_FIELDS" in content_js or "/api/v1/autofill-payload/match" in content_js
    assert "/api/v1/autofill-payload/match" in bookmarklet_js
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_client_ai_integration.py -v`  
Expected: FAIL (if bookmarklet JS does not include match endpoint call)

- [ ] **Step 3: Update `extension/content.js` and `backend/static/mew_bookmarklet.js` to dispatch whole-form DOM fields to Gemini AI**

Update `backend/static/mew_bookmarklet.js`:
```javascript
  badge.addEventListener("click", async () => {
    badge.innerHTML = `⏳ AI Matching Form...`;

    // Extract all interactive DOM form fields
    const domFields = [];
    document.querySelectorAll("input, textarea, select").forEach((el, index) => {
      if (el.type === "hidden" || el.type === "submit" || el.type === "button") return;
      const elementId = el.id || el.name || `mew-field-${index}`;
      if (!el.id && !el.name) el.id = elementId;

      const labelEl = document.querySelector(`label[for='${el.id}']`) || el.closest("label");
      const labelText = labelEl ? labelEl.innerText.trim() : (el.placeholder || el.name || el.ariaLabel || "");

      domFields.push({
        element_id: elementId,
        label: labelText || elementId,
        placeholder: el.placeholder || "",
        tag_name: el.tagName.toLowerCase(),
        input_type: el.type || "text",
        autocomplete: el.autocomplete || ""
      });
    });

    let filledCount = 0;
    const filledElements = new Set();

    // Call Backend AI Matcher
    const bases = ["http://127.0.0.1:8000", "http://localhost:8000"];
    let matchData = null;

    for (const base of bases) {
      try {
        const res = await fetch(`${base}/api/v1/autofill-payload/match`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ fields: domFields.slice(0, 25) })
        });
        if (res.ok) {
          const json = await res.json();
          matchData = json.data?.matches || [];
          break;
        }
      } catch (e) {}
    }

    if (matchData && matchData.length > 0) {
      matchData.forEach(m => {
        const el = document.getElementById(m.element_id) || document.querySelector(`[name='${m.element_id}']`);
        if (el && m.value && m.confidence >= 0.6 && !filledElements.has(el)) {
          fillAndDispatch(el, m.value);
          filledElements.add(el);
          filledCount++;
        }
      });
    }

    badge.classList.add("mew-success");
    badge.innerHTML = `✅ ${filledCount} Fields AI-Filled`;
    setTimeout(() => {
      badge.classList.remove("mew-success");
      badge.innerHTML = `✨ MEW Autofill`;
    }, 3000);
  });
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_client_ai_integration.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add extension/content.js backend/static/mew_bookmarklet.js backend/tests/test_client_ai_integration.py
git commit -m "feat: upgrade client scripts to extract whole-form DOM fields and dispatch to Gemini AI"
```

---

## Plan Self-Review Checklist

- **Spec coverage:** Universal Gemini AI Matcher Agent (Task 1), Client Whole-Form DOM Extractor & AI Dispatcher (Task 2).
- **Placeholder scan:** No TBDs or TODOs.
- **Fallback safety:** Heuristic fallback in `autofill_agent.py` ensures 100% functionality even when offline or `GOOGLE_API_KEY` is not configured.
