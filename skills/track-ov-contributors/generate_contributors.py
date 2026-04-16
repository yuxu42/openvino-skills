#!/usr/bin/env python3
"""
OpenVINO Contributors Tracker
Fetches PR data from GitHub API and generates HTML dashboard pages.

Usage:
    python generate_contributors.py
    python generate_contributors.py --since 2025-10-15
    python generate_contributors.py --token ghp_xxxxx   # for higher rate limits

Outputs:
    openvino-contributors.html         - Summary cards with merged/total PRs
    openvino-contributors-monthly.html - Monthly breakdown with stacked bar charts
"""

import json
import urllib.request
import urllib.error
import time
import argparse
import os
import sys
from datetime import datetime, date

# ============================================================
# CONFIGURATION - Edit this section to add/remove team members
# ============================================================
REPO = "openvinotoolkit/openvino"
DEFAULT_SINCE = "2025-10-15"

# GitHub username list - add or remove members here
USERS = [
    "xuchen-intel",
    "azhai219",
    "zhangYiIntel",
    "chenhu-wang",
    "ceciliapeng2011",
    "liubo-intel",
    "tiger100256-hu",
    "mangguo321",
]
# ============================================================

MONTH_LABELS = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr",
                "May", "Jun", "Jul", "Aug", "Sep"]

MONTH_PREFIX_MAP = {
    "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
    "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
    "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
}


def build_month_range(since_str):
    """Build the list of month labels and YYYY-MM prefixes from since date to today."""
    since = datetime.strptime(since_str, "%Y-%m-%d")
    today = date.today()
    months = []
    year, month = since.year, since.month
    while (year, month) <= (today.year, today.month):
        prefix = f"{year}-{month:02d}"
        label = MONTH_PREFIX_MAP[f"{month:02d}"]
        months.append((prefix, label))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


def github_search(repo, user, since, extra_q="", token=None):
    """Search GitHub issues/PRs API and return items list."""
    q = f"repo:{repo}+type:pr+author:{user}+created:>={since}{extra_q}"
    url = f"https://api.github.com/search/issues?q={q}&per_page=100"
    headers = {"User-Agent": "openvino-contributor-tracker"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        return data.get("total_count", 0), data.get("items", [])
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code == 422:
            print(f"  WARNING: User '{user}' not found on GitHub, skipping.")
            return None, []
        elif e.code == 403:
            print(f"  Rate limited. Waiting 60s...")
            time.sleep(60)
            return github_search(repo, user, since, extra_q, token)
        else:
            print(f"  HTTP {e.code}: {body[:200]}")
            return 0, []


def get_display_name(user, token=None):
    """Fetch display name from GitHub user profile."""
    url = f"https://api.github.com/users/{user}"
    headers = {"User-Agent": "openvino-contributor-tracker"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        return data.get("name") or user
    except Exception:
        return user


def bucket_by_month(items, month_range):
    """Bucket PR items into month counts."""
    counts = {label: 0 for _, label in month_range}
    prefix_to_label = {prefix: label for prefix, label in month_range}
    for item in items:
        ym = item["created_at"][:7]
        if ym in prefix_to_label:
            counts[prefix_to_label[ym]] += 1
    return counts


def fetch_all_data(since, token=None):
    """Fetch all contributor data from GitHub API."""
    month_range = build_month_range(since)
    contributors = []
    delay = 3 if token else 8

    for i, user in enumerate(USERS):
        print(f"[{i+1}/{len(USERS)}] Fetching {user}...")

        # Total PRs
        total_count, all_items = github_search(REPO, user, since, "", token)
        if total_count is None:
            continue
        time.sleep(delay)

        # Merged PRs
        merged_count, merged_items = github_search(REPO, user, since, "+is:merged", token)
        time.sleep(delay)

        # Display name
        name = get_display_name(user, token)
        time.sleep(delay)

        all_monthly = bucket_by_month(all_items, month_range)
        merged_monthly = bucket_by_month(merged_items, month_range)

        contributor = {
            "name": name,
            "username": user,
            "githubUrl": f"https://github.com/{user}",
            "prs": total_count,
            "merged": merged_count or 0,
            "monthly": all_monthly,
            "merged_monthly": merged_monthly,
        }
        contributors.append(contributor)
        print(f"  {name}: {merged_count}/{total_count} PRs (merged/total)")

    return contributors, [label for _, label in month_range]


def generate_summary_html(contributors, since, today_str):
    """Generate openvino-contributors.html content."""
    since_dt = datetime.strptime(since, "%Y-%m-%d")
    month_range_str = f"{since_dt.strftime('%b %Y')} - {datetime.now().strftime('%b %Y')}"

    contrib_js = json.dumps([
        {
            "name": c["name"],
            "username": c["username"],
            "githubUrl": c["githubUrl"],
            "prs": c["prs"],
            "merged": c["merged"],
        }
        for c in contributors
    ], indent=12)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenVINO Contributors</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; padding: 40px 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ text-align: center; color: white; margin-bottom: 50px; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }}
        .subtitle {{ font-size: 1.1rem; opacity: 0.9; }}
        .subtitle a {{ color: white; text-decoration: none; border-bottom: 2px solid rgba(255,255,255,0.5); transition: border-color 0.3s; }}
        .subtitle a:hover {{ border-bottom-color: white; }}
        .contributors-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; margin-top: 30px; }}
        .contributor-card {{
            background: white; border-radius: 12px; padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); transition: transform 0.3s, box-shadow 0.3s;
            display: flex; flex-direction: column; align-items: center; text-align: center;
        }}
        .contributor-card:hover {{ transform: translateY(-5px); box-shadow: 0 15px 40px rgba(0,0,0,0.3); }}
        .avatar {{
            width: 80px; height: 80px; border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 2rem; font-weight: bold; margin-bottom: 15px;
        }}
        .contributor-name {{ font-size: 1.2rem; font-weight: 600; color: #333; margin-bottom: 8px; }}
        .contributor-username {{ color: #666; font-size: 0.95rem; margin-bottom: 12px; }}
        .github-link {{
            display: inline-block; background: #24292e; color: white; text-decoration: none;
            padding: 8px 16px; border-radius: 6px; font-size: 0.9rem; transition: background 0.3s;
        }}
        .github-link:hover {{ background: #444d56; }}
        .stats {{
            margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee;
            width: 100%; display: flex; justify-content: space-around; font-size: 0.85rem; color: #666;
        }}
        .stat-item {{ display: flex; flex-direction: column; align-items: center; }}
        .stat-number {{ font-size: 1.3rem; font-weight: bold; color: #667eea; }}
        .stat-label {{ margin-top: 4px; }}
        .footer {{ text-align: center; color: white; margin-top: 50px; opacity: 0.8; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>OpenVINO Contributors</h1>
            <p class="subtitle">Team members contributing to <a href="https://github.com/{REPO}" target="_blank">{REPO}</a></p>
            <div style="margin-top: 20px; font-size: 1rem;">
                <span id="totalContributors"></span> contributors
                &bull; <span id="totalMerged"></span> merged / <span id="totalPRs"></span> total PRs
                ({month_range_str})
            </div>
        </header>
        <div class="contributors-grid" id="contributorsGrid"></div>
        <footer class="footer"><p>Last updated: {today_str}</p></footer>
    </div>
    <script>
        const contributors = {contrib_js};

        function getInitials(name) {{
            return name.split(' ').map(w => w[0]).join('').toUpperCase().substring(0, 2);
        }}

        function createContributorCard(c) {{
            const card = document.createElement('div');
            card.className = 'contributor-card';
            card.innerHTML = `
                <div class="avatar">${{getInitials(c.name)}}</div>
                <div class="contributor-name">${{c.name}}</div>
                <div class="contributor-username">@${{c.username}}</div>
                <a class="github-link" href="${{c.githubUrl}}" target="_blank">View GitHub Profile</a>
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-number" style="color: #28a745;">${{c.merged}}</div>
                        <div class="stat-label">Merged</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">${{c.prs}}</div>
                        <div class="stat-label">Total PRs</div>
                    </div>
                </div>`;
            return card;
        }}

        (function() {{
            const grid = document.getElementById('contributorsGrid');
            const sorted = [...contributors].sort((a, b) => (b.prs || 0) - (a.prs || 0));
            sorted.forEach(c => grid.appendChild(createContributorCard(c)));
            document.getElementById('totalContributors').textContent = contributors.length;
            document.getElementById('totalPRs').textContent = contributors.reduce((s, c) => s + (c.prs || 0), 0);
            document.getElementById('totalMerged').textContent = contributors.reduce((s, c) => s + (c.merged || 0), 0);
        }})();
    </script>
</body>
</html>'''


def generate_monthly_html(contributors, month_labels, since, today_str):
    """Generate openvino-contributors-monthly.html content."""
    since_dt = datetime.strptime(since, "%Y-%m-%d")
    month_range_str = f"{since_dt.strftime('%b %Y')} - {datetime.now().strftime('%b %Y')}"

    contrib_js = json.dumps([
        {
            "name": c["name"],
            "username": c["username"],
            "githubUrl": c["githubUrl"],
            "monthly": c["monthly"],
            "merged": c["merged_monthly"],
        }
        for c in contributors
    ], indent=12)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenVINO Contributors - Monthly Breakdown</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; padding: 40px 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{ text-align: center; color: white; margin-bottom: 50px; }}
        h1 {{ font-size: 2.5rem; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }}
        .subtitle {{ font-size: 1.1rem; opacity: 0.9; }}
        .subtitle a {{ color: white; text-decoration: none; border-bottom: 2px solid rgba(255,255,255,0.5); }}
        .subtitle a:hover {{ border-bottom-color: white; }}
        .contributors-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 25px; margin-top: 30px; }}
        .contributor-card {{
            background: white; border-radius: 12px; padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); transition: transform 0.3s, box-shadow 0.3s;
        }}
        .contributor-card:hover {{ transform: translateY(-5px); box-shadow: 0 15px 40px rgba(0,0,0,0.3); }}
        .card-header {{
            display: flex; align-items: center; margin-bottom: 20px;
            padding-bottom: 15px; border-bottom: 2px solid #f0f0f0;
        }}
        .avatar {{
            width: 60px; height: 60px; border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 1.5rem; font-weight: bold; margin-right: 15px; flex-shrink: 0;
        }}
        .contributor-info {{ flex: 1; }}
        .contributor-name {{ font-size: 1.2rem; font-weight: 600; color: #333; margin-bottom: 4px; }}
        .contributor-username {{ color: #666; font-size: 0.9rem; }}
        .total-prs {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 8px 16px; border-radius: 20px;
            font-weight: bold; font-size: 1.1rem; margin-left: 10px; white-space: nowrap;
        }}
        .monthly-chart {{ margin: 20px 0; }}
        .chart-title {{ font-size: 0.9rem; font-weight: 600; color: #666; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .chart-bars {{ display: flex; justify-content: space-between; gap: 8px; padding: 10px 0; }}
        .bar-container {{ flex: 1; display: flex; flex-direction: column; align-items: center; }}
        .bar-value {{ font-size: 0.85rem; font-weight: bold; color: #333; height: 20px; line-height: 20px; }}
        .bar-area {{ width: 100%; height: 100px; display: flex; flex-direction: column; justify-content: flex-end; align-items: stretch; }}
        .bar-label {{ font-size: 0.75rem; color: #999; font-weight: 500; margin-top: 5px; }}
        .github-link {{
            display: block; text-align: center; background: #24292e; color: white;
            text-decoration: none; padding: 10px 16px; border-radius: 6px;
            font-size: 0.9rem; transition: background 0.3s; margin-top: 15px;
        }}
        .github-link:hover {{ background: #444d56; }}
        .footer {{ text-align: center; color: white; margin-top: 50px; opacity: 0.8; }}
        @media (max-width: 768px) {{
            .contributors-grid {{ grid-template-columns: 1fr; }}
            .bar-area {{ height: 80px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>OpenVINO Contributors</h1>
            <p class="subtitle">Team members contributing to <a href="https://github.com/{REPO}" target="_blank">{REPO}</a></p>
            <div style="margin-top: 20px; font-size: 1rem;">
                <span id="totalContributors"></span> contributors
                &bull; <span id="totalMerged"></span> merged / <span id="totalPRs"></span> total PRs
                ({month_range_str})
            </div>
        </header>
        <div class="contributors-grid" id="contributorsGrid"></div>
        <footer class="footer"><p>Last updated: {today_str}</p></footer>
    </div>
    <script>
        const contributors = {contrib_js};

        function getInitials(name) {{
            return name.split(' ').map(w => w[0]).join('').toUpperCase().substring(0, 2);
        }}
        function sumValues(obj) {{
            return Object.values(obj).reduce((s, v) => s + v, 0);
        }}

        function createMonthlyChart(monthly, merged) {{
            const maxBarHeight = 100;
            const maxValue = Math.max(...Object.values(monthly), 1);
            const months = Object.keys(monthly);
            let html = '<div class="monthly-chart">';
            html += '<div class="chart-title">Monthly PR Contributions &nbsp;'
                + '<span style="font-size:0.8em;font-weight:normal;">'
                + '(<span style="color:#28a745;">&#9632;</span> merged '
                + '<span style="color:#b8a9e8;">&#9632;</span> unmerged)</span></div>';
            html += '<div class="chart-bars">';
            months.forEach(month => {{
                const total = monthly[month];
                const mc = merged[month] || 0;
                const uc = total - mc;
                const totalH = total > 0 ? Math.max((total / maxValue) * maxBarHeight, 6) : 4;
                const mH = mc > 0 ? Math.max(Math.round((mc / total) * totalH), 4) : 0;
                const uH = uc > 0 ? Math.max(totalH - mH, 4) : 0;

                html += '<div class="bar-container">';
                html += `<div class="bar-value">${{total > 0 ? total : ''}}</div>`;
                html += '<div class="bar-area">';
                if (total === 0) {{
                    html += '<div style="height:4px;width:100%;opacity:0.2;background:#999;border-radius:4px;"></div>';
                }} else {{
                    if (uc > 0) {{
                        const br = mc > 0 ? '4px 4px 0 0' : '4px';
                        html += `<div title="${{uc}} unmerged" style="height:${{uH}}px;background:linear-gradient(to top,#b8a9e8,#d4c5f9);border-radius:${{br}};"></div>`;
                    }}
                    if (mc > 0) {{
                        const br = uc > 0 ? '0 0 4px 4px' : '4px';
                        html += `<div title="${{mc}} merged" style="height:${{mH}}px;background:linear-gradient(to top,#28a745,#34d058);border-radius:${{br}};"></div>`;
                    }}
                }}
                html += '</div>';
                html += `<div class="bar-label">${{month}}</div>`;
                html += '</div>';
            }});
            html += '</div></div>';
            return html;
        }}

        function createContributorCard(c) {{
            const mc = sumValues(c.merged);
            const ac = sumValues(c.monthly);
            const card = document.createElement('div');
            card.className = 'contributor-card';
            card.innerHTML = `
                <div class="card-header">
                    <div class="avatar">${{getInitials(c.name)}}</div>
                    <div class="contributor-info">
                        <div class="contributor-name">${{c.name}}</div>
                        <div class="contributor-username">@${{c.username}}</div>
                    </div>
                    <div class="total-prs" title="${{mc}} merged / ${{ac}} total">${{mc}}/${{ac}} PRs</div>
                </div>
                ${{createMonthlyChart(c.monthly, c.merged)}}
                <a class="github-link" href="${{c.githubUrl}}" target="_blank">View GitHub Profile</a>`;
            return card;
        }}

        (function() {{
            const grid = document.getElementById('contributorsGrid');
            const sorted = [...contributors].sort((a, b) => sumValues(b.monthly) - sumValues(a.monthly));
            sorted.forEach(c => grid.appendChild(createContributorCard(c)));
            const totalPRs = contributors.reduce((s, c) => s + sumValues(c.monthly), 0);
            const totalMerged = contributors.reduce((s, c) => s + sumValues(c.merged), 0);
            document.getElementById('totalContributors').textContent = contributors.length;
            document.getElementById('totalPRs').textContent = totalPRs;
            document.getElementById('totalMerged').textContent = totalMerged;
        }})();
    </script>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(description="Fetch OpenVINO contributor PR stats and generate HTML dashboards.")
    parser.add_argument("--since", default=DEFAULT_SINCE, help=f"Start date YYYY-MM-DD (default: {DEFAULT_SINCE})")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"), help="GitHub token for higher rate limits (or set GITHUB_TOKEN env var)")
    args = parser.parse_args()

    today_str = date.today().strftime("%B %d, %Y")

    print(f"Fetching PR data for {REPO} since {args.since}...")
    print(f"Users: {', '.join(USERS)}")
    if args.token:
        print("Using GitHub token for authentication.")
    else:
        print("No token provided - using unauthenticated API (10 searches/min limit).")
    print()

    contributors, month_labels = fetch_all_data(args.since, args.token)

    if not contributors:
        print("No contributor data fetched. Exiting.")
        sys.exit(1)

    # Generate summary HTML
    summary_path = os.path.join(os.path.dirname(__file__), "openvino-contributors.html")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(generate_summary_html(contributors, args.since, today_str))
    print(f"\nGenerated: {summary_path}")

    # Generate monthly HTML
    monthly_path = os.path.join(os.path.dirname(__file__), "openvino-contributors-monthly.html")
    with open(monthly_path, "w", encoding="utf-8") as f:
        f.write(generate_monthly_html(contributors, month_labels, args.since, today_str))
    print(f"Generated: {monthly_path}")

    # Print summary
    total_prs = sum(c["prs"] for c in contributors)
    total_merged = sum(c["merged"] for c in contributors)
    print(f"\nSummary: {len(contributors)} contributors, {total_merged} merged / {total_prs} total PRs")


if __name__ == "__main__":
    main()
