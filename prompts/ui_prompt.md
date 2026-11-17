# UI master prompt (dark, modern, Webflow-style SaaS)

Build the frontend for "Treatment Pre-Authorisation Decision Desk" (product name "AuthDesk"), a healthcare and insurance multi-agent decision platform. Use Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, Framer Motion, Recharts and Lucide icons. Connect to my FastAPI backend (SSE for live agent events).

DESIGN DIRECTION: A premium dark SaaS website in the style of a modern Webflow startup template. It should look like a polished product site that opens into a real app. Dark mode only.

DESIGN SYSTEM
- Background near-black navy #05070F; cards #0B1020 and #111827
- Borders 1px rgba(255,255,255,0.08); rounded-2xl; soft inner glow
- Primary gradient: teal #14F1D9 to blue #3B82F6 to violet #8B5CF6 (headlines, buttons, glow accents)
- Status: Approve #22C55E, Deny #F43F5E, More Info #F59E0B, as soft glowing badges
- Text: white headings, slate-400 body
- Fonts: Plus Jakarta Sans (headings), Inter (body), JetBrains Mono (clause IDs)
- Effects: glassmorphism (backdrop-blur), blurred gradient orbs behind sections, subtle grid/noise texture, gradient borders on hover
- Motion: Framer Motion fade-up on scroll, staggered card entrances, pulsing dot on the running agent, animated connecting lines between agents, count-up numbers

LANDING PAGE ( / )
1. Sticky glass navbar: logo, links (Features, How it works, Agents, Evaluation), "Launch Desk" gradient button
2. Hero: large gradient headline "Pre-authorisation decisions in seconds, not days", sub-line, two buttons (Launch Desk, Watch Demo), floating glass mockup of the live agent pipeline with glowing lines
3. Trust strip: "Clause-backed decisions - Human peer review - Full audit trail"
4. Features: 6 glass cards with icons (RAG over plan documents, Medical necessity check, Fan-out parallel agents, Human peer review, Draft letters, Audit trail)
5. How it works: 4 animated steps (Parse, Retrieve, Decide, Review and Letter)
6. Agents section: 5 agent cards with roles and glowing icons
7. Stats band with count-up numbers (decision accuracy, avg. time, clause correctness)
8. Final CTA with gradient glow, then footer

APP PAGES (collapsible dark glass sidebar)
1. /dashboard: KPI cards (Total cases, Approval rate, Pending review, Avg. decision time) with sparklines, donut chart of decisions, recent-cases table with glowing status badges
2. /new: request form (patient ID, treatment, diagnosis, provider, notes), "Load sample case" dropdown, large gradient Submit button
3. /cases/[id] (hero screen, 3 columns):
   - Left: original request and parsed fields as key-value chips
   - Centre: live pipeline. Request Parser, fan-out into Coverage Retrieval and Medical Necessity side by side, fan-in to Authorisation Manager, then Letter Drafter. Each agent is a glass card with status (idle, running with pulsing glow, done with green check), short result and confidence bar, joined by animated SVG lines
   - Right: glowing decision banner, cited clause chips that expand to show source text, editable draft letter with Copy and Download PDF
   - Amber "Human review required" banner on every denial
4. /review: queue of cases awaiting a human; AI reasoning beside cited clauses; Uphold / Overturn / Request Info buttons and notes box; verdict updates the case record live
5. /audit: vertical glowing timeline of every agent action and human verdict with timestamps and filters
6. /evaluation: "Run 10 tests" button with progress animation, two radial gauges (Decision accuracy, Clause correctness), confusion matrix heatmap, per-case table (expected vs actual, clause match, pass/fail)

UX: skeleton loaders, toasts, hover/focus states, keyboard accessibility, responsive mobile to desktop, empty states, logo loading screen.

Start with design tokens (tailwind config, globals.css) and shared components (GlassCard, GradientButton, StatusBadge, ClauseChip, AgentCard). Show me a screenshot of the landing hero before building the remaining pages.
