# Prompt for an AI Co-Editor (Cursor / Windsurf / Claude Code / v0)

Paste this in as the project brief:

---

You are building the **preloader** and **hero section** of a landing page for
a B2B programmatic job-advertising agency, replicating the motion and layout
language of an Obys-agency-built site (j-vers.com). Read `design.md` in this
repo first — it is the source of truth for tokens, layout, and timing. Then:

**1. Stack**
- Vanilla HTML/CSS/JS with GSAP for animation (see `requirements.txt`).
- No framework needed for this scope; if the project grows past hero+loader,
  scaffold with Vite + vanilla TS.
- Use Lenis for smooth scroll once sections beyond the hero are added.

**2. Build order**
1. Preloader: fixed full-screen overlay, background `--bg-primary`, a
   bottom-left percentage counter animating 00→100 over ~1.8s (expo.out
   easing), then fade the counter and wipe a curtain panel upward
   (`scaleY: 1→0`, power4.inOut, ~0.9s) to reveal the page.
2. Header: fixed, transparent, logo left, EN/DE switch + menu label right.
   Starts hidden, fades/slides in right after the curtain wipe begins.
3. Hero: full-viewport section, background video (`object-fit:cover`,
   muted/autoplay/loop), dark scrim overlay so text stays legible. Eyebrow
   line, then a two-line H1 where each line lives inside its own
   `overflow:hidden` wrapper and animates `translateY(100%)→0` staggered by
   ~0.12s, subhead paragraph, pill-shaped CTA button with a fill-wipe hover
   effect, and a bottom-right "Scroll Down" indicator with a looping
   traveling line animation.
4. Wire everything into one GSAP master timeline so preloader → curtain →
   header → hero all sequence off one timeline, not independent triggers.

**3. Non-negotiables**
- Respect `prefers-reduced-motion`: skip straight to end-states, no counter
  animation, no curtain wipe, just a fast opacity fade.
- Fully responsive down to 375px width — H1 uses `clamp()`, not fixed px.
- Visible keyboard focus states on the CTA and nav links.
- Video must have a fallback poster image and degrade gracefully if it fails
  to load (don't block the reveal timeline on video load).
- Keep CSS specificity flat — avoid stacking type + class selectors that
  fight each other on padding/margin (e.g. don't mix `.hero h1` rules with a
  competing `.hero .headline` rule for the same properties).

**4. Content to use verbatim**
- Eyebrow: "Programmatic job advertising agency backed by AI"
- H1: "Take control / of hiring"
- Subhead: "No more wasted budgets. Get your job ads in front of the right
  people—at the right place, right time, and right price."
- CTA label: "Get started"

**5. Deliverable**
A single working `index.html` (or Vite project if you scaffold one) that
runs standalone, plus updated `design.md` if you deviate from any token or
timing value — document why.

---

## Notes for whoever runs this prompt
- Swap `REPLACE_WITH_HERO_VIDEO.mp4` in `index.html` for real footage before
  shipping.
- The color/font tokens in `design.md` are inferred, not scraped — run the
  2-minute DevTools check in `design.md` §7 against the live site first and
  update the CSS variables at the top of `index.html` accordingly.
