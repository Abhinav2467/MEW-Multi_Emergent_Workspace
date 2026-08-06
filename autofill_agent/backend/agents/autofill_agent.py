import os
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
try:
    from autofill_agent.backend.schemas.autofill import DOMFieldDescriptor, FuzzyMatchResponse, FuzzyMatchItem
except ModuleNotFoundError:
    from backend.schemas.autofill import DOMFieldDescriptor, FuzzyMatchResponse, FuzzyMatchItem


def _get_heuristic_matches(fields: List[DOMFieldDescriptor], profile_data: Dict[str, Any]) -> List[FuzzyMatchItem]:
    matches = []
    p = profile_data.get("personal", {})
    prof = profile_data.get("professional", {})
    qa = profile_data.get("custom_qa", {})

    for field in fields:
        label_lower = (field.label or "").lower()
        placeholder_lower = (field.placeholder or "").lower()
        elem_id_lower = (field.element_id or "").lower()
        input_type_lower = (field.input_type or "").lower()
        combined = f"{label_lower} {placeholder_lower} {elem_id_lower} {input_type_lower}"

        val = ""
        matched_key = "unknown"

        if any(k in combined for k in ["first_name", "first name", "firstname", "fname", "given-name"]):
            val = p.get("first_name", "") or (p.get("full_name", "").split(" ")[0] if p.get("full_name") else "")
            matched_key = "personal.first_name"
        elif any(k in combined for k in ["last_name", "last name", "lastname", "lname", "family-name"]):
            val = p.get("last_name", "") or (" ".join(p.get("full_name", "").split(" ")[1:]) if p.get("full_name") else "")
            matched_key = "personal.last_name"
        elif any(k in combined for k in ["full_name", "full name", "fullname", "your name"]):
            val = p.get("full_name", "") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
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
        elif any(k in combined for k in ["location", "city", "address", "state"]):
            val = p.get("location", "")
            matched_key = "personal.location"
        elif any(k in combined for k in ["title", "headline", "position", "role"]):
            val = prof.get("current_title", "")
            matched_key = "professional.current_title"
        elif any(k in combined for k in ["skill", "technolog"]):
            skills = prof.get("primary_skills", [])
            val = ", ".join(skills) if isinstance(skills, list) else str(skills)
            matched_key = "professional.primary_skills"
        elif any(k in combined for k in ["experience", "years"]):
            val = str(prof.get("years_experience", 0))
            matched_key = "professional.years_experience"
        elif "relocate" in combined:
            val = qa.get("willing_to_relocate", "Yes")
            matched_key = "custom_qa.willing_to_relocate"

        if val:
            matches.append(FuzzyMatchItem(
                element_id=field.element_id,
                matched_key=matched_key,
                value=val,
                confidence=0.95,
                reasoning="Rule heuristic match."
            ))
    return matches


def match_dom_fields_with_ai(fields: List[DOMFieldDescriptor], profile_data: Dict[str, Any]) -> FuzzyMatchResponse:
    # 1. Deterministic heuristic baseline matches
    base_matches = _get_heuristic_matches(fields, profile_data)
    matched_ids = {m.element_id: m for m in base_matches}

    try:
        from backend.config import get_settings
        settings = get_settings()
        google_key = settings.resolved_gemini_api_key or os.getenv("GOOGLE_API_KEY", "")
        model_name = settings.gemini_model or "gemini-2.5-flash"
    except Exception:
        google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        model_name = "gemini-2.5-flash"

    if not google_key:
        return FuzzyMatchResponse(matches=list(matched_ids.values()))

    try:
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=google_key)
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
        res = structured_llm.invoke(prompt)
        if res and res.matches:
            for item in res.matches:
                if item.element_id not in matched_ids and item.value:
                    matched_ids[item.element_id] = item
                elif item.element_id in matched_ids and item.confidence > matched_ids[item.element_id].confidence:
                    matched_ids[item.element_id] = item
    except Exception as err:
        print(f"[Warning] AI matching LLM fallback to heuristic: {err}")

    return FuzzyMatchResponse(matches=list(matched_ids.values()))
