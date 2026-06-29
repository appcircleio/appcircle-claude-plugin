# Section 0: Maturity Assessment

Reads from: `data.sections.maturity_assessment`. No computation and **no
dependency on any other section** — the tool returns Reliability, Discipline,
Speed, and Security already scored, plus the overall score and label. Section
header: `MATURITY ASSESSMENT · [DATE RANGE]`.

---

## Data Source Map

| Rendered element | Response path |
|---|---|
| Overall score + label | `maturity_assessment.{overall_score, label}` |
| Delta vs previous | `maturity_assessment.previous_overall_score` (compute `overall_score − previous_overall_score`) |
| Reliability score | `maturity_assessment.reliability.score` |
| Reliability factors | `maturity_assessment.reliability.factors.{success_rate, mttr, flaky, warning_hotspots}` each `{value/value_hours/count, factor_score}` |
| Discipline score + sub-scores | `maturity_assessment.discipline.{score, wf_completeness_score, bp_score}` |
| Speed | `maturity_assessment.speed.{score, weighted_avg_ratio, consistency}` |
| Security | `maturity_assessment.security.{score, signing_health_score, env_var_usage_score, expiring_soon[], profiles_without_env_vars[]}` |
| Top improvements | `maturity_assessment.top_improvements[]` → `{check, severity, profiles[]}` |

Reading notes:
- `overall_score` and each dimension `score` are 0–100. `label` is one of
  `Developing` / `Practicing` / `Advancing` / `Optimizing`. Pair the label with an
  emoji (Developing 🌱, Practicing 🛠️, Advancing 🚀, Optimizing 🏆).
- Reliability factor values are raw measurements to display directly:
  `success_rate.value` is a fraction (×100 for `%`); `mttr.value_hours` is hours;
  `flaky.count` and `warning_hotspots.count` are integers. Each factor's
  `factor_score` (0–100) is used only to colour its dot (≥80 green, 50–79 amber,
  <50 red) — never shown as a number.
- The tool owns dimension weighting and returns no weights, so **do not annotate
  bars with weight percentages**. Show four dimension bars with their scores only.
- `top_improvements[].check` is a machine identifier — map it via the table below.
  `severity` is `critical` (red accent) or `advisory` (orange accent).

### `check` → human-readable mapping (Top Improvements)

| `check` | Title | Description |
|---|---|---|
| `resolve_flaky_profiles` | Resolve flaky build profiles | Same commit produces both pass and fail — fix the source of nondeterminism |
| `outlier_build_duration` | Investigate outlier build durations | One profile's median build time is far above its platform peers |
| `custom_script_not_from_git` | Migrate custom scripts to Git | Inline scripts are harder to review and reuse than Git-sourced ones |
| `pr_workflow_not_configured` | Configure PR workflows on all profiles | Changes can reach the main branch without PR-level validation |
| `versioning_not_automated` | Automate versioning on Push workflows | Push workflows should increment build and version numbers automatically |
| `environment_variables_not_configured` | Configure environment variable groups | Profiles without env var groups hardcode or omit configuration |
| `signing_identity_expiring` | Renew expiring signing identities | A certificate or provisioning profile is close to expiry |

For any `check` not in this table, humanize the identifier (replace underscores
with spaces, sentence-case) and omit the description rather than inventing one.

---

## Render: Maturity Assessment Widget

Section header: `MATURITY ASSESSMENT · [DATE RANGE]`. Uses the Global Design System
and Global Copy Rules from the router.

### Layout

```
Score block (left): huge score (64px, #1A3352), label + emoji (#FF8F34),
delta vs prev (▲/▼ X pts), previous score muted.
Dimension bars (right): Reliability / Discipline / Speed / Security, each a
labeled progress bar + score. Fill colours: Reliability orange, Discipline navy,
Speed #B4B2A9, Security #16A34A. Track #E8EAED. No weight labels.

Reliability card and Discipline card side by side, equal height.
Speed card and Security card side by side below.
Top Improvements list at the bottom.
```

### Reliability card

Factor rows, each = coloured dot (8px, coloured by that factor's `factor_score`) +
factor name + measured value right-aligned bold. Show only the measured values, no
factor scores:
- Build success rate → `{success_rate.value × 100:.0f}%`
- Mean time to recovery → `avg {mttr.value_hours:.1f}h` (or `Xm` if < 1h)
- Flaky profiles → `{flaky.count} profiles affected`
- Warning hotspots → `{warning_hotspots.count} profiles affected`

AI Insight box (background `#FFF8F3`, border `#FFD4A3`, radius 6px, padding 12px;
label `● AI INSIGHT` 11px uppercase `#FF8F34`; body 12px `#374151`): name the
lowest-scoring factor (lowest `factor_score`) and what it means in 1–2 plain
sentences, no internal field names.

### Discipline card

Discipline `score` as the headline, then two sub-score bars read straight from the
response:
- **Workflow completeness** → `wf_completeness_score` (navy fill, 3px bar, score
  shown as `XX / 100`).
- **Best practices** → `bp_score` (orange fill, 3px bar, `XX / 100`).

The detailed per-workflow completeness grid and the per-check best-practice
breakdown live in Section 3 (Workflow Quality) and are not duplicated here. If
Section 3 is also in scope, add a muted 11px line: "Full workflow breakdown below."

### Speed card

Two columns. Left: `● P95/P50 RATIO` label, `weighted_avg_ratio` (28px bold),
consistency pill, caption "workspace avg across active profiles". Right: `● SPEED
SCORE` label, `speed.score` (big), small caption. Consistency pill: `consistent` →
pill good, `moderate` → pill warn, `high variance` → pill bad.

### Security card

Left: `● SIGNING HEALTH` label, `signing_health_score` (28px bold), pill good/warn/bad
by band (≥80 good, 50–79 warn, <50 bad). If `expiring_soon` is non-empty, list each
identity below as a pill-bad chip ("Name · expires in N days" when the entry carries
that detail; otherwise just the name). Right: `● ENV VAR USAGE` label,
`env_var_usage_score` (28px bold), and `profiles_without_env_vars` rendered as
profile pills under a muted caption "Profiles with no environment variable group".
If `profiles_without_env_vars` is empty, show muted "All profiles configured." Omit
the whole Security card only if the `security` key is absent or listed in
`meta.omitted_subsections`.

### Top Improvements

Title + "Ranked by impact on overall score" muted subtitle. Render
`top_improvements` in array order (the tool ranks critical before advisory). Each
item: left accent bar (critical → critical accent, advisory → advisory accent) +
bold title (14px, from the mapping) + description (13px muted, from the mapping) +
one profile pill per entry in `profiles[]`. Divider between items. If
`top_improvements` is empty, show a single muted line "No improvement actions for
this period."
