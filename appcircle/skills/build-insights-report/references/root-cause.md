# Section 2: Root Cause

Reads from: `data.sections.root_cause`. No computation. Section header:
`ROOT CAUSE · [DATE RANGE]`.

---

## Data Source Map

| Rendered element | Response path |
|---|---|
| Top failing steps | `root_cause.top_failing_steps[]` → `{step, count, pct_of_failed, top_combos:[{profile, branch, count}]}` |
| MTTR card | `root_cause.mttr[]` → `{profile, branch, avg_hours, sequence_count}` |
| Flaky builds card | `root_cause.flaky[]` → `{profile, branch, flaky_commit_count, wasted_minutes}` |
| Warning hotspots card | `root_cause.warning_hotspots[]` → `{profile, branch, warned_count, top_warning_step}` |
| Zero-success workflows card | `root_cause.zero_success_workflows[]` → `{profile, workflow, run_count, always_failing_step}` |

Reading notes:
- `pct_of_failed` is a percentage (0–100). `top_combos` is already ranked, top first.
- `avg_hours` is hours: render `Xm` if < 1h, else `X.Xh`.
- `wasted_minutes` is minutes: render `Xm` if < 60, else `X.Xh`.
- Each array is already ranked by the tool. Render in given order; the insight cards
  show the top 3 rows each.
- These arrays may be empty even when the section is present (e.g. no flaky builds in
  a clean period). Empty array → render that card's empty-state line, not an omission.

---

## Render: Root Cause Widget

### Top failing steps layout

One full-width card block. Header: "Top failing steps". Subtitle: "Steps most
responsible for build failures, with the top affected profile and branch
combinations".

**Per step row** (one per entry in `top_failing_steps`):
```
Step name                    [████████████░░░░░░░░]  10   67%
  [profileA  branch  4]  [profileB  branch  3]  ...
```
- Step name: 13px, `#111827`, weight 500.
- Horizontal bar: orange `#FF8F34` fill on `#F3F4F6` track, 8px tall, radius 4px.
  Width = `count / max(count across steps) * 100%`.
- `count` right-aligned bold; `pct_of_failed` right-aligned muted `#6B7280`.
- `top_combos` rendered as pills below the bar:
  `background:#FFF3E8; border:1px solid #FFD4A3; border-radius:99px; padding:2px 8px;
  font-size:11px; color:#92400E`. Each pill: "profile  branch  N" with branch in
  monospace. N = that combo's `count`.
- Divider line between steps.

### Four insight cards layout

2×2 grid below the step block. Card style: white card, 0.5px border
`var(--color-border-tertiary)`, radius `var(--border-radius-lg)`, padding 16px.

Left accent bar per card (3px, no radius on the bar):
- MTTR → `#FF8F34` (orange)
- Flaky builds → `#1A3352` (navy)
- Warning hotspots → `#FF8F34` (orange)
- Zero success workflows → `#DC2626` (red)

Each card: title (14px, weight 500) + subtitle (12px muted) + rows.

- **MTTR rows** (from `mttr`, top 3 by `avg_hours`, longest first): profile bold ·
  branch monospace muted · MTTR value right-aligned bold · `"avg across N sequences"`
  (from `sequence_count`) in muted 11px below.
- **Flaky rows** (from `flaky`, top 3 by `wasted_minutes`): profile bold · branch
  monospace · `flaky_commit_count` commits · wasted time right-aligned bold.
- **Warning hotspot rows** (from `warning_hotspots`, top 3 by `warned_count`): profile
  bold · branch monospace · `warned_count` right-aligned · `top_warning_step` in
  muted 11px below.
- **Zero success rows** (from `zero_success_workflows`, top 3 by `run_count`): profile
  bold · `workflow` muted below · `run_count` right-aligned · `always_failing_step`
  in muted 11px.

If a card's source array is empty, show one muted line instead of an empty card:
"No [flaky builds / warning hotspots / zero success workflows / recovery sequences]
detected this period." This per-card empty state is normal whenever the section is
present; only the absence of the whole `root_cause` key (or its listing in
`meta.omitted_sections`) means skip the entire section.
