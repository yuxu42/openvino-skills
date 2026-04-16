---
name: track-ov-contributors
description: Fetch PR contribution stats (total and merged) for OpenVINO team members from GitHub API and generate HTML dashboard pages with summary cards and monthly stacked bar charts.
---

Repository: https://github.com/openvinotoolkit/openvino
Data source: GitHub Search API (`/search/issues`)
Default tracking period: since 2025-10-15

## Team Members

| Name             | GitHub Username   |
|------------------|-------------------|
| Chen Xu          | xuchen-intel      |
| Xiuchuan Zhai    | azhai219          |
| Zhang Yi         | zhangYiIntel      |
| Chenhu Wang      | chenhu-wang       |
| cecilia peng     | ceciliapeng2011   |
| Bo Liu           | liubo-intel       |
| Yuan Hu          | tiger100256-hu    |
| Mang Guo         | mangguo321        |

To add/remove members, edit the `USERS` list in `generate_contributors.py`.

## What This Skill Does

1. **Fetches from GitHub API** for each team member:
   - Total PR count (created since the `--since` date)
   - Merged PR count
   - Monthly breakdown of both total and merged PRs
   - Display name from GitHub profile

2. **Generates two HTML dashboard files:**
   - `openvino-contributors.html` -- Summary cards showing merged/total PRs per contributor, sorted by total PRs descending
   - `openvino-contributors-monthly.html` -- Monthly breakdown with stacked bar charts (green = merged, purple = unmerged)

## Usage

```bash
# Basic usage (unauthenticated API, 10 searches/min)
python generate_contributors.py

# With GitHub token for higher rate limits (30 searches/min)
python generate_contributors.py --token ghp_xxxxx
# Or set the GITHUB_TOKEN environment variable
export GITHUB_TOKEN=ghp_xxxxx
python generate_contributors.py

# Custom start date
python generate_contributors.py --since 2026-01-01
```

## Output

- `openvino-contributors.html` -- Standalone HTML page with contributor cards. Each card shows:
  - Avatar initials, display name, GitHub username
  - Merged count (green) and Total PR count
  - Link to GitHub profile

- `openvino-contributors-monthly.html` -- Standalone HTML page with monthly breakdown. Each card shows:
  - Merged/Total badge (e.g., "9/18 PRs")
  - Stacked bar chart per month: green = merged, light purple = unmerged
  - Legend and tooltips on hover

## Notes

- The GitHub Search API without authentication is limited to 10 requests per minute. The script spaces requests ~8 seconds apart to stay within limits. With a token, delay is reduced to ~3 seconds.
- The script automatically determines the month range from the `--since` date to today.
- Invalid GitHub usernames are detected and skipped with a warning.
- Both HTML files are fully standalone with no external dependencies.
