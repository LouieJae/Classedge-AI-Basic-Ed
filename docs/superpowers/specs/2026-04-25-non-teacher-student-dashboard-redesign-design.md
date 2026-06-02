# Non-Teacher / Non-Student Dashboard Redesign — Design

**Status:** Drafted 2026-04-25
**Scope:** 11 dashboard designs covering 12 roles (Program Head + Principal share one design)
**Mockups:** `~/classedge/.superpowers/brainstorm/53594-1777073650/content/wave-{1..4}-*.html`

## 1. Motivation

The Teacher and Student dashboards are locked, polished design systems:

- **Teacher** (`teacher_base.html`) — Fraunces + Inter Tight, cream/forest/gold/rose palette, editorial paper feel. Built across SP1–SP3.
- **Student** (`student_base.html`) — Bricolage Grotesque + Inter Tight, dark/light theme, gamified (Quest Map, Leaderboard).

Every other role today is one of:

- **No dashboard at all** (Registrar, Academic Director, Coil Admin, Time Keeper, QA, plus the unmodelled Parent/Guardian, Department Staff, Librarian, Guidance Counselor) — they land on the legacy `base.html` or get redirected.
- **A scaffold placeholder** (IT Admin lands on `it_admin_base.html`, shipped during PR #2 as a "good enough for now" sidebar layout).
- **Inconsistent visual language** — what little exists doesn't follow Teacher's Fraunces palette or Student's Bricolage system, so the brand reads as half-finished outside the two main personas.

This spec proposes **one unified dashboard system** for every role that is neither Teacher nor Student, applied to **11 distinct dashboards** (12 roles, with Program Head + Principal sharing one design under different iconography). The system must be extensible so that any future role added to the database can be onboarded without bespoke design work.

Beyond visual consistency, the redesign treats each dashboard as a **decision-support tool** — every KPI must answer a specific question its owner walks in asking, every panel must drive an action, and the data hierarchy must reflect the cognitive job-to-be-done of that role (statistician + psychologist lens).

## 2. Locked decisions

| # | Decision |
|---|----------|
| 1 | Single unified shell ("Operations Mode") for **all** non-teaching, non-student roles. No per-role bespoke shell. |
| 2 | Reuse Teacher's typography (Fraunces + Inter Tight) and palette (cream / forest / gold / rose / ink). Distinguish with sidebar treatment, scope bar, and iconography. |
| 3 | **No gamification** for non-teaching roles. No XP, no badges, no leaderboards. These are professional adults; status anxiety is counter-productive. |
| 4 | **Program Head and Principal share ONE dashboard design.** Iconography (◆ vs ☗) and copy ("Faculty" vs "Teachers", "BS Computer Science" vs "Grade 11 STEM") differ; data shape and layout are identical. |
| 5 | Data hierarchy is per-role and opinionated. Each dashboard has a single "walk-in question" that drives the layout. KPIs that don't drive a decision are removed. |
| 6 | Iconography differentiates roles inside a uniform shell. The role-tag glyph in the sidebar header (▲ Director, ◆ Program Head, ♥ Counselor, ⚙ IT Admin, ⎙ Registrar, ⌖ QA, ⊕ COIL, ⌚ Time Keeper, ⊟ Librarian, ⊟ Dept Staff, ♥ Parent) gives each role its identity without breaking the system. |
| 7 | Two roles (Guidance Counselor, Parent/Guardian) get a **calmer treatment** within the same shell — larger type, more padding, 4 KPIs not 5. The shell bones are unchanged. |
| 8 | Five roles must be **added to the database**: Parent/Guardian, Department Staff/Secretary, Librarian, Guidance Counselor. (Plus a typo fix: merge `Princilpal` into `Principal`.) |

## 3. Roles in scope (12)

| # | Role | DB status | Design treatment | Walk-in question |
|---|---|---|---|---|
| 1 | IT Admin | Exists (id=3) — replaces existing `it_admin_base.html` | Standard | *Is the platform healthy — and is anyone blocked waiting on me?* |
| 2 | Registrar | Exists (id=2) | Standard | *What records action is overdue — and is the term still on schedule?* |
| 3 | Academic Director | Exists (id=4) | **Deep dive** | *Where is the academic program drifting from intent — and is it our content, our teachers, or our students?* |
| 4 | Program Head | Exists (id=6) | **Deep dive** (shared design with Principal) | *Within my department, which courses or sections are off-track this week — and which teachers need backup?* |
| 5 | Principal | Exists (id=16) — also delete typo `Princilpal` (id=14) | Shared with Program Head, swap iconography | Same as Program Head |
| 6 | Coil Admin | Exists (id=7) | Standard, model-aware (mirrors `CoilPartnerSchool.status` pipeline) | *How is the COIL department running this term — and which partner relationships need attention?* |
| 7 | Time Keeper | Exists (id=8) | Standard | *Who's anomalous today — and is the week's DTR ready to close?* |
| 8 | QA | Exists (id=10) | Standard | *What needs review this week — and where is quality drifting?* |
| 9 | Department Staff / Secretary | **NEW** | Standard | *What does the Head need from me — and what's on the calendar today?* |
| 10 | Parent / Guardian | **NEW** | Calmer treatment | *Here's what's happening with my children at school today.* |
| 11 | Librarian | **NEW** | Standard | *What's circulating, what's overdue — and is anything trending we should buy more of?* |
| 12 | Guidance Counselor | **NEW** | Calmer treatment | *Who needs me this week — and am I catching them early enough?* |

= **11 unique designs** (Program Head and Principal share).

## 4. Design system — "Operations Mode"

### 4.1 Shell anatomy

Every non-teacher / non-student dashboard uses these zones in this order:

1. **Sidebar (240px, solid forest `#1b4332`)** — brand mark, role tag (uppercase letterspaced label under brand), nav with section dividers, sticky user block at bottom. Distinct from Teacher's translucent-paper sidebar so the user knows they're in "back-office" not "classroom" context.
2. **Scope bar (top of main)** — pills indicating department / term / "as of" timestamp; right-aligned live indicator. The extension point for any future role: a new role gets new scope tags, no shell change required.
3. **Greeting block** — `Good [time], [first name]` in Fraunces. Italic line below = the role's walk-in question (literal or paraphrased). Right-aligned: 1 secondary action button + 1 primary action button.
4. **KPI strip (4 or 5 cards)** — each card carries: small uppercase label, large Fraunces number with optional unit, delta line (vs prior period or threshold), optional sparkline. Warn-tinted cards (rose-deep gradient) flag anomalies pre-attentively.
5. **Grid main (1.45fr / 1fr)** — primary panel left (the role's worklist or centerpiece visual), secondary panel right (chart / pulse / funnel / pipeline).
6. **Context strip (bottom, two equal columns)** — ambient information that doesn't need action this minute: calendar, runway, kudos, privacy notices, etc.

### 4.2 Typography

- **Display:** Fraunces (300–700), used for greeting headline, KPI numbers, panel section titles, role-tag, child-switcher labels. `font-feature-settings: "ss01"` enabled.
- **Body:** Inter Tight (400–700), used everywhere else.
- **Mono:** JetBrains Mono — used only for technical content (timestamps, IDs, tick-bar uptimes, IP addresses, attendance heatmap day labels).

### 4.3 Color semantics (locked from Teacher)

| Token | Hex | Use |
|---|---|---|
| `--cream` | `#faf7f2` | main bg, neutral |
| `--cream-2` | `#f3ede2` | page-chrome bg |
| `--paper` | `#ffffff` | cards, panels |
| `--forest` | `#1b4332` | sidebar, primary actions, headlines |
| `--forest-2` | `#2d5a47` | hover, gradient stops |
| `--forest-light` | `#d9e4dd` | "ok" pills, scope tags |
| `--gold` | `#b7925a` | highlight, secondary tags, sparklines |
| `--gold-bg` | `rgba(183,146,90,.08)` | subtle highlight |
| `--rose` | `#c08479` | warn |
| `--rose-soft` | `#f4e0dc` | warn pills, warn card gradient |
| `--rose-deep` | `#7a3e3e` | warn text, warn delta, severe state |
| `--ink` | `#2d3142` | primary text |
| `--ink-dim` | `#6c7080` | secondary text |
| `--ink-muted` | `#a0a4b8` | tertiary text, labels |

**Semantics enforced across all 11 designs:**
- Forest = department / scope / primary action
- Gold = highlight, secondary, "interesting"
- Rose / rose-deep = warn, attention required, SLA breach
- Forest-light = ok, on-track, present
- Gradient cards (`.kpi.warn` / `.kpi.ok`) provide a third state cue that is pre-attentive.

### 4.4 The standard template (for the 8 template-driven roles)

When a new role is added later, the design lives or dies by whether its data fits this template:

| Zone | What it is | Psychology purpose |
|---|---|---|
| Scope bar | Term · scope-of-work · "as of" timestamp | Anchors trust ("I'm looking at the right thing") |
| Hero KPI strip | 4–5 numbers, each with delta vs prior period | Glance-and-go — am I OK or not OK? |
| Primary worklist | The role's queue (oldest first / SLA-flagged) | Removes the "what should I do next" decision |
| Secondary panel | One chart trending the most volatile KPI | Trend, not state — answers "is this getting better or worse?" |
| Context strip | Announcements / runway / handoffs | Reduces meeting & slack noise |

If a new role's data doesn't fit this shape, the new role probably doesn't need a dashboard — it needs a single page or an inbox.

## 5. Per-role data hierarchy

### 5.1 Deep dives (3 roles)

The three roles where the data choices are non-obvious and high-stakes get explicit data hierarchies.

#### Academic Director
- **Hero KPIs (4):** Curriculum coverage %, Outcome attainment %, At-risk cohort count + Δ, Content health %.
- **Primary panel:** Program × Performance Band heatmap (5 programs × 5 bands). Click cell = drill into program.
- **Secondary panel:** Pending decisions queue (SyllabusPlan approvals, regen requests, content escalations) — oldest first.
- **Context strip:** Term close-out runway + Content Generator handoff status.
- **Anti-pattern:** No student names. Wrong altitude — invites micromanagement of teachers.

#### Program Head / Principal (one design, two skins)
- **Hero KPIs (5):** Dept avg score vs school avg, At-risk students, Teacher coverage %, Outstanding ratings, Schedule integrity.
- **Primary panel:** Course health table — rows = CourseOfferings; sortable; red-bar accent floats trouble to top.
- **Secondary panel:** Teacher pulse — reframed as **"who needs support this week"** (not a leaderboard). Same TeacherGamification data (IP, ranks) read inversely.
- **Context strip:** Department calendar (uses `feat/department-scoped-calendars` data) + quick actions.
- **Anti-pattern:** Showing IP/rank as a leaderboard to a head creates perverse incentives and breaks trust with faculty.
- **Differentiation Program Head ↔ Principal:** Iconography (◆ vs ☗) + scope-bar copy ("BS Computer Science" vs "Grade 11 STEM") + nav copy ("Faculty" vs "Teachers").

#### Guidance Counselor (calmer treatment)
- **Hero KPIs (4):** Active caseload, New flags this week, Sessions logged this week, **Time-to-first-contact** (avg days from flag → first session).
- **Primary panel:** Student watchlist sorted by **severity × time since last contact** — NOT alphabetical, NOT by grade. Privacy-protected view.
- **Secondary panel:** Incoming referrals from teachers — one-click acknowledge / schedule.
- **Context strip:** This week's calendar + visible **privacy notice** + consent / confidentiality flags.
- **Anti-pattern:** "Cases closed this month" as a KPI — incentivizes premature closure. Time-to-first-contact incentivizes early response, which is what helps students.
- **Calmer treatment justification:** This role does emotionally heavy work; UI should not add cognitive load. Larger type, more padding, 4 KPIs, more whitespace within the same shell.

### 5.2 Standard-template roles (8)

Brief data sketch per role; full mockup in `.superpowers/brainstorm/`.

| Role | Hero KPIs | Primary panel | Secondary panel |
|---|---|---|---|
| **IT Admin** | Active users 24h · failed logins 1h · 5xx rate · Celery queue depth · DB p95 latency | Pending requests + recent admin actions (interleaved feed) | Service health (24h tick bars per service) + ring stats |
| **Registrar** | Active enrollments · pending requests · records flagged · today's tx · SLA hit rate 30d | Aging queue (sorted by age alone, SLA-flagged) | Request volume 14d chart + capacity ring |
| **Coil Admin** | Active partner schools · students participating · collaborative classes · joint sessions this wk · pending invites | Partner schools table (mirrors `CoilPartnerSchool.status` pipeline; pending invites first) | Partner pipeline funnel (Sent → Pending → Partner → Rejected) |
| **Time Keeper** | Present today · absent (no leave) · late · on approved leave · % attendance week | Anomalies queue (buddy-punch / missing clock-out / chronic / no-leave / OT) — by severity | Department × 10-day attendance heatmap with pattern callout |
| **QA** | Open audit items · defects this wk · courses w/ quality flag · time-to-resolve avg · closed this wk (positive last) | Audit queue (severity × age, escalated rises) | Department × 8-week quality trend matrix (issues per 100 enrolled) |
| **Department Staff / Secretary** | From-the-Head open · doc requests · today's bookings · upcoming events 14d · closed this wk | Task inbox (one queue, "From" tag distinguishes Head / teachers / system) | Today's schedule (Head's day + your bookings, gold rail = now) |
| **Librarian** | Items checked out · overdue · holds · today's returns · catalog utilization (positive) | Overdue + holds unified queue (chronic → overdue → holds-ready) | Circulation 14d chart + trending titles list (drives acquisitions) |
| **Parent / Guardian** *(calmer)* | Per child: attendance % · current avg · upcoming due · recognitions | Child's subjects + grades (with contextualized drops, e.g. teacher's re-take offer) | Messages from teachers (recognitions highlighted) |

### 5.3 Cross-cutting design rules

These apply to all 11 dashboards and any future role:

1. **Every KPI carries a delta or threshold.** A single-period number is almost never decision-ready. Either Δ vs prior period, or "target ≤ X · holding" framing.
2. **Sort by signal urgency, not alphabetically.** Worklists float trouble to the top via severity × age. Alphabetical is the antithesis of operational design.
3. **Pre-attentive cues do the heavy lifting.** Warn-tinted cards (`.kpi.warn` gradient), red bar accents on flagged table rows, gold "now" rail in calendars. The eye lands on what matters before the brain reads.
4. **Reframe leaderboards as intervention queues.** Wherever a "rank / standing" framing would naturally fit (Teacher pulse, QA defects), invert to "who needs support" / "who responded fast." Same data, healthier behavior loop.
5. **Calmer treatment for emotionally-heavy roles.** Guidance Counselor + Parent get larger type, more padding, 4 KPIs not 5. Same shell — shell density is the variable.
6. **No gamification language outside Teacher and Student.** "XP" / "badges" / "rank" / "streak" never appear in the 11 dashboards. "Recognition" is the Parent-facing translation.
7. **Privacy is visible by design where applicable.** Guidance Counselor surfaces a rose-tinted privacy notice on every load. Consent flags inline.
8. **Each panel header may carry a `<span class="why">italic micro-rationale</span>`.** Tells the user *why* the panel is sorted the way it is ("severity × time since last contact — not alphabetical"). One line, removable when the user internalizes the pattern.

## 6. Iconography per role

Used in: tab buttons, sidebar role-tag, scope-bar leading glyph. Sourced from Unicode geometric shapes — no icon font dependency.

| Role | Glyph | Reasoning |
|---|---|---|
| IT Admin | `⚙` | System / settings |
| Registrar | `⎙` | Print / records / ledger |
| Academic Director | `▲` | Highest altitude / pinnacle |
| Program Head | `◆` | Diamond — distinct, premium |
| Principal | `☗` *(or alt)* | Different from Program Head; same data |
| Coil Admin | `⊕` | Network / connect / collaboration |
| Time Keeper | `⌚` | Clock — direct |
| QA | `⌖` | Crosshair / target / audit |
| Department Staff | `⊟` | Stack / list / inbox |
| Parent / Guardian | `♥` | Care / family — also used for Counselor with different semantic |
| Librarian | `⊟` | Stack — repurposed (reading collection); could swap for `📚` if web font allows emoji |
| Guidance Counselor | `♥` | Care — overlap with Parent intentional; both are "support roles," visual link is OK |

If overlap on `♥` between Parent and Counselor causes navigation confusion, Counselor can shift to `✚` (medical-cross / care).

## 7. Implementation outline (high-level only — full plan in writing-plans phase)

**Pre-work (data layer):**

1. Add roles to DB via migration: `Parent/Guardian`, `Department Staff`, `Librarian`, `Guidance Counselor`. Delete typo `Princilpal` (id=14) — verify no users assigned, or re-assign to `Principal` (id=16).
2. Add new permissions for each new role's expected views (per Phase 3 categorization style).
3. Decide whether Parent/Guardian is multi-tenant aware (one parent → many children across possibly multiple schools). For now, assume single-school single-deployment per existing locked decision (Phase 1 of role refactor).

**Frontend foundation:**

4. Create `templates/operations_base.html` — the unified Operations Mode shell. Variables: `role_tag`, `role_glyph`, `nav_items` (list of dicts), `scope_tags` (list of dicts), `quick_actions`, `greeting_question`.
5. Extract shared CSS to `static/css/operations_base.css` — all CSS currently inline in mockups becomes one stylesheet.
6. Create `templates/operations/` partials: `kpi_strip.html`, `worklist_panel.html`, `scope_bar.html`, `child_switcher.html` (Parent only), `context_strip.html`.

**View layer (one per role):**

7. Routing: extend `accounts/views/dashboard.py` router so each role lands on its own dashboard view. Existing Teacher / Student routing untouched.
8. One view module per role (e.g., `accounts/views/registrar_dashboard.py`, `accounts/views/it_admin_dashboard.py`). Each computes the KPIs + panel data and renders `operations_base.html` with role-specific config.
9. Replace the existing `it_admin_base.html` / `it_admin_dashboard` view with the redesigned IT Admin dashboard. Keep the existing nav targets working.

**Per-role data sources (audit before implementation):**

| Role | Data source notes |
|---|---|
| IT Admin | New: `OperationsHealthService` aggregating Django auth log, Celery introspection, Postgres `pg_stat_activity`. |
| Registrar | Audit existing `accounts/`, `course/` for enrollment and request models. |
| Academic Director | Aggregate from `gamification/` (at-risk, outcomes), `central_content/` (content health), existing `ai_content/` engagement. |
| Program Head / Principal | Existing department-scoped calendars + course/section data + TeacherGamification (read inversely). |
| Coil Admin | `coil/CoilPartnerSchool` model — already exists. New: collaborative-class concept (currently informal) — model TBD or read from existing course associations. |
| Time Keeper | NEW: `attendance/` or `dtr/` app needed. Audit if any HR/Worksy schema can be reused. |
| QA | NEW: `audit/` app — needs audit-item model, severity, source, status, owner, age. |
| Department Staff | NEW: `tasks/` app or extend `message/` for inboxed tasks. Cross-references Head's calendar. |
| Librarian | NEW: `library/` app — circulation, holds, fines, catalog. Likely a sizable build. |
| Parent / Guardian | NEW: `Guardian` model linking `CustomUser` (parent) → many `CustomUser` (children). Multi-child UI built into shell. |
| Guidance Counselor | NEW: `guidance/` app — case, session note, referral, consent. Privacy-by-design models. |

**Rollout staging:**

10. **Wave A — replace existing scaffolds:** IT Admin (existing rough scaffold) + Registrar / Academic Director / Coil Admin (no dashboards today). Lowest risk because the data sources mostly exist.
11. **Wave B — add Operations roles:** Time Keeper + QA + Librarian + Guidance Counselor + Department Staff. Each requires its own data layer; treat each as its own sub-project.
12. **Wave C — Program Head / Principal:** Largest data surface; depends on dept-scoped calendars (already merged) and TeacherGamification (already merged).
13. **Wave D — Parent / Guardian:** Multi-child UX is the unique complexity; depends on `Guardian` model and per-child data scoping.

Each Wave is its own brainstorm → spec → plan → PR cycle. This spec only locks the design; it does not commit to a build sequence beyond the recommendation above.

## 8. Out of scope

- **Implementation in code.** This spec stops at design. The writing-plans skill turns it into per-Wave plans.
- **Mobile-responsive layout.** Mockups are desktop-first; mobile breakpoints are a follow-up. Parent/Guardian especially needs mobile, since Filipino guardians often check on phones.
- **Dark theme.** Mockups are cream-background only. A dark variant would follow Student's pattern; deferred.
- **Real-time data binding via WebSockets.** Scope bars say "Live · 4:12 PM" but the actual refresh cadence (poll vs websocket) is a build decision per role.
- **i18n / Filipino translation strings.** Greeting questions and panel labels are English-only in mockups; localization is a separate spec.
- **Permission gating per panel.** Each role's nav and panels assume their permissions are present; the actual `@permission_required` wiring follows the Phase 2 pattern from the role refactor.

## 9. Open questions

1. **Counselor vs Parent iconography clash on `♥`.** Pick one alternative for Counselor (`✚` or `⚕`) before build. Recommend confirming with end users which feels right.
2. **Principal glyph choice.** `☗` is geometrically distinct from Program Head's `◆` but reads as "chess rook." Could swap for `▣` or `❖`. Pick during Wave C.
3. **Librarian `⊟` overlap with Department Staff.** Visually identical glyph for two unrelated roles; needs differentiation. Suggest Librarian → `⊞` (grid, 4-quadrant) or actual book emoji `📚` if the system font supports it consistently.
4. **Coil Admin's "collaborative classes" panel.** The existing `CoilPartnerSchool` model has no class-level association. Either extend the model (preferred — add `CoilCollaborativeClass`) or stub the panel as future-state. Decide before Wave A's Coil dashboard ships.
5. **Time Keeper data source.** No DTR / attendance app exists in `~/classedge`. Audit `~/worksy` (HRMS) for reusable schema before building from scratch.
6. **Guidance Counselor data privacy at the model layer.** Privacy notice in UI is necessary but insufficient. Models for case / session-note / consent need row-level security, not just template-level visibility. Worth a sub-spec.

## 10. Mockup file map (reference)

All mockups live at `~/classedge/.superpowers/brainstorm/53594-1777073650/content/`:

| File | Roles |
|---|---|
| `welcome.html` | Scope intro + family lineup |
| `layout-system.html` | Three layout-shell options (A / B / C); B "Operations Mode" picked |
| `wave-1-deep-dives.html` | Academic Director · Program Head/Principal · Guidance Counselor |
| `wave-2-admin-ops.html` | IT Admin · Registrar · QA |
| `wave-3-specialist.html` | Coil Admin (revised post-feedback) · Time Keeper · Librarian |
| `wave-4-support-facing.html` | Department Staff/Secretary · Parent/Guardian |

Mockups persist in `.superpowers/brainstorm/` for reference during implementation. Files are static HTML/CSS — do not consume Classedge runtime resources.

## 11. Brainstorm trail

- 2026-04-25 — Brainstorm session: confirmed 12 roles in scope, locked Operations Mode shell, agreed Pareto deep-dive approach (3 deep + 8 template), validated all 4 mockup waves, refined Coil Admin to match existing `CoilPartnerSchool` model and "department" framing per user feedback.
- Working style established: tight iteration loop, minimal back-and-forth, batched data briefs over per-role debate.
