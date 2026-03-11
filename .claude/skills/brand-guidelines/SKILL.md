---
name: brand-guidelines
description: "Use when defining, documenting, or enforcing a brand system across a project — covering colour tokens, typographic scale, spacing, component conventions, and visual consistency. Use when starting a new design system, auditing inconsistent styles, or applying brand identity to components, pages, or documents. Triggers on: brand colors, brand system, design tokens, visual identity, style guide, typography scale, inconsistent styles, apply brand, brand consistency, component theming."
argument-hint: "Describe the brand or project — include existing colours, fonts, tone, and what needs to be made consistent (components, pages, docs, presentations, etc.)"
---

# Brand Guidelines

Establishes and enforces a coherent brand system. A strong brand is not a mood board — it is a set of decisions made once and respected everywhere.

> "Design is the silent ambassador of your brand."  
> — Paul Rand

## When to Use

- Starting a project with no established visual language
- Auditing a codebase where colours, fonts, and spacing are inconsistent across components
- Documenting a brand system so collaborators can follow it without guessing
- Applying an existing brand identity to a new surface (component, page, presentation, email)
- Extending a brand system with new tokens without breaking consistency

## The Brand System

A complete brand system has five layers. Work top-down when creating; audit bottom-up when fixing.

| Layer                | What it defines                                                      |
| -------------------- | -------------------------------------------------------------------- |
| **Identity**         | Name, logo, tone of voice, personality                               |
| **Colour**           | Primary palette, accent palette, neutral scale, semantic roles       |
| **Typography**       | Font families, size scale, weight scale, line-height, letter-spacing |
| **Spacing & Layout** | Base unit, spacing scale, grid columns, breakpoints                  |
| **Components**       | Border-radius, shadow system, icon style, interaction states         |

## Procedure

### Step 1: Extract or Define the Palette

If a brand already exists, extract its tokens before writing any code. If starting fresh, define them now — don't let them emerge organically across files.

**Colour roles to assign explicitly:**

| Role                    | Purpose                                      |
| ----------------------- | -------------------------------------------- |
| `--color-bg`            | Page / canvas background                     |
| `--color-surface`       | Card, modal, panel background                |
| `--color-border`        | Dividers, input outlines                     |
| `--color-text`          | Primary body copy                            |
| `--color-text-muted`    | Secondary labels, captions                   |
| `--color-accent`        | Primary action (buttons, links, focus rings) |
| `--color-accent-subtle` | Hover states, tinted backgrounds             |
| `--color-destructive`   | Errors, delete actions                       |
| `--color-success`       | Confirmations, positive status               |

Prefer `oklch()` for colour values — perceptually uniform, predictable lightness steps, wider gamut than hex.

### Step 2: Establish the Type Scale

Use a modular scale (1.25× or 1.333×) anchored to a base size. Never invent font sizes ad-hoc.

| Token         | Multiplier  | Example use              |
| ------------- | ----------- | ------------------------ |
| `--text-xs`   | 0.64× base  | Labels, badges           |
| `--text-sm`   | 0.8× base   | Secondary copy, metadata |
| `--text-base` | 1× (16px)   | Body prose               |
| `--text-lg`   | 1.25× base  | Lead paragraphs          |
| `--text-xl`   | 1.563× base | Section headings         |
| `--text-2xl`  | 1.953× base | Page headings            |
| `--text-3xl`  | 2.441× base | Hero / display           |

Pair a **display font** (headings) with a **body font** (prose). They should create contrast — similar typefaces side by side reads as a mistake, not a system.

### Step 3: Define Tokens in Code

**Tailwind v4 — `@theme {}` in global CSS:**

```css
@import "tailwindcss";

@theme {
  /* Colour */
  --color-bg: oklch(0.08 0 0);
  --color-surface: oklch(0.12 0 0);
  --color-border: oklch(0.22 0 0);
  --color-text: oklch(0.93 0.02 80);
  --color-text-muted: oklch(0.55 0 0);
  --color-accent: oklch(0.65 0.18 45);
  --color-accent-subtle: oklch(0.18 0.04 45);
  --color-destructive: oklch(0.58 0.22 25);
  --color-success: oklch(0.62 0.16 145);

  /* Typography */
  --font-display: var(--font-display); /* hoisted from next/font */
  --font-body: var(--font-body);

  /* Spacing base unit: 4px */
  --spacing: 0.25rem;

  /* Radius */
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 1rem;
}
```

Tailwind auto-generates utilities from every `--color-*` token: `bg-accent`, `text-muted`, `border-border`, etc.

**Plain CSS (no Tailwind):**

```css
:root {
  --color-bg: #0a0a08;
  --color-surface: #141412;
  --color-text: #f0ede6;
  --color-accent: #d97740;
}
```

### Step 4: Audit for Drift

Before shipping, check for brand drift — tokens defined but overridden inline, or colours/fonts used without going through the token system.

**Grep patterns to catch drift:**

```bash
# Hardcoded hex colours outside token definitions
grep -rn '#[0-9a-fA-F]\{3,6\}' src/ --include="*.tsx" --include="*.css"

# Inline style overrides
grep -rn 'style={{' src/ --include="*.tsx"

# Raw font-family declarations outside @theme / :root
grep -rn 'font-family:' src/ --include="*.css"
```

Any hit that isn't inside a `@theme {}` or `:root {}` block is a brand drift violation.

## Anti-Patterns

| Pattern                                                                 | Why it fails                                                           | Fix                                                                       |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Raw hex literals scattered in components                                | Token becomes unsyncable — changing a colour requires grep-and-replace | Route all colour through named tokens                                     |
| Different font sizes per component with no shared scale                 | Visual rhythm breaks; pages feel assembled, not designed               | Define a modular scale; enforce via tokens                                |
| Accent colour used for every interactive element AND errors AND success | Semantic meaning collapses; user cannot build mental model             | Assign semantic roles (`--color-destructive`, `--color-success`)          |
| Radius inconsistency (`4px` here, `8px` there, `12px` somewhere else)   | Signals no system thinking                                             | Define `--radius-sm/md/lg`; never use raw `px` values inline              |
| Dark mode colours as inline overrides in a media query                  | Doubles the drift surface area                                         | Use `prefers-color-scheme` to swap CSS custom properties at `:root` scope |

## Documentation Template

When handing a brand system to collaborators, document it in this order:

```markdown
## Colours

| Token            | Value                 | Use                       |
| ---------------- | --------------------- | ------------------------- |
| `--color-accent` | `oklch(0.65 0.18 45)` | Primary CTAs, focus rings |

...

## Typography

| Token            | Value            | Use           |
| ---------------- | ---------------- | ------------- |
| `--font-display` | Instrument Serif | Headings ≥ xl |

...

## Spacing

Base unit: 4px. All spacing is multiples: 4, 8, 12, 16, 24, 32, 48, 64.

## Do / Don't

- ✅ Use `text-accent` for interactive labels
- ❌ Use `text-accent` for error states (use `text-destructive`)
```
