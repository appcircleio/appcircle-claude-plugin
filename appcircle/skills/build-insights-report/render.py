#!/usr/bin/env python3
"""
render.py — Build Insights Report renderer.

Takes a get_build_insights_report MCP response (JSON) and emits one
self-contained HTML report. All section render logic lives here so the skill's
render step is a single script run instead of hand-authored HTML per report.

Usage:
    python render.py <response.json> [output.html]
    cat response.json | python render.py - [output.html]

The input is the FULL tool envelope: {"success", "data": {...}, "meta": {...}}.
Sections absent from data.sections (or listed in meta.omitted_sections) are
skipped. Charts use Chart.js from cdnjs (works in any normal browser).
"""

import sys
import json
import html
from datetime import datetime

# --------------------------------------------------------------------------
# Design system (single source of truth, emitted once per report)
# --------------------------------------------------------------------------

CSS = """
:root{
  --bg:#F5F7FA; --card:#FFFFFF; --bd:#E8EAED; --bd2:#F3F4F6;
  --orange:#FF8F34; --navy:#1A3352; --tp:#111827; --ts:#6B7280; --tm:#9CA3AF;
  --green:#16A34A; --red:#DC2626; --gray:#B4B2A9;
  --rec-bg:#FFF8F3; --rec-bd:#FFD9AD;
  --ai-bg:#FFF8F3; --ai-bd:#FFD4A3;
  --combo-bg:#FFF3E8; --combo-bd:#FFD4A3; --combo-c:#92400E;
  --hbar-track:#F3F4F6;
  --rec-body:#374151; --ai-body:#374151;
  --qbtn-bg:#fff;
}
@media(prefers-color-scheme:dark){
  :root{
    --bg:#0F1117; --card:#1C2030; --bd:#2A3045; --bd2:#232840;
    --orange:#FF8F34; --navy:#4E7BAF; --tp:#E5E7EB; --ts:#9CA3AF; --tm:#6B7280;
    --green:#22C55E; --red:#F87171; --gray:#6B7280;
    --rec-bg:#251A10; --rec-bd:#7A4A1A;
    --ai-bg:#251A10; --ai-bd:#7A4A1A;
    --combo-bg:#2C1E0F; --combo-bd:#7A4A1A; --combo-c:#FBB07A;
    --hbar-track:#2A3045;
    --rec-body:#CBD5E1; --ai-body:#CBD5E1;
    --qbtn-bg:transparent;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tp);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:14px;line-height:1.45;padding:20px;}
.wrap{max-width:760px;margin:0 auto;}
.sec{margin-bottom:22px;}
.hdr{font-size:11px;letter-spacing:.5px;color:var(--ts);text-transform:uppercase;margin-bottom:12px;}
.card{background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:14px 16px;}
.row{display:flex;gap:12px;flex-wrap:wrap;}
.col{flex:1;min-width:260px;}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;}
.gridp{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:2px 24px;}
.mcard{background:var(--card);border:1px solid var(--bd);border-top:3px solid var(--orange);
  border-radius:8px;padding:12px 14px;}
.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--ts);}
.val{font-size:30px;font-weight:500;margin:2px 0 6px;}
.val28{font-size:28px;font-weight:500;margin:6px 0 8px;}
.ctitle{font-size:14px;font-weight:500;}
.csub{font-size:12px;color:var(--ts);margin-bottom:10px;}
.muted{color:var(--ts);} .mut2{color:var(--tm);}
.right{text-align:right;}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ts);font-size:12px;}
.pill{display:inline-block;border-radius:99px;padding:2px 8px;font-size:11px;border:1px solid;}
.pg{background:#F0FDF4;color:var(--green);border-color:#BBF7D0;}
.pw{background:#FFF7ED;color:#D97706;border-color:#FED7AA;}
.pb{background:#FEF2F2;color:var(--red);border-color:#FECACA;}
.pn{background:#F3F4F6;color:var(--ts);border-color:#E5E7EB;}
.pp{background:#F3F4F6;color:#374151;border:1px solid #E5E7EB;border-radius:99px;padding:3px 10px;font-size:12px;display:inline-block;}
.bpush{background:#FFF0E0;color:var(--orange);border:.5px solid var(--orange);border-radius:4px;padding:1px 6px;font-size:10px;font-weight:600;}
.bpr{background:#E6EEF5;color:var(--navy);border:.5px solid var(--navy);border-radius:4px;padding:1px 6px;font-size:10px;font-weight:600;}
.track{height:8px;background:var(--bd);border-radius:4px;overflow:hidden;}
.track3{height:3px;background:var(--bd);}
.fill{display:block;height:100%;}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;}
.circ{width:20px;height:20px;border-radius:50%;background:var(--navy);color:#fff;font-size:11px;
  display:inline-flex;align-items:center;justify-content:center;}
.frow{display:flex;align-items:center;justify-content:space-between;padding:6px 0;}
.bd-b{border-bottom:1px solid var(--bd2);}
.acc{border-left:3px solid;padding:8px 0 8px 12px;}
.acc-c{border-color:var(--red);} .acc-a{border-color:var(--orange);} .acc-n{border-color:var(--tm);}
.ai{background:var(--ai-bg);border:1px solid var(--ai-bd);border-radius:6px;padding:12px;margin-top:12px;}
.ai-l{font-size:11px;letter-spacing:.5px;text-transform:uppercase;color:var(--orange);margin-bottom:5px;}
.ai-t{font-size:12px;color:var(--ai-body);line-height:1.55;}
.note{font-size:13px;color:var(--ts);margin-top:14px;}
.rec{background:var(--rec-bg);border:1px solid var(--rec-bd);border-radius:8px;padding:16px 18px;margin-top:14px;}
.rec-l{font-size:11px;letter-spacing:.5px;text-transform:uppercase;color:var(--orange);margin-bottom:8px;font-weight:600;}
.rec-h{font-size:15px;font-weight:700;color:var(--navy);margin-bottom:8px;line-height:1.3;}
.rec-b{font-size:13px;color:var(--rec-body);line-height:1.65;margin-bottom:14px;}
.rec-b strong{color:var(--navy);}
.qbtn{display:inline-block;border:1px solid var(--orange);color:var(--orange);background:var(--qbtn-bg);
  border-radius:99px;padding:8px 16px;font-size:13px;font-weight:600;text-decoration:none;margin:0 10px 0 0;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:var(--ts);font-weight:500;text-align:left;padding:4px 0;}
td{padding:8px 0;border-top:1px solid var(--bd2);}
.barbox{display:flex;align-items:center;gap:10px;}
.hbar-track{flex:1;height:8px;background:var(--hbar-track);border-radius:4px;overflow:hidden;}
.combo{background:var(--combo-bg);border:1px solid var(--combo-bd);border-radius:99px;padding:2px 8px;font-size:11px;color:var(--combo-c);display:inline-block;margin:3px 4px 0 0;}
canvas{max-width:100%;}
"""

OS_MAP = {1: "iOS", 2: "Android"}

IMPROVEMENT_MAP = {
    "resolve_flaky_profiles": ("Resolve flaky build profiles",
        "Same commit produces both pass and fail. Fix the source of nondeterminism"),
    "outlier_build_duration": ("Investigate outlier build durations",
        "One profile's median build time is far above its platform peers"),
    "custom_script_not_from_git": ("Migrate custom scripts to Git",
        "Inline scripts are harder to review and reuse than Git-sourced ones"),
    "pr_workflow_not_configured": ("Configure PR workflows on all profiles",
        "Changes can reach the main branch without PR-level validation"),
    "versioning_not_automated": ("Automate versioning on Push workflows",
        "Push workflows should increment build and version numbers automatically"),
    "environment_variables_not_configured": ("Configure environment variable groups",
        "Profiles without env var groups hardcode or omit configuration"),
    "signing_identity_expiring": ("Renew expiring signing identities",
        "A certificate or provisioning profile is close to expiry"),
}

BP_MAP = {
    "versioning_not_automated": ("Versioning not automated",
        "Push workflows should automate build number increments"),
    "custom_script_not_from_git": ("Custom scripts not from Git",
        "Scripts stored in workflow config are harder to review and reuse"),
    "pr_workflow_not_configured": ("No PR workflow configured",
        "Changes may reach the main branch without PR-level validation"),
}

STEP_NOTES = {
    "Git clone": "Cloning the source repository",
    "Dependencies": "Installing project dependencies",
    "Signing": "iOS / Android code signing and certificates",
    "Build": "Compiling and building the application",
    "Export build artifacts": "Without this step build outputs are not stored and cannot be distributed",
    "Cache pull": "Restoring cached dependencies to speed up builds",
    "Cache push": "Saving dependencies to cache for future builds",
    "Versioning": "iOS / Android increment build and version number",
    "Test": "Xcodebuild / React Native / Flutter / Android unit tests",
    "Code quality": "SwiftLint / Danger / SonarQube (iOS) · Detekt / Android Lint (Android)",
    "Static security": "Snyk scan",
    "File size check": "Checking artifact file size against a threshold",
    "Notify": "Jira comment / Azure Boards notification",
    "Binary security": "Data Theorem / KOBIL / Fortify (iOS) · AppSweep / KOBIL / Fortify (Android)",
}

# Official Appcircle doc URLs (retrieved from docs.appcircle.io component catalog).
_COM = "https://docs.appcircle.io/workflows/common-workflow-steps"
_IOS = "https://docs.appcircle.io/workflows/ios-specific-workflow-steps"
_AND = "https://docs.appcircle.io/workflows/android-specific-workflow-steps"

# Single-purpose groups: one fixed doc page, linked on the group title.
STEP_DOCS_FIXED = {
    "Git clone": _COM + "/git-clone",
    "Export build artifacts": _COM + "/export-build-artifacts",
    "File size check": _COM + "/file-size-check",
    "Cache pull": _COM + "/build-cache/cache-pull",
    "Cache push": _COM + "/build-cache/cache-push",
}

# Multi-tool ("basket") groups: each named integration links to its own page.
# (label, url, platform) where platform is "iOS" / "Android" / "Common".
STEP_TOOLS = {
    "Build": [
        ("Xcodebuild for Devices", _IOS + "/xcodebuild-for-devices", "iOS"),
        ("Android Build", _AND + "/android-build", "Android")],
    "Dependencies": [
        ("CocoaPods Install", _IOS + "/cocoapods-install", "iOS"),
        ("Carthage", _IOS + "/carthage", "iOS"),
        ("Gradle Runner", _AND + "/gradle-runner", "Android"),
        ("Android Dependency Report", _AND + "/android-dependency-report", "Android")],
    "Signing": [
        ("Install Certificates and Profiles", _IOS + "/install-certificates-provisions", "iOS"),
        ("Android Sign", _AND + "/android-sign", "Android")],
    "Versioning": [
        ("iOS Increment Build and Version", _IOS + "/ios-increment-build-and-version-number", "iOS"),
        ("Android Increment Build and Version", _AND + "/increment-build-and-version-number", "Android")],
    "Test": [
        ("Xcodebuild Unit and UI Tests", _IOS + "/xcodebuild-for-unit-and-ui-test", "iOS"),
        ("Test Reports for iOS", _IOS + "/test-reports-for-ios", "iOS"),
        ("Android Unit Tests", _AND + "/android-unit-tests", "Android"),
        ("Test Reports for Android", _AND + "/test-reports-for-android", "Android")],
    "Code quality": [
        ("SwiftLint", _IOS + "/swiftlint", "iOS"),
        ("Detekt", _AND + "/detekt", "Android"),
        ("Android Lint", _AND + "/lint", "Android"),
        ("Danger", _COM + "/danger", "Common"),
        ("SonarQube", _COM + "/sonarqube", "Common")],
    "Static security": [
        ("Snyk", _COM + "/snyk-scan-security", "Common")],
    "Binary security": [
        ("Appdome Build-2Secure", _IOS + "/appdome-build-to-secure-for-ios", "iOS"),
        ("Appdome Build-2Secure", _AND + "/appdome-build-to-secure-for-android", "Android"),
        ("AppSweep", _AND + "/appsweep-mobile-security-testing", "Android"),
        ("Data Theorem", _COM + "/data-theorem-mobile-secure", "Common"),
        ("KOBIL Appshield", _COM + "/kobil-appshield-scanner", "Common"),
        ("Fortify on Demand", _COM + "/fod-mobile-assesment", "Common")],
    "Notify": [
        ("Jira Comment", _COM + "/jira-comment", "Common"),
        ("Azure Boards", _COM + "/azure-board", "Common")],
}

_LINK_STYLE = "color:#1A3352;text-decoration:none;border-bottom:1px dotted #C9CDD3;"

def step_title_url(group):
    """URL for a single-purpose group's title link, or None for basket groups."""
    return STEP_DOCS_FIXED.get(group)

def render_step_tools(group, os_set):
    """Render a basket group's tools as per-tool links, filtered to the affected
    platforms (Common tools always shown). Returns None if the group is not a basket."""
    tools = STEP_TOOLS.get(group)
    if not tools:
        return None
    show_ios = (not os_set) or (1 in os_set)
    show_and = (not os_set) or (2 in os_set)
    segs = []
    for plat, ok, suffix in (("iOS", show_ios, " (iOS)"), ("Android", show_and, " (Android)"), ("Common", True, "")):
        items = [t for t in tools if t[2] == plat]
        if not items or not ok:
            continue
        links = " / ".join(
            f'<a href="{esc(u)}" target="_blank" rel="noopener" style="{_LINK_STYLE}">{esc(lbl)}</a>'
            for lbl, u, _ in items)
        segs.append(links + suffix)
    return " · ".join(segs)

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def esc(s):
    return html.escape(str(s), quote=True)

def humanize(key):
    return key.replace("_", " ").capitalize()

def fmt_mins(m):
    if m is None:
        return "—"
    if m < 60:
        return f"{round(m)}m"
    return f"{m/60:.1f}h"

def fmt_hours(h):
    if h is None:
        return "—"
    if h < 1:
        return f"{round(h*60)}m"
    return f"{h:.1f}h"

def fmt_date(iso):
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return f"{d.strftime('%b')} {d.day}, {d.year}"
    except Exception:
        return iso[:10]

def fmt_range(dr):
    try:
        a = datetime.fromisoformat(dr["current_start"])
        b = datetime.fromisoformat(dr["current_end"])
        if a.year == b.year:
            return f"{a.strftime('%b')} {a.day} – {b.strftime('%b')} {b.day}, {b.year}"
        return f"{a.strftime('%b')} {a.day}, {a.year} – {b.strftime('%b')} {b.day}, {b.year}"
    except Exception:
        return f"{dr.get('current_start','')} – {dr.get('current_end','')}"

def short_label(iso):
    try:
        d = datetime.fromisoformat(iso)
        return f"{d.strftime('%b')} {d.day}"
    except Exception:
        return iso[5:]

def rate_pill_class(rate):
    if rate >= 80:
        return "pg"
    if rate >= 60:
        return "pw"
    return "pb"

def score_color(score):
    if score >= 80:
        return "var(--green)"
    if score >= 50:
        return "var(--orange)"
    return "var(--red)"

def delta_badge(value, good_when, unit):
    """value: number or None; good_when: 'up' or 'down'; unit: 'pp' or 'pct'."""
    if value is None:
        return '<span class="pill pn">no prior period</span>'
    arrow = "&#9650;" if value >= 0 else "&#9660;"
    mag = abs(round(value, 1)) if unit == "pp" else abs(round(value))
    txt = f"{arrow} {mag}{'pp' if unit=='pp' else '%'}"
    if good_when == "neutral":
        cls = "pn"
    else:
        positive_good = (value >= 0) == (good_when == "up")
        cls = "pg" if positive_good else "pb"
    return f'<span class="pill {cls}">{txt}</span>'

# --------------------------------------------------------------------------
# Section renderers — each returns (html_str, chart_scripts_list)
# --------------------------------------------------------------------------

def r_health(hs, rng):
    s = hs.get("summary", {})
    cur, dl = s.get("current", {}), s.get("delta", {})
    out = [f'<div class="sec"><div class="hdr">Health snapshot · {esc(rng)}</div>']

    out.append('<div class="grid" style="margin-bottom:14px;">')
    out.append(f'<div class="mcard"><div class="lbl">Total builds</div><div class="val">{cur.get("total",0)}</div>{delta_badge(dl.get("total_pct",0),"neutral","pct")}</div>')
    out.append(f'<div class="mcard"><div class="lbl">Success rate</div><div class="val">{round(cur.get("success_rate",0))}%</div>{delta_badge(dl.get("success_rate_pp",0),"up","pp")}</div>')
    out.append(f'<div class="mcard"><div class="lbl">Failed builds</div><div class="val">{cur.get("failed",0)}</div>{delta_badge(dl.get("failure_rate_pp",0),"down","pp")}</div>')
    out.append(f'<div class="mcard"><div class="lbl">Canceled / timeout</div><div class="val">{cur.get("canceled",0)}</div>{delta_badge(dl.get("canceled_rate_pp",0),"down","pp")}</div>')
    out.append('</div>')

    out.append('<div class="row" style="margin-bottom:14px;">')
    out.append('<div class="col card"><div class="frow" style="padding:0 0 8px;"><span class="ctitle">Top active profiles</span></div>')
    for i, p in enumerate(hs.get("top_active_profiles", []), 1):
        rate = p.get("success_rate", 0)
        col = "var(--green)" if rate >= 80 else ("#D97706" if rate >= 60 else "var(--red)")
        bc = "bd-b" if i < len(hs.get("top_active_profiles", [])) else ""
        out.append(f'<div class="frow {bc}"><span style="display:flex;align-items:center;gap:10px;"><span class="circ">{i}</span>{esc(p["profile"])}</span>'
                   f'<span><span class="muted">{p.get("build_count",0)} builds</span> &nbsp; <span style="color:{col};font-weight:500;">{round(rate)}%</span></span></div>')
    out.append('</div>')

    out.append('<div class="col card"><div class="frow" style="padding:0 0 8px;"><span class="ctitle">Top build activity</span></div>')
    acts = hs.get("top_build_activity", [])
    for i, a in enumerate(acts):
        bc = "bd-b" if i < len(acts) - 1 else ""
        out.append(f'<div class="frow {bc}"><span>{esc(a["profile"])} &nbsp; <span class="mono">{esc(a.get("branch",""))}</span></span><span style="font-weight:500;">{a.get("build_count",0)}</span></div>')
    out.append('</div></div>')

    inactive = hs.get("inactive_profiles", [])
    if inactive:
        out.append('<div class="card" style="margin-bottom:14px;"><div class="ctitle">Inactive profiles</div>'
                   '<div class="csub">Profiles with no builds in the last 30 days — may need cleanup or archiving</div><div class="gridp">')
        for p in inactive[:12]:
            d = fmt_date(p.get("last_build_date")) or "No recent builds found"
            out.append(f'<div class="frow" style="padding:4px 0;border-bottom:1px solid #F7F7F8;font-size:13px;"><span>{esc(p["profile"])}</span><span class="muted">{esc(d)}</span></div>')
        out.append('</div>')
        if len(inactive) > 12:
            out.append(f'<div class="mut2" style="font-size:12px;margin-top:8px;">+{len(inactive)-12} more inactive profiles</div>')
        out.append('</div>')

    out.append('<div class="row" style="margin-bottom:14px;">')
    out.append('<div class="col card"><div class="ctitle">Top manual triggers</div><div class="csub">Builds started by a person</div>')
    man = hs.get("top_triggers", {}).get("manual", [])
    if man:
        for t in man[:5]:
            who = t.get("initiated_by", "")
            who = who if len(who) <= 28 else who[:27] + "…"
            out.append(f'<div class="frow" style="padding:5px 0;"><span>{esc(who)}</span><span style="font-weight:500;">{t.get("build_count",0)}</span></div>')
    else:
        out.append('<div class="mut2" style="padding:5px 0;font-size:13px;">(none this period)</div>')
    out.append('</div>')
    out.append('<div class="col card"><div class="ctitle">Top automated triggers</div><div class="csub">Builds started by push, PR, or schedule</div>')
    auto = hs.get("top_triggers", {}).get("automated", [])
    if auto:
        for t in auto[:5]:
            who = t.get("initiated_by", "")
            who = who if len(who) <= 28 else who[:27] + "…"
            out.append(f'<div class="frow" style="padding:5px 0;"><span>{esc(who)}</span><span style="font-weight:500;">{t.get("build_count",0)}</span></div>')
    else:
        out.append('<div class="mut2" style="padding:5px 0;font-size:13px;">(none this period)</div>')
    out.append('</div></div>')

    summary = _health_ai(cur, hs)
    out.append(f'<div class="ai" style="border-left:4px solid var(--orange);"><div class="ai-l">&#9679; AI summary</div><div class="ai-t">{esc(summary)}</div></div>')
    out.append('</div>')
    return "".join(out), []

def _health_ai(cur, hs):
    total = cur.get("total", 0)
    sr = round(cur.get("success_rate", 0))
    top = hs.get("top_active_profiles", [])
    lead = top[0]["profile"] if top else "the busiest profile"
    canceled = cur.get("canceled", 0)
    parts = [f"This period ran {total} build{'s' if total != 1 else ''} at a {sr}% success rate."]
    if canceled and total and canceled / total >= 0.3:
        parts.append(f"Cancellations are a notable share ({canceled} of {total}), so the success rate reflects abandoned runs as much as real failures.")
    if top:
        parts.append(f"{lead} drove the most activity and is the first profile to check if volume grows.")
    return " ".join(parts)

def r_trends(hs, rng):
    tr = hs.get("trends", {})
    ds = tr.get("daily_series", [])
    if not ds:
        return "", []
    labels = [short_label(d["date"]) for d in ds]
    pass_r = [d.get("pass_rate", 0) for d in ds]
    fail_r = [d.get("fail_rate", 0) for d in ds]
    succ = [d.get("success", 0) for d in ds]
    fld = [d.get("failed", 0) for d in ds]
    can = [d.get("canceled", 0) for d in ds]
    tmo = [d.get("timeout", 0) for d in ds]

    out = [f'<div class="sec"><div class="hdr">Trends · {esc(rng)}</div>']

    out.append('<div class="card" style="margin-bottom:12px;"><div class="ctitle" style="margin-bottom:8px;">Pass rate and fail rate</div>')
    out.append('<div style="display:flex;gap:16px;margin-bottom:8px;font-size:12px;color:var(--ts);">'
               '<span style="display:flex;align-items:center;gap:5px;"><span style="width:14px;height:3px;background:#16A34A;"></span>Pass rate</span>'
               '<span style="display:flex;align-items:center;gap:5px;"><span style="width:14px;height:3px;background:#DC2626;"></span>Fail rate</span></div>')
    out.append('<div style="position:relative;width:100%;height:180px;"><canvas id="cRate" role="img" aria-label="Daily pass rate and fail rate line chart."></canvas></div></div>')

    out.append('<div class="card" style="margin-bottom:12px;"><div class="ctitle" style="margin-bottom:8px;">Build volume</div>')
    out.append('<div style="display:flex;gap:16px;margin-bottom:8px;font-size:12px;color:var(--ts);flex-wrap:wrap;">'
               '<span style="display:flex;align-items:center;gap:5px;"><span style="width:10px;height:10px;border-radius:2px;background:#16A34A;"></span>Success</span>'
               '<span style="display:flex;align-items:center;gap:5px;"><span style="width:10px;height:10px;border-radius:2px;background:#DC2626;"></span>Failed</span>'
               '<span style="display:flex;align-items:center;gap:5px;"><span style="width:10px;height:10px;border-radius:2px;background:#FF8F34;"></span>Canceled</span>'
               '<span style="display:flex;align-items:center;gap:5px;"><span style="width:10px;height:10px;border-radius:2px;background:#7C3AED;"></span>Timeout</span></div>')
    out.append('<div style="position:relative;width:100%;height:180px;"><canvas id="cVol" role="img" aria-label="Daily build volume stacked bar chart."></canvas></div></div>')

    # per-profile duration: chart only if any non-null p50 exists
    series = tr.get("per_profile_duration_series", [])
    palette = ["#FF8F34", "#1A3352", "#16A34A", "#7C3AED", "#DC2626"]
    has_points = any(pt.get("p50") is not None for sObj in series for pt in sObj.get("series", []))

    out.append('<div class="card"><div class="frow" style="padding:0 0 4px;"><span class="ctitle">Build duration per profile</span></div>'
               '<div class="csub" style="margin-bottom:0;">P50, P95, and consistency for each active profile.</div>')

    dur_scripts = []
    if has_points:
        out.append('<div style="position:relative;width:100%;height:200px;margin-top:8px;"><canvas id="cDur" role="img" aria-label="Per-profile median build duration over time."></canvas></div>')
        labels_d = [pt["date"][5:] for pt in series[0].get("series", [])] if series else labels
        dsets = []
        for i, sObj in enumerate(series):
            data = [pt.get("p50") for pt in sObj.get("series", [])]
            color = palette[i % len(palette)]
            dsets.append({"label": sObj.get("profile", ""), "data": data, "borderColor": color,
                          "backgroundColor": color, "spanGaps": False, "pointRadius": 3, "tension": 0.3})
        dur_scripts.append(_chart_js("cDur", "line", {"labels": labels_d, "datasets": dsets},
                                     y_label_suffix="m"))

    table = hs.get("trends", {}).get("per_profile_duration", [])
    if table:
        out.append('<table style="margin-top:10px;"><tr><th>Profile</th><th class="right">P50</th><th class="right">P95</th><th class="right">P95/P50</th><th class="right">Trend</th><th class="right">Consistency</th></tr>')
        tp = {"faster": "pg", "stable": "pn", "slower": "pb"}
        cp = {"consistent": "pg", "moderate": "pw", "high variance": "pb"}
        for r in table:
            out.append(f'<tr><td>{esc(r["profile"])}</td><td class="right">{r.get("p50",0):.1f}m</td>'
                       f'<td class="right">{r.get("p95",0):.1f}m</td><td class="right">{r.get("ratio",0):.1f}</td>'
                       f'<td class="right"><span class="pill {tp.get(r.get("trend"),"pn")}">{esc(r.get("trend",""))}</span></td>'
                       f'<td class="right"><span class="pill {cp.get(r.get("consistency"),"pn")}">{esc(r.get("consistency",""))}</span></td></tr>')
        out.append('</table>')
    if not has_points:
        out.append('<div class="mut2" style="font-size:12px;margin-top:10px;border-top:1px solid var(--bd2);padding-top:8px;">'
                   'The per-day duration chart needs at least 2 successful builds on the same day to plot a median. '
                   'No day in this window met that, so the daily duration lines are not shown.</div>')
    out.append('</div></div>')

    rate_js = _chart_js("cRate", "line", {"labels": labels, "datasets": [
        {"label": "Pass rate", "data": pass_r, "borderColor": "#16A34A", "backgroundColor": "#16A34A", "borderWidth": 2, "pointRadius": 2, "tension": 0.3},
        {"label": "Fail rate", "data": fail_r, "borderColor": "#DC2626", "backgroundColor": "#DC2626", "borderWidth": 2, "borderDash": [5, 4], "pointRadius": 2, "tension": 0.3},
    ]}, y_max=100, y_label_suffix="%")
    vol_js = _chart_js("cVol", "bar", {"labels": labels, "datasets": [
        {"label": "Success", "data": succ, "backgroundColor": "#16A34A"},
        {"label": "Failed", "data": fld, "backgroundColor": "#DC2626"},
        {"label": "Canceled", "data": can, "backgroundColor": "#FF8F34"},
        {"label": "Timeout", "data": tmo, "backgroundColor": "#7C3AED"},
    ]}, stacked=True)
    return "".join(out), [rate_js, vol_js] + dur_scripts

def _chart_js(cid, ctype, data, y_max=None, y_label_suffix=None, stacked=False):
    data_json = json.dumps(data)
    ymax = f"max:{y_max}," if y_max is not None else ""
    ycb = (f"callback:function(v){{return v+'{y_label_suffix}';}}," if y_label_suffix else "")
    sx = "stacked:true," if stacked else ""
    sy = "stacked:true,beginAtZero:true," if stacked else ""
    return f"""
new Chart(document.getElementById('{cid}'),{{type:'{ctype}',data:{data_json},
options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
scales:{{x:{{{sx}ticks:{{color:_tc,font:{{size:10}},maxTicksLimit:7}},grid:{{display:false}}}},
y:{{{sy}min:0,{ymax}ticks:{{color:_tc,font:{{size:10}},{ycb}precision:0}},grid:{{color:_gc}}}}}}}}}});"""

def r_root_cause(rc, rng):
    out = [f'<div class="sec"><div class="hdr">Root cause · {esc(rng)}</div>']
    steps = rc.get("top_failing_steps", [])
    out.append('<div class="card" style="margin-bottom:12px;"><div class="ctitle">Top failing steps</div>'
               '<div class="csub">Steps most responsible for build failures, with the top affected profile and branch combinations</div>')
    if steps:
        mx = max((s.get("count", 0) for s in steps), default=1) or 1
        for i, s in enumerate(steps):
            w = round(s.get("count", 0) / mx * 100)
            out.append(f'<div style="padding:8px 0;{ "border-bottom:1px solid var(--bd2);" if i<len(steps)-1 else "" }">')
            out.append(f'<div class="barbox"><span style="flex:0 0 38%;font-size:13px;">{esc(s["step"])}</span>'
                       f'<span class="hbar-track"><span class="fill" style="width:{w}%;background:var(--orange);"></span></span>'
                       f'<span style="font-weight:500;min-width:24px;text-align:right;">{s.get("count",0)}</span>'
                       f'<span class="muted" style="min-width:36px;text-align:right;">{round(s.get("pct_of_failed",0))}%</span></div>')
            combos = "".join(f'<span class="combo">{esc(c["profile"])} <span style="font-family:monospace;">{esc(c.get("branch",""))}</span> {c.get("count",0)}</span>' for c in s.get("top_combos", []))
            if combos:
                out.append(f'<div style="margin-top:4px;">{combos}</div>')
            out.append('</div>')
    else:
        out.append('<div class="mut2" style="font-size:13px;">No failing steps recorded this period.</div>')
    out.append('</div>')

    out.append('<div class="row">')
    out.append(_rc_card("MTTR", "acc-a", "Mean time to recovery", "Longest failure-to-success gaps",
        rc.get("mttr", []), lambda r: (r["profile"], r.get("branch",""), fmt_hours(r.get("avg_hours")), f'avg across {r.get("sequence_count",0)} sequence{"s" if r.get("sequence_count",0)!=1 else ""}'), "recovery sequences"))
    out.append(_rc_card("Flaky", "acc-n2", "Flaky builds", "Same commit passing and failing",
        rc.get("flaky", []), lambda r: (r["profile"], r.get("branch",""), fmt_mins(r.get("wasted_minutes")), f'{r.get("flaky_commit_count",0)} flaky commit{"s" if r.get("flaky_commit_count",0)!=1 else ""}'), "flaky builds"))
    out.append('</div><div class="row" style="margin-top:12px;">')
    out.append(_rc_card("Warn", "acc-a", "Warning hotspots", "Builds passing with warnings",
        rc.get("warning_hotspots", []), lambda r: (r["profile"], r.get("branch",""), str(r.get("warned_count",0)), esc(r.get("top_warning_step") or "")), "warning hotspots"))
    out.append(_rc_card("Zero", "acc-c", "Zero success workflows", "Workflows with no passing runs",
        rc.get("zero_success_workflows", []), lambda r: (r["profile"], r.get("workflow",""), str(r.get("run_count",0)), esc(r.get("always_failing_step",""))), "zero success workflows", mono_second=False))
    out.append('</div></div>')
    return "".join(out), []

def _rc_card(_key, accent, title, sub, rows, mapper, empty_word, mono_second=True):
    acc = "acc-a" if accent == "acc-a" else ("acc-c" if accent == "acc-c" else ("acc-n" if accent == "acc-n2" else accent))
    style = ""
    if accent == "acc-n2":
        style = 'style="border-left-color:var(--navy);"'
    h = [f'<div class="col card"><div class="acc {acc}" {style}><div class="ctitle">{esc(title)}</div><div class="csub" style="margin-bottom:6px;">{esc(sub)}</div>']
    if rows:
        for r in rows[:3]:
            a, b, val, note = mapper(r)
            second = f'<span class="mono">{esc(b)}</span>' if mono_second else f'<span class="muted" style="font-size:12px;">{esc(b)}</span>'
            h.append(f'<div style="padding:5px 0;"><div class="frow" style="padding:0;"><span><span style="font-weight:500;">{esc(a)}</span> &nbsp; {second}</span><span style="font-weight:500;">{val}</span></div>'
                     f'<div class="mut2" style="font-size:11px;">{note}</div></div>')
    else:
        h.append(f'<div class="mut2" style="font-size:12px;">No {empty_word} detected this period.</div>')
    h.append('</div></div>')
    return "".join(h)

def r_maturity(ma, rng, omitted_sub=None):
    omitted_sub = omitted_sub or []
    out = [f'<div class="sec"><div class="hdr">Maturity assessment · {esc(rng)}</div>']
    overall = ma.get("overall_score", 0)
    prev = ma.get("previous_overall_score")
    delta = (overall - prev) if prev is not None else 0
    arrow = "&#9650;" if delta >= 0 else "&#9660;"
    dcol = "var(--green)" if delta >= 0 else "var(--red)"
    label = ma.get("label", "")

    rel = ma.get("reliability") or {}
    disc = ma.get("discipline")  # None means the subsection was not computed this period
    sp = ma.get("speed") or {}
    sec = ma.get("security")

    out.append('<div class="row" style="margin-bottom:12px;">')
    out.append(f'<div class="card" style="min-width:170px;display:flex;flex-direction:column;justify-content:center;">'
               f'<div style="font-size:64px;font-weight:500;line-height:1;color:var(--navy);">{overall}</div>'
               f'<div style="font-size:15px;font-weight:500;color:var(--orange);margin-top:8px;">{esc(label)}</div>'
               + (f'<div style="font-size:12px;color:{dcol};margin-top:6px;">{arrow} {abs(delta)} pt vs previous</div>'
                  f'<div class="mut2" style="font-size:11px;">previous score {prev}</div>' if prev is not None
                  else '<div class="mut2" style="font-size:12px;margin-top:6px;">No prior period to compare</div>')
               + '</div>')
    out.append('<div class="col card">')
    dims = [("Reliability", rel.get("score", 0), "var(--orange)")]
    if disc is not None:
        dims.append(("Discipline", disc.get("score", 0), "var(--navy)"))
    dims.append(("Speed", sp.get("score", 0), "var(--gray)"))
    if sec is not None:
        dims.append(("Security", sec.get("score", 0), "var(--green)"))
    for i, (name, score, color) in enumerate(dims):
        mb = "13px" if i < len(dims) - 1 else "0"
        out.append(f'<div style="margin-bottom:{mb};"><div class="frow" style="padding:0 0 4px;font-size:12px;"><span class="muted">{name}</span><span style="font-weight:500;">{score}</span></div>'
                   f'<div class="track"><span class="fill" style="width:{score}%;background:{color};"></span></div></div>')
    if disc is None:
        out.append('<div class="mut2" style="font-size:11px;margin-top:6px;">Discipline not available this period (not enough workflow data).</div>')
    out.append('</div></div>')

    # Reliability + Discipline (Discipline card only if computed this period)
    out.append('<div class="row" style="margin-bottom:12px;">')
    f = rel.get("factors", {})
    out.append(f'<div class="col card"><div class="ctitle">Reliability</div><div class="csub">Score {rel.get("score",0)}</div>')
    rel_rows = [
        ("Build success rate", f"{round(f.get('success_rate',{}).get('value',0)*100)}%", f.get("success_rate", {}).get("factor_score", 0)),
        ("Mean time to recovery", f"avg {fmt_hours(f.get('mttr',{}).get('value_hours'))}", f.get("mttr", {}).get("factor_score", 0)),
        ("Flaky profiles", f"{f.get('flaky',{}).get('count',0)} profiles affected", f.get("flaky", {}).get("factor_score", 0)),
        ("Warning hotspots", f"{f.get('warning_hotspots',{}).get('count',0)} profiles affected", f.get("warning_hotspots", {}).get("factor_score", 0)),
    ]
    for i, (name, val, fs) in enumerate(rel_rows):
        bc = "bd-b" if i < len(rel_rows) - 1 else ""
        out.append(f'<div class="frow {bc}"><span style="display:flex;align-items:center;gap:8px;font-size:13px;"><span class="dot" style="background:{score_color(fs)};"></span>{name}</span><span style="font-weight:500;font-size:13px;">{val}</span></div>')
    lowest = min(rel_rows, key=lambda r: r[2]) if rel_rows else None
    if lowest:
        out.append(f'<div class="ai"><div class="ai-l">&#9679; AI insight</div><div class="ai-t">{esc(_rel_insight(lowest, f))}</div></div>')
    out.append('</div>')

    if disc is not None:
        wfc = disc.get("wf_completeness_score", 0)
        bps = disc.get("bp_score", 0)
        out.append(f'<div class="col card"><div class="ctitle">Discipline</div><div class="csub" style="margin-bottom:14px;">Score {disc.get("score",0)}</div>')
        out.append(f'<div class="frow" style="padding:0 0 5px;font-size:13px;"><span class="muted">Workflow completeness</span><span style="font-weight:500;">{wfc} / 100</span></div>'
                   f'<div class="track3" style="margin-bottom:16px;"><span class="fill" style="width:{wfc}%;background:var(--navy);"></span></div>')
        out.append(f'<div class="frow" style="padding:0 0 5px;font-size:13px;"><span class="muted">Best practices</span><span style="font-weight:500;">{bps} / 100</span></div>'
                   f'<div class="track3"><span class="fill" style="width:{bps}%;background:var(--orange);"></span></div>')
        out.append(f'<div class="ai"><div class="ai-l">&#9679; AI insight</div><div class="ai-t">{esc(_disc_insight(wfc, bps))}</div></div>')
        out.append('</div>')
    out.append('</div>')

    # Speed + Security
    out.append('<div class="row" style="margin-bottom:12px;">')
    cp = {"consistent": "pg", "moderate": "pw", "high variance": "pb"}
    out.append(f'<div class="col card"><div class="ctitle" style="margin-bottom:12px;">Speed</div><div style="display:flex;gap:16px;">'
               f'<div style="flex:1;"><div class="lbl">&#9679; P95 / P50 ratio</div><div class="val28">{sp.get("weighted_avg_ratio",0):.1f}</div>'
               f'<span class="pill {cp.get(sp.get("consistency"),"pn")}">{esc(sp.get("consistency",""))}</span>'
               f'<div class="mut2" style="font-size:11px;margin-top:8px;">workspace avg across active profiles</div></div>'
               f'<div style="flex:1;"><div class="lbl">&#9679; Speed score</div><div class="val28">{sp.get("score",0)}</div></div></div>'
               f'<div class="ai"><div class="ai-l">&#9679; AI insight</div><div class="ai-t">{esc(_speed_insight(sp))}</div></div></div>')

    if sec is not None:
        pe = "".join(f'<span class="pp">{esc(p)}</span>' for p in sec.get("profiles_without_env_vars", []))
        sh = sec.get("signing_health_score", 0)
        shp = "pg" if sh >= 80 else ("pw" if sh >= 50 else "pb")
        out.append(f'<div class="col card"><div class="ctitle" style="margin-bottom:12px;">Security</div><div style="display:flex;gap:16px;">'
                   f'<div style="flex:1;"><div class="lbl">&#9679; Signing health</div><div class="val28">{sh}</div><span class="pill {shp}">{"healthy" if sh>=80 else "attention"}</span></div>'
                   f'<div style="flex:1;"><div class="lbl">&#9679; Env var usage</div><div class="val28">{sec.get("env_var_usage_score",0)}</div>'
                   + (f'<div class="mut2" style="font-size:11px;margin-bottom:6px;">Profiles with no environment variable group</div><div>{pe}</div>' if pe else '<div class="mut2" style="font-size:11px;">All profiles configured.</div>')
                   + f'</div></div><div class="ai"><div class="ai-l">&#9679; AI insight</div><div class="ai-t">{esc(_security_insight(sec))}</div></div></div>')
    out.append('</div>')

    imps = ma.get("top_improvements", [])
    out.append('<div class="card"><div class="ctitle">Top improvements</div><div class="csub">Ranked by impact on overall score</div>')
    if imps:
        for i, im in enumerate(imps):
            title, desc = IMPROVEMENT_MAP.get(im.get("check"), (humanize(im.get("check", "")), ""))
            acc = "acc-c" if im.get("severity") == "critical" else "acc-a"
            bc = "border-bottom:1px solid var(--bd2);" if i < len(imps) - 1 else ""
            pills = "".join(f'<span class="pp">{esc(p)}</span>' for p in im.get("profiles", []))
            out.append(f'<div class="acc {acc}" style="{bc}"><div class="ctitle">{esc(title)}</div>'
                       + (f'<div class="csub" style="margin:2px 0 7px;">{esc(desc)}</div>' if desc else '')
                       + f'<div>{pills}</div></div>')
    else:
        out.append('<div class="mut2" style="font-size:13px;">No improvement actions for this period.</div>')
    out.append('</div></div>')
    return "".join(out), []

def _rel_insight(lowest, f):
    name = lowest[0]
    if name == "Build success rate":
        v = round(f.get("success_rate", {}).get("value", 0) * 100)
        return f"Build success rate is the main reliability drag at {v}%. The lever is getting more builds to pass on the first run."
    if name == "Mean time to recovery":
        return f"Recovery time is the weakest factor, averaging {fmt_hours(f.get('mttr',{}).get('value_hours'))} from a failed build to the next success."
    if name == "Flaky profiles":
        return f"Flaky builds are the biggest reliability drag, with {f.get('flaky',{}).get('count',0)} profile(s) producing inconsistent results on the same commit."
    return f"Warning hotspots are the weakest factor, with {f.get('warning_hotspots',{}).get('count',0)} profile(s) frequently passing with warnings."

# --------------------------------------------------------------------------
# Queue time recommendation card
# --------------------------------------------------------------------------

# Appcircle machine plan tiers, lowest to highest concurrency/performance.
PLAN_ORDER = ["Standard", "Velocity", "Ultra"]
NEXT_PLAN = {"Standard": "Velocity", "Velocity": "Ultra"}  # Ultra has no next tier
DOC_CONCURRENCY = "https://appcircle.io/contact"
DOC_PRICING = "https://appcircle.io/contact"

def _queue_trend(daily_trend):
    vals = [d.get("avg_wait_minutes") for d in (daily_trend or []) if d.get("avg_wait_minutes") is not None]
    if len(vals) < 2:
        return "insufficient"
    first, last = vals[0], vals[-1]
    if first <= 0.01:
        return "climbing" if last > 0.5 else "stable"
    change = (last - first) / first
    if change > 0.25:
        return "climbing"
    if change < -0.25:
        return "improving"
    return "stable"

_BREAKDOWN_KEYS = {"standard_wait_minutes": "Standard", "velocity_wait_minutes": "Velocity", "ultra_wait_minutes": "Ultra"}

def _plan_from_breakdown(breakdown):
    """queue_time.plan_breakdown attributes queue wait minutes to each machine
    tier, e.g. {'standard_wait_minutes': 6.0, 'velocity_wait_minutes': 0.0,
    'ultra_wait_minutes': 0.0}. Returns (dominant_tier, is_multi_tier, pairs)
    where dominant_tier is whichever tier absorbed the most wait this period
    (the one upgrading would help most), pairs is [(tier, minutes), ...] in
    PLAN_ORDER for display, and is_multi_tier flags whether more than one tier
    saw real activity (worth caveating the recommendation copy)."""
    if not breakdown:
        return None, False, []
    pairs = [(_BREAKDOWN_KEYS[k], v) for k, v in breakdown.items() if k in _BREAKDOWN_KEYS and v is not None]
    if not pairs:
        return None, False, []
    pairs.sort(key=lambda tv: PLAN_ORDER.index(tv[0]) if tv[0] in PLAN_ORDER else 99)
    active = [(t, v) for t, v in pairs if v > 0]
    dominant = max(active, key=lambda tv: tv[1])[0] if active else pairs[0][0]
    return dominant, len(active) > 1, pairs

def _queue_recommendation(qt):
    """Builds the upgrade-nudge card when queue wait is long or trending up.
    Prefers a flat `qt['plan']` string if present (not part of the confirmed
    schema, kept for forward compatibility); otherwise infers the relevant
    tier from `qt['plan_breakdown']`, the per-tier wait-minute attribution the
    tool actually returns. With neither, falls back to plan-agnostic copy."""
    p95 = qt.get("p95_wait_minutes") or 0
    trend = _queue_trend(qt.get("daily_trend"))
    plan = qt.get("plan")
    multi_tier = False
    if not plan:
        plan, multi_tier, _ = _plan_from_breakdown(qt.get("plan_breakdown"))

    show = (p95 >= 3) or (trend == "climbing" and p95 >= 1.5)
    if not show:
        return None

    p95_txt = fmt_mins(p95)
    if trend == "climbing":
        headline = "Queue times are growing — your current capacity may not keep up"
        trend_txt = ", with the trend climbing throughout the period"
    elif trend == "improving":
        headline = "Queue wait is elevated, though easing — keep an eye on capacity"
        trend_txt = ", though the trend has been easing"
    else:
        headline = "Queue wait is elevated — consider more capacity"
        trend_txt = ""

    if plan:
        nxt = NEXT_PLAN.get(plan)
        scope = "Most of your queue wait this period was on the" if multi_tier else "Your organization's queue wait this period was on the"
        body = (f"{scope} <strong>{esc(plan)} plan</strong>, and P95 queue wait has reached "
                f"<strong>{p95_txt}</strong>{trend_txt}. This suggests your current concurrency limit is being "
                f"reached during peak hours. Consider increasing your concurrency limit"
                + (f" or upgrading to the <strong>{esc(nxt)} plan</strong>" if nxt else "")
                + " to reduce wait times across all builds.")
    else:
        body = (f"P95 queue wait has reached <strong>{p95_txt}</strong>{trend_txt}. This may indicate your "
                "concurrency limit is being reached during peak hours. Consider increasing your concurrency "
                "limit or upgrading your machine plan to reduce wait times across all builds.")

    buttons = [("Increase concurrency", DOC_CONCURRENCY)]
    if not plan or plan != "Ultra":
        label = f"Upgrade to {NEXT_PLAN[plan]}" if plan and plan in NEXT_PLAN else "View plans"
        buttons.append((label, DOC_PRICING))

    return {"headline": headline, "body": body, "buttons": buttons}

def _band(score, kind):
    if kind == "completeness":
        if score < 50: return "miss many of the recommended steps"
        if score < 75: return "cover the essentials but skip several recommended steps such as caching, tests, or notifications"
        if score < 90: return "are fairly complete, with only a few advanced steps left out"
        return "are close to the ideal Appcircle flow"
    if score < 50: return "several best-practice checks are failing"
    if score < 75: return "a few best-practice checks still fail, most often scripts kept in workflow config rather than Git"
    if score < 90: return "most best-practice checks pass"
    return "best-practice checks are almost all passing"

def _disc_insight(wfc, bps):
    return (f"Workflows {_band(wfc, 'completeness')} (completeness {wfc}/100). "
            f"On best practices ({bps}/100), {_band(bps, 'bp')}. "
            "The detailed per-workflow breakdown is in the Workflow Quality section.")

def _speed_insight(sp):
    ratio = sp.get("weighted_avg_ratio", 0)
    cons = sp.get("consistency", "")
    if ratio <= 1.2:
        tail = f"Builds are evenly paced (P95 is {ratio:.1f}x the median), so there are very few slow outliers."
    elif ratio <= 2:
        tail = f"P95 builds run about {ratio:.1f}x the median, so a minority of slower runs stretch the tail."
    else:
        tail = f"P95 builds run {ratio:.1f}x the median, so a few slow outliers are dragging the tail well above typical."
    return f"{tail} The {cons} rating reflects how tightly build times cluster across active profiles."

def _security_insight(sec):
    sh = sec.get("signing_health_score", 0)
    ev = sec.get("env_var_usage_score", 0)
    n = len(sec.get("profiles_without_env_vars", []))
    exp = sec.get("expiring_soon", [])
    parts = []
    if sh >= 80:
        parts.append("Signing identities are healthy")
    else:
        parts.append(f"Signing health is the concern at {sh}/100")
    if exp:
        parts.append(f"and {len(exp)} identity(ies) are expiring soon")
    if ev >= 80:
        parts.append(". Environment variable coverage is also solid")
    elif n:
        parts.append(f". The main drag is environment variables: {n} profile(s) have no env var group, holding usage at {ev}/100")
    else:
        parts.append(f". Environment variable usage scores {ev}/100")
    return "".join(parts).replace(" .", ".") + "."

def r_workflow(wq, rng):
    out = [f'<div class="sec"><div class="hdr">Workflow quality · {esc(rng)}</div>']
    profiles = wq.get("per_profile", [])
    out.append('<div class="card" style="margin-bottom:12px;"><div class="ctitle">Workflow completeness</div>'
               '<div class="csub">Most active workflow per trigger type · evaluated against Appcircle ideal flows</div>')
    out.append('<div class="row">')
    for p in profiles:
        plat = OS_MAP.get(p.get("os"), "")
        out.append(f'<div style="flex:1;min-width:180px;background:#F9FAFB;border-radius:6px;padding:10px 12px;">'
                   f'<div style="font-size:13px;font-weight:500;">{esc(p["profile"])}</div><div class="mut2" style="font-size:11px;margin-bottom:8px;">{plat}</div>')
        for kind, badge in (("push", "bpush"), ("pr", "bpr")):
            w = p.get(kind)
            lbl = "Push" if kind == "push" else "PR"
            if w:
                name = w.get("workflow_name", "")
                name = name if len(name) <= 22 else name[:21] + "…"
                color = "var(--orange)" if kind == "push" else "var(--navy)"
                out.append(f'<div style="margin-bottom:6px;"><span class="{badge}">{lbl}</span> <span style="font-weight:500;">{w.get("total_score",0)} / 100</span> <span class="mut2" style="font-size:11px;">{esc(name)}</span>'
                           f'<div class="track3" style="margin-top:3px;"><span class="fill" style="width:{w.get("total_score",0)}%;background:{color};"></span></div></div>')
            else:
                out.append(f'<div style="margin-bottom:6px;" class="mut2"><em>No {lbl}</em></div>')
        out.append('</div>')
    out.append('</div>')

    # Missing steps pooled by tier
    pool = {"Critical": [], "Important": [], "Advanced": []}
    for p in profiles:
        for kind in ("push", "pr"):
            w = p.get(kind)
            if not w:
                continue
            for mg in w.get("missing_groups", []):
                tier = mg.get("tier")
                if tier in pool:
                    pool[tier].append((mg.get("group"), p["profile"], w.get("workflow_name", ""), "Push" if kind == "push" else "PR", p.get("os")))
    tier_meta = [("Critical", "Must have", "var(--red)", "acc-c"), ("Important", "Great to have", "var(--orange)", "acc-a"), ("Advanced", "Good to have", "var(--tm)", "acc-n")]
    for tier, sub, dotc, acc in tier_meta:
        items = pool[tier]
        if not items:
            continue
        groups = {}
        for g, prof, wf, trig, osc in items:
            groups.setdefault(g, []).append((prof, wf, trig, osc))
        out.append(f'<div style="margin-top:12px;"><div style="font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--ts);display:flex;justify-content:space-between;">'
                   f'<span><span style="color:{dotc};">&#9679;</span> {tier} &nbsp; {sub}</span><span>{len(items)}</span></div>')
        for g, affected in groups.items():
            pills = "".join(f'<span class="pill pn"><span class="{ "bpush" if t=="Push" else "bpr" }">{t}</span> {esc(pr)} · {esc(wf)}</span>' for pr, wf, t, _ in affected)
            os_set = {o for _, _, _, o in affected if o is not None}
            tools_html = render_step_tools(g, os_set)
            if tools_html:
                gname = esc(g)
                note = tools_html
            else:
                url = step_title_url(g)
                if url:
                    gname = f'<a href="{esc(url)}" target="_blank" rel="noopener" style="color:inherit;text-decoration:none;border-bottom:1px dotted #9CA3AF;">{esc(g)} <span style="color:#9CA3AF;font-size:11px;">&#8599;</span></a>'
                else:
                    gname = esc(g)
                note = esc(STEP_NOTES.get(g, ""))
            out.append(f'<div class="acc {acc}" style="border-bottom:1px solid var(--bd2);"><div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;">'
                       f'<div><div style="font-size:13px;font-weight:500;">{gname}</div><div class="mut2" style="font-size:12px;">{note}</div></div>'
                       f'<div style="text-align:right;">{pills}</div></div></div>')
        out.append('</div>')
    out.append('</div>')

    # Best practice checks
    issues = wq.get("best_practice_issues", [])
    out.append('<div class="card"><div class="ctitle">Best practice checks</div><div class="csub">Configuration issues detected across active profiles</div>')
    if issues:
        bychk = {}
        for it in issues:
            bychk.setdefault(it.get("check"), []).append(it)
        for chk, items in bychk.items():
            name, desc = BP_MAP.get(chk, (humanize(chk), ""))
            acc = "acc-c" if items[0].get("severity") == "critical" else "acc-a"
            pills = ""
            for it in items:
                extra = f' · {it.get("count")} scripts' if it.get("count", 0) > 1 and "script" in chk else ""
                pills += f'<span class="pp">{esc(it.get("profile",""))} · {esc(it.get("workflow",""))}{extra}</span>'
            out.append(f'<div class="acc {acc}"><div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;">'
                       f'<div><div style="font-size:13px;font-weight:500;">{esc(name)}</div><div class="mut2" style="font-size:12px;">{esc(desc)}</div></div>'
                       f'<div style="text-align:right;">{pills}</div></div></div>')
    else:
        out.append('<div class="mut2" style="font-size:13px;">No configuration issues detected.</div>')
    out.append('</div></div>')
    return "".join(out), []

def r_artifact(ah, rng):
    out = [f'<div class="sec"><div class="hdr">Artifact health · {esc(rng)}</div>']
    sizes = ah.get("artifact_size_per_profile", [])
    out.append('<div class="card" style="margin-bottom:12px;"><div class="ctitle">Artifact size per profile</div>'
               '<div class="csub">Average primary artifact size · top profiles by size</div>')
    if sizes:
        mx = max((s.get("current_avg_size_mb", 0) for s in sizes), default=1) or 1
        for s in sizes:
            w = round(s.get("current_avg_size_mb", 0) / mx * 100)
            out.append(f'<div style="padding:6px 0;"><div class="barbox"><span style="flex:0 0 32%;font-size:13px;font-weight:500;">{esc(s["profile"])}</span>'
                       f'<span class="hbar-track" style="height:8px;"><span class="fill" style="width:{w}%;background:var(--navy);"></span></span>'
                       f'<span style="min-width:64px;text-align:right;font-size:13px;">{s.get("current_avg_size_mb",0):.1f} MB</span></div></div>')
    else:
        out.append('<div class="mut2" style="font-size:13px;">No artifact size data available for this period.</div>')
    out.append('</div>')

    g, sh = ah.get("biggest_grower"), ah.get("biggest_shrinker")
    show_g = bool(g) and g.get("delta_mb") is not None and round(g.get("delta_mb", 0), 1) >= 0.1
    show_s = bool(sh) and sh.get("delta_mb") is not None and round(sh.get("delta_mb", 0), 1) <= -0.1
    if show_g or show_s:
        out.append('<div class="row">')
        if show_g:
            out.append(f'<div class="col card"><div class="acc acc-c"><div class="lbl">Biggest grower</div>'
                       f'<div style="font-size:16px;font-weight:500;margin:4px 0;">{esc(g["profile"])}</div>'
                       f'<div style="color:var(--red);font-weight:500;">&#9650; +{g.get("delta_mb",0):.1f} MB</div>'
                       f'<div class="mut2" style="font-size:12px;">{g.get("prev_avg_size_mb",0):.1f} MB to {g.get("current_avg_size_mb",0):.1f} MB</div></div></div>')
        if show_s:
            out.append(f'<div class="col card"><div class="acc" style="border-left-color:var(--green);"><div class="lbl">Biggest shrinker</div>'
                       f'<div style="font-size:16px;font-weight:500;margin:4px 0;">{esc(sh["profile"])}</div>'
                       f'<div style="color:var(--green);font-weight:500;">&#9660; -{abs(sh.get("delta_mb",0)):.1f} MB</div>'
                       f'<div class="mut2" style="font-size:12px;">{sh.get("prev_avg_size_mb",0):.1f} MB to {sh.get("current_avg_size_mb",0):.1f} MB</div></div></div>')
        out.append('</div>')
    elif g or sh:
        out.append('<div class="mut2" style="font-size:13px;">Artifact sizes were stable this period. No profile grew or shrank by a meaningful amount.</div>')
    out.append('</div>')
    return "".join(out), []

def r_queue(qt, rng):
    out = [f'<div class="sec"><div class="hdr">Queue time · {esc(rng)}</div>']
    p95 = qt.get("p95_wait_minutes", 0)
    p95c = "var(--green)" if p95 <= 5 else ("#D97706" if p95 <= 15 else "var(--red)")
    out.append('<div class="card"><div class="grid">')
    out.append(f'<div class="mcard" style="border-top-color:var(--navy);"><div class="lbl">Avg wait</div><div class="val">{fmt_mins(qt.get("avg_wait_minutes"))}</div></div>')
    out.append(f'<div class="mcard" style="border-top-color:var(--navy);"><div class="lbl">P50 wait</div><div class="val">{fmt_mins(qt.get("p50_wait_minutes"))}</div></div>')
    out.append(f'<div class="mcard" style="border-top-color:var(--navy);"><div class="lbl">P95 wait</div><div class="val" style="color:{p95c};">{fmt_mins(p95)}</div></div>')
    out.append(f'<div class="mcard" style="border-top-color:var(--navy);"><div class="lbl">Total wait</div><div class="val">{fmt_mins(qt.get("total_wait_minutes"))}</div></div>')
    out.append('</div>')
    out.append(f'<div class="mut2" style="font-size:12px;margin-top:8px;">Across {qt.get("build_count",0)} builds with queue data</div>')
    _, _, _bd_pairs = _plan_from_breakdown(qt.get("plan_breakdown"))
    if _bd_pairs:
        bd_txt = " · ".join(f"{t} {fmt_mins(v)}" for t, v in _bd_pairs)
        out.append(f'<div class="mut2" style="font-size:12px;margin-top:2px;">By plan: {bd_txt}</div>')
    trend = qt.get("daily_trend", [])
    scripts = []
    if len(trend) >= 2:
        labels = [short_label(t["date"]) for t in trend]
        data = [t.get("avg_wait_minutes", 0) for t in trend]
        out.append('<div class="csub" style="margin:10px 0 0;">Average queue wait per day.</div>'
                   '<div style="position:relative;width:100%;height:180px;margin-top:6px;"><canvas id="cQ" role="img" aria-label="Average queue wait per day line chart."></canvas></div>')
        scripts.append(_chart_js("cQ", "line", {"labels": labels, "datasets": [
            {"label": "Avg wait", "data": data, "borderColor": "#1A3352", "backgroundColor": "#1A3352", "borderWidth": 2, "pointRadius": 3, "tension": 0.3, "spanGaps": True}]}, y_label_suffix="m"))

    rec = _queue_recommendation(qt)
    if rec:
        btns = "".join(f'<a href="{esc(u)}" target="_blank" rel="noopener" class="qbtn">{esc(l)}</a>' for l, u in rec["buttons"])
        out.append(f'<div class="rec"><div class="rec-l">&#9679; Recommendation</div>'
                   f'<div class="rec-h">{esc(rec["headline"])}</div>'
                   f'<div class="rec-b">{rec["body"]}</div>'
                   f'<div>{btns}</div></div>')

    out.append('</div></div>')
    return "".join(out), scripts

# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

ORDER = [
    ("maturity_assessment", r_maturity),
    ("health_snapshot", r_health),
    ("root_cause", r_root_cause),
    ("workflow_quality", r_workflow),
    ("artifact_health", r_artifact),
    ("queue_time", r_queue),
]

def build_report(envelope):
    if not envelope.get("success", True):
        err = envelope.get("error", {})
        return f"<!doctype html><meta charset=utf-8><body style='font-family:sans-serif;padding:24px;'>Report could not be generated: {esc(err.get('message','unknown error'))}</body>"
    data = envelope.get("data", {})
    meta = envelope.get("meta", {})
    rng = fmt_range(data.get("date_range", {}))
    sections = data.get("sections", {})

    body, scripts = [], []
    for key, fn in ORDER:
        if key in sections and key not in meta.get("omitted_sections", []):
            h, sc = fn(sections[key], rng)
            if h:
                body.append(h)
                scripts.extend(sc)
        # health_snapshot carries trends as a second widget
        if key == "health_snapshot" and key in sections:
            th, ts = r_trends(sections[key], rng)
            if th:
                body.append(th)
                scripts.extend(ts)

    omitted = meta.get("omitted_sections", [])
    if omitted:
        body.append(f'<div class="note">Note: {len(omitted)} section(s) could not be generated from the available data for this period.</div>')

    chart_block = ""
    if scripts:
        _js_pre = (
            'var _cs=getComputedStyle(document.documentElement);'
            'var _tc=_cs.getPropertyValue("--tm").trim()||"#9CA3AF";'
            'var _gc=_cs.getPropertyValue("--bd").trim()||"rgba(0,0,0,0.06)";'
        )
        chart_block = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>'
                       '<script>window.addEventListener("DOMContentLoaded",function(){'
                       + _js_pre + "".join(scripts) + '});</script>')

    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="color-scheme" content="light dark">'
            f'<title>Build Insights Report · {esc(rng)}</title><style>{CSS}</style></head>'
            f'<body><div class="wrap">{"".join(body)}</div>{chart_block}</body></html>')

def main():
    if len(sys.argv) < 2:
        print("usage: python render.py <response.json|-> [output.html]", file=sys.stderr)
        sys.exit(2)
    src = sys.argv[1]
    raw = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
    envelope = json.loads(raw)
    out_path = sys.argv[2] if len(sys.argv) > 2 else "report.html"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(build_report(envelope))
    print(out_path)

if __name__ == "__main__":
    main()
