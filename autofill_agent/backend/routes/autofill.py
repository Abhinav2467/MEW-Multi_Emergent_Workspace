from fastapi import APIRouter
try:
    from autofill_agent.backend.routes.profile import load_profile_data
    from autofill_agent.backend.schemas.autofill import EventHints, FuzzyMatchRequest
    from autofill_agent.backend.agents.autofill_agent import match_dom_fields_with_ai
except ModuleNotFoundError:
    from backend.routes.profile import load_profile_data
    from backend.schemas.autofill import EventHints, FuzzyMatchRequest
    from backend.agents.autofill_agent import match_dom_fields_with_ai

router = APIRouter(prefix="/api/v1", tags=["Autofill"])

@router.get("/autofill-payload")
async def get_autofill_payload():
    profile = load_profile_data()
    payload = profile.copy()
    payload["event_hints"] = EventHints().model_dump()
    return {"status": "success", "data": payload}

@router.post("/autofill-payload/match")
async def match_autofill_fields(request: FuzzyMatchRequest):
    profile = load_profile_data()
    match_response = match_dom_fields_with_ai(request.fields, profile)
    return {"status": "success", "data": match_response.model_dump()}

