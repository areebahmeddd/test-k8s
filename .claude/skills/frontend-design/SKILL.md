---
name: frontend-design
description: "Use when building web components, pages, dashboards, landing pages, HTML/CSS layouts, React/Next.js components, or styling/beautifying any web UI. Produces distinctive, production-grade interfaces that avoid generic AI aesthetics. Triggers on: build a UI, design this page, create a component, make it look good, frontend, landing page, dashboard, web design, CSS, React component, Next.js page, style this, beautify, redesign."
argument-hint: "Describe the component, page, or UI to design — include purpose, audience, tone, and any technical constraints (React, Next.js, plain HTML/CSS, etc.)"
---

# Frontend Design

Creates distinctive, production-grade web interfaces with a strong aesthetic point of view. Avoids the generic "AI-generated" look by making deliberate design choices from the start.

> "The details are not the details. They make the design."  
> — Charles Eames

## When to Use

- Building or redesigning any web page, component, or UI artifact
- Writing HTML/CSS/JS, React, or Next.js code that will be seen by users
- Styling an existing component to look polished and intentional
- Reviewing a UI that feels generic, dated, or visually unmemorable
- Creating dashboards, docs pages, landing pages, or admin panels

## Design Thinking (Do This First)

Before writing a single line of code, answer these four questions:

| Question            | What to resolve                                                            |
| ------------------- | -------------------------------------------------------------------------- |
| **Purpose**         | What job does this UI do? What decision or action does it enable?          |
| **Tone**            | Pick ONE extreme and commit to it (see Tone Reference below)               |
| **Constraints**     | Framework, browser support, existing design system, performance budget     |
| **Differentiation** | What makes this UNFORGETTABLE? What is the one thing a user will remember? |

### Tone Reference

Choose a clear conceptual direction and execute with precision. Uncommitted, middle-ground aesthetics produce forgettable results.

| Tone                 | Character                                                      |
| -------------------- | -------------------------------------------------------------- |
| Brutally minimal     | One visual element. Negative space is the design.              |
| Maximalist chaos     | Dense, layered, typographically rich — controlled overwhelm    |
| Retro-futuristic     | CRT scanlines, terminal aesthetics, monospace grids            |
| Organic / natural    | Irregular shapes, earthy palettes, imperfect textures          |
| Luxury / refined     | Tight leading, serif type, deep backgrounds, restrained colour |
| Playful / toy-like   | Bright fills, rounded corners, tactile drop shadows            |
| Editorial / magazine | Strong typographic hierarchy, pull quotes, image-text flow     |
| Brutalist / raw      | Exposed structure, high-contrast, deliberate anti-polish       |
| Art deco / geometric | Symmetry, ruled lines, repeating motifs                        |

## Aesthetic Guidelines

### Typography

- Use **distinctive, characterful fonts** — load from Google Fonts, Bunny Fonts, or bundle locally
- Pair a display font (headings) with a body font (prose)
- **Never default to** Inter, Roboto, Arial, Space Grotesk, or system-ui as the primary typeface
- Set type on a clear scale: 3–5 distinct sizes with intentional weight variation
- Typographic contrast creates hierarchy — size, weight, case, and spacing all count
- For Next.js: use `next/font/google` with `variable: '--font-display'` — self-hosted, zero layout shift, no external requests:
  ```tsx
  const display = SomeFont({
    subsets: ["latin"],
    variable: "--font-display",
    display: "swap",
  });
  // apply on <html className={display.variable}>, then reference via var(--font-display) in @theme
  ```

### Colour and Theme

- Define a palette via CSS custom properties (`--color-*`) at `:root`
- Pick 1–2 dominant colours and 1 sharp accent — avoid evenly distributed palettes
- CSS variable example (warm editorial dark theme):
  ```css
  :root {
    --bg: #0d0d0d;
    --surface: #1a1a1a;
    --text: #f2ede7;
    --accent: #e06c2e;
    --accent-sharp: #f08c55;
    --muted: #737373;
  }
  ```
- Dark backgrounds amplify texture and typography — use them confidently
- For Next.js / Tailwind v4, define colour tokens in `@theme {}` inside your global CSS — **not** in `tailwind.config.ts` (that pattern is Tailwind v3 only). Token names follow `--color-*` and Tailwind auto-generates utility classes (`bg-accent`, `text-muted`, etc.):

  ```css
  @import "tailwindcss";

  @theme {
    --color-bg: #0d0d0d;
    --color-surface: #1a1a1a;
    --color-text: #f2ede7;
    --color-accent: #e06c2e;
    --color-muted: #737373;
    --font-display: var(--font-display); /* hoisted from next/font */
  }
  ```

### Motion

Use **`motion/react`** (motion.dev v12+) for all React and Next.js work. Never reach for `@keyframes` or `setTimeout` hacks — motion handles orchestration, exit animations, and scroll binding natively.

**Staggered entrance with `useInView`:**

```tsx
import { motion, useInView } from "motion/react";
import { useRef } from "react";

const variants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.4, ease: "easeOut" },
  }),
};

export function CardList({ items }: { items: string[] }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  return (
    <ul ref={ref}>
      {items.map((item, i) => (
        <motion.li
          key={item}
          custom={i}
          variants={variants}
          initial="hidden"
          animate={inView ? "visible" : "hidden"}
        >
          {item}
        </motion.li>
      ))}
    </ul>
  );
}
```

**Page transitions in Next.js App Router** — create a `'use client'` wrapper component, then use it in `app/layout.tsx`:

```tsx
"use client";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";

export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.25 }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
```

> `AnimatePresence` requires a Client Component — it cannot be used directly in a Server Component layout.

**Scroll-linked effects** (`useScroll` + `useTransform`):

```tsx
const { scrollYProgress } = useScroll();
const opacity = useTransform(scrollYProgress, [0, 0.15], [1, 0]);
const scale = useTransform(scrollYProgress, [0, 0.15], [1, 0.95]);
```

**Rules:**

- Stagger via `custom` index + `variants` — not manual `delay` arithmetic
- Use `useInView({ once: true })` for below-fold content — not on-mount triggers
- Always call `useReducedMotion()` and skip or minimise animations when it returns `true`
- One coherent page-load sequence beats scattered micro-interactions across every element

### Spatial Composition

- Break the grid deliberately: at least one element should violate a strict column boundary
- Use asymmetry as a tool — unequal column splits (60/40, 70/30) produce more energy than 50/50
- Generous whitespace OR controlled density — pick one and apply it consistently
- Overlapping elements (negative `margin`, `z-index` layering) add depth without extra assets
- Diagonal lines, rotated text, or tilted containers signal intentionality

### Backgrounds and Visual Detail

Choose at least one from this list; bare flat backgrounds are never the final answer:

| Technique              | Implementation                                                             |
| ---------------------- | -------------------------------------------------------------------------- |
| Gradient mesh          | Multi-stop radial gradients layered with `mix-blend-mode`                  |
| Noise texture          | SVG `feTurbulence` filter or a CSS `background-image: url(noise.svg)`      |
| Geometric pattern      | CSS `repeating-linear-gradient` or inline SVG patterns                     |
| Layered transparencies | Stacked `::before` / `::after` with `opacity` and `backdrop-filter`        |
| Grain overlay          | `::after` with `opacity: 0.04` noise, `pointer-events: none`               |
| Dramatic shadow        | Multi-layer `box-shadow` with spread and offset, not a single blurred ring |

## Anti-Patterns

| Pattern                                | Why it fails                                               | Fix                                                                       |
| -------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------- |
| Inter / Roboto / Arial as primary font | Signals zero design intent — every generic SaaS uses these | Pick a characterful font; use system fonts only for dense prose body text |
| Purple gradient on white background    | The default "AI-generated" look, instantly forgettable     | Commit to a real palette with CSS variables                               |
| Equal-weight colour distribution       | Flat, no focal point                                       | One dominant colour, one accent, everything else neutral                  |
| Cards everywhere, same radius          | Predictable component soup                                 | Vary element types; mix cards with full-bleed sections, borders, tables   |
| Animations on every element            | Noise, not signal                                          | Animate 2–3 key moments; let the rest be still                            |
| Symmetric, centred layouts only        | Passive, templated                                         | Add one intentional asymmetric break                                      |

## Implementation Checklist

Before delivering any UI artifact:

- [ ] Typography: at least one non-system, characterful font loaded and applied
- [ ] Colour: CSS variables defined at `:root`; palette has a clear dominant + accent
- [ ] Background: at least one texture, gradient, or geometric detail — not bare flat fill
- [ ] Layout: at least one asymmetric or grid-breaking element
- [ ] Motion: `motion/react` used for entrance or scroll-trigger; `useReducedMotion()` respected
- [ ] Anti-patterns: none of the six patterns from the table above are present
- [ ] Responsive: layout tested at 375 px, 768 px, and 1280 px
- [ ] Accessibility: min 4.5:1 contrast ratio on body text; `prefers-reduced-motion` respected
