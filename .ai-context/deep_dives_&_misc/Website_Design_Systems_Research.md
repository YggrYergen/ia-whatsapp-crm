# Website Design Systems Research Report

**Date:** 2026-04-13  
**Research Scope:** 25 web searches across the design ecosystem  
**Objective:** Identify the top 3 world-class web design systems for AI-assisted development compatible with Antigravity + Claude Opus 4.6  

---

## EXECUTIVE SUMMARY

After exhaustive research across the vibe-coding landscape, design system ecosystems, component libraries, animation frameworks, and deployment strategies, three distinct "systems" emerged as the current world-class standard for producing breathtaking, professional websites through AI-assisted coding.

**The critical insight:** The difference between "mid" and "masterpiece" is NOT the prompting. It's the **component ecosystem** the AI has access to. Give Claude access to Aceternity UI's 3D cards and it WILL produce stunning output. Give it only vanilla CSS and it'll produce a clean but forgettable page. **The system defines the ceiling.**

| # | System Name | Aesthetic | Best For | Complexity |
|:--|:-----------|:---------|:---------|:-----------|
| **A** | **Cinematic Premium** | Immersive, motion-heavy, jaw-dropping | Hero sections, premium brand identity | High |
| **B** | **Polished SaaS** | Clean, modern, conversion-optimized | SaaS landing pages, high conversion | Medium |
| **C** | **Performance Purist** | Elegant, fast-loading, razor-sharp | Speed-first sites, SEO, mobile-first | Low |

---

## SYSTEM A: "CINEMATIC PREMIUM"

### The Stack
```
Framework:    Next.js 15 (App Router)
UI Base:      shadcn/ui (Radix UI + Tailwind CSS)
Motion Layer: Aceternity UI (200+ cinematic components)
Animation:    Framer Motion
Typography:   Geist (headlines) + Inter (body)
Deployment:   Cloudflare Pages (static export)
```

### What It Produces
This is the **Awwwards-level** stack. It creates websites that feel like Apple product pages — immersive scroll experiences, 3D card effects, particle backgrounds, parallax layers, and cinematic hero sections. When someone opens the site, they go "holy shit."

### Core Components Available (Aceternity UI)
| Component | Visual Effect | Use Case |
|:----------|:-------------|:---------|
| Hero Parallax | Scroll-driven 3D rotation + translation | Hero section |
| 3D Card Effect | Perspective tilt on hover | Feature cards |
| Background Beams | Animated light beams | Page backgrounds |
| Sparkles | Configurable particles | Decorative elements |
| Aurora Background | Northern lights gradient animation | Full-page backgrounds |
| Vortex Background | Swirly animated particles | Hero/section backgrounds |
| Spotlight Effect | Mouse-following light gradient | Interactive hero sections |
| Floating Dock | macOS-style animated dock | Navigation |
| Text Generate Effect | Typewriter/AI-style text reveal | Headlines |
| Infinite Moving Cards | Auto-scrolling testimonial cards | Social proof |
| Tracing Beam | Scroll-following beam effect | Content sections |
| Wavy Background | Subtle wave animation | Section dividers |

### Installation (Exact Commands)
```bash
# 1. Create Next.js project
npx -y create-next-app@latest ./ --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm

# 2. Initialize shadcn/ui
npx shadcn@latest init

# 3. Install Framer Motion
npm install framer-motion

# 4. Add Aceternity components (example)
# Copy components from https://ui.aceternity.com/components
# Into: src/components/ui/

# 5. Install additional dependencies (most Aceternity components need these)
npm install clsx tailwind-merge mini-svg-data-uri @tabler/icons-react
```

### tailwind.config.ts Additions (Required for Aceternity)
```typescript
// Add to tailwind.config.ts for aceternity animations
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      animation: {
        spotlight: "spotlight 2s ease .75s 1 forwards",
        shimmer: "shimmer 2s linear infinite",
        "meteor-effect": "meteor 5s linear infinite",
      },
      keyframes: {
        spotlight: {
          "0%": { opacity: 0, transform: "translate(-72%, -62%) scale(0.5)" },
          "100%": { opacity: 1, transform: "translate(-50%,-40%) scale(1)" },
        },
        shimmer: {
          from: { backgroundPosition: "0 0" },
          to: { backgroundPosition: "-200% 0" },
        },
        meteor: {
          "0%": { transform: "rotate(215deg) translateX(0)", opacity: 1 },
          "70%": { opacity: 1 },
          "100%": { transform: "rotate(215deg) translateX(-500px)", opacity: 0 },
        },
      },
    },
  },
}
```

### Typography Setup
```typescript
// src/app/layout.tsx
import { GeistSans } from 'geist/font/sans'
import { GeistMono } from 'geist/font/mono'

// npm install geist
// Geist for headlines (clean, modern, Vercel's own font)
// Inter for body (the industry standard for readability)
```

### Pros
- ✅ Produces the most visually impressive websites possible
- ✅ 200+ pre-built animated components
- ✅ Copy-paste workflow — full code ownership
- ✅ Built on shadcn/ui = accessible, customizable
- ✅ Dark mode optimized
- ✅ AI (Claude) handles this stack extremely well because it knows React + Tailwind deeply

### Cons
- ❌ Heaviest JS bundle of the three systems
- ❌ Some components are complex — more moving parts to break
- ❌ Can feel "over-animated" if not restrained
- ❌ Requires disciplined component selection to avoid visual overload
- ❌ More setup time

### Best Example Sites
- [aceternity.com](https://ui.aceternity.com) itself
- Sites in the [Godly.website](https://godly.website) gallery
- Awwwards dark-mode SaaS winners

---

## SYSTEM B: "POLISHED SAAS"

### The Stack
```
Framework:    Next.js 15 (App Router)
UI Base:      shadcn/ui (Radix UI + Tailwind CSS)
Motion Layer: Magic UI (150+ marketing components) + Motion Primitives
Animation:    Framer Motion
Typography:   Sora (headlines) + Inter (body)
Deployment:   Cloudflare Pages (static export)
```

### What It Produces
This is the **Stripe/Linear/Vercel** tier. Clean, sophisticated, modern SaaS marketing pages that feel premium without being overwhelming. Every animation is purposeful. Every spacing is intentional. It CONVERTS — this is the conversion-optimized system.

### Core Components Available (Magic UI)
| Component | Visual Effect | Use Case |
|:----------|:-------------|:---------|
| Bento Grid | Responsive multi-size grid layout | Feature showcase |
| Animated List | Items animate in/out smoothly | Notifications, updates |
| Marquee | Auto-scrolling content band | Logo bars, testimonials |
| Dot Pattern | Subtle dot grid background | Section backgrounds |
| Globe Effect | 3D rotating globe | Geographic coverage |
| Number Ticker | Animated counting numbers | Stats, KPIs |
| Dock | macOS-style dock navigation | Nav/footer |
| Shimmer Button | Subtle shimmer CTA effect | Primary CTAs |
| Animated Beam | Light beam connecting elements | Connection diagrams |
| Orbiting Circles | Elements orbiting a central point | Product ecosystem |
| Magic Card | Gradient-following hover effect | Feature cards |
| Ripple Effect | Click/hover ripple | Interactive elements |

### Additional Components (Motion Primitives)
| Component | Effect | Use Case |
|:----------|:-------|:---------|
| Text Reveal | Scroll-triggered text appear | Headlines |
| Fade In | Intersection-based fade | Any section |
| Spotlight | Mouse-following light | Hero sections |
| Morphing Dialog | Smooth element transition | Modals |
| Scroll Progress | Page scroll indicator | Navigation |

### Additional Blocks (shadcn Blocks/Studio)
Ready-made landing page sections:
- Hero sections (5+ variants)
- Pricing tables (3+ variants)
- Testimonial sections (with avatars, stars)
- Feature grids (icon + text)
- FAQ accordions
- Footer layouts
- Navbar variants

### Installation (Exact Commands)
```bash
# 1. Create Next.js project
npx -y create-next-app@latest ./ --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm

# 2. Initialize shadcn/ui
npx shadcn@latest init

# 3. Install Framer Motion
npm install framer-motion

# 4. Add Magic UI components via CLI
npx shadcn@latest add @magicui/bento-grid
npx shadcn@latest add @magicui/marquee
npx shadcn@latest add @magicui/animated-list
npx shadcn@latest add @magicui/number-ticker
npx shadcn@latest add @magicui/shimmer-button
npx shadcn@latest add @magicui/dot-pattern
# (add more as needed from https://magicui.design/)

# 5. Add Motion Primitives (copy from https://motion-primitives.com/)
# Into: src/components/motion/

# 6. Add shadcn blocks
npx shadcn@latest add button card dialog sheet tabs badge separator
```

### Typography Setup
```typescript
// src/app/layout.tsx  
import { Sora, Inter } from 'next/font/google'

const sora = Sora({ subsets: ['latin'], variable: '--font-sora' })
const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

// Sora for headlines: geometric, modern, more personality than Inter
// Inter for body: the workhorse, maximum readability at all sizes
```

### Pros
- ✅ The highest conversion-rate aesthetic — this is what Stripe/Linear/Vercel use
- ✅ CLI-based installation — fastest setup of all three
- ✅ 150+ pre-built marketing components
- ✅ Every animation is conversion-purposeful (not just decorative)
- ✅ shadcn Blocks provide ready-made page sections (hero, pricing, testimonials)
- ✅ Moderate JS bundle — good balance of beauty and performance
- ✅ Claude knows this ecosystem perfectly — Magic UI docs are well-structured

### Cons
- ❌ Less "wow factor" than System A — professional, not cinematic
- ❌ Can look "generic SaaS" if you don't customize colors/typography enough
- ❌ Needs careful color palette selection to stand out from the crowd

### Best Example Sites
- [Linear.app](https://linear.app) — the gold standard for System B aesthetic
- [Vercel.com](https://vercel.com) — clean, dark, purposeful
- [Resend.com](https://resend.com) — Magic UI showcase

---

## SYSTEM C: "PERFORMANCE PURIST"

### The Stack
```
Framework:    Astro 5 (Islands Architecture)
Styling:      Tailwind CSS v4
Motion Layer: GSAP (GreenSock) + ScrollTrigger plugin
Animation:    CSS animations + GSAP for complex sequences
Typography:   Outfit (headlines) + Inter (body)
Deployment:   Cloudflare Pages (native — zero config)
```

### What It Produces
This is the **Performance obsessive's** stack. Near-zero JavaScript. Lighthouse 100/100. Sub-second load times. The design feels razor-sharp, deliberate, and elegant — like a beautifully typeset book. No framework overhead. Clean HTML. The focus is on typography, spacing, and deliberate motion.

### Core Approach
Unlike Systems A and B which use component libraries, System C relies on:
1. **Custom Tailwind components** — you build each section by hand (or Claude does)
2. **CSS animations** for simple transitions (fades, slides, reveals)
3. **GSAP** for complex scroll-driven sequences (when needed)
4. **Intersection Observer API** for scroll-triggered reveals
5. **No React runtime** — Astro ships zero JS by default

### GSAP Setup
```bash
npm install gsap
```

```javascript
// GSAP ScrollTrigger for scroll-driven animations
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
gsap.registerPlugin(ScrollTrigger);

// Example: Fade in elements as they scroll into view
gsap.utils.toArray('.animate-in').forEach(el => {
  gsap.from(el, {
    y: 60,
    opacity: 0,
    duration: 1,
    ease: "power3.out",
    scrollTrigger: {
      trigger: el,
      start: "top 85%",
    }
  });
});
```

### Installation (Exact Commands)
```bash
# 1. Create Astro project
npm create astro@latest ./ -- --template minimal --no-install --typescript strict

# 2. Install dependencies
npm install

# 3. Add Tailwind CSS integration
npx astro add tailwind

# 4. Install GSAP
npm install gsap

# 5. (Optional) Add React integration for specific interactive islands
npx astro add react
```

### Typography Setup
```css
/* In global.css or layout */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --font-headline: 'Outfit', sans-serif;
  --font-body: 'Inter', sans-serif;
}
```

### Pros
- ✅ Fastest possible page loads — Lighthouse 100 out of the box
- ✅ Smallest JS bundle — near-zero for static content
- ✅ Native Cloudflare Pages deployment (zero config)
- ✅ SEO dominance — search engines love fast, clean HTML
- ✅ Most maintainable — no dependency bloat
- ✅ Framework-agnostic — can add React "islands" only where needed
- ✅ Claude can write Astro + Tailwind extremely well

### Cons
- ❌ No pre-built animated component library — everything is custom
- ❌ Less "wow factor" than Systems A or B without significant custom animation work
- ❌ GSAP has a steeper learning curve than Framer Motion
- ❌ No shadcn/ui ecosystem (though Tailwind variants exist for Astro)
- ❌ Requires more design skill from the AI since there's no component library to lean on

### Best Example Sites
- [Astro.build](https://astro.build) itself
- Agency portfolio sites on Awwwards
- High-performance editorial/content sites

---

## CROSS-SYSTEM COMPARISON

| Factor | System A (Cinematic) | System B (Polished SaaS) | System C (Performance) |
|:-------|:--------------------|:------------------------|:----------------------|
| **Visual Impact** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Load Speed** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Conversion Optimization** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **SEO** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Setup Speed** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Claude Compatibility** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Maintenance** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Pre-built Components** | 200+ (Aceternity) | 150+ (Magic UI) + Blocks | 0 (custom build) |
| **Animation Quality** | Cinematic | Professional/Purposeful | Surgical/Precise |
| **Mobile Performance** | Good (heavy animations) | Great | Perfect |
| **JS Bundle Size** | ~150-250KB | ~80-150KB | ~0-30KB |

---

## AI CONTEXT CONFIGURATION — The Secret Weapon

Regardless of which system you choose, the KEY to getting Claude to produce designer-grade output (not generic) is providing a **design system file** as context. This is the single biggest lever.

### For Antigravity (Claude Opus 4.6)

Since Antigravity is our environment, we don't use `.cursorrules` or `CLAUDE.md`. Instead, we provide context through:

1. **Project files that Claude reads** — a `design-system.md` in `.ai-context/`
2. **The initial prompt** when starting the website build chat
3. **Reference images** — screenshots of target aesthetics

### The Design System Prompt Template

Use this as the foundation prompt when starting the website build in a new chat:

```markdown
# Design System Rules — tuAsistenteVirtual

## Stack
- [System A/B/C — whichever we choose]

## Color Palette
- Background: #0a0a0f (near-black, NOT pure black)
- Surface: #141420 (cards, elevated elements)
- Border: rgba(255, 255, 255, 0.06)
- Text Primary: #f0f0f0
- Text Secondary: #8a8a9a
- Accent Primary: #3b82f6 (electric blue)
- Accent Gradient: linear-gradient(135deg, #3b82f6, #8b5cf6)
- Success: #22c55e
- Warning: #f59e0b

## Typography
- Headlines: [Geist/Sora/Outfit] — weight 600-800
- Body: Inter — weight 400-500
- Size scale: clamp-based responsive (no fixed px)

## Spacing
- Section padding: py-24 md:py-32
- Component gap: gap-6 md:gap-8
- Card padding: p-6 md:p-8

## Component Rules
- All cards use backdrop-blur-sm + bg-surface/80 + border border-white/5
- All CTAs use the accent gradient + hover:scale-105 transition
- All section entrances use fade-in-up animation (scroll-triggered)
- Maximum 2 animated elements visible simultaneously
- Mobile: reduce or disable heavy animations

## Psychological Design Rules (from our extracted principles)
- Hero: Pain-question headline (PS-01, PS-10)
- Social proof section: Real data only (PS-03, PS-04)
- Pricing: Anchor effect via 3-tier layout (MM-33)
- CTA: Primary (low barrier) + Secondary ("LO NECESITO AHORA")
- Guarantee: Prominent, near pricing (OF-25/26)
- FAQ: Real objection handling (OF-12/13)
```

### Pro Tips for Prompting Claude to Produce Designer-Grade Output

1. **Specify constraints, not aesthetics:** "Use `bg-[#141420]` instead of `bg-gray-900`" > "make it look dark"
2. **Reference specific component libraries:** "Use the Aceternity Hero Parallax component" > "add a cool hero"
3. **Limit animations:** "Maximum 2 animated elements in viewport at once" > "add lots of animations"
4. **Enforce consistency:** "All spacing must use the scale: 4, 6, 8, 12, 16, 24, 32" > "add some padding"
5. **Show, don't describe:** Provide screenshots from Godly.website or Awwwards as reference images

---

## MY RECOMMENDATION FOR tuAsistenteVirtual

### Go with: **System B (Polished SaaS)** as PRIMARY

**Why:**
1. **Conversion-optimized** — our #1 goal is clients, not design awards
2. **Fastest setup** — CLI-based, we can build in hours not days
3. **Claude compatibility** — highest of all three (knows the ecosystem deeply)
4. **Pre-built blocks** — hero, pricing, testimonials already exist as copy-paste sections
5. **Professional not overwhelming** — Chilean business owners need to trust us, not be dazzled
6. **Current site already uses Next.js** — no migration needed, just upgrade

### Enhance with: **Select Aceternity UI components** from System A

Cherry-pick 2-3 high-impact components from System A for the "wow" sections:
- **Hero section**: Use Aceternity's Spotlight or Aurora Background (jaw-dropping first impression)
- **Feature section**: Use Aceternity's 3D Card Effect (premium feel)
- **Everything else**: Magic UI + shadcn Blocks (clean, professional, fast)

This hybrid approach gives us **System B's conversion power with System A's "wow" in the critical first 5 seconds.**

### Deployment: Cloudflare Pages (static export)
- Our current site is already on Cloudflare
- `output: 'export'` in next.config.ts → static HTML → Cloudflare Pages
- Zero additional infrastructure cost

---

## DESIGN INSPIRATION RESOURCES

Bookmark these for the build session:

| Resource | URL | Use |
|:---------|:----|:----|
| Godly | godly.website | Premium design inspiration |
| Awwwards | awwwards.com | Award-winning sites to reference |
| SaaS Landing Page | saaslandingpage.com | SaaS-specific dark mode examples |
| Magic UI Showcase | magicui.design | Component demos |
| Aceternity UI | ui.aceternity.com | Component demos |
| shadcn Blocks | shadcnblocks.com | Ready-made page sections |
| shadcn Studio | shadcnstudio.com | Marketing-focused blocks |

---

## NEXT STEPS

When we start the website build in a fresh chat:

1. **Decide which system** (I recommend B + select A components)
2. **I provide the design system prompt** as initial context
3. **Reference 2-3 screenshot inspirations** from the galleries above
4. **Build section by section**, psych-mapping each one per the corrected strategic framework
5. **Test on mobile** immediately — Chilean market is mobile-first

> **The ceiling is no longer the AI. The ceiling is the component ecosystem. Choose the right system, feed Claude the right context, and the output will be world-class.**
