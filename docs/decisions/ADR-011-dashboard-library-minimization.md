# ADR-011: Dashboard Library Minimization

- **Status:** Accepted
- **Date:** 2026-04-29
- **Supersedes:** None (refines the implicit stack pinned in ADR-006)
- **Superseded by:** None

## 1. Context

After a five-agent dashboard v2 build (branding, header + active-calls indicator, date filter, KPI cards with deltas, drill-through), the Next.js dashboard had picked up five new runtime dependencies on top of the React 19 + Next 15 + Tailwind 4 + shadcn/Radix + Recharts baseline:

- `nuqs` — typed URL state for filter params (~5 KB gz)
- `@tremor/react` — `BadgeDelta` + `SparkAreaChart` on KPI cards (~10 KB gz)
- `react-day-picker` — calendar control inside the date-range picker (~25 KB gz)
- `date-fns` — date arithmetic helpers used by the date filter (~10 KB gz)
- `@radix-ui/react-popover` — popover wrapper for the calendar (~12 KB gz)

The user pushed back twice (verbatim: *"mantain dashboard simple clen why so many libreries"* and *"If dashboard is using many complex libraries simplify"*). To make the call evidence-driven rather than vibe-driven, a self-contained visual A/B mockup was generated at `dashboard/library-cut-comparison.html` (27 KB, no JS dependencies) showing each library against its vanilla replacement.

The mockup confirmed: the visible difference between Tremor `BadgeDelta` and a custom `<span>` + Lucide icon is roughly 5%; Tremor `SparkAreaChart` is literally a thin wrapper over Recharts and renders identically; `nuqs` is a developer-ergonomics lib with zero user-visible footprint; `date-fns` is invisible (no UI surface); the only meaningful loss is the shadcn Calendar two-month grid + range highlight + dark polish, swappable for native `<input type="date">` at a 37 KB savings.

## 2. Decision

**Cut all five libraries. Replace with vanilla equivalents (Option Y, full minimalism).**

| Library cut | Bundle save (gz) | Replaced with |
|---|---|---|
| `nuqs` | ~5 KB | `useSearchParams` + `useRouter` + `usePathname` (Next 15 native) |
| `@tremor/react` | ~10 KB | Custom `<span>` with Lucide `TrendingUp`/`TrendingDown` icons + bare Recharts `<AreaChart>` in `<ResponsiveContainer>` |
| `react-day-picker` | ~25 KB | Two paired `<input type="date">` elements inside a hand-rolled dropdown |
| `date-fns` | ~10 KB | Inline native `Date` helpers (`subDays`, `startOfDay`, `endOfDay`, `subWeeks`, `subMonths`, `subYears`) — ~25 LOC total |
| `@radix-ui/react-popover` | ~12 KB | Custom dropdown div with `useState` + click-outside `useEffect` (~30 LOC) |

**Total savings: ~62 KB gz.** The remaining frontend stack is React 19, Next 15 App Router, Tailwind 4, the Radix primitives shadcn already wraps for Tooltip / Tabs / Select / Separator / Slot, Recharts (used directly), `lucide-react`, `server-only`, and the shadcn-standard `class-variance-authority` + `clsx` + `tailwind-merge` trio.

## 3. Rationale

- **Visual cost confirmed minimal via the A/B mockup.** Every cut except the calendar is essentially indistinguishable from its replacement; the calendar is the only judgment call and the user took it.
- **Bundle is leaner and the mental model simpler.** Five fewer libraries to track for security advisories, version bumps, and React 18→19 peer-dep dances.
- **One fewer paragraph in the broker-facing architecture doc.** "Why Tremor when we already have Recharts?" is a question the doc no longer has to answer.
- **Reflects user's repeated explicit direction.** Lean design is a recorded preference (`feedback_lean_design.md`) and the user named it twice in the same session.
- **No functionality lost that affects the take-home demo.** Every metric, every chart, every drill-through, and every filter still works.
- **Native HTML primitives are accessibility-stable by default.** `<input type="date">` ships with screen-reader and keyboard support; the hand-rolled dropdown is small enough to audit by eye.

## 4. Consequences

### Positive
- ~62 KB gz off the JavaScript bundle; faster first paint on cold loads.
- One peer-dep matrix to think about (React 19) instead of five.
- Hand-rolled date dropdown and dropdown-popover are small enough to fully understand in a single sitting.

### Negative
- Date-range picker UI is more utilitarian than a Power BI / shadcn Calendar experience — native browser date input chrome is OS-themed and varies (Chrome / Safari / Firefox each render slightly differently).
- Lost Tremor's tiny chip mount-animation (color fades in on render). Practically invisible; called out for completeness.
- `SparkAreaChart`'s animated render becomes a static area path. Also practically invisible.

### Neutral
- If a future customer demo flags the calendar polish as "not premium enough," `react-day-picker` + `@radix-ui/react-popover` can be swapped back at the cost of ~37 KB. **Do not also re-add Tremor or nuqs in that swap** — they are independent calls.
- The hand-rolled click-outside hook becomes a vector for subtle bugs (focus-trap edge cases, multi-dropdown stacking). Keep the dropdown count low.

## 5. Alternatives considered

**Option Z' — cut just `nuqs` + Tremor; keep the calendar.** Saves ~15 KB while preserving the two-month-grid date picker polish. Runner-up. Rejected because the mockup showed `<input type="date">` is functionally adequate and the user chose full minimalism.

**Option K — ship as-is.** Zero work but accepts ~62 KB of library bloat for marginal visual gain. Rejected as drift away from the recorded lean-design preference.

**Re-introduce a CSS-only date range slider.** Considered briefly — would have been the most native option but loses the calendar metaphor users expect. Skipped.

## 6. References

- `dashboard/library-cut-comparison.html` — visual A/B mockup (27 KB self-contained HTML, no external deps).
- User direction in conversation 2026-04-29: *"mantain dashboard simple clen why so many libreries"* and *"If dashboard is using many complex libraries simplify"*.
- Memory: `feedback_lean_design.md` — minimal-design preference.
- Memory: `project_dashboard_v2_locked_option_b.md` — earlier Option B (kept Tremor + nuqs); superseded by this ADR. The memory file has been rewritten to reflect Option Y.
- ADR-006: Next.js dashboard commit (precursor — this ADR refines the dependency footprint pinned implicitly there).
