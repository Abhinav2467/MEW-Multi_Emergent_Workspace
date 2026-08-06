from typing import List, Optional
from pydantic import BaseModel

class ApplicationLogItem(BaseModel):
    id: Optional[str] = None
    company: str
    job_title: str
    url: str
    status: str = "Submitted"
    timestamp: Optional[str] = None

class ApplicationLogResponse(BaseModel):
    status: str = "success"
    data: List[ApplicationLogItem]
