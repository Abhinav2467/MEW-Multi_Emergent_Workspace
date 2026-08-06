from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class EventHints(BaseModel):
    dispatch_sequence: List[str] = ["focus", "input", "change", "blur"]
    simulate_synthetic_events: bool = True

class DOMFieldDescriptor(BaseModel):
    element_id: str
    label: str = ""
    placeholder: str = ""
    tag_name: str = "input"
    input_type: str = "text"

class FuzzyMatchRequest(BaseModel):
    fields: List[DOMFieldDescriptor]

class FuzzyMatchItem(BaseModel):
    element_id: str
    matched_key: str
    value: str
    confidence: float
    reasoning: str

class FuzzyMatchResponse(BaseModel):
    matches: List[FuzzyMatchItem]
