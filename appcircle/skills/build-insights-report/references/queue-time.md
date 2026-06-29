# Section 5: Queue Time

Reads from: `data.sections.queue_time`. No computation. Section header:
`QUEUE TIME · [DATE RANGE]`. This section aggregates how long builds waited in
queue before starting (always tree-wide, regardless of `include_sub_orgs`).

---

## Data Source Map

| Rendered element | Response path |
|---|---|
| Stat cells | `queue_time.{total_wait_minutes, avg_wait_minutes, p50_wait_minutes, p95_wait_minutes, build_count}` |
| Daily trend chart | `queue_time.daily_trend[]` → `{date, avg_wait_minutes}` |

Reading notes:
- All wait values are minutes. Render `Xm` if < 60, else `X.Xh`.
- `build_count` is the number of builds that contributed wait data — show it as
  context, not as a primary metric.
- `daily_trend` contains only days that had queued builds (it is sparse, not a full
  calendar). Plot the points as given; do not back-fill missing days.
- The section is omitted entirely (listed in `meta.omitted_sections`) when no queue
  waiting data is available for the period — in that case render nothing.

---

## Render: Queue Time Widget

Section header: `QUEUE TIME · [DATE RANGE]`. Uses the Global Design System.

### Stat cells

A row of four cells, same card style as the Health Snapshot summary cards (muted
uppercase label, large bold value), top accent `#1A3352` (navy) 3px:
- **Avg wait** → `avg_wait_minutes`
- **P50 wait** → `p50_wait_minutes`
- **P95 wait** → `p95_wait_minutes`
- **Total wait** → `total_wait_minutes`

Below the row, a muted 12px caption: "Across N builds with queue data" (from
`build_count`).

Colour the P95 value by band so a long tail is visible at a glance: green if
`p95_wait_minutes` ≤ 5, amber if ≤ 15, red if > 15 (minutes).

### Daily trend chart

Only render if `daily_trend` has at least two points. Type: line, single dataset of
`avg_wait_minutes` against `date`, navy `#1A3352`, point radius 3px, tension 0.3,
`spanGaps: true` (the series is sparse by design). Y-axis label minutes (e.g. `2m`).
Subtitle: "Average queue wait per day." Canvas height 180px. Same Chart.js setup and
technical requirements as the Trends section (single `DOMContentLoaded`, grid
`rgba(0,0,0,0.06)`, ticks `#9CA3AF` 10px, `maintainAspectRatio: false`).

If `daily_trend` has fewer than two points, skip the chart and keep just the stat
cells with the caption.

---

## Recommendation card

When queue wait is long or trending up, render a recommendation box below the
chart, styled to match Appcircle's in-product upgrade nudge: a light orange card
(`.rec`) with an uppercase "RECOMMENDATION" label, a bold navy headline, body
copy explaining the situation, and one or two pill-outline buttons.

`render.py` builds this from `_queue_recommendation(qt)`:

- **Trigger.** Shows when `p95_wait_minutes >= 3`, or when the trend is climbing
  and P95 is at least 1.5 minutes. Otherwise queue health is fine and no card
  renders — this is not a permanent fixture of the section.
- **Trend.** Computed from `daily_trend`: compares the first and last point.
  >25% increase → "climbing" (most urgent headline, "...your current capacity
  may not keep up"); >25% decrease → "improving"; otherwise "stable". Fewer than
  two points → "insufficient" (no trend claim made, headline stays neutral).
- **Plan-aware copy.** Appcircle's machine plans, lowest to highest, are
  Standard → Velocity → Ultra (`PLAN_ORDER` / `NEXT_PLAN` in `render.py`). The tool
  attributes queue wait to each tier via `queue_time.plan_breakdown`, e.g.
  `{"standard_wait_minutes": 6.0, "velocity_wait_minutes": 0.0,
  "ultra_wait_minutes": 0.0}`. `_plan_from_breakdown()` picks the tier that
  absorbed the most wait this period (the one an upgrade would help most) and
  flags whether more than one tier saw real activity. The card then names that
  tier and the next one up ("Upgrade to {next plan}"); if more than one tier was
  active it reads "Most of your queue wait..." rather than implying it's the
  org's only tier. Already on Ultra → only the "Increase concurrency" button
  shows, since there's no higher tier to suggest. A flat `queue_time.plan`
  string, if the tool ever adds one directly, is checked first and used as-is —
  the breakdown is the fallback, not the other way around. With neither field,
  the card still renders with plan-agnostic copy ("upgrading your machine
  plan") and a generic "View plans" button.
- **Breakdown caption.** Whenever `plan_breakdown` is present, a small caption
  under the build-count line shows the raw split, e.g. "By plan: Standard 6m ·
  Velocity 0m · Ultra 0m" — so the inference behind the recommendation is
  visible, not just asserted.
- **Buttons.** "Increase concurrency" links to `https://appcircle.io/contact`.
  The second button (upgrade / "View plans") also links to `https://appcircle.io/contact`.

If the tool's `plan_breakdown` keys or shape change, update `_BREAKDOWN_KEYS` and
`_plan_from_breakdown()` in `render.py` (and this table) to match.
