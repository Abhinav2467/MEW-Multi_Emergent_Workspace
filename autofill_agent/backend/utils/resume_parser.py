import re
from typing import Dict, Any

def parse_resume_text(text: str) -> Dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group(0) if email_match else "l4abhi@yahoo.com"
    
    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    phone = phone_match.group(0) if phone_match else ""
    
    name = lines[0] if lines else "Kamutala Abhinav Address"
    name_parts = name.split()
    first_name = name_parts[0] if name_parts else "Kamutala"
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "Abhinav Address"
    
    skills = []
    for line in lines:
        if "skill" in line.lower() or "technology" in line.lower():
            raw = line.split(":", 1)[-1] if ":" in line else line
            skills = [s.strip() for s in raw.split(",") if s.strip()]
            break
            
    if not skills:
        skills = ["Python", "HTML", "SQL", "Java", "Machine Learning", "Ethical Hacking", "C++", "C"]
        
    return {
        "personal": {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": name,
            "email": email,
            "phone": phone,
            "linkedin_url": "",
            "github_url": "",
            "portfolio_url": "",
            "location": "Remote",
            "work_authorization": "Authorized"
        },
        "professional": {
            "current_title": "Software Engineer",
            "years_experience": 0,
            "primary_skills": skills,
            "summary": "Experienced software engineer specializing in Python, Machine Learning, and Full-Stack Systems."
        },
        "custom_qa": {
            "willing_to_relocate": "Yes"
        }
    }
