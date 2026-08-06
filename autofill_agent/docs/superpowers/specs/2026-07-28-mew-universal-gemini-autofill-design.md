# Project MEW — Universal Gemini AI DOM Autofill Engine Design

**Date:** 2026-07-28  
**Author:** AI Pair Programmer & Lead Developer  
**Status:** Approved  

---

## 1. Overview & Objectives

This design specifies the **Universal Gemini AI DOM Autofill Engine**:
1. **Whole-Page DOM Extraction:** Collecting all interactive form elements (`input`, `textarea`, `select`) on any job portal (Workday, Microsoft, Qualcomm, Greenhouse, Lever, LinkedIn, Ashby, Taleo, custom career sites) into clean DOM descriptors (`element_id`, `label`, `placeholder`, `tag_name`, `input_type`, `autocomplete`).
2. **AI-Powered Field Mapping (`backend/agents/autofill_agent.py`):** Sending the extracted DOM descriptors to `POST /api/v1/autofill-payload/match`. Gemini AI (`gemini-1.5-flash` / Gemini 2.0) evaluates the entire form schema against the candidate's parsed profile JSON and returns 100% structured field mappings with context-aware values.
3. **Resilient Local Fallback:** If `GOOGLE_API_KEY` is absent or offline, the system seamlessly uses local pattern matching without throwing errors.

---

## 2. Component Architecture

```text
[ Job Portal Page / Microsoft / Workday / Lever ]
                        │
       (User clicks "✨ MEW Autofill")
                        ▼
[ DOM Extractor (content.js & mew_bookmarklet.js) ]
                        │
        Extracts descriptors for all inputs/textareas
                        │
                        ▼
[ POST /api/v1/autofill-payload/match ]
                        │
                        ▼
[ Gemini AI Agent (backend/agents/autofill_agent.py) ]
                        │
       Evaluates DOM labels against Candidate Profile
                        │
                        ▼
[ Structured Matches Returned (element_id, value, confidence) ]
                        │
                        ▼
[ Synthetic Event Field Filler (focus -> input -> change -> blur) ]
```

---

## 3. Data Schemas & Prompt Engineering

### 3.1 DOMFieldDescriptor & Match Request (`backend/schemas/autofill.py`)
```python
class DOMFieldDescriptor(BaseModel):
    element_id: str
    label: str
    placeholder: Optional[str] = ""
    tag_name: str = "input"
    input_type: Optional[str] = "text"
    autocomplete: Optional[str] = ""

class FuzzyMatchRequest(BaseModel):
    fields: List[DOMFieldDescriptor]
```

### 3.2 Gemini AI Structured Output Prompt (`backend/agents/autofill_agent.py`)
```python
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
```

---

## 4. Verification Plan

### 4.1 Unit & API Tests
- Test `match_dom_fields_with_ai` in `backend/tests/test_fuzzy_match.py`.
- Test `POST /api/v1/autofill-payload/match` with whole-form DOM payloads.

### 4.2 End-to-End Verification
- Test on `http://localhost:8000/test-forms` across all 5 scenario forms.
- Test on live portals using both Bookmarklet and Chrome Extension.
