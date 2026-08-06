# Mew Combined Web Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a unified, fully functional Single-Page Web Application (`index.html`) combining the Landing page, Resume Parser, and AI Job Matcher into a seamless step-by-step user workflow with dynamic state management and an active progress stepper.

**Architecture:** A responsive single-page architecture (`index.html`) using HTML5, Tailwind CSS, Google Material Symbols, and Vanilla JavaScript. Dynamic view switching (`#view-landing`, `#view-parser`, `#view-matches`, `#view-dashboard`) is controlled by a central `MewAppState` manager with `localStorage` persistence and top-header progress stepper indicators.

**Tech Stack:** HTML5, Tailwind CSS (via CDN with extended theme config), Vanilla JavaScript ES6+, Google Fonts (Hanken Grotesk, Inter, JetBrains Mono, Plus Jakarta Sans), Material Symbols Outlined.

## Global Constraints
- Target file: `claude_frontend/landing.html/index.html`
- Preserved files: `landing.html`, `resumeparsingpage.html`, `jobmatch.html` (do not delete)
- Colors & Typography: Use exact Tailwind theme configuration merging all three source templates.
- Workflow requirement: Landing Auth form submission -> Resume Parser view -> Resume upload / Save -> AI Job Matcher view.

---

### Task 1: Scaffolding and Unified Layout Base

**Files:**
- Create: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: Tailwind CSS config, Google Fonts, Material Symbols
- Produces: Base HTML layout with fixed header (containing Stepper), left sidebar, and container element for views.

- [ ] **Step 1: Create `claude_frontend/landing.html/index.html` with merged Tailwind theme and font links**
- [ ] **Step 2: Add fixed sidebar navigation and top header bar with progress stepper**
- [ ] **Step 3: Define view containers (`#view-landing`, `#view-parser`, `#view-matches`, `#view-dashboard`)**
- [ ] **Step 4: Commit layout base**

```bash
git add claude_frontend/landing.html/index.html
git commit -m "feat: scaffold unified index.html layout base with stepper and navigation"
```

---

### Task 2: Integrate View 1 - Landing & Auth Section

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `#view-landing` container, `landing.html` hero and auth elements
- Produces: Form submit event handlers on `#email`, `#password`, and `#btn-get-started` / `#btn-google-auth` transitioning to `#view-parser`.

- [ ] **Step 1: Port hero section, badge, and copy from `landing.html` into `#view-landing`**
- [ ] **Step 2: Port work email / password auth form and Google auth button into `#view-landing`**
- [ ] **Step 3: Port Autonomous Advantage features section and testimonial section**
- [ ] **Step 4: Add JS event listener to authentication form to store email and transition to Parser view**
- [ ] **Step 5: Commit Landing View integration**

```bash
git add claude_frontend/landing.html/index.html
git commit -m "feat: integrate landing and auth view with state transition handler"
```

---

### Task 3: Integrate View 2 - Resume Parser Workspace

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `#view-parser` container, `resumeparsingpage.html` parser components
- Produces: Drag & Drop resume upload handler, live parsing progress animation, skill editor, and "Save to Matches" button transitioning to `#view-matches`.

- [ ] **Step 1: Port Drag & Drop upload zone and Live Parsing queue into `#view-parser`**
- [ ] **Step 2: Port extracted candidate profile editor (Contact details, Core skills tags, Work experience) into `#view-parser`**
- [ ] **Step 3: Implement file upload simulation script (adding item to queue, animating progress, parsing skills)**
- [ ] **Step 4: Add event listener to "Save to Matches" button to update `MewAppState.resume` and transition to Matches view**
- [ ] **Step 5: Commit Resume Parser integration**

```bash
git add claude_frontend/landing.html/index.html
git commit -m "feat: integrate resume parser workspace with upload animation and state persistence"
```

---

### Task 4: Integrate View 3 - AI Job Matcher Stack

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: `#view-matches` container, `jobmatch.html` 3D card stack
- Produces: Interactive 3D card fan/swipe controls, keyboard arrow navigation, match score indicators, and "Click to Apply" action handler.

- [ ] **Step 1: Port 3D stacked job card deck into `#view-matches`**
- [ ] **Step 2: Add keyboard arrow controls (← Pass, → Apply) and button click listeners to cycle card stack**
- [ ] **Step 3: Add application confirmation feedback toast / notification**
- [ ] **Step 4: Commit AI Job Matcher integration**

```bash
git add claude_frontend/landing.html/index.html
git commit -m "feat: integrate AI job matcher card stack with swipe and keyboard controls"
```

---

### Task 5: Centralized State Engine & Router Sync

**Files:**
- Modify: `claude_frontend/landing.html/index.html`

**Interfaces:**
- Consumes: All view containers (`#view-landing`, `#view-parser`, `#view-matches`, `#view-dashboard`), Header Stepper elements, Sidebar navigation links
- Produces: `MewRouter.navigateTo(viewName)` method syncing view visibility, header progress stepper status, sidebar active highlight, and `localStorage` state.

- [ ] **Step 1: Implement `MewAppState` object and `MewRouter` view switcher**
- [ ] **Step 2: Wire header progress stepper (`[1. Auth] -> [2. Parser] -> [3. Matches]`) to update status icons and active styling**
- [ ] **Step 3: Wire sidebar navigation items (`Dashboard`, `Parser`, `Matches`, `Settings`) to switch views on click**
- [ ] **Step 4: Pre-fill candidate profile in Parser and header profile badge from `MewAppState`**
- [ ] **Step 5: Commit state engine & router controller**

```bash
git add claude_frontend/landing.html/index.html
git commit -m "feat: implement centralized MewAppState engine and view router with stepper sync"
```

---

### Task 6: Final Verification & Integration Testing

**Files:**
- Verify: `claude_frontend/landing.html/index.html`

- [ ] **Step 1: Open `index.html` in browser and test complete end-to-end flow**
  - Fill email on Landing -> click Get Started -> verify transition to Parser view.
  - Drop/upload resume file -> verify parsing progress animation -> edit skill -> click Save to Matches -> verify transition to Job Matcher view.
  - Interact with job card stack (Apply / Pass) -> verify card rotation.
  - Click sidebar and header stepper links -> verify instantaneous view navigation.
- [ ] **Step 2: Commit final verified web application**

```bash
git add claude_frontend/landing.html/index.html
git commit -m "chore: complete and verify combined Mew autonomous career platform website"
```
