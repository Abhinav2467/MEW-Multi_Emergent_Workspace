# Design Specification: Robust Multi-Portal Autofill & Dual-Mode Resume Upload

## Goal & Background
Enhance the MEW Chrome Extension autofill engine to reliably autofill application forms across international and Indian career portals (Greenhouse embedded/direct, Workday, Lever, Oracle HCM, Phenom, Wellfound, custom company career sites). 

Key focus areas:
1. Fix missing Phone and Location fields (both plain text and autocomplete dropdowns).
2. Support multi-portal DOM structures including `<iframe>` elements and Shadow DOMs.
3. Provide a **Dual-Mode Resume Upload** mechanism:
   - **Primary**: Fully automated synthetic DOM attachment via `DataTransfer`.
   - **Secondary / Backup**: Floating interactive Drag-and-Drop Resume Pill for easy manual dragging onto any "Choose File" button.

---

## User Review Required

> [!IMPORTANT]
> **Dual-Mode Resume Upload**:
> - **Mode 1 (Primary - Automated)**: The extension automatically attaches your candidate resume PDF to all file inputs on the page without opening OS file manager popups.
> - **Mode 2 (Secondary - Backup Drag & Drop)**: A floating `📄 Resume PDF` badge appears on the webpage. If a portal blocks programmatic file attachment, you can simply drag this badge onto the "Choose File" button.

---

## Proposed Changes

### Component 1: Extension Content Script (`autofill_agent/extension/content.js`)

#### 1. Recursive DOM & Frame Traversal
- Traverses top-level `document` AND all accessible `<iframe>` frames and Shadow DOM elements.
- Extracts form inputs (`input`, `textarea`, `select`, `[role="combobox"]`).

#### 2. Enhanced Field Matching (Phone & Location)
- **Phone Field Identification**:
  - Checks `input[type="tel"]`, `name` / `id` / `aria-label` / `placeholder` matching `phone`, `mobile`, `cell`, `contact`.
  - Scans parent container labels for `"Phone Number"`, `"Contact Number"`, `"Mobile"`.
- **Location Field Identification (Plain Text & Combobox Dropdowns)**:
  - Plain Text Inputs: Sets value and dispatches `focus`, `input`, `change`, `blur`.
  - Autocomplete / Combobox Dropdowns (`role="combobox"`, `aria-autocomplete`, `select2`, Google Places):
    1. Focuses element and types location text.
    2. Dispatches `input` and key events (`ArrowDown`, `Enter`).
    3. If an active dropdown menu (`[role="option"]`, `.pac-container`, `.select2-results`) opens, auto-clicks the first matching location choice.

#### 3. Dual-Mode Resume PDF Attachment
- **Automated Mode**:
  - Fetches `/api/v1/resume/download-latest` blob.
  - Locates `input[type="file"]` elements across main page and iframes.
  - Injects file via `DataTransfer` and fires `change`, `input`, `blur`, and synthetic `drop` events.
- **Backup Drag-and-Drop Pill**:
  - Injects a floating draggable badge (`📄 Drag Resume PDF`) in the bottom-right corner of the webpage.
  - Listens for `dragstart` and sets `event.dataTransfer.items.add(file)`.
  - Enables effortless drag-and-drop uploading onto any webpage file dropzone if synthetic attachment is restricted.

---

### Component 2: Extension Background Worker (`autofill_agent/extension/background.js`)

- Maintains cached PDF blob in memory for instant drag-and-drop setup.
- Handles iframe communication and status badges.

---

## Verification Plan

### Automated Tests
- Run `backend/.venv/bin/pytest backend/tests` to verify profile serialization and endpoint health.

### Manual Verification
- Test on Greenhouse embedded portal: `https://www.alpha-grep.com/career-opportunity/?jid=8622142002`
- Verify Phone number autofills cleanly.
- Verify Location autofills (plain text or autocomplete dropdown).
- Verify Resume PDF is automatically attached to hidden/visible file inputs.
- Verify Backup Floating Resume Pill appears and allows dragging onto file inputs.
