import json
from pathlib import Path
from agent import send_outreach

TOKEN_PATH = Path("token.json")

if not TOKEN_PATH.exists():
    raise SystemExit("token.json not found. Save your Google credentials JSON as token.json.")

with TOKEN_PATH.open("r") as f:
    token_data = json.load(f)
    if isinstance(token_data, str):
        token_data = json.loads(token_data)

user_token_json = json.dumps(token_data)
user_profile_json = json.dumps({
    "full_name": "Demo User",
    "expertise": "cold email outreach"
})

try:
    response = send_outreach(
        user_token_json=user_token_json,
        user_profile_json=user_profile_json,
        lead_email="test.recipient+demo@example.com",
        lead_name="Demo Recipient",
        company="OpenAI",
        role="Recruiter",
        send_now=False,
    )
    print("Draft created successfully.")
    print(response)
except Exception as exc:
    print("Draft creation failed:")
    print(exc)
