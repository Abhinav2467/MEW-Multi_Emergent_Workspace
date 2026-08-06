# 🌟 Project Aura: Cold Email Outreach Agent (Standalone)

This agent handles lead discovery, Google OAuth registration, and dynamic email drafting as a direct Python module.

## 🧠 How the Agent Works
This script provides reusable functions for handling lead search, user token generation, and outreach drafting.
It no longer depends on an MCP runtime wrapper in this branch.

### 🛠️ Core Capabilities
1. **`get_registration_link`**: Generates a Google login URL.
2. **`finalize_user_token`**: Swaps the browser code for permanent JSON credentials.
3. **`find_leads`**: Discovers recruiter leads and verifies emails.
4. **`send_outreach`**: Crafts and drafts or sends outreach emails.

---

## 🚀 Standalone Usage
Run a simple demonstration with:

```bash
python agent.py demo
```

This prints a registration URL sample and shows how the module can be used directly from Python.

### Direct function usage
Import the file and call the functions directly from your own script:

```python
from agent import get_registration_link, find_leads, send_outreach

link = get_registration_link()
leads = find_leads("OpenAI", "Recruiter", "openai.com")
```

## 🔑 Refresh your Gmail token
If your `token.json` is stale or revoked, generate a new one with:

```bash
source venv/bin/activate
python3 refresh_token.py
```

Follow the printed URL, authorize the app, and paste the returned auth code.
The script saves the refreshed credentials to `token.json`.

Then create a draft safely with:

```bash
python3 create_draft.py
```

## 🎓 Notes for Review
This branch preserves the original business logic while removing the MCP runtime layer.
A future restore to MCP can use the `mcp-stripped.md` backup file to reintroduce the wrapper and runtime entrypoint.
