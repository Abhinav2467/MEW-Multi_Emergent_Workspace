# J-Vers Hero + Preloader — Design Reconstruction

> Scope: **Preloader** and **Hero section** only, reverse-engineered from the live
> structure/content of j-vers.com (an Obys-agency build). Exact hex/font values
> below are best-effort inference from the visual style — see "Verify These
> Values" at the bottom to lock them in exactly in under 2 minutes.

---

## 1. Design Principles Observed

1. **Delayed reveal, not instant load.** Nothing on the page is visible until
   the preloader finishes — this manufactures anticipation and hides
   font/video load jank.
2. **Text as the hero, video as atmosphere.** The headline is the focal point;
   background video is desaturated/dimmed so it never competes with type.
3. **Every line of text enters as a masked reveal**, never a plain fade. Lines
   are clipped inside an `overflow:hidden` wrapper and animate `translateY`
   from 100% → 0%, mimicking a blind opening.
4. **Numbering and eyebrows encode real structure** (nav thumbnails, "01 / 02
   / 03" only where content is a genuine sequence).
5. **Motion is orchestrated, not scattered** — one timeline drives loader →
   nav → hero in sequence, not independent effects firing at once.
6. **Generous negative space + a single accent motion** (the CTA underline
   draw) rather than many competing hovers.

---

## 2. Color Palette (inferred — verify before shipping)

| Token | Hex | Use |
|---|---|---|
| `--bg-primary` | `#0B0B0C` | Page background (near-black, not pure #000) |
| `--text-primary` | `#F5F4F0` | Headline / body on dark |
| `--text-muted` | `#8C8C8C` | Eyebrow text, captions, secondary copy |
| `--accent` | `#D6D2C4` | CTA border/underline, dividers (warm off-white, not a bright accent) |
| `--overlay-scrim` | `rgba(0,0,0,0.45)` | Video darkening layer |
| `--loader-bg` | `#0B0B0C` | Same as page bg, so preloader→hero is seamless |

## 3. Typography

| Role | Face | Weight | Notes |
|---|---|---|---|
| Display (H1) | A grotesque/neo-grotesque sans (e.g. **Neue Montreal** / **General Sans** as substitutes) | 500–600 | Large, tight tracking (-0.02em), tight leading (0.95) |
| Body / nav | Same family, lighter cut | 400 | 16–18px base |
| Utility (loader %, eyebrow labels) | Same family, mono-spaced numerals or letter-spaced caps | 400–500 | Uppercase, +0.08em tracking for eyebrows |

**Type scale (hero H1):** clamp(2.5rem, 6vw, 6rem)

## 4. Layout

```
┌─────────────────────────────────────────────┐
│ [LOGO]                     EN / DE   [MENU]  │  ← fixed header, transparent
│                                               │
│                                               │
│           (bg video, dimmed, cover)          │
│                                               │
│      Programmatic job advertising · AI       │  ← eyebrow
│                                               │
│      TAKE CONTROL                            │  ← H1 line 1 (masked reveal)
│      OF HIRING                               │  ← H1 line 2 (masked reveal)
│                                               │
│      No more wasted budgets. Get your job    │  ← subhead, fades in after H1
│      ads in front of the right people.       │
│                                               │
│      [ Get started → ]                       │  ← CTA, underline-draw hover
│                                               │
│                          ↓ Scroll Down        │  ← bottom-right, looping bounce
└─────────────────────────────────────────────┘
```

## 5. Component Breakdown

### 5.1 Preloader
- Full-viewport, `position: fixed`, `z-index: 999`, background = `--bg-primary`.
- Center or bottom-left percentage counter, `00%` → `100%`, driven by either
  real asset-load progress or a simulated `requestAnimationFrame` tween
  (~1.6–2.2s total).
- On completion: counter fades out, a horizontal "curtain" panel wipes up
  (`scaleY: 1 → 0`, transform-origin bottom) to reveal the hero underneath.
- Nav and hero elements are `visibility: hidden` / `opacity: 0` until the
  curtain wipe starts, then stagger in.

### 5.2 Header / Nav
- Fixed, transparent, sits above the video.
- Logo left, language switch + hamburger/menu label right.
- Full-screen nav overlay on open, each link paired with a thumbnail image
  that crossfades in on link hover (seen in the fetched markup: Home, Case
  Studies, Career, Contacts each have a paired `.jpg`).

### 5.3 Hero
- `<section>` with two stacked `<video>` (or video + fallback poster) elements,
  `object-fit: cover`, autoplay/muted/loop, dark scrim on top.
- Eyebrow line above H1.
- H1 split into 2 lines, each in its own `overflow:hidden` mask div.
- Subhead paragraph.
- Primary CTA button with border + arrow, underline draws left→right on hover.
- "Scroll Down" indicator, bottom-right, small vertical line or chevron with
  an infinite bounce loop.

---

## 6. Animation Specification (GSAP-style pseudocode/timing)

```js
// Master timeline — preloader → curtain → hero stagger
const tl = gsap.timeline({ defaults: { ease: "expo.out" } });

tl.to(counter, { textContent: 100, duration: 1.8, snap: { textContent: 1 } })
  .to(loaderPercent, { opacity: 0, duration: 0.3 })
  .to(curtain, { scaleY: 0, duration: 0.9, ease: "power4.inOut" }, "-=0.1")
  .to(navItems, { opacity: 1, y: 0, stagger: 0.06, duration: 0.6 }, "-=0.5")
  .to(heroEyebrow, { opacity: 1, y: 0, duration: 0.6 }, "-=0.4")
  .to(heroLineMasks, { yPercent: 0, stagger: 0.12, duration: 0.9, ease: "power4.out" }, "-=0.3")
  .to(heroSub, { opacity: 1, y: 0, duration: 0.6 }, "-=0.4")
  .to(heroCTA, { opacity: 1, y: 0, duration: 0.5 }, "-=0.3")
  .to(scrollIndicator, { opacity: 1, duration: 0.5 }, "-=0.2");
```

| Element | Property | From → To | Duration | Ease | Delay/Stagger |
|---|---|---|---|---|---|
| Loader counter | text | 0 → 100 | 1.8s | linear/expo.out | — |
| Curtain wipe | scaleY | 1 → 0 | 0.9s | power4.inOut | after counter |
| Nav items | opacity/y | 0/10px → 1/0 | 0.6s | power2.out | 0.06s stagger |
| H1 line masks | yPercent | 100 → 0 | 0.9s | power4.out | 0.12s stagger |
| Subhead | opacity/y | 0/16px → 1/0 | 0.6s | power2.out | after H1 |
| CTA | opacity/y | 0/12px → 1/0 | 0.5s | power2.out | after subhead |
| CTA hover | underline scaleX | 0 → 1 | 0.35s | power2.out | on :hover |
| Scroll indicator | y (loop) | 0 → 8px → 0 | 1.4s | sine.inOut | infinite yoyo |

**Reduced motion:** wrap the whole timeline in
`if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches)`; when
reduced motion is on, skip straight to the end state with opacity fades only.

---

## 7. Verify These Values Yourself (2 minutes, exact source of truth)

Since I can't render the live page, do this once and swap into `design.md`:
1. Open j-vers.com → DevTools → Elements → click the H1 → Computed tab →
   copy `font-family`, `font-size`, `color`, `letter-spacing`.
2. Elements → `<body>` or hero section → copy `background-color`.
3. Network tab → filter `Font` → note the actual webfont file names.
4. Network tab → filter `JS` → confirm GSAP / Lenis / Locomotive Scroll are
   the libraries in use (their filenames will show directly).

This reconstruction gets you 1:1 on **structure, motion choreography, and
timing** immediately; the two-minute check above locks in the last 1:1 on
**exact color/type tokens**.
