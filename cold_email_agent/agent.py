import os
import json
import sys
from langchain_groq import ChatGroq
from tools import (
    discover_recruiter_leads,
    execute_cold_email,
    generate_auth_url,
    swap_code_for_token
)

llm = ChatGroq(
    model="llama-3.1-8b-instant", 
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2 
)

def get_registration_link() -> str:
    """Generates Google login URL."""
    return generate_auth_url()


def finalize_user_token(auth_code: str):
    """Swaps code for permanent JSON credentials."""
    try:
        result = swap_code_for_token(auth_code)
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result
        return result
    except Exception as e:
        return f"Error: {str(e)}"


def find_leads(company: str, role: str, domain: str) -> str:
    """Extracts leads from LinkedIn with Hunter fallback."""
    leads = discover_recruiter_leads(company, role, domain)
    return json.dumps(leads) if leads else "No leads found."


def send_outreach(user_token_json: str, user_profile_json: str, lead_email: str, lead_name: str, company: str, role: str, send_now: bool = False):
    """Crafts and executes dynamic outreach."""
    user_token = json.loads(user_token_json)
    profile = json.loads(user_profile_json)
    sender_name = profile.get("full_name", "Candidate")
    resume_path = profile.get("resume_path", "resume.pdf")
    
    prompt = f"Write a 3-sentence email from {sender_name} ({profile.get('expertise')}) to {lead_name.split()[0]} for {role} at {company}. Format: Hi [Name], ... Best regards, {sender_name}."
    body = llm.invoke(prompt).content.strip()
    
    return execute_cold_email(user_token, sender_name, lead_email, lead_name, f"Inquiry: {role}", body, company, role, resume_path, send_now)

def run_demo() -> None:
    print("🚀 Aura Email Agent Standalone Demo")
    print("\n1) get_registration_link")
    try:
        print(f"   {get_registration_link()}")
    except Exception as exc:
        print(f"   Error generating registration link: {exc}")

    print("\n2) find_leads sample call")
    try:
        leads = discover_recruiter_leads("OpenAI", "Recruiter", "openai.com")
        print(f"   Sample leads count: {len(leads)}")
        print(f"   Sample output: {json.dumps(leads[:2], indent=2)}")
    except Exception as exc:
        print(f"   Error running find_leads sample: {exc}")

    print("\n3) send_outreach dry-run")
    print("   To avoid accidental email sends, please call send_outreach(...) with send_now=False from your own script.")


def print_usage() -> None:
    print("Usage:")
    print("  python agent.py demo")
    print("  python agent.py help")
    print("\nAvailable functions:")
    print("  get_registration_link()")
    print("  finalize_user_token(auth_code)")
    print("  find_leads(company, role, domain)")
    print("  send_outreach(user_token_json, user_profile_json, lead_email, lead_name, company, role, send_now=False)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in {"demo", "--demo"}:
        run_demo()
    else:
        print_usage()