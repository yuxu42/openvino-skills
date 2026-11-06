#!/usr/bin/env python3
"""
JIRA CPU Issue Tracker
Fetches daily new/closed issue counts for a JIRA project+component and
generates a standalone HTML dashboard with trend and activity charts.

Usage:
    python generate_tracker.py
    python generate_tracker.py --days 60 --output my-tracker.html
    python generate_tracker.py --start 2026-10-01 --end 2026-11-01

Environment variables (or .env file):
    JIRA_URL       Base URL, default https://jira.devtools.intel.com
    JIRA_PAT       Personal Access Token (Bearer auth)
    JIRA_PROJECT   Project key, default CVS
    JIRA_COMPONENT Component name, default "IE CPU Plugin"
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


# ── Defaults ─────────────────────────────────────────────────────────────────
JIRA_URL = os.environ.get("JIRA_URL", "https://jira.devtools.intel.com")
CLOSED_STATUSES = ["Implemented", "In testing", "Verified", "Closed"]
EXPOSURE_FIELD  = "customfield_13805"   # JIRA Exposure custom field


# ── CLI args ─────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        description="Generate JIRA CPU issue daily tracker dashboard"
    )
    p.add_argument("--days", type=int, default=31,
                   help="Days of history to fetch (default 31). Ignored if --start given.")
    p.add_argument("--start", help="Start date YYYY-MM-DD")
    p.add_argument("--end",   help="End date YYYY-MM-DD (inclusive, default: today)")
    p.add_argument("--output", default="cpu-issue-tracker.html",
                   help="Output HTML file path")
    p.add_argument("--pat",   help="JIRA PAT (overrides JIRA_PAT env)")
    p.add_argument("--project",   default=os.environ.get("JIRA_PROJECT", "CVS"))
    p.add_argument("--component", default=os.environ.get("JIRA_COMPONENT", "IE CPU Plugin"))
    p.add_argument("--current-open", type=int,
                   help="Provide current open count directly (skips auto-fetch)")
    p.add_argument("--jira-url", default=JIRA_URL)
    return p.parse_args()


# ── JIRA API ─────────────────────────────────────────────────────────────────
def jira_request(pat, url, params=None, jira_url=JIRA_URL):
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json",
    }
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def jira_search_all(pat, jql, fields="key,summary,created,updated,priority,status",
                    jira_url=JIRA_URL, page_size=100):
    """Paginate through all JIRA search results."""
    base = f"{jira_url}/rest/api/2/search"
    results, start = [], 0
    while True:
        data = jira_request(pat, base, {
            "jql": jql,
            "startAt": start,
            "maxResults": page_size,
            "fields": fields,
        }, jira_url)
        issues = data.get("issues", [])
        total  = data.get("total", 0)
        results.extend(issues)
        start += len(issues)
        print(f"  fetched {min(start, total)}/{total}", end="\r", flush=True)
        if start >= total or not issues:
            break
        time.sleep(0.5)
    print(flush=True)
    return results


def get_current_open(pat, project, component, jira_url=JIRA_URL):
    """Return the current open issue count using the same filter logic."""
    closed_in = ", ".join(f'"{s}"' for s in CLOSED_STATUSES)
    jql = (
        f'project = {project} AND component = "{component}"'
        f' AND status not in ({closed_in})'
    )
    base = f"{jira_url}/rest/api/2/search"
    data = jira_request(pat, base, {"jql": jql, "maxResults": 0, "fields": "key"}, jira_url)
    return data.get("total", 0)


# ── Data fetching ─────────────────────────────────────────────────────────────
def fetch_data(pat, project, component, start_date, end_date, jira_url=JIRA_URL):
    closed_in = ", ".join(f'"{s}"' for s in CLOSED_STATUSES)
    day_before = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Fetching new issues ({start_date} → {end_date})...")
    new_jql = (
        f'project = {project} AND component = "{component}"'
        f' AND created >= "{start_date}" AND created <= "{end_date}"'
        f' ORDER BY created ASC'
    )
    new_issues = jira_search_all(pat, new_jql, jira_url=jira_url)
    print(f"  → {len(new_issues)} new issues")

    print(f"Fetching resolved issues (after {day_before})...")
    closed_jql = (
        f'project = {project} AND component = "{component}"'
        f' AND status changed to ({closed_in}) after "{day_before}"'
        f' AND status changed to ({closed_in}) before "{end_date} 23:59"'
        f' ORDER BY updated ASC'
    )
    closed_issues = jira_search_all(pat, closed_jql, jira_url=jira_url)
    print(f"  → {len(closed_issues)} resolved issues")

    return new_issues, closed_issues


def fetch_high_exposure_bugs(pat, project, component, jira_url=JIRA_URL):
    """
    Fetch open Bug tickets with Critical or High exposure (issuetype=Bug only).
    Returns list of dicts with key, summary, status, exposure, created, updated.

    NOTE: The Exposure field (customfield_13805) captures customer-facing impact.
          Filtering by issuetype=Bug avoids conflating Epics/Stories with defects.
    """
    closed_in = ", ".join(f'"{s}"' for s in CLOSED_STATUSES)
    jql = (
        f'project = {project} AND component = "{component}"'
        f' AND issuetype = Bug'
        f' AND status not in ({closed_in})'
        f' AND "Exposure" in ("1-Critical","2-High")'
        f' ORDER BY EXPOSURE ASC, updated DESC'
    )
    fields = f"key,summary,priority,status,created,updated,{EXPOSURE_FIELD}"
    issues = jira_search_all(pat, jql, fields=fields, jira_url=jira_url)

    result = []
    for iss in issues:
        f = iss["fields"]
        exp_field = f.get(EXPOSURE_FIELD) or {}
        result.append({
            "key":     iss["key"],
            "summary": (f.get("summary") or "")[:120],
            "status":  f["status"]["name"],
            "exposure": exp_field.get("value", "") if isinstance(exp_field, dict) else "",
            "created": (f.get("created") or "")[:10],
            "updated": (f.get("updated") or "")[:10],
        })
    return result


def fetch_exposure_map(pat, keys, jira_url=JIRA_URL):
    """Return {issue_key: exposure_value} for a list of keys."""
    if not keys:
        return {}
    jql = f'issue in ({",".join(keys)})'
    fields = f"key,{EXPOSURE_FIELD}"
    issues = jira_search_all(pat, jql, fields=fields, jira_url=jira_url)
    out = {}
    for iss in issues:
        exp = iss["fields"].get(EXPOSURE_FIELD) or {}
        out[iss["key"]] = exp.get("value", "") if isinstance(exp, dict) else ""
    return out


# ── Daily breakdown ───────────────────────────────────────────────────────────
def build_daily(new_issues, closed_issues, start_date, end_date):
    days = []
    d = datetime.strptime(start_date, "%Y-%m-%d")
    end_d = datetime.strptime(end_date, "%Y-%m-%d")
    while d <= end_d:
        days.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)

    new_by_day    = defaultdict(list)
    closed_by_day = defaultdict(list)

    for iss in new_issues:
        created = iss["fields"]["created"][:10]
        if start_date <= created <= end_date:
            new_by_day[created].append({
                "key": iss["key"],
                "s":   (iss["fields"].get("summary") or "")[:90],
                "p":   _prio(iss["fields"].get("priority", {})),
            })

    for iss in closed_issues:
        updated = iss["fields"]["updated"][:10]
        if start_date <= updated <= end_date:
            closed_by_day[updated].append({
                "key": iss["key"],
                "s":   (iss["fields"].get("summary") or "")[:90],
                "p":   _prio(iss["fields"].get("priority", {})),
                "st":  iss["fields"]["status"]["name"],
            })

    status_counts = defaultdict(int)
    for iss in closed_issues:
        status_counts[iss["fields"]["status"]["name"]] += 1

    return days, new_by_day, closed_by_day, dict(status_counts)


def _prio(p):
    name = (p or {}).get("name", "")
    if "P1" in name or "Stopper" in name: return "P1"
    if "P2" in name or "High" in name:    return "P2"
    if "P3" in name or "Medium" in name:  return "P3"
    if "P4" in name or "Low" in name:     return "P4"
    return ""


def compute_open_totals(days, new_by_day, closed_by_day, current_open):
    """Back-calculate open counts from current_open using daily deltas."""
    daily_new    = [len(new_by_day[d])    for d in days]
    daily_closed = [len(closed_by_day[d]) for d in days]
    n = len(days)
    open_total = [0] * n
    open_total[-1] = current_open
    for i in range(n - 2, -1, -1):
        open_total[i] = open_total[i+1] - daily_new[i+1] + daily_closed[i+1]
    return daily_new, daily_closed, open_total


# ── HTML template ─────────────────────────────────────────────────────────────
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{{TITLE}}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;background:#0f1117;color:#e2e8f0;min-height:100vh;padding:32px 24px}
.container{max-width:1300px;margin:0 auto}
header{margin-bottom:36px}
.hdr{display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:12px}
h1{font-size:1.9rem;font-weight:700;color:#f8fafc;letter-spacing:-.5px}
h1 span{color:#f87171}
.badge{display:inline-flex;align-items:center;gap:6px;background:#1a0f0f;border:1px solid #7f1d1d;color:#fca5a5;padding:6px 14px;border-radius:20px;font-size:.82rem;font-weight:500}
.badge::before{content:'';width:7px;height:7px;border-radius:50%;background:#f87171;display:inline-block}
.sub{color:#94a3b8;font-size:.86rem;margin-top:6px}
.sub a{color:#f87171;text-decoration:none}
/* Summary */
.sg{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:24px}
@media(max-width:900px){.sg{grid-template-columns:repeat(3,1fr)}}
.sc{background:#1e2130;border:1px solid #2d3348;border-radius:12px;padding:18px 20px}
.sl{font-size:.70rem;color:#64748b;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin-bottom:8px}
.sv{font-size:2.1rem;font-weight:700;line-height:1}
.ss{font-size:.74rem;color:#64748b;margin-top:5px}
/* Status pills */
.sr{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}
.sp{background:#1e2130;border:1px solid #2d3348;border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:12px}
.si{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:.9rem;flex-shrink:0}
.pn{font-size:.68rem;color:#64748b;text-transform:uppercase;letter-spacing:.7px;font-weight:600}
.pv{font-size:1.1rem;font-weight:700}
/* Panel */
.panel{background:#1e2130;border:1px solid #2d3348;border-radius:12px;padding:22px;margin-bottom:20px}
.pt{font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:#64748b;margin-bottom:16px}
.cw{width:100%;overflow-x:auto}
.cw svg{display:block}
.leg{display:flex;gap:20px;margin-top:12px;font-size:.74rem;color:#94a3b8;flex-wrap:wrap}
.li{display:flex;align-items:center;gap:6px}
.ld{width:12px;height:12px;border-radius:3px;flex-shrink:0}
.dn{font-size:.72rem;color:#475569;margin-top:12px;line-height:1.5}
/* Exposure panel */
.ci-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:900px){.ci-grid{grid-template-columns:1fr}}
.ci-col-title{font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #2d3348}
.ci-row{display:flex;align-items:flex-start;gap:10px;padding:9px 0;border-bottom:1px solid #161b27}
.ci-row:last-child{border-bottom:none}
.ci-left{min-width:160px;flex-shrink:0}
.ci-key a{color:#60a5fa;text-decoration:none;font-weight:700;font-size:.75rem}
.ci-key a:hover{text-decoration:underline}
.ci-meta{font-size:.63rem;color:#475569;margin-top:3px}
.ci-summary{color:#94a3b8;font-size:.76rem;flex:1}
.new-tag{background:rgba(248,113,113,.15);color:#f87171;padding:1px 5px;border-radius:4px;font-size:.62rem;font-weight:700}
/* Status badges (exposure panel) */
.st-open    {background:rgba(248,113,113,.18);color:#f87171;padding:2px 6px;border-radius:5px;font-size:.67rem;font-weight:700}
.st-needinfo{background:rgba(251,191,36,.15);color:#fbbf24;padding:2px 6px;border-radius:5px;font-size:.67rem;font-weight:700}
.st-deferred{background:rgba(100,116,139,.18);color:#94a3b8;padding:2px 6px;border-radius:5px;font-size:.67rem;font-weight:600}
.st-generic {background:rgba(100,116,139,.15);color:#94a3b8;padding:2px 6px;border-radius:5px;font-size:.67rem;font-weight:600}
/* Activity log */
.at{width:100%;border-collapse:collapse}
.at thead th{font-size:.69rem;text-transform:uppercase;letter-spacing:.7px;color:#64748b;font-weight:700;padding:0 8px 10px 0;text-align:left;border-bottom:1px solid #2d3348}
.at tbody tr{border-bottom:1px solid #161b27}
.at tbody tr:last-child{border-bottom:none}
.at tbody td{padding:9px 8px 9px 0;font-size:.79rem;vertical-align:top}
.dc{color:#94a3b8;font-weight:600;white-space:nowrap;width:88px}
.dc .dw{font-size:.63rem;color:#475569;display:block}
.il{display:flex;flex-direction:column;gap:5px}
.ip{display:flex;align-items:flex-start;gap:5px}
.ik a{color:#60a5fa;text-decoration:none;font-weight:600;font-size:.73rem;white-space:nowrap}
.ik a:hover{text-decoration:underline}
.is{color:#94a3b8;font-size:.75rem}
.p1{background:rgba(248,113,113,.18);color:#f87171;padding:1px 5px;border-radius:4px;font-size:.62rem;font-weight:700;white-space:nowrap}
.p2{background:rgba(251,191,36,.15);color:#fbbf24;padding:1px 5px;border-radius:4px;font-size:.62rem;font-weight:700;white-space:nowrap}
.p3{background:rgba(96,165,250,.12);color:#60a5fa;padding:1px 5px;border-radius:4px;font-size:.62rem;font-weight:700;white-space:nowrap}
.si-impl{background:rgba(52,211,153,.12);color:#34d399;padding:1px 5px;border-radius:4px;font-size:.62rem;font-weight:600;white-space:nowrap}
.si-cl{background:rgba(100,116,139,.15);color:#94a3b8;padding:1px 5px;border-radius:4px;font-size:.62rem;font-weight:600;white-space:nowrap}
.si-it{background:rgba(251,191,36,.12);color:#fbbf24;padding:1px 5px;border-radius:4px;font-size:.62rem;font-weight:600;white-space:nowrap}
.si-vr{background:rgba(129,140,248,.12);color:#818cf8;padding:1px 5px;border-radius:4px;font-size:.62rem;font-weight:600;white-space:nowrap}
/* Exposure inline badges */
.exp-crit{background:#7f1d1d;color:#fca5a5;padding:1px 5px;border-radius:4px;font-size:.62rem;font-weight:700;white-space:nowrap}
.exp-high{background:#78350f;color:#fcd34d;padding:1px 5px;border-radius:4px;font-size:.62rem;font-weight:700;white-space:nowrap}
/* Row-level exposure highlight */
.exp-critical-row td{border-left:3px solid #f87171;padding-left:8px}
.exp-high-row td{border-left:3px solid #fbbf24;padding-left:8px}
.dp{color:#f87171;font-weight:700}.dn2{color:#34d399;font-weight:700}.dz{color:#334155}
.on{color:#818cf8;font-weight:700}
.wr td{background:rgba(255,255,255,.018)}
.c-r{color:#f87171}.c-g{color:#34d399}.c-a{color:#fbbf24}.c-p{color:#818cf8}
footer{text-align:center;color:#334155;font-size:.74rem;margin-top:40px}
</style>
</head>
<body>
<div class="container">
<header>
<div class="hdr">
<div>
<h1>CPU Plugin <span>Issue Tracker</span></h1>
<p class="sub">JIRA &mdash; project <strong>{{PROJECT}}</strong> &mdash; component <strong>"{{COMPONENT}}"</strong>
&nbsp;&middot;&nbsp; Closed&nbsp;=&nbsp;Implemented&nbsp;|&nbsp;In Testing&nbsp;|&nbsp;Verified&nbsp;|&nbsp;Closed</p>
</div>
<span class="badge">{{START_DATE}} &ndash; {{END_DATE}} &nbsp;&middot;&nbsp; {{N_DAYS}} days</span>
</div>
</header>

<div class="sg">
<div class="sc"><div class="sl">Current Open</div><div class="sv c-r">{{CURRENT_OPEN}}</div><div class="ss">As of {{END_DATE}}</div></div>
<div class="sc"><div class="sl">Period Start Est.</div><div class="sv c-p">{{START_OPEN}}</div><div class="ss">Back-calc from {{START_DATE}}</div></div>
<div class="sc"><div class="sl">Net Change</div><div class="sv c-a">{{NET_SIGN}}{{NET_CHANGE}}</div><div class="ss">{{TOTAL_NEW}} new &minus; {{TOTAL_CLOSED}} resolved</div></div>
<div class="sc"><div class="sl">New Filed</div><div class="sv c-r">{{TOTAL_NEW}}</div><div class="ss">{{START_DATE}} &ndash; {{END_DATE}}</div></div>
<div class="sc"><div class="sl">Resolved</div><div class="sv c-g">{{TOTAL_CLOSED}}</div><div class="ss">Impl / InTest / Verified / Closed</div></div>
</div>

<div class="sr">
<div class="sp"><div class="si" style="background:rgba(52,211,153,.15);color:#34d399;">&#10003;</div><div><div class="pn">Implemented</div><div class="pv c-g">{{CNT_IMPL}}</div></div></div>
<div class="sp"><div class="si" style="background:rgba(100,116,139,.15);color:#94a3b8;">&#128274;</div><div><div class="pn">Closed</div><div class="pv" style="color:#94a3b8;">{{CNT_CLOSED}}</div></div></div>
<div class="sp"><div class="si" style="background:rgba(251,191,36,.12);color:#fbbf24;">&#128300;</div><div><div class="pn">In Testing</div><div class="pv c-a">{{CNT_INTEST}}</div></div></div>
<div class="sp"><div class="si" style="background:rgba(129,140,248,.12);color:#818cf8;">&#10004;</div><div><div class="pn">Verified</div><div class="pv c-p">{{CNT_VERIFIED}}</div></div></div>
</div>

<div class="panel">
<div class="pt">Critical &amp; High Exposure Bugs
<span style="color:#334155;font-weight:400;text-transform:none;letter-spacing:0;font-size:.74rem;">&nbsp;&mdash; open bugs (issuetype=Bug) with highest customer impact</span></div>
<div class="ci-grid">
<div>
<div class="ci-col-title" style="color:#f87171;">&#128308; 1-Critical &nbsp;<span style="color:#334155;font-weight:400;" id="critCount"></span></div>
<div id="critList"></div>
</div>
<div>
<div class="ci-col-title" style="color:#fcd34d;">&#9888; 2-High &nbsp;<span style="color:#334155;font-weight:400;" id="highCount"></span></div>
<div id="highList"></div>
</div>
</div>
<p class="dn" style="margin-top:14px;">Filter: <code style="color:#475569;">issuetype=Bug AND "Exposure" in ("1-Critical","2-High") AND status not in (Implemented,"In testing",Verified,Closed)</code>
&bull; Issues marked <span class="new-tag">New</span> were filed in this tracking period.</p>
</div>

<div class="panel">
<div class="pt">Open Issue Count Trend (end-of-day)</div>
<div class="cw"><svg id="tc" viewBox="0 0 1200 240" preserveAspectRatio="xMidYMid meet" style="width:100%;height:240px;"></svg></div>
<div class="leg"><div class="li"><div class="ld" style="background:#818cf8;"></div>Total open issues (end of day)</div></div>
<p class="dn">Running total back-calculated from confirmed current open count (<strong>{{CURRENT_OPEN}}</strong> as of {{END_DATE}}) using daily new/resolved deltas.</p>
</div>

<div class="panel">
<div class="pt">Daily Activity &mdash; New vs Resolved Issues</div>
<div class="cw"><svg id="ac" viewBox="0 0 1200 200" preserveAspectRatio="xMidYMid meet" style="width:100%;height:200px;"></svg></div>
<div class="leg">
<div class="li"><div class="ld" style="background:#f87171;"></div>New issues filed</div>
<div class="li"><div class="ld" style="background:#34d399;"></div>Resolved (Implemented / Closed / In Testing / Verified)</div>
</div>
<p class="dn">Weekends shown at reduced opacity. Rows with a coloured left border contain High (amber) or Critical (red) exposure bugs.</p>
</div>

<div class="panel">
<div class="pt">Day-by-Day Activity Log <span style="color:#334155;font-weight:400;text-transform:none;letter-spacing:0;font-size:.74rem;">(active days only)</span></div>
<table class="at">
<thead><tr>
<th style="width:85px;">Date</th><th style="width:50px;">New</th><th style="width:65px;">Resolved</th>
<th style="width:65px;">Delta</th><th style="width:75px;">Open EOD</th>
<th>New Issues Filed</th><th>Resolved Issues</th>
</tr></thead>
<tbody id="log"></tbody>
</table>
<p class="dn">Open EOD = open count at end of day (back-calculated). JQL: <code style="color:#475569;">status changed to (Implemented, "In testing", Verified, Closed) after "{{START_DATE}}"</code></p>
</div>
</div>
<footer>Generated {{GEN_DATE}} &bull; Source: JIRA REST API &bull; project {{PROJECT}} &middot; component "{{COMPONENT}}"</footer>

<script>
const JIRA = "{{JIRA_URL}}/browse/";
const days         = {{DAYS_JSON}};
const daily_new    = {{DAILY_NEW_JSON}};
const daily_closed = {{DAILY_CLOSED_JSON}};
const open_total   = {{OPEN_TOTAL_JSON}};
const newDetails   = {{NEW_DETAILS_JSON}};
const closedDetails = {{CLOSED_DETAILS_JSON}};
// Exposure map: {key -> exposure_value} for all issues tracked in this period
const EXPOSURE_MAP = {{EXPOSURE_MAP_JSON}};
// Open Bug tickets with Critical/High exposure
const HIGH_EXP_BUGS = {{HIGH_EXP_BUGS_JSON}};
// Issue keys filed in this period
const PERIOD_KEYS = new Set({{PERIOD_KEYS_JSON}});

// ── Exposure panel ────────────────────────────────────────────────────────────
(function(){
  const STATUS_CLS = {'Open':'st-open','Need Info':'st-needinfo','Deferred':'st-deferred'};
  function stBadge(s){ return `<span class="${STATUS_CLS[s]||'st-generic'}">${s}</span>`; }

  function row(item){
    const isNew = PERIOD_KEYS.has(item.key);
    return `<div class="ci-row">
      <div class="ci-left">
        <div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;">
          <span class="ci-key"><a href="${JIRA}${item.key}" target="_blank">${item.key}</a></span>
          ${stBadge(item.status)}${isNew?'<span class="new-tag">New</span>':''}
        </div>
        <div class="ci-meta">Filed ${item.created} &middot; upd ${item.updated}</div>
      </div>
      <span class="ci-summary">${item.s}</span>
    </div>`;
  }

  const crit = HIGH_EXP_BUGS.filter(i=>i.exp==='1-Critical');
  const high = HIGH_EXP_BUGS.filter(i=>i.exp==='2-High');
  document.getElementById('critCount').textContent = `${crit.length} open`;
  document.getElementById('highCount').textContent = `${high.length} open`;
  document.getElementById('critList').innerHTML = crit.length
    ? crit.map(row).join('')
    : '<p style="color:#334155;font-size:.8rem;padding:12px 0;">No open 1-Critical bugs.</p>';
  document.getElementById('highList').innerHTML = high.length
    ? high.map(row).join('')
    : '<p style="color:#334155;font-size:.8rem;padding:12px 0;">No open 2-High bugs.</p>';
})();

// ── Chart helpers ─────────────────────────────────────────────────────────────
const N=days.length,PL=52,PR=16,PT=18,PB=36,W=1200;
const cW=(W-PL-PR)/N;
function isWE(d){const x=new Date(d+'T12:00:00Z');return x.getUTCDay()===0||x.getUTCDay()===6;}
function dl(d){const[,m,dy]=d.split('-');return `${parseInt(m)}/${parseInt(dy)}`;}
function xs(i){return PL+i*cW+cW/2;}
function xc(i){return PL+i*cW;}
const DOW=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const intv=Math.max(1,Math.round(N/12));

// ── Trend chart ───────────────────────────────────────────────────────────────
(function(){
  const H=240,cH=H-PT-PB;
  const minV=Math.min(...open_total)-4,maxV=Math.max(...open_total)+6;
  function ys(v){return PT+cH-(v-minV)/(maxV-minV)*cH;}
  let h='';
  days.forEach((d,i)=>{if(isWE(d))h+=`<rect x="${xc(i)}" y="${PT}" width="${cW}" height="${cH}" fill="rgba(255,255,255,.025)"/>`;});
  const step=5;
  for(let v=Math.ceil(minV/step)*step;v<=maxV;v+=step){
    const y=ys(v);
    h+=`<line x1="${PL}" y1="${y}" x2="${W-PR}" y2="${y}" stroke="#1a2535" stroke-width="1"/>`;
    h+=`<text x="${PL-5}" y="${y+4}" text-anchor="end" fill="#334155" font-size="10">${v}</text>`;
  }
  const pts=days.map((_,i)=>`${xs(i)},${ys(open_total[i])}`).join(' ');
  const bY=PT+cH;
  h+=`<polygon points="${xs(0)},${bY} ${pts} ${xs(N-1)},${bY}" fill="rgba(129,140,248,.1)"/>`;
  h+=`<polyline points="${pts}" fill="none" stroke="#818cf8" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
  days.forEach((d,i)=>{
    const act=daily_new[i]>0||daily_closed[i]>0;
    if(act||i===0||i===N-1) h+=`<circle cx="${xs(i)}" cy="${ys(open_total[i])}" r="${i===N-1?5:3}" fill="${i===N-1?'#f87171':'#4338ca'}" stroke="${i===N-1?'#fca5a5':'#6366f1'}" stroke-width="1.5"/>`;
  });
  const pi=open_total.indexOf(Math.max(...open_total));
  h+=`<text x="${xs(0)}" y="${ys(open_total[0])-9}" text-anchor="middle" fill="#818cf8" font-size="10" font-weight="600">${open_total[0]}</text>`;
  h+=`<text x="${xs(N-1)}" y="${ys(open_total[N-1])-9}" text-anchor="middle" fill="#f87171" font-size="10" font-weight="700">${open_total[N-1]}</text>`;
  h+=`<text x="${xs(pi)}" y="${ys(open_total[pi])-10}" text-anchor="middle" fill="#fbbf24" font-size="10" font-weight="600">&#9650; Peak ${open_total[pi]}</text>`;
  h+=`<line x1="${PL}" y1="${bY}" x2="${W-PR}" y2="${bY}" stroke="#2d3348" stroke-width="1"/>`;
  days.forEach((d,i)=>{if(i%intv===0||i===N-1) h+=`<text x="${xs(i)}" y="${H-7}" text-anchor="middle" fill="${i===N-1?'#f87171':'#334155'}" font-size="9">${dl(d)}</text>`;});
  document.getElementById('tc').innerHTML=h;
})();

// ── Activity chart ────────────────────────────────────────────────────────────
(function(){
  const H=200,cH=H-PT-PB;
  const maxA=Math.max(...daily_new,...daily_closed,1);
  const bW=Math.max(cW*0.38,3);
  function ya(v){return PT+cH-v/(maxA+1)*cH;}
  let h='';
  for(let v=2;v<=maxA;v+=2){
    const y=ya(v);
    h+=`<line x1="${PL}" y1="${y}" x2="${W-PR}" y2="${y}" stroke="#1a2030" stroke-width="1"/>`;
    h+=`<text x="${PL-5}" y="${y+4}" text-anchor="end" fill="#334155" font-size="10">${v}</text>`;
  }
  const bY=PT+cH;
  days.forEach((d,i)=>{
    const wk=isWE(d)?0.4:1,cx=xs(i),nv=daily_new[i],cv=daily_closed[i];
    if(nv>0){const bh=bY-ya(nv);h+=`<rect x="${cx-bW-1}" y="${ya(nv)}" width="${bW}" height="${bh}" fill="#f87171" opacity="${wk}" rx="2"/>`;if(nv>=4)h+=`<text x="${cx-bW/2-1}" y="${ya(nv)-3}" text-anchor="middle" fill="#f87171" font-size="9" font-weight="600">${nv}</text>`;}
    if(cv>0){const bh=bY-ya(cv);h+=`<rect x="${cx+1}" y="${ya(cv)}" width="${bW}" height="${bh}" fill="#34d399" opacity="${wk}" rx="2"/>`;if(cv>=4)h+=`<text x="${cx+bW/2+1}" y="${ya(cv)-3}" text-anchor="middle" fill="#34d399" font-size="9" font-weight="600">${cv}</text>`;}
  });
  h+=`<line x1="${PL}" y1="${bY}" x2="${W-PR}" y2="${bY}" stroke="#2d3348" stroke-width="1"/>`;
  days.forEach((d,i)=>{if(i%intv===0||i===N-1) h+=`<text x="${xs(i)}" y="${H-7}" text-anchor="middle" fill="#334155" font-size="9">${dl(d)}</text>`;});
  document.getElementById('ac').innerHTML=h;
})();

// ── Activity log ──────────────────────────────────────────────────────────────
(function(){
  const tb=document.getElementById('log');
  const stM={'Implemented':'si-impl','Closed':'si-cl','In Testing':'si-it','Verified':'si-vr'};
  const stL={'Implemented':'Impl','Closed':'Closed','In Testing':'InTest','Verified':'Verified'};
  const pM={'P1':'p1','P2':'p2','P3':'p3','P4':'p3'};

  function expBadge(key){
    const e=EXPOSURE_MAP[key]||'';
    if(e==='1-Critical') return '<span class="exp-crit">&#128308;&thinsp;Critical</span> ';
    if(e==='2-High')     return '<span class="exp-high">&#9888;&thinsp;High</span> ';
    return '';
  }

  function issRows(arr){
    if(!arr||!arr.length) return '<span style="color:#1e293b;">&mdash;</span>';
    return '<div class="il">'+arr.map(it=>{
      const pb=it.p&&pM[it.p]?`<span class="${pM[it.p]}">${it.p}</span> `:'';
      const sb=it.st?`<span class="${stM[it.st]||'si-cl'}">${stL[it.st]||it.st}</span> `:'';
      return `<div class="ip"><span class="ik"><a href="${JIRA}${it.key}" target="_blank">${it.key}</a></span> ${pb}${expBadge(it.key)}${sb}<span class="is">${it.s}</span></div>`;
    }).join('')+'</div>';
  }

  function rowExpCls(d){
    const keys=[...(newDetails[d]||[]),...(closedDetails[d]||[])].map(x=>x.key);
    if(keys.some(k=>EXPOSURE_MAP[k]==='1-Critical')) return 'exp-critical-row';
    if(keys.some(k=>EXPOSURE_MAP[k]==='2-High'))     return 'exp-high-row';
    return '';
  }

  days.forEach((d,i)=>{
    const nv=daily_new[i],cv=daily_closed[i];
    if(!nv&&!cv) return;
    const delta=nv-cv,dO=new Date(d+'T12:00:00Z'),dow=DOW[dO.getUTCDay()];
    const cls=[isWE(d)?'wr':'',rowExpCls(d)].filter(Boolean).join(' ');
    const dh=delta>0?`<span class="dp">+${delta}</span>`:delta<0?`<span class="dn2">${delta}</span>`:`<span class="dz">&plusmn;0</span>`;
    tb.innerHTML+=`<tr class="${cls}"><td class="dc">${d.slice(5)}<span class="dw">${dow}${isWE(d)?' &middot; wknd':''}</span></td><td style="color:#f87171;font-weight:700;">${nv||'&mdash;'}</td><td style="color:#34d399;font-weight:700;">${cv||'&mdash;'}</td><td>${dh}</td><td><span class="on">${open_total[i]}</span></td><td>${issRows(newDetails[d])}</td><td>${issRows(closedDetails[d])}</td></tr>`;
  });
})();
</script>
</body>
</html>"""


def render_html(template, data):
    """Simple {{KEY}} substitution."""
    result = template
    for k, v in data.items():
        result = result.replace("{{" + k + "}}", str(v))
    return result


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    args = parse_args()

    # Load .env if present
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    pat = args.pat or os.environ.get("JIRA_PAT", "")
    if not pat:
        print("ERROR: JIRA PAT required. Set JIRA_PAT env var or use --pat.", file=sys.stderr)
        sys.exit(1)

    jira_url  = args.jira_url
    project   = args.project
    component = args.component

    # Date range
    today = datetime.now(timezone.utc).date()
    end_date   = args.end   or today.strftime("%Y-%m-%d")
    if args.start:
        start_date = args.start
    else:
        start_dt = today - timedelta(days=args.days - 1)
        start_date = start_dt.strftime("%Y-%m-%d")

    n_days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1
    print(f"Period: {start_date} → {end_date} ({n_days} days)")

    # Fetch daily new/resolved data
    new_issues, closed_issues = fetch_data(pat, project, component, start_date, end_date, jira_url)
    days, new_by_day, closed_by_day, status_counts = build_daily(
        new_issues, closed_issues, start_date, end_date
    )

    # Current open count
    if args.current_open is not None:
        current_open = args.current_open
        print(f"Using provided current open count: {current_open}")
    else:
        print("Fetching current open count...")
        current_open = get_current_open(pat, project, component, jira_url)
        print(f"  → {current_open} open")

    daily_new, daily_closed, open_total = compute_open_totals(
        days, new_by_day, closed_by_day, current_open
    )

    # Collect all period issue keys for exposure lookup
    all_period_keys = list({
        iss["key"] for iss in new_issues + closed_issues
    })
    print(f"Fetching exposure field for {len(all_period_keys)} period issues...")
    exposure_map = fetch_exposure_map(pat, all_period_keys, jira_url)

    # Fetch open high-exposure bugs
    print("Fetching Critical/High exposure open bugs...")
    high_exp_bugs = fetch_high_exposure_bugs(pat, project, component, jira_url)
    print(f"  → {len(high_exp_bugs)} bugs (1-Critical: {sum(1 for b in high_exp_bugs if b['exposure']=='1-Critical')}, 2-High: {sum(1 for b in high_exp_bugs if b['exposure']=='2-High')})")

    total_new    = sum(daily_new)
    total_closed = sum(daily_closed)
    start_open   = open_total[0]
    net_change   = current_open - start_open

    print(f"\nSummary:")
    print(f"  New:          {total_new}")
    print(f"  Resolved:     {total_closed}")
    print(f"  Net change:   {net_change:+d}")
    print(f"  Peak open:    {max(open_total)} ({days[open_total.index(max(open_total))]})")

    # Build JSON for template
    new_details_json = {
        d: [{"key": i["key"], "s": i["s"], "p": i["p"]} for i in items]
        for d, items in new_by_day.items()
    }
    closed_details_json = {
        d: [{"key": i["key"], "s": i["s"], "p": i["p"], "st": i["st"]} for i in items]
        for d, items in closed_by_day.items()
    }
    # Rename 'summary' key to 's' for the template
    high_exp_for_js = [
        {"key": b["key"], "s": b["summary"], "status": b["status"],
         "exp": b["exposure"], "created": b["created"], "updated": b["updated"]}
        for b in high_exp_bugs
    ]
    period_keys_list = list({iss["key"] for iss in new_issues})

    html = render_html(HTML_TEMPLATE, {
        "TITLE":            f"CPU Plugin Issue Tracker · {start_date} – {end_date}",
        "PROJECT":          project,
        "COMPONENT":        component,
        "START_DATE":       start_date,
        "END_DATE":         end_date,
        "N_DAYS":           n_days,
        "GEN_DATE":         today.strftime("%b %d, %Y"),
        "JIRA_URL":         jira_url,
        "CURRENT_OPEN":     current_open,
        "START_OPEN":       start_open,
        "NET_SIGN":         "+" if net_change >= 0 else "",
        "NET_CHANGE":       net_change,
        "TOTAL_NEW":        total_new,
        "TOTAL_CLOSED":     total_closed,
        "CNT_IMPL":         status_counts.get("Implemented", 0),
        "CNT_CLOSED":       status_counts.get("Closed", 0),
        "CNT_INTEST":       status_counts.get("In Testing", 0),
        "CNT_VERIFIED":     status_counts.get("Verified", 0),
        "DAYS_JSON":        json.dumps(days),
        "DAILY_NEW_JSON":   json.dumps(daily_new),
        "DAILY_CLOSED_JSON": json.dumps(daily_closed),
        "OPEN_TOTAL_JSON":  json.dumps(open_total),
        "NEW_DETAILS_JSON": json.dumps(new_details_json),
        "CLOSED_DETAILS_JSON": json.dumps(closed_details_json),
        "EXPOSURE_MAP_JSON": json.dumps(exposure_map),
        "HIGH_EXP_BUGS_JSON": json.dumps(high_exp_for_js),
        "PERIOD_KEYS_JSON": json.dumps(period_keys_list),
    })

    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    print(f"\nDashboard written to: {out.resolve()}")


if __name__ == "__main__":
    main()
