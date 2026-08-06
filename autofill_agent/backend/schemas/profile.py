from typing import List, Dict, Optional
from pydantic import BaseModel, EmailStr

class PersonalProfile(BaseModel):
    first_name: str
    last_name: str
    full_name: str
    email: EmailStr
    phone: str
    linkedin_url: Optional[str] = ""
    github_url: Optional[str] = ""
    portfolio_url: Optional[str] = ""
    location: str
    work_authorization: str

class ProfessionalProfile(BaseModel):
    current_title: str
    years_experience: int
    primary_skills: List[str]
    summary: str

class CandidateProfile(BaseModel):
    personal: PersonalProfile
    professional: ProfessionalProfile
    custom_qa: Dict[str, str] = {}
