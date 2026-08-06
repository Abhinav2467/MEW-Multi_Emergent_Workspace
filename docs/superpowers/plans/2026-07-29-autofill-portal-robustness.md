# Multi-Portal Autofill & Dual-Mode Resume Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build multi-portal form field matching (Phone, Plain Text Location & Combobox Dropdowns) across main page and iFrames (Greenhouse, Workday, Lever), and implement Dual-Mode Resume Upload (Automated DOM synthetic attachment + Backup Floating Drag-and-Drop Resume Pill).

**Architecture:** Update Chrome extension `content.js` to traverse `<iframe>` elements and Shadow DOMs, handle combobox selection events, inject synthetic `DataTransfer` files onto `input[type="file"]`, and render a floating drag-and-drop badge for manual file uploading.

**Tech Stack:** JavaScript (DOM, HTML5 DataTransfer API, Synthetic Events), Python, FastAPI, Pytest.

## Global Constraints
- Target files: `autofill_agent/extension/content.js`, `autofill_agent/extension/content.css` (or inline styles), `backend/tests/test_autofill_integration.py`.
- Must preserve backward compatibility with all existing backend routes and tests.

---

### Task 1: iFrame Traversal & Enhanced Field Extraction (Phone & Location Dropdowns)

**Files:**
- Modify: `autofill_agent/extension/content.js`

**Interfaces:**
- Consumes: Candidate profile data from `chrome.storage.local` and `/api/v1/autofill-payload`.
- Produces: Normalized DOM field descriptors across document and iframes.

- [ ] **Step 1: Implement `extractFieldsFromDocumentAndFrames` in `content.js`**
  Add recursive iframe and shadow DOM scanning to collect input fields even when embedded in Greenhouse / Workday iframe widgets.

- [ ] **Step 2: Add phone and location (combobox dropdown) matching helpers**
  Update `matchFieldsLocally` to detect `input[type="tel"]`, phone keywords (`phone`, `mobile`, `contact`), plain text locations, and location comboboxes (`role="combobox"`, `aria-autocomplete`). For comboboxes, dispatch `input`, `focus`, and `keydown` events to trigger option selection.

- [ ] **Step 3: Test local field matching logic**
  Verify field matching in `content.js` correctly identifies phone and location fields.

---

### Task 2: Dual-Mode Resume Upload (Automated DOM Attachment + Backup Drag-and-Drop Pill)

**Files:**
- Modify: `autofill_agent/extension/content.js`

**Interfaces:**
- Consumes: `/api/v1/resume/download-latest` PDF blob.
- Produces: Synthetic file input attachment + Floating Draggable Resume Pill DOM element (`#mew-resume-pill`).

- [ ] **Step 1: Implement Automated Synthetic `DataTransfer` Upload**
  In `autofillResumeFileInputs()`, query file inputs across `document` and all `<iframe>` elements. Attach the resume `File` object using `DataTransfer`, and dispatch `change`, `input`, and `drop` events.

- [ ] **Step 2: Create Floating Draggable Resume Pill (`#mew-resume-pill`)**
  Render a sleek floating pill badge at bottom-right (`📄 Drag Resume PDF`). Add `draggable="true"` and set `dragstart` event listener with `event.dataTransfer.items.add(file)` so users can drag the badge onto any webpage "Choose File" area as a backup.

- [ ] **Step 3: Test dual-mode upload**
  Verify both automated injection and floating pill drag-and-drop setup.

---

### Task 3: End-to-End Test Suite Verification

**Files:**
- Modify: `backend/tests/test_autofill_integration.py`

- [ ] **Step 1: Add automated test for phone & location payload matching**
  Write pytest test case in `backend/tests/test_autofill_integration.py` for phone and location fields.

- [ ] **Step 2: Run pytest test suite**
  Execute `backend/.venv/bin/pytest backend/tests` to verify all 19+ tests pass.

- [ ] **Step 3: Commit all changes**
  Run `git add .` and `git commit -m "feat: implement multi-portal autofill & dual-mode resume upload"`.
