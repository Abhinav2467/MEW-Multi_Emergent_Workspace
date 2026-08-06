"""
DEPRECATED: Use the unified FastAPI backend instead.

    uvicorn backend.main:app --reload --port 8000

See backend/API.md. Matching and recruiter logic lives in backend/agents/.
"""
import sys
import os
import re
from pathlib import Path
import requests
import pandas as pd
from urllib.parse import urlparse
from dotenv import load_dotenv

print(
    "WARNING: orchestrator.py is deprecated. Prefer: uvicorn backend.main:app --reload",
    file=sys.stderr,
)

# Set paths
WORKSPACE_DIR = Path(__file__).resolve().parent
COLD_EMAIL_AGENT_DIR = WORKSPACE_DIR / "cold_email_agent"
RESUME_PARSER_AGENT_DIR = WORKSPACE_DIR / "resume parsing agent"

# Add resume parser src to sys.path
sys.path.append(str(RESUME_PARSER_AGENT_DIR / "src"))
# Add cold email agent to sys.path to allow importing discover_recruiter_leads
sys.path.append(str(COLD_EMAIL_AGENT_DIR))

# Load root environment variables
load_dotenv(WORKSPACE_DIR / ".env")

from resume_parser_agent.parser.service import ResumeParserService
from tools import discover_recruiter_leads
from langchain_groq import ChatGroq

print("🌟 Starting Job Matching and Cold Email Lead Pipeline...")

# Step 1: Parse the PDF resume
print("📄 Parsing resume...")
resume_pdf_path = RESUME_PARSER_AGENT_DIR / "data" / "resumes" / "GORU_PARINITHA_REDDY__5fb4ab172fee4914917746fe5c8cea97.pdf"
if not resume_pdf_path.exists():
    print(f"❌ Error: Resume not found at {resume_pdf_path}")
    sys.exit(1)

parser_service = ResumeParserService()
parsed_resume = parser_service.parse_file(resume_pdf_path)

candidate_name = parsed_resume.contact.name or "Candidate"
candidate_email = parsed_resume.contact.email or ""
candidate_skills = [s.lower() for s in parsed_resume.skills]
resume_text_lower = parsed_resume.raw_text.lower()

print(f"✅ Resume parsed successfully!")
print(f"👤 Candidate Name: {candidate_name}")
print(f"📧 Candidate Email: {candidate_email}")
print(f"🛠️ Extracted Skills: {parsed_resume.skills}")

# Step 2: Fetch jobs from CareerZenith API
print("🌐 Fetching jobs from CareerZenith API...")
all_jobs = []
page = 1
while True:
    try:
        url = f"https://api.careerzenith.ai/job-board/user/?page={page}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            break
        data = response.json()
        all_jobs.extend(data['jobs'])
        total_pages = data['total_pages']
        if page >= total_pages:
            break
        page += 1
    except Exception as e:
        print(f"⚠️ Error fetching jobs from API: {e}")
        break

print(f"💼 Fetched {len(all_jobs)} total jobs.")

# Skill and keyword definitions matching match.rb
skills_dict = [
    'react', 'node', 'express', 'next', 'fastapi', 'tailwind', 'redux', 'docker', 'git',
    'python', 'c++', 'c', 'java', 'javascript', 'typescript',
    'mongodb', 'sql', 'vector database', 'pinecone',
    'rag', 'llama', 'gemini', 'genkit', 'agentic', 'langchain', 'langgraph',
    'packet inspection', 'wireshark', 'multi-thread', 'concurrency', 'rest api', 'distributed systems',
    'css', 'html', 'mysql', 'oop'
]

context_keywords = [
    'full-stack', 'backend', 'frontend', 'ai', 'machine learning', 'database engine', 
    'search engine', 'recommendation', 'parser', 'network security', 'automation', 'chatgpt'
]

# Cache of common company domains to avoid API calls or LLM queries
company_domain_cache = {
    "synopsys": "synopsys.com",
    "bny": "bnymellon.com",
    "tower research capital": "towerresearch.com",
    "cisco": "cisco.com",
    "google": "google.com",
    "microsoft": "microsoft.com",
    "ibm": "ibm.com",
    "docusign": "docusign.com",
    "intuit": "intuit.com",
    "hpe": "hpe.com",
    "visa": "visa.com",
    "amazon": "amazon.com",
    "mathworks": "mathworks.com",
    "amd": "amd.com",
    "lseg": "lseg.com",
    "netapp": "netapp.com",
    "aditya birla group": "adityabirla.com"
}

def resolve_company_domain(company_name, apply_link):
    """Helper to determine the company's domain name from url, cache or LLM."""
    parsed = urlparse(apply_link)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
        
    third_party_boards = ["greenhouse.io", "eightfold.ai", "smartrecruiters.com", "myworkdayjobs.com", "linkedin.com", "peoplestrong.com"]
    is_third_party = any(board in netloc for board in third_party_boards)
    
    if not is_third_party and "." in netloc:
        parts = netloc.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
            
    name_clean = company_name.lower().strip()
    if name_clean in company_domain_cache:
        return company_domain_cache[name_clean]
        
    for k, v in company_domain_cache.items():
        if k in name_clean or name_clean in k:
            return v
            
    # Fallback to LLM
    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant", 
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0
        )
        prompt = f"Identify the primary domain name for the company '{company_name}'. Return ONLY the domain name (e.g. google.com), nothing else."
        response = llm.invoke(prompt).content.strip().lower()
        if "." in response and len(response.split()) == 1:
            return response
    except Exception as e:
        print(f"⚠️ LLM domain resolution failed for {company_name}: {e}")
        
    return name_clean.replace(" ", "") + ".com"

# Step 3: Run job matching
print("🔍 Running matching logic...")
scored_jobs = []

for job in all_jobs:
    title = job.get('title', '').strip()
    desc = job.get('description', '').strip()
    company = job.get('company', {}).get('name', '').strip()
    url = job.get('url', '').strip()
    job_type = job.get('job_type', '').strip()
    exp_low = int(job.get('experience_low_level', 0))
    exp_high = int(job.get('experience_high_level', 0))
    
    title_lower = title.lower()
    desc_lower = desc.lower()
    
    # Filter junior/internship only
    if exp_low > 2 and job_type != 'INTERNSHIP':
        continue
    if any(k in title_lower for k in ['senior', 'lead', 'architect', 'principal', 'manager']):
        continue
        
    score = 0
    matched_skills = []
    
    # Match skills from job description
    for skill in skills_dict:
        pattern = rf"\b{re.escape(skill)}\b"
        if re.search(pattern, desc_lower) or re.search(pattern, title_lower):
            score += 10
            matched_skills.append(skill)
            
    # Context keywords match
    for kw in context_keywords:
        pattern = rf"\b{re.escape(kw)}\b"
        if re.search(pattern, desc_lower) or re.search(pattern, title_lower):
            score += 3
            
    # Internship boost
    if job_type == 'INTERNSHIP' or any(k in title_lower for k in ['intern', 'trainee', 'graduate']):
        score += 15
        
    max_possible_skill_matches = 8
    
    # Check if resume contains matched skills
    matched_skills_in_resume = []
    for skill in matched_skills:
        # Check against parsed list or raw resume text
        if skill in candidate_skills or re.search(rf"\b{re.escape(skill)}\b", resume_text_lower):
            matched_skills_in_resume.append(skill)
            
    if len(matched_skills_in_resume) > 0:
        match_percentage = min(int((len(matched_skills_in_resume) / max_possible_skill_matches) * 100), 100)
        if match_percentage == 0 and any(k in title_lower for k in ['software', 'developer', 'engineer']):
            match_percentage = 40
            
        scored_jobs.append({
            "company_name": company,
            "title": title,
            "apply_link": url,
            "job_type": job_type,
            "location": job.get('location', ''),
            "experience": f"{exp_low}-{exp_high} years",
            "matching_percentage": match_percentage,
            "matched_skills": list(set(matched_skills_in_resume))
        })

# Sort jobs by matching percentage descending
scored_jobs.sort(key=lambda x: x['matching_percentage'], reverse=True)

# Select top 15 matches (same as Ruby script limit)
top_matches = scored_jobs[:15]
print(f"📊 Identified {len(top_matches)} top matching jobs.")

# Step 4: Find HR Emails using Cold Email Agent
print("📧 Discovering recruiter email contacts...")
results_data = []

for idx, match in enumerate(top_matches):
    company = match["company_name"]
    link = match["apply_link"]
    skills_list = ", ".join(match["matched_skills"]).title()
    match_percentage = f"{match['matching_percentage']}%"
    
    # Find domain
    domain = resolve_company_domain(company, link)
    print(f"   [{idx+1}/15] {company} (Domain: {domain})...")
    
    # Search recruiter leads
    hr_email = "No contact found"
    hr_name = "Not found"
    
    try:
        leads = discover_recruiter_leads(company, "Recruiter", domain, job_title=match["title"], job_location=match.get("location", ""))
        if leads and len(leads) > 0:
            # Pick first lead that has an email
            lead = leads[0]
            hr_email = lead.get("email", "No contact found")
            hr_name = lead.get("name", "Not found")
            # If lead status is unverified_limit, maybe label it or note it
            if lead.get("status") == "unverified_limit":
                hr_email += " (unverified)"
    except Exception as e:
        print(f"      ⚠️ Recruiter search failed for {company}: {e}")
        
    results_data.append({
        "Company Name": company,
        "Position": match["title"],
        "Apply Link": link,
        "Matching Percentage": match_percentage,
        "Relevant Skilled Match": skills_list,
        "HR Recruiter Name": hr_name,
        "HR Recruiter Email": hr_email
    })

# Step 5: Save to Excel
output_excel_path = WORKSPACE_DIR / "job_matches_outreach.xlsx"
print(f"💾 Saving results to Excel: {output_excel_path}")

df = pd.DataFrame(results_data)
# Reorder columns as requested
df = df[["Company Name", "Position", "Apply Link", "Matching Percentage", "Relevant Skilled Match", "HR Recruiter Name", "HR Recruiter Email"]]

# Save to Excel
df.to_excel(output_excel_path, index=False)
print("🎉 Pipeline executed successfully!")
print(f"📂 Output generated at: {output_excel_path}")
