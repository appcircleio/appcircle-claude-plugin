---
name: build-insights-report
description: >
  Render a visual Build Insights Report for an Appcircle workspace from the
  get_build_insights_report MCP tool. Use this skill whenever the user asks for
  build insights, build analytics, CI health reports, CI maturity, build trends,
  build metrics, build performance, failure analysis, queue time, or anything
  related to summarizing or visualizing build history data. Also trigger when the
  user mentions "build report", "build stats", "how are our builds doing", "build
  success rate", "build times", "maturity assessment", "queue time", or asks to
  compare builds across time periods. Always use this skill — even if the request
  is brief (e.g. "give me a build report" or "build insights for last month") —
  because this skill owns the presentation layer: it calls the single
  get_build_insights_report tool and renders the returned sections as widgets.
version: 0.1.0
---

# Build Insights Report Skill — Render Router

This skill is the **presentation layer**. All fetching, metric computation,
percentile/MTTR/flaky math, and scoring now happen **server-side inside the
`get_build_insights_report` MCP tool**, which returns a small pre-aggregated
JSON envelope. This skill makes **one** tool call and renders each returned
section. It does not fetch raw build history, does not page, and does not compute
metrics — if a number isn't in the tool response, it isn't shown.

The skill is a thin always-loaded router (this file) plus per-section reference
files under `references/`, opened only when that section is actually rendered.
**Only load the section files relevant to what the person asked for.** A request
for "just root cause" loads this router plus `references/root-cause.md` — nothing
else.

Available sections (each maps to one key under `data.sections` in the response):

| # | Name | Response key | File |
|---|------|--------------|------|
| 0 | Maturity Assessment | `maturity_assessment` | `references/maturity-assessment.md` |
| 1 | Health Snapshot + Trends | `health_snapshot` | `references/health-snapshot-trends.md` |
| 2 | Root Cause | `root_cause` | `references/root-cause.md` |
| 3 | Workflow Quality | `workflow_quality` | `references/workflow-quality.md` |
| 4 | Artifact Health | `artifact_health` | `references/artifact-health.md` |
| 5 | Queue Time | `queue_time` | `references/queue-time.md` |

"A build report" / "build insights" / "how are builds doing" with no qualifier
means the FULL report: render all six sections in the order above. If the person
names specific sections, render only those. If unclear which they mean, ask rather
than defaulting to the full report.

There is no cross-section dependency. The tool returns `discipline.wf_completeness_score`
and `discipline.bp_score` pre-computed, so Maturity Assessment can be rendered
entirely on its own.

---

## The One Tool Call

Make a single call to `get_build_insights_report` (in the user's Appcircle MCP
namespace, e.g. `appcircle-prod`). Resolve the date range and the `sections` list
from the request, then render.

| Param | How to set it |
|-------|---------------|
| `start_date`, `end_date` | `"YYYY-MM-DD"`. Resolved per Time Range Rules below. Omit both for the default last-30-days window. |
| `sections` | The list matching the requested sections (response keys above). **Omit entirely for a full report** — the tool defaults to all six. Passing a subset is what keeps a single-section request cheap. |
| `include_sub_orgs` | `true` only if the person explicitly wants cross-org build records folded into history-derived metrics. Default `false`. |

Request-to-`sections` mapping:

| Person asks for | `sections` value |
|---|---|
| full report / "build insights" / unqualified | *(omit — defaults to all six)* |
| health snapshot **or** trends | `["health_snapshot"]` (trends live under `health_snapshot.trends`) |
| root cause / failure analysis | `["root_cause"]` |
| maturity / CI maturity / maturity score | `["maturity_assessment"]` |
| workflow quality / workflow completeness | `["workflow_quality"]` |
| artifact health / artifact size | `["artifact_health"]` |
| queue time / wait time | `["queue_time"]` |

**Reuse, don't re-call.** If a `get_build_insights_report` response for the
requested window and sections is already present in the conversation (the person
pasted it, or it was fetched earlier this turn), render from it directly instead
of calling again.

### Envelope

```
{ "success": true,
  "data": {
    "date_range": { current_start, current_end, previous_start, previous_end },
    "sections": { health_snapshot?, root_cause?, artifact_health?,
                  workflow_quality?, queue_time?, maturity_assessment? } },
  "meta": { requested_sections, omitted_sections, omitted_subsections,
            failed_fetches, cross_org_builds_excluded, unresolved_profiles } }
```

If `success` is `false`, show the `error.message` plainly and stop — do not
fabricate a report. Use `data.date_range` for every section's `[DATE RANGE]`
header label (format as e.g. `May 1 – May 31, 2025`).

---

## Omission & Partial-Data Handling — Driven by `meta`

The tool already decides what can and cannot be computed and reports it. This skill
does **not** re-derive that; it trusts `meta` and the presence of section keys.

1. **Section absent** — if a requested section key is missing from `data.sections`,
   or is listed in `meta.omitted_sections`, do not render it. Render nothing in its
   place (no empty card, no zeros, no placeholder).
2. **Subsection absent** — `meta.omitted_subsections` lists parts dropped within a
   section that was otherwise computed (e.g. a single card). Skip just that card;
   render the rest of the section normally.
3. **Empty-but-present** — a section key that is present with genuinely empty arrays
   is a real result (e.g. zero failures in a clean period). Render it per that
   section's empty-state rules, not as an omission.
4. **Closing note** — if `meta.omitted_sections` is non-empty, add one plain line
   after the last rendered section: "Note: N section(s) could not be generated from
   the available data for this period." No elaboration, no speculation about roles
   or permissions. Skip the line entirely if nothing was omitted.
5. **`meta.failed_fetches`** is diagnostic only — do not surface it in the rendered
   report. `meta.cross_org_builds_excluded` and `meta.unresolved_profiles` are
   likewise not rendered unless the person asks about scope.

The tool never returns fabricated zeros for missing data, so the skill never has to
guess whether a zero is real. A present number is real; an absent section is absent.

---

## Rendering — use the bundled renderer, do not hand-author HTML

This skill ships `render.py`, which contains the entire design system and one
render function per section. It is the canonical renderer. Hand-writing report
HTML token by token is exactly the cost this skill exists to avoid, so the default
path is: get the response onto disk, run the script, present the file. The
per-section reference files are the human-readable spec that `render.py`
implements (and the fallback for the widget path below) — they are not a license
to re-type the HTML each time.

### Primary path (any environment with code execution — Claude Code, Cowork, analysis tool)

1. Write the **full** `get_build_insights_report` envelope (the entire
   `{success, data, meta}` object) to a JSON file, e.g. `response.json`.
2. Run `python render.py response.json report.html` from the skill directory.
   The script selects sections from `data.sections`, honors
   `meta.omitted_sections`, renders in canonical order (maturity, health + trends,
   root cause, workflow quality, artifact health, queue time), embeds Chart.js
   from cdnjs for the chart sections, and appends the omission note when needed.
3. Present `report.html` (an existing `reports/`/`output/` folder if present, else
   the current directory). One `present_files` call, no postamble.

The renderer takes the response exactly as the tool returns it — including the
full daily series and the complete inactive-profile list — and does the trimming
at render time (inactive list capped at 12 with a "+N more" line, all-null
duration series replaced with a note instead of an empty chart). No pre-processing
of the payload is required or wanted.

### Widget fallback (chat surface, only when the person wants it inline)

`render.py` produces a downloadable file, which for a build report is usually the
better artifact (shareable, exportable). Only when the person specifically wants
the report rendered inline in chat, and `visualize:show_widget` is available, fall
back to rendering each section as a `show_widget` call built from that section's
reference file (call `visualize:read_me` once, modules `mockup` for the card
sections and `chart` for trends/queue). This path costs more tokens per report —
prefer the file unless inline is explicitly requested.

If neither code execution nor `show_widget` is available, write the HTML by hand
from the reference files as a last resort.

If the `get_build_insights_report` tool itself is unavailable, say so plainly and
stop — don't fabricate data or ask the person to paste raw build history.

---

## Time Range Rules

These resolve `start_date`/`end_date` for the tool call. The tool fills the
previous-period comparison window itself, so only the current window is set here.

"Last month" → previous calendar month. "Last 30 days" → today minus 30. No range
specified → omit both params (tool defaults to last 30 days vs the 30 days before).
Any specific window the person names (a week, a custom range, a quarter) is passed
through exactly. The inactivity window for the inactive-profiles card is computed
server-side; this skill does not set or adjust it.

---

## Global Design System

Used by every section's render step — defined once here, not repeated per section.

```
Background:         #F5F7FA
Card background:    #FFFFFF
Card border:        1px solid #E8EAED
Card radius:        8px

Brand orange:       #FF8F34
Brand navy:         #1A3352
Text primary:       #111827
Text secondary:     #6B7280
Text muted label:   uppercase, 11px, #6B7280, letter-spacing 0.5px

Pill good:          background #F0FDF4, color #16A34A, border #BBF7D0
Pill warn:          background #FFF7ED, color #D97706, border #FED7AA
Pill bad:           background #FEF2F2, color #DC2626, border #FECACA
Pill neutral:       background #F3F4F6, color #6B7280, border #E5E7EB

Push badge:         background #FFF0E0, color #FF8F34, border 0.5px #FF8F34
PR badge:           background #E6EEF5, color #1A3352, border 0.5px #1A3352

Left accent bar critical: 3px solid #DC2626
Left accent bar advisory: 3px solid #FF8F34
Left accent bar neutral:  3px solid #9CA3AF

Profile pill: background #F3F4F6, border 1px #E5E7EB, border-radius 99px,
              padding 3px 10px, font-size 12px, color #374151

Chart palette (per-profile, fixed order): ['#FF8F34','#1A3352','#16A34A','#7C3AED','#DC2626']
```

The report supports **dark mode** via `prefers-color-scheme: dark`. All colors are
defined as CSS custom properties in `:root`; `render.py` emits a `@media` block
that overrides them. Chart.js grid and tick colors are resolved at runtime via
`getComputedStyle` so they adapt automatically. Reference files refer to tokens by
name (e.g. "pill good", "left accent bar critical") rather than restating hex
values.

---

## Global Copy and Behavior Rules

Apply across every section:

1. **Never expose raw response keys or internal identifiers** in rendered output
   (`buildStatus`, `triggerCategory`, `factor_score`, `os`, check identifiers like
   `pr_workflow_not_configured`, `appcircle_*` component types). Map them to the
   human-readable labels each section file defines.
2. **No em dashes** anywhere in generated copy.
3. **"Push" not "Commit"** for trigger labels.
4. **No colored row backgrounds** — left accent bars only.
5. **Durations and sizes are already converted** in the response (minutes for build
   and queue time, MB for artifacts). Render them as given; do not re-divide.
6. **AI narrative is authored at render time** from the returned numbers — the tool
   returns data, not prose. Where a section calls for an "AI Summary" or "AI
   Insight", write it from that section's values. Keep it plain and direct, no
   jargon, no internal field names.
7. Do not automatically offer to export after rendering. Wait for the next
   instruction.

---

## After Rendering

Wait for the person's next instruction — don't proactively offer to export,
continue to another section, or summarize what was just shown unless they ask.
