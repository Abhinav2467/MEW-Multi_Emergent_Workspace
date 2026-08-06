import os
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI

def generate_cold_email(company: str, job_title: str, recruiter_name: str, profile_data: Dict[str, Any]) -> Dict[str, str]:
    p = profile_data.get("personal", {})
    prof = profile_data.get("professional", {})
    candidate_name = p.get("full_name", "Kamutala Abhinav Address")
    skills = ", ".join(prof.get("primary_skills", ["Python", "Machine Learning"]))
    
    google_key = os.getenv("GOOGLE_API_KEY", "")
    if google_key:
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=google_key)
            prompt = f"""
Write a high-converting, concise recruiter outreach email for a job application.
Candidate: {candidate_name} ({p.get('email')})
Skills: {skills}
Target Role: {job_title} at {company}
Recruiter: {recruiter_name or 'Hiring Manager'}

Format as JSON with 'subject' and 'body'.
"""
            res = llm.invoke(prompt)
        except Exception:
            pass

    subject = f"Application for {job_title} — {candidate_name}"
    body = f"""Hi {recruiter_name or 'Hiring Manager'},

I recently applied for the {job_title} role at {company} and wanted to reach out directly. 

With strong experience in {skills}, I have built high-impact software systems and AI automation tools. I would love to discuss how my background aligns with the engineering goals at {company}.

My resume is attached, and you can also check out my profile here: {p.get('portfolio_url') or 'https://github.com/Abhinav2467'}.

Best regards,
{candidate_name}
{p.get('email')} | {p.get('phone')}
"""
    return {"subject": subject, "body": body}
