---
name: jira-cpu-issue-tracker
description: Generate a daily JIRA issue tracking dashboard for the OpenVINO CPU Plugin component. Shows new issues filed, resolved issues (Implemented/Closed/In Testing/Verified), and a running open-issue count trend over a configurable date range.
---

# JIRA CPU Issue Tracker

## Overview

Fetches daily new and resolved issues from Intel JIRA for a specific project and component, back-calculates the running open-issue count from the confirmed current total, and generates a self-contained HTML dashboard with:

- **Summary cards** — current open, start estimate, net change, new, resolved
- **Status breakdown** — Implemented / Closed / In Testing / Verified counts
- **Trend chart** — open issue count per day (SVG area+line)
- **Activity chart** — daily new vs resolved bar chart (SVG)
- **Activity log** — day-by-day table with clickable JIRA issue links, priority badges, and resolution status

No external charting libraries required — charts are rendered via inline SVG + JavaScript.

## When to Use

- Weekly/monthly JIRA defect health reviews
- Sprint retrospectives (see if open count is trending up or down)
- Manager/stakeholder reports on backlog health
- Detecting filing spikes (e.g. a bad hardware bring-up week)

## Prerequisites

- Python 3.8+ (stdlib only — no pip install needed)
- JIRA Personal Access Token with read access to the target project
- Network access to `jira.devtools.intel.com` (or your JIRA instance)

## Setup

```bash
cp .env.example .env
# Edit .env and fill in JIRA_PAT
```

## Usage

### Basic (last 31 days)

```bash
python generate_tracker.py
```

### Custom date range

```bash
python generate_tracker.py --start 2026-10-01 --end 2026-11-05
```

### Longer history

```bash
python generate_tracker.py --days 90 --output q4-tracker.html
```

### Different project / component

```bash
python generate_tracker.py \
  --project CVS \
  --component "IE GPU Plugin" \
  --output gpu-tracker.html
```

### Skip current-open API call (use known value)

```bash
# If you already know the current open count from the JIRA filter UI:
python generate_tracker.py --current-open 392
```

## Configuration

### Environment variables (.env)

```bash
JIRA_URL=https://jira.devtools.intel.com   # Optional, this is the default
JIRA_PAT=NjYx...your_token_here            # Required
JIRA_PROJECT=CVS                            # Optional, default CVS
JIRA_COMPONENT=IE CPU Plugin               # Optional, default "IE CPU Plugin"
```

### CLI flags

| Flag | Default | Description |
|------|---------|-------------|
| `--days` | `31` | Days of history (ignored if `--start` given) |
| `--start` | — | Start date YYYY-MM-DD |
| `--end` | today | End date YYYY-MM-DD |
| `--output` | `cpu-issue-tracker.html` | Output file path |
| `--pat` | `$JIRA_PAT` | JIRA Personal Access Token |
| `--project` | `CVS` | JIRA project key |
| `--component` | `IE CPU Plugin` | JIRA component name (exact match) |
| `--current-open` | — | Provide current open count directly (skips auto-fetch) |
| `--jira-url` | `https://jira.devtools.intel.com` | Base JIRA URL |

## How the Open Count Is Computed

The JIRA REST API does not expose historical open counts. Instead:

1. The **current** open count is fetched using:
   ```
   project = CVS AND component = "IE CPU Plugin"
   AND status not in (Implemented, "In testing", Verified, Closed)
   ```
2. Daily new and resolved counts are fetched for the period.
3. The open count for prior days is **back-calculated**:
   ```
   open[day-1] = open[day] - new[day] + closed[day]
   ```
   This unwinds each day's delta moving backwards from the confirmed current total.

> **Tip**: For the most accurate baseline, run the script on the same day as your JIRA filter query. The confirmed current total drives the entire back-calculation.

## "Resolved" Definition

An issue counts as **resolved on a given day** if its `updated` timestamp falls on that day **and** it has transitioned to one of:

| Status | Meaning |
|--------|---------|
| Implemented | Fix merged/released |
| In Testing | Fix in QA pipeline |
| Verified | QA confirmed fixed |
| Closed | Administratively closed (won't fix, duplicate, etc.) |

This matches the JIRA filter: `status not in (Implemented, "In testing", Verified)` used to define "open defects."

## Output

Generates a single standalone `.html` file (~60–80 KB) with no external dependencies.

Open in any browser — no web server needed.

## Troubleshooting

### 401 Unauthorized

JIRA uses Bearer token auth (not Basic Auth). Generate a PAT from:
`https://jira.devtools.intel.com` → Profile → Personal Access Tokens

### SSL / proxy errors

If behind a corporate proxy, set environment variables before running:

```bash
export HTTPS_PROXY=http://child-prc.intel.com:913
export HTTP_PROXY=http://child-prc.intel.com:913
```

Or add to your `.env` file — the script will pick them up via `os.environ`.

### "current-open" mismatch

If the auto-fetched open count differs from what you see in the JIRA UI, check:
1. Your filter URL uses `filter = "OV Open Defects"` — the saved filter may add extra constraints beyond project+component.
2. Use `--current-open N` to pass the value you see in the UI directly.

### Missing issues

The script uses `updated` as the resolved date, not the actual transition date (changelog access requires extra API calls per issue). If an issue was transitioned then edited later, it may appear on the wrong day.

## Related Skills

- `team-dashboard`: Weekly team PR + JIRA combined dashboard
- `audit-ov-cpu-pr`: GitHub PR audit for CPU plugin contributions
