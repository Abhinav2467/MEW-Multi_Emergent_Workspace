# Project MEW — Hybrid Bookmarklet & Chrome Extension Design Spec

**Date:** 2026-07-28  
**Author:** AI Pair Programmer & Lead Developer  
**Status:** Approved  

---

## 1. Overview & Objectives

This design specifies a **Hybrid Zero-Friction Installation Architecture**:
1. **1-Click Bookmarklet (`backend/static/mew_bookmarklet.js` & Dashboard):** A zero-install bookmarklet that candidates drag to their browser toolbar once (`javascript:...`). Clicking the bookmark on ANY live career portal (Microsoft, Qualcomm, Workday, Greenhouse, Lever, LinkedIn, etc.) instantly injects the floating **"✨ MEW Autofill"** badge and fills application fields—requiring ZERO Chrome Developer Mode setup or folder unpacking.
2. **Chrome Extension Package (`extension/`):** Preserved for power users who want automatic badge injection on every page load.

---

## 2. Component Layout & Specification

```text
development/mew/
├── backend/
│   ├── static/
│   │   ├── mew_bookmarklet.js      # Zero-install standalone bookmarklet script
│   │   └── test_forms.html         # Interactive test suite with Drag-to-Bookmarks button
│   ├── routes/
│   │   └── testing.py              # Bookmarklet endpoint & static file router
│   └── security/
│       └── auth.py                 # Static asset CORS and authentication bypass
├── extension/                       # Chrome Manifest V3 extension package (power users)
└── docs/
    └── superpowers/specs/2026-07-28-mew-hybrid-bookmarklet-extension-design.md
```

---

## 3. Bookmarklet Technical Details

### 3.1 Drag-to-Bookmarks Link Generator
The dashboard renders an interactive draggable link:
```html
<a href="javascript:(function(){if(window.__mew_injected){const b=document.getElementById('mew-autofill-badge');if(b)b.click();return;}window.__mew_injected=true;const s=document.createElement('script');s.src='http://127.0.0.1:8000/static/mew_bookmarklet.js';document.body.appendChild(s);})();" class="bookmarklet-btn">
  ✨ Drag to Bookmarks Bar: MEW Autofill
</a>
```

### 3.2 Standalone Bookmarklet Script (`backend/static/mew_bookmarklet.js`)
- Runs in any browser context (Chrome, Safari, Edge, Firefox, Brave, Arc, Mobile).
- Injects floating badge `#mew-autofill-badge` into `document.body`.
- Fetches candidate profile from `http://127.0.0.1:8000/autofill/preview` (or `/api/v1/autofill-payload` if API key present).
- Matches standard fields (`first_name`, `last_name`, `email`, `phone`, `full_name`, `linkedin_url`, `github_url`, `portfolio_url`, `current_title`, `location`).
- Sends unmapped custom QA fields to `http://127.0.0.1:8000/api/v1/autofill-payload/match` for AI fuzzy matching.
- Dispatches synthetic framework events (`focus`, `input`, `change`, `blur`).
- Updates badge to `✅ N Fields Filled`.

---

## 4. Verification Plan

### 4.1 Unit & Integration Tests
- Verify static asset routes in `backend/routes/testing.py`.
- Verify CORS and authentication exemptions for `/static/mew_bookmarklet.js`.

### 4.2 Manual Verification
- Open `http://localhost:8000/test-forms`.
- Drag the **"✨ MEW Autofill"** button to the Chrome Bookmarks Bar.
- Open Microsoft Careers (`https://apply.careers.microsoft.com/...`) or Qualcomm Careers (`https://careers.qualcomm.com/...`).
- Click the **"✨ MEW Autofill"** bookmark in the toolbar.
- Verify badge appears and populates all form fields cleanly.
