# Section 4: Artifact Health

Reads from: `data.sections.artifact_health`. No computation. Section header:
`ARTIFACT HEALTH · [DATE RANGE]`.

---

## Data Source Map

| Rendered element | Response path |
|---|---|
| Size bar chart | `artifact_health.artifact_size_per_profile[]` → `{profile, current_avg_size_mb, prev_avg_size_mb, delta_mb, delta_pct}` |
| Biggest grower card | `artifact_health.biggest_grower` → `{profile, current_avg_size_mb, prev_avg_size_mb, delta_mb, delta_pct}` (or `null`) |
| Biggest shrinker card | `artifact_health.biggest_shrinker` → same shape (or `null`) |

Reading notes:
- Sizes are already in MB. `current_avg_size_mb` always present for listed profiles;
  `prev_avg_size_mb`, `delta_mb`, `delta_pct` are `null` when there is no
  previous-period baseline for that profile (render the bar, skip the delta).
- `artifact_size_per_profile` is already sorted by `current_avg_size_mb` descending.
- `biggest_grower` / `biggest_shrinker` are pre-selected and may be `null` (no change,
  or no baseline). A `null` card is simply not rendered.

---

## Render: Artifact Health Widget

### Artifact size per profile (horizontal bar chart)

Card. Title: "Artifact size per profile". Subtitle: "Average primary artifact size ·
top profiles by size."

Per profile row (from `artifact_size_per_profile`, in given order):
- Profile name (bold 13px).
- Horizontal bar: navy `#1A3352` fill on `var(--color-background-secondary)` track,
  8px tall. Width = `current_avg_size_mb / max(current_avg_size_mb) * 100%`.
- Size value right-aligned: `XX.X MB` (one decimal). No labels on the bars.

### Biggest grower / biggest shrinker (side by side, below the bar chart)

Two cards side by side (or one, or none, depending on which are non-null).

**Biggest grower** (render only if `biggest_grower` is non-null):
- Left accent `#DC2626` (red).
- Label "Biggest grower"; profile name bold 16px.
- Change: `▲ +X.X MB` red bold (from `delta_mb`).
- Sub-label: `XX.X MB to XX.X MB` muted 12px (`prev_avg_size_mb` → `current_avg_size_mb`).

**Biggest shrinker** (render only if `biggest_shrinker` is non-null):
- Left accent `#16A34A` (green).
- Label "Biggest shrinker"; profile name bold 16px.
- Change: `▼ -X.X MB` green bold (absolute value of `delta_mb`).
- Sub-label: `XX.X MB to XX.X MB` muted 12px.

If both are null (no baseline, or all profiles stable), omit both cards and render
only the bar chart.
