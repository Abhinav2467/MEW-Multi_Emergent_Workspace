import os, base64, shutil
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from tavily import TavilyClient
from pyhunter import PyHunter
from dotenv import load_dotenv

load_dotenv()
SCOPES = ['https://www.googleapis.com/auth/gmail.compose', 'https://www.googleapis.com/auth/gmail.send']

def get_gmail_service(user_creds_dict):
    creds = Credentials.from_authorized_user_info(user_creds_dict, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('gmail', 'v1', credentials=creds)

def generate_auth_url():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    return url

def swap_code_for_token(code):
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    flow.fetch_token(code=code)
    return flow.credentials.to_json()

def discover_recruiter_leads(company, role, domain, job_title=None, job_location=None):
    import json
    import re
    from langchain_groq import ChatGroq

    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    hunter = PyHunter(os.getenv("HUNTER_API_KEY"))
    
    search_query = f"{role} at {company} LinkedIn"
    if job_location:
        search_query = f"{role} at {company} {job_location} LinkedIn"
        
    try:
        results = tavily.search(query=search_query, search_depth="advanced", max_results=3)['results']
    except Exception as e:
        print(f"⚠️ Tavily search failed: {e}")
        return []
        
    leads = []
    search_data = []
    for r in results:
        search_data.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", "")
        })
        
    groq_api_key = os.getenv("GROQ_API_KEY")
    recruiter_profiles = []
    
    def clean_json_comments(json_str):
        # Match // only when NOT preceded by http: or https:
        json_str = re.sub(r'(?<!http:)(?<!https:)//.*$', '', json_str, flags=re.MULTILINE)
        # Strip multi-line comments
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        return json_str

    def extract_json_list(text):
        text = text.strip()
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end+1]
            json_str = clean_json_comments(json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                # Fallback cleanup
                cleaned = re.sub(r',\s*\]', ']', json_str)
                cleaned = re.sub(r',\s*\}', '}', cleaned)
                try:
                    return json.loads(cleaned)
                except Exception:
                    raise e
        raise ValueError(f"Could not parse JSON list from text: {text}")

    if groq_api_key:
        try:
            llm = ChatGroq(
                model="llama-3.1-8b-instant",
                groq_api_key=groq_api_key,
                temperature=0.0
            )
            
            prompt = (
                f"You are a recruiter research assistant. Analyze the following Google/Tavily search results for a LinkedIn recruiter at '{company}' "
                f"to find recruiters for the target job title '{job_title or 'N/A'}' and target location '{job_location or 'N/A'}'.\n\n"
                "Identify if any search result corresponds to a SPECIFIC, REAL INDIVIDUAL who is currently a Recruiter, Talent Acquisition, or HR professional at this company.\n\n"
                "Rules:\n"
                "1. Ignore company pages, job postings, group profiles, general articles, lists, news, or profiles that are NOT recruiters/HR at this company.\n"
                "2. Evaluate GEOGRAPHIC ALIGNMENT: Prioritize recruiters located in or hiring for the target location. Do not select recruiters in completely different geographic regions if a local recruiter is present.\n"
                "3. Evaluate ROLE/DEPARTMENT ALIGNMENT: Prioritize technical recruiters, university/campus recruiters (for junior roles), or engineering recruiters if the target job is technical. Avoid recruiting contacts in completely unrelated domains (like sales, finance, or retail recruitment) unless no other contact exists.\n"
                "4. For each identified real person, extract their first and last name (clean name only, remove prefixes/suffixes like 'MBA', 'MS', 'PHD', etc.) and their LinkedIn URL.\n"
                "5. If no recruiter profile aligns, return an empty JSON list [].\n"
                "6. DO NOT include any comments, explanations, notes, or double-slashes (//) inside the JSON output.\n\n"
                f"Search Results:\n{json.dumps(search_data, indent=2)}\n\n"
                "Format the output strictly as a JSON list of objects, with no markdown fences, explanation, or code blocks. Example:\n"
                "[\n"
                "  {\"name\": \"John Doe\", \"linkedin\": \"https://linkedin.com/in/...\"}\n"
                "]"
            )
            
            response_text = llm.invoke(prompt).content.strip()
            recruiter_profiles = extract_json_list(response_text)
        except Exception as e:
            print(f"⚠️ Groq recruiter identification failed: {e}")
            recruiter_profiles = []
            
    # Fallback to standard parsing if LLM failed
    if not recruiter_profiles:
        for r in results:
            title = r.get("title", "")
            title_lower = title.lower()
            if any(term in title_lower for term in ["hiring", "jobs", "careers", "recruitment", "scam", "news"]):
                continue
            name = title.split("-")[0].split("|")[0].strip()
            parts = name.split()
            if len(parts) >= 2 and len(parts) <= 4:
                recruiter_profiles.append({
                    "name": name,
                    "linkedin": r.get("url")
                })
                
    for profile in recruiter_profiles:
        name = profile.get("name", "").strip()
        linkedin = profile.get("linkedin", "").strip()
        if not name:
            continue
            
        parts = name.split()
        cleaned_parts = []
        for p in parts:
            clean_part = re.sub(r'[^a-zA-Z-]', '', p)
            if clean_part and clean_part.upper() not in ["MS", "MBA", "PHD", "HR", "RECRUITER", "II", "III", "IV", "V"]:
                cleaned_parts.append(clean_part)
                
        if len(cleaned_parts) >= 2:
            email = f"{cleaned_parts[0].lower()}.{cleaned_parts[-1].lower()}@{domain}"
        else:
            simple_parts = [re.sub(r'[^a-zA-Z-]', '', p) for p in parts if re.sub(r'[^a-zA-Z-]', '', p)]
            if len(simple_parts) >= 2:
                email = f"{simple_parts[0].lower()}.{simple_parts[-1].lower()}@{domain}"
            elif simple_parts:
                email = f"{simple_parts[0].lower()}@{domain}"
            else:
                email = f"recruiter@{domain}"
                
        status = "guessed"
        try:
            verify_res = hunter.email_verifier(email)
            if verify_res.get('result') == 'deliverable':
                status = "verified"
        except Exception as e:
            print(f"⚠️ Hunter error: {e}")
            status = "unverified_limit"
            
        leads.append({"name": name, "email": email, "linkedin": linkedin, "status": status})
            
    # Generic Fallback if no specific recruiter leads could be found
    if not leads:
        generic_prefixes = ["careers", "hr", "recruiting", "jobs", "talent"]
        for prefix in generic_prefixes:
            email = f"{prefix}@{domain}"
            try:
                verify_res = hunter.email_verifier(email)
                if verify_res.get('result') == 'deliverable':
                    leads.append({
                        "name": f"{company} HR Team",
                        "email": email,
                        "linkedin": f"https://www.{domain}",
                        "status": "verified"
                    })
                    break
            except Exception as e:
                print(f"⚠️ Generic verification failed for {email}: {e}")
                
    return leads

def execute_cold_email(creds, sender, to_email, to_name, subject, body, company, role, file_path, send_now):
    service = get_gmail_service(creds)
    msg = MIMEMultipart()
    msg['to'], msg['subject'] = to_email, subject
    msg.attach(MIMEText(body, 'plain'))
    new_name = None
    if os.path.exists(file_path):
        new_name = f"{sender.replace(' ','_')}_{company.replace(' ','')}.pdf"
        shutil.copy2(file_path, new_name)
        with open(new_name, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part); part.add_header('Content-Disposition', f'attachment; filename="{new_name}"')
        msg.attach(part)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    res = service.users().messages().send(userId='me', body={'raw': raw}).execute() if send_now else service.users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()
    if new_name and os.path.exists(new_name):
        os.remove(new_name)
    return res