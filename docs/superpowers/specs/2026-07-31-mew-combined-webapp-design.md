# Design Specification: Mew Autonomous Career Platform Unified Web App

**Date**: 2026-07-31  
**Status**: Approved  

---

## 1. Overview
The Mew Autonomous Career Platform unifies three distinct UI layouts into a cohesive Single-Page Application (SPA) web experience with dynamic state persistence and step-by-step progress tracking:
1. **Landing & Authentication View** (`landing.html`)
2. **Resume Parser Workspace** (`resumeparsingpage.html`)
3. **AI Job Matcher Stack** (`jobmatch.html`)

---

## 2. User Workflow & View Routing

```
 [1. Landing / Auth View] ──(Submit Email / Google Auth)──> [2. Resume Parser View] ──(Upload / Save Resume)──> [3. AI Job Matcher View]
```

### Step 1: Landing Page & Auth (`#view-landing`)
* **Hero Banner**: Presenting Mew AI V2 capabilities and value proposition.
* **Authentication Form**: Work email & password input + Google Auth trigger.
* **Transition Trigger**: Clicking "Get Started" or "See how it works" validates user inputs, initializes the `MewAppState` with user credentials, and transitions to `#view-parser` with a smooth fade/slide animation.

### Step 2: Resume Parser Workspace (`#view-parser`)
* **Drag & Drop Upload Zone**: Supports PDF and DOCX files.
* **Live Parsing Queue**: Simulates real-time skill extraction, displaying animated parsing progress bars.
* **Extracted Candidate Profile Editor**:
  * Contact info (email pre-filled from auth, phone, location).
  * Core skill tags (React, TypeScript, Node.js, etc.) with ability to add/remove skills.
  * Work experience list.
* **Transition Trigger**: Uploading a resume or clicking "Save to Matches" saves the parsed skills into state and transitions to `#view-matches`.

### Step 3: AI Job Matcher Stack (`#view-matches`)
* **Interactive Job Card Stack**: 3D card stack displaying top matched jobs scored by match percentage (e.g., 98% Match for Senior Product Designer).
* **Interactions**:
  * "Click to Apply" / Arrow keys (← Pass, → Apply) / Mouse swipe to cycle through job cards.
  * Real-time match feedback and application confirmation modal.
  * Match scores dynamically computed against candidate skills saved in Step 2.

---

## 3. UI System & Design Integration

### Unified Header & Navigation Bar
* **Glassmorphism Header**: Fixed top navigation bar with `backdrop-blur-xl`, displaying Mew Logo, dynamic user profile badge, notification button, and an active workflow progress stepper:
  ```
  Step 1: Auth  ✓  ───>  Step 2: Resume Parser  [Active]  ───>  Step 3: AI Job Matcher
  ```
* **Sidebar Navigation**: Left sidebar supporting quick navigation between views (`Dashboard`, `Parser`, `Matches`, `Settings`).

### Unified Typography & Color Palette
* **Fonts**: Google Fonts (`Hanken Grotesk`, `Inter`, `JetBrains Mono`, `Plus Jakarta Sans`, `IBM Plex Mono`).
* **Icons**: Google Material Symbols Outlined.
* **Theme Tokens**: Custom Tailwind CSS extend config containing `kinetic-cyan`, `horizon-green`, `deep-forest`, `surface-container-lowest`, etc.

---

## 4. State Management Engine (`MewAppState`)

Centralized JavaScript state saved in `localStorage`:

```javascript
const MewAppState = {
  activeView: 'landing', // 'landing' | 'parser' | 'matches' | 'dashboard'
  user: {
    email: '',
    name: 'Alex Rivera',
    role: 'Lead Analyst'
  },
  resume: {
    fileName: '',
    email: '',
    phone: '',
    location: '',
    skills: [],
    experience: []
  },
  appliedJobs: []
};
```

---

## 5. File Structure
* Main Unified Web Application: `claude_frontend/landing.html/index.html`
* Preserved reference layouts:
  * `claude_frontend/landing.html/landing.html`
  * `claude_frontend/landing.html/resumeparsingpage.html`
  * `claude_frontend/landing.html/jobmatch.html`

---

## 6. Verification Plan
* Validate form submission on Landing Page switches view to Resume Parser.
* Validate file upload / "Save to Matches" on Resume Parser switches view to Job Matcher.
* Validate Header Stepper updates active state correctly.
* Validate Sidebar links switch views cleanly.
* Verify responsiveness across mobile, tablet, and desktop viewports.
