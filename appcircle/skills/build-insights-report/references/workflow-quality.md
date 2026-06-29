# Section 3: Workflow Quality

Reads from: `data.sections.workflow_quality`. No computation — workflow scoring,
tier detection, and best-practice checks are done server-side. Section header:
`WORKFLOW QUALITY · [DATE RANGE]`.

---

## Data Source Map

| Rendered element | Response path |
|---|---|
| Per-profile score cards | `workflow_quality.per_profile[]` → `{profile, os, push, pr}` |
| Push workflow score | `per_profile[].push` → `{workflow_name, tier1_score, tier2_score, tier3_score, total_score, missing_groups:[{tier, group}]}` (or `null`) |
| PR workflow score | `per_profile[].pr` → same shape (or `null`) |
| Best practice checks | `workflow_quality.best_practice_issues[]` → `{check, severity, profile, workflow, count}` |

Reading notes:
- `os` is a platform code: **1 → iOS, 2 → Android**. Use it for the platform
  sub-label on each card. Never render the raw code.
- A `null` `push` or `pr` means that workflow type is not configured for the profile
  — render the "No Push/No PR" state, not a zero score.
- `total_score` is 0–100 (`tier1+tier2+tier3`). The tier sub-scores are available if
  a breakdown is wanted, but the card shows `total_score`.
- `missing_groups[].tier` is one of `Critical` / `Important` / `Advanced`;
  `missing_groups[].group` is already human-readable (e.g. "Cache pull", "Test").
  Pool the `missing_groups` across all evaluated workflows to build the tiered table.
- `best_practice_issues[].check` is a machine identifier — map via the table below.
  `severity` is `critical` (red accent) or `advisory` (orange accent). `count` is the
  number of offending steps for that profile+workflow (e.g. inline scripts).

### `check` → label/description mapping (best practice checks)

| `check` | Check name | Description |
|---|---|---|
| `versioning_not_automated` | Versioning not automated | Push workflows should automate build number increments |
| `custom_script_not_from_git` | Custom scripts not from Git | Scripts stored in workflow config are harder to review and reuse |
| `pr_workflow_not_configured` | No PR workflow configured | Changes may reach the main branch without PR-level validation |

Humanize any unmapped `check` and omit its description.

### Step-group notes (for the missing-steps table)

| Group | Note |
|---|---|
| Git clone | Cloning the source repository |
| Dependencies | Installing project dependencies |
| Signing | iOS / Android code signing and certificates |
| Build | Compiling and building the application |
| Export build artifacts | Without this step build outputs are not stored and cannot be distributed |
| Cache pull | Restoring cached dependencies to speed up builds |
| Cache push | Saving dependencies to cache for future builds |
| Versioning | iOS / Android increment build and version number |
| Test | Xcodebuild / React Native / Flutter / Android unit tests |
| Code quality | SwiftLint / Danger / SonarQube (iOS) · Detekt / Android Lint (Android) |
| Static security | Snyk scan |
| File size check | Checking artifact file size against a threshold |
| Notify | Jira comment / Azure Boards notification |
| Binary security | Data Theorem / KOBIL / Fortify (iOS) · AppSweep / KOBIL / Fortify (Android) |

### Step group doc links

In the missing-steps tiers, every step group links out to official Appcircle docs.
`render.py` distinguishes two kinds of group:

- **Single-purpose groups** (Git clone, Export build artifacts, File size check,
  Cache pull, Cache push) — the **group title** links directly to that step's own
  doc page (dotted underline + ↗). One tool, one link.
- **Basket groups** that bundle several distinct integrations (Dependencies, Build,
  Signing, Versioning, Test, Code quality, Static security, Binary security,
  Notify) — the group title stays plain text, and instead **each tool named in the
  note line becomes its own link** to that tool's own doc page, e.g. "SwiftLint ·
  Danger · SonarQube" each link separately rather than the whole "Code quality"
  label pointing at one page. Tools are grouped by platform with a `(iOS)` /
  `(Android)` suffix where relevant; platform-neutral tools (Danger, SonarQube,
  Snyk, Jira Comment, Azure Boards, Data Theorem, KOBIL, Fortify on Demand) show no
  suffix. The tool list is filtered to the platform(s) of the profiles actually
  missing that step — an iOS-only profile missing Binary security shows only the
  iOS Appdome link plus the platform-neutral tools, not AppSweep (Android-only).

All URLs were retrieved from `docs.appcircle.io`'s common/iOS/Android workflow-step
catalogs, never hand-constructed. The full map lives in `STEP_DOCS_FIXED` (single-
purpose) and `STEP_TOOLS` (basket groups, as `(label, url, platform)` tuples) near
the top of `render.py`. An unmapped group or tool renders as plain text with no
link rather than a guessed URL. If Appcircle restructures its docs or adds a new
integration to a group, update `STEP_TOOLS` / `STEP_DOCS_FIXED` (and this table)
to match.

---

## Render: Workflow Quality Widget

### Part 1 — Per-profile completeness cards

Full-width card. Title: "Workflow completeness". Subtitle: "Most active workflow per
trigger type · evaluated against Appcircle ideal flows".

Render a horizontal row of cards, one per entry in `per_profile`. Each card:
- Profile name (bold 13px) + platform sub-label (muted 11px) from `os` (iOS / Android).
- Push line (if `push` non-null): `Push` badge (orange) + `total_score / 100` (bold)
  + `workflow_name` (muted, truncate 22 chars) + progress bar (orange fill, 3px).
- PR line (if `pr` non-null): `PR` badge (navy) + `total_score / 100` (bold) +
  `workflow_name` (muted) + progress bar (navy fill, 3px).
- If `push`/`pr` is null: `No Push` / `No PR` in muted italic instead of that line.

Push badge: `background:#FFF0E0; color:#FF8F34; border:0.5px solid #FF8F34;
border-radius:4px; padding:1px 6px; font-size:10px; font-weight:600`.
PR badge: `background:#E6EEF5; color:#1A3352; border:0.5px solid #1A3352;
border-radius:4px; padding:1px 6px; font-size:10px; font-weight:600`.

### Part 2 — Missing steps (tiered table)

Pool every `missing_groups` entry across all `push`/`pr` workflows, tagging each with
its profile, workflow name, and trigger type (Push/PR). Group into three tiers.

**Tier section headers** (count of issues right-aligned):
- `● CRITICAL  Must have` — red dot
- `● IMPORTANT  Great to have` — orange dot
- `● ADVANCED  Good to have` — grey dot

**Per missing-step row:** step group name (bold 13px) + note (muted 12px, from the
step-group notes table) + pills on the right, one per affected (profile, workflow,
trigger): `[Push|PR badge] profile · workflow`. Pills compact:
`background: var(--color-background-secondary); border: 0.5px solid
var(--color-border-tertiary); border-radius: 4px; padding: 2px 8px; font-size: 11px`.

Left accent bar per row: red (Critical), orange (Important), grey (Advanced), 3px,
no radius. No coloured row backgrounds. Divider between rows. Omit a tier section
entirely if it has no missing groups.

### Part 3 — Best practice checks card

Separate card below. Title: "Best practice checks". Subtitle: "Configuration issues
detected across active profiles".

Group `best_practice_issues` by `check`. One row per check that has issues, left
accent bar by `severity` (critical red / advisory orange): check name (bold 13px,
from mapping) + description (muted 12px) + pills on the right, one per issue:
`profile · workflow` (append `· N scripts` when `count` > 1 and the check is about
scripts). Omit a check row if it has no issues. If `best_practice_issues` is empty,
show a single muted line: "No configuration issues detected."
