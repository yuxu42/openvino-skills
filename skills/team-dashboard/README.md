# Team Dashboard Generator

Generate comprehensive weekly team dashboards combining GitHub PRs, JIRA tickets, GPU/CPU features, and customer engagement metrics.

## Features

- ✅ **GitHub PR Tracking**: All open PRs (in review) and merged PRs this week
- ✅ **JIRA Ticket Tracking**: Bugs vs Features, Completed vs In Progress
- ✅ **GPU/CPU Features**: Component-based categorization (IE GPU Plugin / IE CPU Plugin)
- ✅ **Weekly Summaries**: Auto-reads team weekly report emails from Outlook (Windows)
- ✅ **Customer Engagement**: GitHub issues responded to and closed
- ✅ **Intel JIRA Integration**: Bearer token authentication with SSO support
- ✅ **Corporate Proxy**: Intel network proxy support

## Quick Start

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Create `.env` file** (see `.env.example`):
```bash
GITHUB_TOKEN=your_github_token
JIRA_EMAIL=your.email@intel.com
JIRA_API_TOKEN=your_jira_bearer_token
HTTP_PROXY=http://child-prc.intel.com:913
HTTPS_PROXY=http://child-prc.intel.com:913
```

3. **Configure team** in `config.yaml` (see `config.yaml.example`)

4. **Generate dashboard**:
```bash
python generate_dashboard.py --format html
```

## Output

Beautiful HTML dashboard at `reports/weekly_dashboard_YYYY-MM-DD.html` (~52KB)

## Documentation

- **SKILL.md**: Complete skill documentation
- **JIRA_COUNTING_LOGIC.md**: Detailed counting rules
- **README.md**: This file

## Key Features

- Bearer token authentication for Intel JIRA SSO
- Changelog analysis for accurate ticket counting
- Component-based GPU/CPU categorization
- Merged PR detection (catches PRs created earlier, merged this week)
