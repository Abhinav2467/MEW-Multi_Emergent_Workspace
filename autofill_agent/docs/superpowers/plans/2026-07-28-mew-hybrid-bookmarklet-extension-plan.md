# MEW Hybrid Bookmarklet & Extension System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a zero-install, 1-click **Bookmarklet system** (`backend/static/mew_bookmarklet.js`) that candidates can drag to their browser toolbar once. Clicking the bookmark on ANY live career portal (Microsoft, Qualcomm, Workday, Greenhouse, Lever, LinkedIn, etc.) instantly injects the floating **"✨ MEW Autofill"** badge and populates form fields without requiring Chrome Developer Mode or extension loading.

**Tech Stack:** JavaScript (ES6+), HTML5, CSS3, FastAPI StaticFiles.

## Tasks

### Task 1: Standalone Bookmarklet Script & Static Asset Exemption

**Files:**
- Create: `backend/static/mew_bookmarklet.js`
- Modify: `backend/security/auth.py`
- Modify: `backend/main.py`
- Create: `backend/tests/test_bookmarklet.py`

**Interfaces:**
- Consumes: `GET http://127.0.0.1:8000/autofill/preview` or `http://127.0.0.1:8000/api/v1/autofill-payload`.
- Produces: `http://127.0.0.1:8000/static/mew_bookmarklet.js` static route.

- [ ] **Step 1: Write failing test for static bookmarklet endpoint**

```python
# backend/tests/test_bookmarklet.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_bookmarklet_static_file_accessible():
    res = client.get("/static/mew_bookmarklet.js")
    assert res.status_code == 200
    assert "mew-autofill-badge" in res.text
    assert "fillAndDispatch" in res.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_bookmarklet.py -v`  
Expected: FAIL (file does not exist or 404/401)

- [ ] **Step 3: Write `mew_bookmarklet.js`, update `auth.py`, and mount `/static` in `main.py`**

Create `backend/static/mew_bookmarklet.js`:
```javascript
(function () {
  if (document.getElementById("mew-autofill-badge")) {
    const existing = document.getElementById("mew-autofill-badge");
    existing.click();
    return;
  }

  // Inject Styles
  const style = document.createElement("style");
  style.textContent = `
    #mew-autofill-badge {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 999999;
      background: #0f172a;
      color: #38bdf8;
      border: 1px solid #38bdf8;
      padding: 10px 18px;
      border-radius: 30px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 13px;
      font-weight: 600;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease-in-out;
      user-select: none;
    }
    #mew-autofill-badge:hover {
      background: #38bdf8;
      color: #0f172a;
      transform: translateY(-2px);
      box-shadow: 0 12px 28px rgba(56, 189, 248, 0.4);
    }
    #mew-autofill-badge.mew-success {
      border-color: #4ade80;
      color: #4ade80;
    }
  `;
  document.head.appendChild(style);

  // Inject Floating Badge
  const badge = document.createElement("div");
  badge.id = "mew-autofill-badge";
  badge.innerHTML = `✨ MEW Autofill`;
  document.body.appendChild(badge);

  function fillAndDispatch(el, val) {
    if (!el || val === undefined || val === null || val === "") return;
    el.focus();
    el.value = val;
    ["focus", "input", "change", "blur"].forEach((evtType) => {
      el.dispatchEvent(new Event(evtType, { bubbles: true, cancelable: true }));
    });
  }

  async function safeFetchProfile() {
    const bases = ["http://127.0.0.1:8000", "http://localhost:8000"];
    for (const base of bases) {
      try {
        const res = await fetch(`${base}/autofill/preview`, { mode: "cors" });
        if (res.ok) {
          const json = await res.json();
          return json.data?.active_profile || json.data;
        }
      } catch (e) {}
    }
    return null;
  }

  badge.addEventListener("click", async () => {
    badge.innerHTML = `⏳ Loading Payload...`;

    const profileData = await safeFetchProfile();
    if (!profileData) {
      badge.innerHTML = `❌ Backend Offline`;
      setTimeout(() => { badge.innerHTML = `✨ MEW Autofill`; }, 4000);
      return;
    }

    const p = profileData.personal || {};
    const prof = profileData.professional || {};
    let filledCount = 0;
    const filledElements = new Set();

    const fieldMappings = [
      {
        selectors: [
          "input[name='first_name']", "input[id='first_name']", "input[name='firstname']", "input[id='firstname']",
          "input[name='fname']", "input[id='fname']", "input[name='first-name']", "input[id='first-name']",
          "input[autocomplete='given-name']", "input[aria-label*='first' i]", "input[placeholder*='first' i]"
        ],
        val: p.first_name
      },
      {
        selectors: [
          "input[name='last_name']", "input[id='last_name']", "input[name='lastname']", "input[id='lastname']",
          "input[name='lname']", "input[id='lname']", "input[name='last-name']", "input[id='last-name']",
          "input[autocomplete='family-name']", "input[aria-label*='last' i]", "input[placeholder*='last' i]"
        ],
        val: p.last_name
      },
      {
        selectors: [
          "input[id='react-name']", "input[name='full_name']", "input[id='full_name']", "input[name='fullname']",
          "input[name='name']", "input[autocomplete='name']", "input[aria-label*='full name' i]", "input[placeholder*='full name' i]"
        ],
        val: p.full_name
      },
      {
        selectors: [
          "input[name='email']", "input[id='email']", "input[type='email']", "input[autocomplete='email']",
          "input[name='email_address']", "input[id='email_address']", "input[aria-label*='email' i]", "input[placeholder*='email' i]"
        ],
        val: p.email
      },
      {
        selectors: [
          "input[name='phone']", "input[id='phone']", "input[type='tel']", "input[autocomplete='tel']",
          "input[name='mobile']", "input[id='mobile']", "input[name='phone_number']", "input[id='phone_number']",
          "input[aria-label*='phone' i]", "input[placeholder*='phone' i]"
        ],
        val: p.phone
      },
      {
        selectors: [
          "input[id='react-linkedin']", "input[name*='linkedin' i]", "input[id*='linkedin' i]",
          "input[aria-label*='linkedin' i]", "input[placeholder*='linkedin' i]"
        ],
        val: p.linkedin_url
      },
      {
        selectors: [
          "input[name*='github' i]", "input[id*='github' i]",
          "input[aria-label*='github' i]", "input[placeholder*='github' i]"
        ],
        val: p.github_url
      },
      {
        selectors: [
          "input[id='shadow-portfolio']", "input[name*='portfolio' i]", "input[id*='portfolio' i]",
          "input[name*='website' i]", "input[id*='website' i]", "input[placeholder*='portfolio' i]"
        ],
        val: p.portfolio_url
      },
      {
        selectors: [
          "input[id='wizard-title']", "input[name*='title' i]", "input[id*='title' i]",
          "input[name*='headline' i]", "input[placeholder*='job title' i]"
        ],
        val: prof.current_title
      },
      {
        selectors: [
          "input[name*='location' i]", "input[id*='location' i]", "input[name*='city' i]", "input[id*='city' i]",
          "input[placeholder*='location' i]", "input[placeholder*='city' i]"
        ],
        val: p.location
      }
    ];

    fieldMappings.forEach(item => {
      if (!item.val) return;
      for (const sel of item.selectors) {
        const el = document.querySelector(sel);
        if (el && !filledElements.has(el)) {
          fillAndDispatch(el, item.val);
          filledElements.add(el);
          filledCount++;
          break;
        }
      }
    });

    badge.classList.add("mew-success");
    badge.innerHTML = `✅ ${filledCount} Fields Filled`;
    setTimeout(() => {
      badge.classList.remove("mew-success");
      badge.innerHTML = `✨ MEW Autofill`;
    }, 3000);
  });

  // Automatically trigger first click on bookmark execution
  badge.click();
})();
```

Modify `backend/security/auth.py` to exempt `/static/*`:
```python
async def verify_api_key(request: Request):
    if request.url.path.startswith("/test-forms") or request.url.path.startswith("/static") or request.url.path.startswith("/autofill/preview") or request.url.path.startswith("/api/v1/auth") or request.url.path in ["/favicon.ico", "/docs", "/openapi.json", "/redoc"]:
        return None
```

Mount `StaticFiles` in `backend/main.py`:
```python
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_bookmarklet.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/static/mew_bookmarklet.js backend/security/auth.py backend/main.py backend/tests/test_bookmarklet.py
git commit -m "feat: implement standalone 1-click MEW bookmarklet script and static asset route"
```

---

### Task 2: Drag-to-Bookmarks Button & Test Dashboard Update

**Files:**
- Modify: `backend/static/test_forms.html`
- Create: `backend/tests/test_bookmarklet_ui.py`

**Interfaces:**
- Consumes: `http://127.0.0.1:8000/static/mew_bookmarklet.js`.
- Produces: Interactive draggable link button on dashboard UI.

- [ ] **Step 1: Write failing test for Drag-to-Bookmarks UI element**

```python
# backend/tests/test_bookmarklet_ui.py
from pathlib import Path
import pytest

def test_bookmarklet_button_in_test_forms():
    html_path = Path("backend/static/test_forms.html")
    assert html_path.exists()
    content = html_path.read_text()
    assert "javascript:(function()" in content
    assert "Drag to Bookmarks Bar" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_bookmarklet_ui.py -v`  
Expected: FAIL (bookmarklet href does not exist in test_forms.html)

- [ ] **Step 3: Update `backend/static/test_forms.html` with Drag-to-Bookmarks button**

Add to `action-bar` in `test_forms.html`:
```html
<a href="javascript:(function(){if(window.__mew_injected){const b=document.getElementById('mew-autofill-badge');if(b)b.click();return;}window.__mew_injected=true;const s=document.createElement('script');s.src='http://127.0.0.1:8000/static/mew_bookmarklet.js';document.body.appendChild(s);})();" class="bookmarklet-btn" title="Drag this link to your Chrome/Safari Bookmarks Bar for 1-click autofill on any job application!">
  ✨ Drag to Bookmarks Bar: MEW Autofill
</a>
```

Add styling in `test_forms.html`:
```css
.bookmarklet-btn {
  background: linear-gradient(135deg, #a855f7, #38bdf8);
  color: #ffffff;
  text-decoration: none;
  padding: 10px 20px;
  font-weight: bold;
  border-radius: 6px;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 14px rgba(168, 85, 247, 0.4);
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: grab;
}
.bookmarklet-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(56, 189, 248, 0.5);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_bookmarklet_ui.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/static/test_forms.html backend/tests/test_bookmarklet_ui.py
git commit -m "feat: add interactive Drag-to-Bookmarks Bar button and styling to test suite UI"
```

---

## Plan Self-Review Checklist

- **Spec coverage:** Standalone Bookmarklet Script (Task 1), Static Asset Exemption (Task 1), Draggable Button UI (Task 2).
- **Placeholder scan:** No TBDs or TODOs.
- **Type consistency:** Identical element IDs (`#mew-autofill-badge`) and synthetic event logic as extension package.
