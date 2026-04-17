---
name: team-dashboard
description: Generate weekly team dashboard with GitHub PRs, JIRA tickets (bugs/features), GPU/CPU features, and customer engagement metrics. Uses Bearer token auth for Intel JIRA with corporate proxy support.
---

# Team Dashboard Generator

## Overview

Generate comprehensive weekly team dashboards combining:
- **GitHub PRs**: Submitted and merged (with proper merged-date filtering)
- **JIRA Tickets**: Bugs vs Features, Completed vs In Progress
- **Key Features**: GPU/CPU categorization using JIRA components (IE GPU Plugin / IE CPU Plugin)
- **Customer Engagement**: GitHub issues responded to and closed

## When To Use

Use this skill when you need to:
- Generate weekly team status reports
- Track PR and JIRA metrics for retrospectives
- Visualize GPU/CPU feature distribution
- Report team productivity to stakeholders

## Prerequisites

1. **GitHub Token**: Read access to target repositories
2. **JIRA Bearer Token**: Access to Intel JIRA with SSO authentication
3. **Corporate Proxy**: Configured for Intel network (child-prc.intel.com:913)
4. **Python 3.8+**: With dependencies installed

## Configuration

### 1. Environment Variables (.env)

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# JIRA Configuration (Bearer Token)
JIRA_EMAIL=user.name@intel.com
JIRA_API_TOKEN=your_jira_bearer_token_here

# Proxy Configuration
HTTP_PROXY=http://child-prc.intel.com:913
HTTPS_PROXY=http://child-prc.intel.com:913
http_proxy=http://child-prc.intel.com:913
https_proxy=http://child-prc.intel.com:913
```

### 2. Team Configuration (config.yaml)

```yaml
team_members:
  - name: "Team Member Name"
    github_username: "github-user"
    jira_username: "jira-user"

github:
  token: "${GITHUB_TOKEN}"
  repositories:
    - "org/repo"

jira:
  url: "https://jira.devtools.intel.com"
  email: "${JIRA_EMAIL}"
  api_token: "${JIRA_API_TOKEN}"
  project_keys:
    - "CVS"  # or "OpenVINO", etc.
```

## Usage

### Generate Current Week Dashboard

```bash
python generate_dashboard.py --format html
```

### Generate Historical Dashboard

```bash
# Last week
python generate_dashboard.py --weeks-ago 1

# Two weeks ago
python generate_dashboard.py --weeks-ago 2
```

### Output

Generates: `reports/weekly_dashboard_YYYY-MM-DD.html`

Beautiful HTML dashboard with:
- Purple gradient design
- Responsive layout
- Clickable links to GitHub/JIRA
- Summary metrics cards
- Per-member breakdowns

## Key Features

### 1. GitHub PR Tracking

**Submitted PRs**: PRs created during the week
**Merged PRs**: PRs merged during the week (even if created earlier)

Uses separate queries to correctly capture:
- PRs created this week (sorted by `created`)
- PRs merged this week (sorted by `updated`, status `closed`)

### 2. JIRA Ticket Categorization

**By Type**:
- 🐛 **Bugs**: Bug, Defect, Incident
- ✨ **Features**: Story, Epic, Feature, Enhancement, Improvement, Task, Requirement

**By Status**:
- **Completed**: Status changed to "Implemented" or "Closed" during the week (uses changelog)
- **In Progress**: Current status is "In Progress", "In Review", or "In Development"

### 3. Key Features (GPU/CPU)

Extracted from JIRA Story/Epic tickets in progress:

**GPU Features**: Component = `"IE GPU Plugin"`
**CPU Features**: Component = `"IE CPU Plugin"`
**Other Features**: Different or no component

### 4. Authentication

**GitHub**: Token-based (standard)
**JIRA**: Bearer token with corporate proxy
- Intel JIRA uses Microsoft SSO
- Requires Bearer token (not Basic Auth)
- Format: `Authorization: Bearer <token>`

## JIRA Counting Logic

### Completed Tickets

✅ Counts tickets where:
1. Current status = "Implemented" OR "Closed"
2. Status **changed** to one of these during the week
3. Uses **changelog** to verify transition date

### Why Changelog?

❌ **Wrong**: `if status == "Closed": count += 1`
- Counts ALL closed tickets, including old ones

✅ **Correct**: Check when status changed to Closed
- Only counts tickets completed THIS WEEK

### Example

```python
for history in changelog.histories:
    history_date = parse(history.created)
    if week_start <= history_date < week_end:
        if status changed to "Implemented" or "Closed":
            count_as_completed()
```

## Troubleshooting

### JIRA 401 Unauthorized

**Cause**: Basic Auth not supported, need Bearer token
**Solution**: Use Bearer token from JIRA Personal Access Tokens

### SSL Certificate Errors

**Cause**: Corporate proxy with SSL inspection
**Solution**: Code includes `verify=False` and disables urllib3 warnings

### No JIRA Tickets Found

**Check**:
1. Project key correct? (CVS vs OpenVINO)
2. JIRA usernames match team members?
3. Token has read access to project?

### PRs Missing

**Merged PRs not showing**:
- Code now uses separate query for merged PRs
- Sorts by `updated` date, not `created`
- Captures PRs created earlier but merged this week

## File Structure

```
team-dashboard/
├── generate_dashboard.py      # Main generator (Bearer auth)
├── config.yaml                 # Team configuration
├── .env                        # Credentials (git-ignored)
├── dashboard_template.html     # Jinja2 template
├── JIRA_COUNTING_LOGIC.md     # Detailed counting rules
├── test_jira.py               # JIRA connection tester
└── reports/
    └── weekly_dashboard_*.html # Generated dashboards
```

## Key Code Sections

### JIRA Bearer Token Auth

```python
session = requests.Session()
session.headers.update({
    'Authorization': f"Bearer {api_token}",
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0'
})
session.verify = False
session.proxies = {
    'http': os.environ.get('HTTP_PROXY'),
    'https': os.environ.get('HTTPS_PROXY')
}
```

### Component-Based GPU/CPU Detection

```python
components = fields.get('components', [])
is_gpu = any('IE GPU Plugin' in c['name'] for c in components)
is_cpu = any('IE CPU Plugin' in c['name'] for c in components)
```

### Merged PR Detection

```python
# Separate query for PRs merged this week
prs_updated = repo.get_pulls(state='closed', sort='updated', direction='desc')
for pr in prs_updated:
    if pr.updated_at < week_start:
        break
    if pr.merged and pr.merged_at:
        if week_start <= pr.merged_at < week_end:
            count_as_merged(pr)
```

## Metrics Summary

Dashboard displays:
- **PRs**: Submitted/Merged totals + per-member lists
- **JIRA Tickets**: 
  - Total Completed (Bugs/Features split)
  - Total In Progress (Bugs/Features split)
  - Per-member ticket lists with types
- **Key Features**:
  - GPU/CPU/Other counts
  - Grouped feature lists with components
- **Customer Engagement**:
  - Issues responded
  - Issues closed

## Related Skills

- `jira-get-content`: JIRA data fetching with Bearer auth
- `track-ov-contributors`: GitHub contributor tracking

## Notes

- Week runs Monday 00:00:00 to Sunday 23:59:59 UTC
- Dashboard file ~50KB with full team data
- Supports multiple JIRA projects in config
- Proxy settings optional (set empty string to disable)
- Component names must match exactly: "IE CPU Plugin", "IE GPU Plugin"
