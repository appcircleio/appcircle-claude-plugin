# Section 1: Health Snapshot + Trends

Reads from: `data.sections.health_snapshot`. No computation — every value below is
read directly from the response. Section headers: `HEALTH SNAPSHOT · [DATE RANGE]`
and `TRENDS · [DATE RANGE]` (date range from `data.date_range`).

---

## Data Source Map

| Rendered element | Response path |
|---|---|
| Summary cards (current) | `health_snapshot.summary.current.{total, success, failed, canceled, success_rate, failure_rate, canceled_rate}` |
| Summary deltas | `health_snapshot.summary.delta.{total_pct, success_rate_pp, failure_rate_pp, canceled_rate_pp}` |
| Previous-period values (muted captions) | `health_snapshot.summary.previous.{...}` |
| Top active profiles | `health_snapshot.top_active_profiles[]` → `{profile, build_count, success_rate}` |
| Inactive profiles | `health_snapshot.inactive_profiles[]` → `{profile, last_build_date}` |
| Top build activity | `health_snapshot.top_build_activity[]` → `{profile, branch, build_count}` |
| Manual triggers | `health_snapshot.top_triggers.manual[]` → `{initiated_by, build_count}` |
| Automated triggers | `health_snapshot.top_triggers.automated[]` → `{initiated_by, build_count}` |
| Daily series (charts 1 & 2) | `health_snapshot.trends.daily_series[]` → `{date, total, success, failed, canceled, timeout, pass_rate, fail_rate}` |
| Per-profile duration table | `health_snapshot.trends.per_profile_duration[]` → `{profile, p50, p95, ratio, consistency, trend}` |
| Per-profile duration chart (chart 3) | `health_snapshot.trends.per_profile_duration_series[]` → `{profile, series:[{date, p50}]}` |

Notes on reading the data:
- `success_rate` / `failure_rate` / `canceled_rate` are percentages (0–100). Round
  to whole numbers for the big card values.
- Deltas: `total_pct` is a percentage change (render `▲/▼ X%`, neutral grey).
  The `*_pp` deltas are percentage points (render `▲/▼ X.Xpp`).
- `last_build_date` is whatever the tool returns (it reflects the profile's most
  recent build, which can fall outside the report window). Render it as a date; if
  `null`, show "No recent builds found."
- `per_profile_duration` values (`p50`, `p95`) are already in minutes. `consistency`
  is one of `consistent` / `moderate` / `high variance`; `trend` is `faster` /
  `stable` / `slower`.
- In `per_profile_duration_series`, days with no value carry `p50: null` — plot with
  `spanGaps: false`, do not interpolate.

---

## Render: Health Snapshot Widget

Section header: `HEALTH SNAPSHOT · [DATE RANGE]`. Uses Global Design System and
Global Copy Rules from the router.

### Layout

```
┌────────────┬────────────┬────────────┬────────────┐
│ Total      │ Success    │ Failed     │ Canceled/  │
│ builds     │ rate       │ builds     │ Timeout    │
│ 61         │ 70%        │ 15         │ 3          │
│ ▲56% prev  │ ▲24.3pp    │ ▼11% prev  │ ▼ prev     │
└────────────┴────────────┴────────────┴────────────┘

Top active profiles            [date range]
Profile        Builds  Success rate
① RN0780       17      88%
...

Inactive profiles
Profiles with no builds in the last 30 days — may need cleanup or archiving
ProfileName     Last build: May 27, 2025
...

Top build activity             [date range]
Profile · Branch               Builds
iOS-hello_world-default  main  9
...

Top manual triggers     |  Top automated triggers
Initiated by   Builds   |  Initiated by   Builds
nur@...        61       |  (none this period)

● AI SUMMARY
[2–3 sentence narrative authored from the values above]
```

### Summary card design

4 cards in a row. Each card: muted uppercase label (13px), large bold value, delta
badge below.
- Total builds delta: neutral (grey) pill, from `delta.total_pct`.
- Success rate: green if `▲`, red if `▼`, from `delta.success_rate_pp`.
- Failed: green if `▼` (fewer failures is good), red if `▲`, from `delta.failure_rate_pp`.
- Canceled/Timeout: same direction logic as failed, from `delta.canceled_rate_pp`.

Delta format for rates: `▲ 24.3pp` / `▼ 11.3pp`. Delta format for counts: `▲ 56%`.
Top accent border on each card: `#FF8F34`, 3px.

### Top active profiles table

Navy numbered circles (①②③④⑤) for rank. Columns: Profile · Builds · Success rate.
Success rate is coloured percentage text only — green if ≥80%, amber if 60–79%, red
if <60%. No mini bar. Date range label top-right.

### Inactive profiles

Simple card, no rank. Each row: profile name (left) + `Last build: [date]` (right,
muted). Subtitle: "Profiles with no builds in the last 30 days — may need cleanup or
archiving." Omit this card entirely if `inactive_profiles` is empty or absent
(also see `meta.omitted_subsections`). The list can be long; cap the rendered rows
at 12 and append a muted "+N more" line.

### Top build activity table

Profile name bold + branch name in monospace style, muted. Build count right-aligned.
No mini bars. Source rows are already ranked; render in given order.

### Top manual / automated triggers

Two cards side by side. Each: sub-label ("Top manual triggers" / "Top automated
triggers"), subtitle below, then rows of `initiated_by · count` right-aligned. Show
full email if short; truncate at 28 chars with `…` if long. If a list is empty,
show a single muted line "(none this period)" rather than an empty card.

### AI Summary

Full-width card, left border `4px solid #FF8F34`, background `#FFF8F3`. Label
`● AI SUMMARY` in orange uppercase 11px. Text below in 13px `#374151`. Cover:
overall volume and success-rate signal (healthy or not), the single most notable
finding (dominant failing profile, recovery, spike), and one concrete observation.

---

## Render: Trends Widget

Section header: `TRENDS · [DATE RANGE]`. Rendered immediately after Health Snapshot
when both are in scope. Load Chart.js from
`https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js`.

All chart data is read straight from the response arrays and embedded as JS literals.
The `daily_series` array already contains a complete day-by-day sequence with zero
days filled — use it as-is for the X-axis labels; do not regenerate dates.

### Chart 1: Pass rate & fail rate

Type: line. Two datasets from `daily_series`: pass rate `#16A34A`, fail rate
`#DC2626`, both solid 2px. Y-axis 0–100% labelled `%`. X-axis: `date`. Legend with
green/red swatches. Canvas height 180px.

### Chart 2: Build volume

Type: bar, stacked. Four datasets from `daily_series`: success `#16A34A`, failed
`#DC2626`, canceled `#FF8F34`, timeout `#7C3AED`. Canvas height 180px. Legend below.

### Chart 3: Build duration per profile

Rendered BEFORE the duration table. Type: line, one dataset per entry in
`per_profile_duration_series`, in array order, using the fixed chart palette. Each
dataset plots `series[].p50` against `series[].date`, `spanGaps: false`, point
radius 3px, tension 0.3. Y-axis label minutes (e.g. `4m`). Legend: profile names
with colour swatches. Subtitle: "How each profile's median build time (P50) has
changed over the period." Canvas height 200px.

If every point across all series is null (no day had two or more successful builds
for any profile), skip this chart entirely and show a muted note in its place
("The per-day duration chart needs at least 2 successful builds on the same day to
plot a median..."); still render the duration table below, which uses the
already-aggregated `per_profile_duration` values. `render.py` does this
automatically.

### Per-profile duration table

Rendered AFTER the duration chart. Columns: Profile · P50 · P95 · P95/P50 · Trend ·
Consistency — read directly from `per_profile_duration` (`p50`, `p95`, `ratio`,
`trend`, `consistency`). P50/P95 shown as `X.Xm`. Date range top-right, subtitle
"P50, P95, and consistency for each active profile."

Trend pill: `faster` → pill good, `stable` → pill neutral, `slower` → pill bad.
Consistency pill: `consistent` → pill good, `moderate` → pill warn, `high variance`
→ pill bad.

### Chart technical requirements

All charts initialized in a single `DOMContentLoaded` listener. Grid lines
`rgba(0,0,0,0.06)`, tick colour `#9CA3AF`, font 10px. `maxTicksLimit: 7` on the
X-axis. `maintainAspectRatio: false` on all charts.
