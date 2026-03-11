---
name: web-performance
description: "Use when building or auditing any public-facing website or web app for performance, search visibility, and AI discoverability. Covers rendering strategy (SSR/SSG/CSR pitfalls), Core Web Vitals (LCP, CLS, INP), technical SEO, GEO (Generative Engine Optimization for AI search), robots.txt, llms.txt, and agentic browsing readiness. Triggers on: web performance, Core Web Vitals, LCP, CLS, INP, SEO, GEO, robots.txt, llms.txt, sitemap, structured data, schema.org, AI search, agentic browsing, SSR, SSG, CSR, rendering strategy."
argument-hint: "Describe the site or page to audit — include URL, framework, and any known issues (slow LCP, poor rankings, AI search visibility, etc.)"
---

# Web Performance, SEO & AI Discoverability

Covers everything that affects whether a page is found, loaded fast, ranked, and understood — by humans, search engines, and AI agents.

## 1. Rendering Strategy

Choose the right rendering mode per content type. Wrong choices cause SEO failures and poor vitals.

| Mode                               | Best for                                  | Pitfalls                                                                       |
| ---------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------ |
| **SSG** (Static Site Gen)          | Docs, marketing, blogs                    | Stale content without revalidation                                             |
| **SSR** (Server-Side Render)       | Dynamic, personalized, auth-gated content | Higher TTFB if server is slow; hydration mismatch causes CLS                   |
| **ISR** (Incremental Static Regen) | High-traffic pages with periodic updates  | Stale-while-revalidate window can serve outdated content                       |
| **CSR** (Client-Side Render)       | Dashboards behind auth, internal tools    | Googlebot executes JS but with delay — DON'T use for public SEO-critical pages |

**Key pitfalls:**

- Hydration mismatch (SSR HTML ≠ client render) — causes layout shift and React warnings; debug with `suppressHydrationWarning` only as last resort
- Lazy-loading above-the-fold content — kills LCP; only lazy-load what's off-screen
- Blocking render with large JS bundles — defer non-critical scripts, use dynamic `import()`

## 2. Core Web Vitals

Google's ranking signals. Measure with Lighthouse, PageSpeed Insights, or `web-vitals` JS package.

| Metric                              | Measures                                  | Good    | Needs Work | Poor    |
| ----------------------------------- | ----------------------------------------- | ------- | ---------- | ------- |
| **LCP** — Largest Contentful Paint  | Perceived load speed                      | < 2.5s  | 2.5–4s     | > 4s    |
| **CLS** — Cumulative Layout Shift   | Visual stability                          | < 0.1   | 0.1–0.25   | > 0.25  |
| **INP** — Interaction to Next Paint | Responsiveness (replaced FID, March 2024) | < 200ms | 200–500ms  | > 500ms |

### LCP fixes

```html
<!-- Preload hero image — single most impactful LCP fix -->
<link rel="preload" as="image" href="/hero.webp" fetchpriority="high" />

<!-- Never lazy-load above-fold images -->
<img src="/hero.webp" alt="..." loading="eager" fetchpriority="high" />
```

- Use `<link rel="preconnect">` for third-party origins (fonts, CDN)
- Serve images in WebP/AVIF, size them with `srcset`

### CLS fixes

- Always set explicit `width` and `height` on `<img>` and `<video>` — browser reserves space before load
- Avoid inserting DOM above existing content (banners, cookie notices) — use reserved space
- Use `font-display: swap` with size-adjust to prevent font CLS

### INP fixes

- Break up long tasks (> 50ms) with `scheduler.yield()` or `setTimeout(fn, 0)`
- Move heavy computation off the main thread into Web Workers
- Avoid synchronous layout thrashing (read then write DOM, never interleave)

## 3. Technical SEO

### HTML structure

```html
<head>
  <title>Page Title — Site Name</title>
  <!-- 50–60 chars -->
  <meta name="description" content="..." />
  <!-- 150–160 chars, unique per page -->
  <link rel="canonical" href="https://example.com/page/" />
  <!-- prevent duplicate content -->

  <!-- Open Graph (Facebook, LinkedIn, Slack previews) -->
  <meta property="og:title" content="..." />
  <meta property="og:description" content="..." />
  <meta property="og:image" content="https://example.com/og.png" />
  <!-- 1200×630px -->
  <meta property="og:url" content="https://example.com/page/" />

  <!-- Twitter/X Card -->
  <meta name="twitter:card" content="summary_large_image" />
</head>
```

### Semantic HTML (non-negotiable)

- One `<h1>` per page — the primary topic
- Logical heading hierarchy: `h1 → h2 → h3` (never skip levels)
- `<main>`, `<nav>`, `<article>`, `<section>`, `<aside>`, `<footer>` — landmark elements crawlers use for structure
- Descriptive link text — never "click here" or "read more" on its own

### Structured data (JSON-LD)

```html
<script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "...",
    "datePublished": "2026-01-01",
    "author": { "@type": "Person", "name": "..." },
    "publisher": { "@type": "Organization", "name": "...", "logo": "..." }
  }
</script>
```

Use the right `@type` for the content: `Article`, `Product`, `FAQPage`, `BreadcrumbList`, `SoftwareApplication`. Validate with [Google's Rich Results Test](https://search.google.com/test/rich-results).

### sitemap.xml

- List all indexable URLs; submit to Google Search Console and Bing Webmaster Tools
- Include `<lastmod>` — use real modification dates, not today's date on every page
- Exclude paginated pages, filtered variants, and auth-gated URLs

## 4. GEO — Generative Engine Optimization

AI search engines (Perplexity, ChatGPT Search, Gemini, Google AI Overviews) and AI agents cite and summarize web content differently from traditional search. Optimize for how LLMs extract and attribute information.

**Content principles:**

- Write in clear, declarative prose — state the answer directly, don't bury it in preamble
- Use Q&A or FAQ structure: AI models prefer extractable question-answer pairs
- Include entity signals: named people, companies, dates, locations — specificity increases citation likelihood
- Cite authoritative external sources — content with outbound links to trusted sources gets cited more often
- Keep paragraphs short (3–5 sentences) — easier to extract as a coherent chunk

**Structural principles:**

- `<h2>` headings should read as standalone statements or questions: "How does X work?" not "Overview"
- Add FAQ schema (`"@type": "FAQPage"`) for explicit Q&A content — picked up by AI Overviews
- `datePublished` and `dateModified` schema signals freshness to AI ranking systems
- Author `@type: Person` with `sameAs` links to authoritative profiles (LinkedIn, GitHub) — establishes authorship signal

## 5. robots.txt

Controls crawler access. Lives at `/robots.txt`.

```
# Allow all well-behaved crawlers
User-agent: *
Allow: /

# Disallow internal/admin paths
Disallow: /admin/
Disallow: /api/
Disallow: /_next/

# Major AI training crawlers — block if you don't want your content in training data
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: PerplexityBot
Allow: /          # Allow AI search (inference) — different from training

User-agent: Googlebot-Extended
Disallow: /       # Blocks Google AI training (Gemini), not web search

Sitemap: https://example.com/sitemap.xml
```

**Key distinction:** `GPTBot` / `ClaudeBot` = training data crawlers. `PerplexityBot` / `ChatGPT-User` = inference search crawlers. Block training if desired; allowing inference improves GEO visibility.

## 6. llms.txt

The `/llms.txt` standard (llmstxt.org) gives AI agents a curated, LLM-readable entry point to your site — analogous to `robots.txt` but for AI context rather than access control.

**Format** (file at `/llms.txt`):

```markdown
# Project or Site Name

> One-paragraph summary of what the site is and who it's for.
> Include key facts an LLM needs to understand the rest of the file.

Optional additional context (lists, notes, caveats).

## Section Name

- [Page Title](https://example.com/page.md): Brief description of what this page covers

## Docs

- [API Reference](https://example.com/api.md): Full API endpoints and parameters
- [Quick Start](https://example.com/quickstart.md): Setup in 5 minutes

## Optional

- [Changelog](https://example.com/changelog.md): Version history
```

**Rules:**

- H1 = project name (required); blockquote = summary (strongly recommended)
- Link to `.md` versions of pages where possible — clean markdown is more useful to LLMs than HTML
- `## Optional` section is skipped by agents when context is limited — put secondary content there
- Keep it under 100 lines; link out for depth rather than inlining everything

## 7. Agentic Browsing Readiness

AI agents (browser-use, computer-use, AutoGPT, Copilot Workspace) navigate and interact with pages programmatically. Poorly structured pages fail silently.

- **ARIA labels** on every interactive element without visible text: `<button aria-label="Close dialog">`
- **`role` attributes** where HTML semantics are ambiguous: `role="search"`, `role="status"`, `role="alert"`
- **Machine-readable dates**: `<time datetime="2026-03-11">March 11, 2026</time>`
- **Stable IDs**: don't use auto-generated IDs like `div-823a4f` — agents use IDs to target elements
- **Descriptive `alt` text**: not "image1.jpg" — describe content and function
- **No click-only interactions**: keyboard/tab navigation must work; agents often don't simulate mouse

## Quick Audit Checklist

- [ ] Rendering mode chosen intentionally for each route (SSG/SSR/CSR)
- [ ] LCP < 2.5s — hero image preloaded, no lazy-load above fold
- [ ] CLS < 0.1 — images have explicit dimensions, no layout-shifting fonts
- [ ] INP < 200ms — no long tasks blocking main thread
- [ ] Unique `<title>` and `<meta name="description">` on every page
- [ ] One `<h1>`, logical heading hierarchy, semantic landmarks
- [ ] JSON-LD structured data present and validated
- [ ] `sitemap.xml` submitted to Search Console
- [ ] `robots.txt` reviewed — AI crawler directives intentional
- [ ] `/llms.txt` present for public-facing documentation or product sites
- [ ] All images have meaningful `alt` text
- [ ] Interactive elements have ARIA labels where needed
