#!/usr/bin/env python3
"""
Team Weekly Dashboard Generator
Generates comprehensive weekly reports for team activities
"""

import os
import yaml
import json
from datetime import datetime, timedelta
from pathlib import Path
from github import Github
from collections import defaultdict
import argparse
from jinja2 import Template


class DashboardGenerator:
    def __init__(self, config_path="config.yaml"):
        self.config = self.load_config(config_path)
        self.github_client = None
        self.jira_client = None
        self.week_start = None
        self.week_end = None

    def load_config(self, config_path):
        """Load configuration from YAML file"""
        # Load .env file first
        from dotenv import load_dotenv
        load_dotenv()

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Expand environment variables
        if 'github' in config and 'token' in config['github']:
            config['github']['token'] = os.path.expandvars(config['github']['token'])
        if 'jira' in config:
            if 'email' in config['jira']:
                config['jira']['email'] = os.path.expandvars(config['jira']['email'])
            if 'api_token' in config['jira']:
                config['jira']['api_token'] = os.path.expandvars(config['jira']['api_token'])

        return config

    def setup_clients(self):
        """Initialize GitHub and JIRA clients"""
        # Set proxy from environment
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # GitHub
        if self.config.get('github', {}).get('token'):
            self.github_client = Github(self.config['github']['token'])
            print("GitHub client initialized")
        else:
            print("WARNING: GitHub token not configured")

        # JIRA - Use Bearer token authentication
        jira_config = self.config.get('jira', {})
        if jira_config.get('url') and jira_config.get('api_token'):
            try:
                # Test connection with bearer token
                import requests
                test_url = f"{jira_config['url']}/rest/api/2/myself"
                response = requests.get(
                    test_url,
                    headers={
                        'Authorization': f"Bearer {jira_config['api_token']}",
                        'Accept': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                    },
                    verify=False,
                    timeout=10,
                    proxies={
                        'http': os.environ.get('HTTP_PROXY', ''),
                        'https': os.environ.get('HTTPS_PROXY', '')
                    }
                )
                if response.status_code == 200:
                    self.jira_config = jira_config
                    self.jira_client = True  # Flag to indicate JIRA is available
                    print(f"JIRA client initialized (Bearer auth)")
                else:
                    print(f"WARNING: JIRA authentication failed - Status {response.status_code}")
                    self.jira_client = None
            except Exception as e:
                print(f"WARNING: JIRA initialization failed - {type(e).__name__}")
                print("Dashboard will be generated without JIRA data")
                self.jira_client = None
        else:
            print("WARNING: JIRA credentials not configured")
            self.jira_client = None

    def set_week_range(self, weeks_ago=0):
        """Set the week range for the report"""
        from datetime import timezone
        today = datetime.now(timezone.utc)

        # Find the most recent Monday (or configured start day)
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday + (weeks_ago * 7))
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        week_end = week_start + timedelta(days=7)

        self.week_start = week_start
        self.week_end = week_end

        return week_start, week_end

    def get_pr_metrics(self):
        """Fetch PR submission and merge metrics"""
        if not self.github_client:
            return {"error": "GitHub client not configured"}

        metrics = {
            "submitted": defaultdict(list),
            "merged": defaultdict(list),
            "total_submitted": 0,
            "total_merged": 0
        }

        team_usernames = [m['github_username'] for m in self.config.get('team_members', [])]

        for repo_name in self.config['github'].get('repositories', []):
            try:
                repo = self.github_client.get_repo(repo_name)

                # Get PRs created during the week (for submitted count)
                prs_created = repo.get_pulls(state='all', sort='created', direction='desc')
                for pr in prs_created:
                    if pr.created_at < self.week_start:
                        break

                    if pr.created_at >= self.week_start and pr.created_at < self.week_end:
                        author = pr.user.login
                        if author in team_usernames:
                            metrics["submitted"][author].append({
                                "title": pr.title,
                                "number": pr.number,
                                "url": pr.html_url,
                                "repo": repo_name
                            })
                            metrics["total_submitted"] += 1

                # Get PRs updated recently to check for merges during the week
                # This catches PRs created before the week but merged during it
                prs_updated = repo.get_pulls(state='closed', sort='updated', direction='desc')
                for pr in prs_updated:
                    # Stop when we reach PRs updated before the week
                    if pr.updated_at < self.week_start:
                        break

                    # Check if merged during the week
                    if pr.merged and pr.merged_at:
                        if pr.merged_at >= self.week_start and pr.merged_at < self.week_end:
                            author = pr.user.login
                            if author in team_usernames:
                                metrics["merged"][author].append({
                                    "title": pr.title,
                                    "number": pr.number,
                                    "url": pr.html_url,
                                    "repo": repo_name
                                })
                                metrics["total_merged"] += 1

                print(f"[OK] Processed PR metrics for {repo_name}")
            except Exception as e:
                print(f"[X] Error processing {repo_name}: {e}")

        return metrics

    def get_jira_tickets(self):
        """Fetch JIRA ticket metrics using Bearer token authentication"""
        if not self.jira_client:
            return {"error": "JIRA client not configured"}

        import requests
        import urllib3
        urllib3.disable_warnings()

        metrics = {
            "completed": defaultdict(list),
            "in_progress": defaultdict(list),
            "completed_bugs": defaultdict(list),
            "completed_features": defaultdict(list),
            "in_progress_bugs": defaultdict(list),
            "in_progress_features": defaultdict(list),
            "total_completed": 0,
            "total_in_progress": 0,
            "total_completed_bugs": 0,
            "total_completed_features": 0,
            "total_in_progress_bugs": 0,
            "total_in_progress_features": 0
        }

        team_usernames = [m['jira_username'] for m in self.config.get('team_members', [])]
        project_keys = self.config['jira'].get('project_keys', [])

        # Setup session with bearer token
        session = requests.Session()
        session.headers.update({
            'Authorization': f"Bearer {self.jira_config['api_token']}",
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        session.verify = False
        session.proxies = {
            'http': os.environ.get('HTTP_PROXY', ''),
            'https': os.environ.get('HTTPS_PROXY', '')
        }

        for project_key in project_keys:
            try:
                team_filter = ', '.join(team_usernames)

                # Query for tickets updated during the week
                days_back = (datetime.now() - self.week_start.replace(tzinfo=None)).days + 1
                jql = f'project = {project_key} AND assignee in ({team_filter}) AND updated >= -{days_back}d'

                # Fetch issues with changelog
                search_url = f"{self.jira_config['url']}/rest/api/2/search"
                params = {
                    'jql': jql,
                    'maxResults': 200,
                    'expand': 'changelog',
                    'fields': 'summary,status,assignee,issuetype'
                }

                response = session.get(search_url, params=params, timeout=30)
                response.raise_for_status()

                # Debug: Check response
                if response.status_code != 200:
                    print(f"[X] JIRA returned status {response.status_code}")
                    continue

                try:
                    data = response.json()
                except Exception as json_err:
                    print(f"[X] JSON decode error: {json_err}")
                    print(f"[X] Response content-type: {response.headers.get('Content-Type')}")
                    print(f"[X] Response first 500 chars: {response.text[:500]}")
                    continue

                for issue in data.get('issues', []):
                    fields = issue.get('fields', {})
                    assignee_data = fields.get('assignee')
                    assignee = assignee_data.get('name') if assignee_data else None

                    if assignee in team_usernames:
                        issue_key = issue.get('key')
                        summary = fields.get('summary', '')
                        status_data = fields.get('status', {})
                        current_status = status_data.get('name', '')

                        # Get issue type
                        issuetype_data = fields.get('issuetype', {})
                        issue_type = issuetype_data.get('name', '')

                        # Classify as bug or feature
                        is_bug = issue_type.lower() in ['bug', 'defect', 'incident']
                        is_feature = issue_type.lower() in ['story', 'epic', 'feature', 'enhancement', 'improvement', 'task', 'requirement']

                        issue_data = {
                            "key": issue_key,
                            "summary": summary,
                            "status": current_status,
                            "type": issue_type,
                            "url": f"{self.jira_config['url']}/browse/{issue_key}"
                        }

                        # Check if status changed to Implemented or Closed during the week
                        status_changed_this_week = False
                        changelog = issue.get('changelog', {})
                        if changelog:
                            for history in changelog.get('histories', []):
                                history_created = history.get('created', '')
                                history_date = datetime.strptime(history_created.split('T')[0], '%Y-%m-%d')
                                week_start_naive = self.week_start.replace(tzinfo=None)
                                week_end_naive = self.week_end.replace(tzinfo=None)

                                if week_start_naive <= history_date < week_end_naive:
                                    for item in history.get('items', []):
                                        if item.get('field') == 'status' and item.get('toString') in ["Implemented", "Closed"]:
                                            status_changed_this_week = True
                                            break

                        # Count tickets that are Implemented or Closed AND changed to that status this week
                        if current_status in ["Implemented", "Closed"] and status_changed_this_week:
                            metrics["completed"][assignee].append(issue_data)
                            metrics["total_completed"] += 1

                            # Categorize by type
                            if is_bug:
                                metrics["completed_bugs"][assignee].append(issue_data)
                                metrics["total_completed_bugs"] += 1
                            elif is_feature:
                                metrics["completed_features"][assignee].append(issue_data)
                                metrics["total_completed_features"] += 1

                        elif current_status in ["In Progress", "In Review", "In Development"]:
                            metrics["in_progress"][assignee].append(issue_data)
                            metrics["total_in_progress"] += 1

                            # Categorize by type
                            if is_bug:
                                metrics["in_progress_bugs"][assignee].append(issue_data)
                                metrics["total_in_progress_bugs"] += 1
                            elif is_feature:
                                metrics["in_progress_features"][assignee].append(issue_data)
                                metrics["total_in_progress_features"] += 1

                print(f"[OK] Processed JIRA tickets for {project_key}")
            except Exception as e:
                print(f"[X] Error processing JIRA project {project_key}: {e}")

        return metrics

    def get_key_features(self):
        """Get current features being worked on from JIRA Story and Epic tickets"""
        if not self.jira_client:
            return {"gpu_features": [], "cpu_features": [], "other_features": []}

        import requests
        import urllib3
        urllib3.disable_warnings()

        # Setup session with bearer token
        session = requests.Session()
        session.headers.update({
            'Authorization': f"Bearer {self.jira_config['api_token']}",
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        session.verify = False
        session.proxies = {
            'http': os.environ.get('HTTP_PROXY', ''),
            'https': os.environ.get('HTTPS_PROXY', '')
        }

        team_usernames = [m['jira_username'] for m in self.config.get('team_members', [])]
        project_keys = self.config['jira'].get('project_keys', [])

        gpu_features = []
        cpu_features = []
        other_features = []

        for project_key in project_keys:
            try:
                team_filter = ', '.join(team_usernames)

                # Query for Story and Epic tickets in progress
                jql = f'project = {project_key} AND assignee in ({team_filter}) AND type in (Story, Epic) AND status in ("In Progress", "In Review", "In Development")'

                search_url = f"{self.jira_config['url']}/rest/api/2/search"
                params = {
                    'jql': jql,
                    'maxResults': 100,
                    'fields': 'summary,status,assignee,issuetype,components'
                }

                response = session.get(search_url, params=params, timeout=30)
                response.raise_for_status()

                try:
                    data = response.json()
                except Exception as json_err:
                    print(f"[X] JSON decode error in get_key_features: {json_err}")
                    continue

                for issue in data.get('issues', []):
                    fields = issue.get('fields', {})
                    assignee_data = fields.get('assignee')
                    assignee = assignee_data.get('name') if assignee_data else None

                    if assignee in team_usernames:
                        issue_key = issue.get('key')
                        summary = fields.get('summary', '')
                        status_data = fields.get('status', {})
                        status = status_data.get('name', '')
                        issuetype_data = fields.get('issuetype', {})
                        issue_type = issuetype_data.get('name', '')
                        components = fields.get('components', [])
                        component_names = [c['name'] for c in components]

                        feature_data = {
                            "key": issue_key,
                            "name": summary,
                            "lead": assignee,
                            "status": status,
                            "type": issue_type,
                            "components": ', '.join(component_names) if component_names else 'N/A',
                            "url": f"{self.jira_config['url']}/browse/{issue_key}"
                        }

                        # Categorize by GPU/CPU based on component field
                        is_gpu = any('IE GPU Plugin' in comp for comp in component_names)
                        is_cpu = any('IE CPU Plugin' in comp for comp in component_names)

                        if is_gpu:
                            gpu_features.append(feature_data)
                        elif is_cpu:
                            cpu_features.append(feature_data)
                        else:
                            other_features.append(feature_data)

                print(f"[OK] Processed features from {project_key}")
            except Exception as e:
                print(f"[X] Error processing features from {project_key}: {e}")

        return {
            "gpu_features": gpu_features,
            "cpu_features": cpu_features,
            "other_features": other_features,
            "total_gpu": len(gpu_features),
            "total_cpu": len(cpu_features),
            "total_other": len(other_features)
        }

    def get_model_support(self):
        """Track new model support added"""
        models_file = self.config.get('models', {}).get('tracking_file', 'models.json')

        if not os.path.exists(models_file):
            return {"error": "Models tracking file not found", "new_models": []}

        try:
            with open(models_file, 'r') as f:
                data = json.load(f)

            new_models = []
            for model in data.get('models', []):
                added_date = datetime.fromisoformat(model.get('added_date', ''))
                if self.week_start <= added_date < self.week_end:
                    new_models.append(model)

            return {"new_models": new_models, "total_models": len(data.get('models', []))}
        except Exception as e:
            return {"error": str(e), "new_models": []}

    def get_customer_engagement(self):
        """Track customer issue engagement"""
        if not self.github_client:
            return {"error": "GitHub client not configured"}

        engagement = {
            "issues_responded": defaultdict(list),
            "issues_closed": defaultdict(list),
            "total_responded": 0,
            "total_closed": 0
        }

        team_usernames = [m['github_username'] for m in self.config.get('team_members', [])]

        for repo_name in self.config['github'].get('repositories', []):
            try:
                repo = self.github_client.get_repo(repo_name)
                issues = repo.get_issues(state='all', since=self.week_start)

                for issue in issues:
                    if issue.pull_request:
                        continue  # Skip PRs

                    # Check comments for team responses
                    comments = issue.get_comments()
                    for comment in comments:
                        if comment.created_at >= self.week_start and comment.created_at < self.week_end:
                            if comment.user.login in team_usernames:
                                engagement["issues_responded"][comment.user.login].append({
                                    "issue": issue.number,
                                    "title": issue.title,
                                    "url": issue.html_url,
                                    "repo": repo_name
                                })
                                engagement["total_responded"] += 1

                    # Check if closed this week
                    if issue.closed_at and issue.closed_at >= self.week_start and issue.closed_at < self.week_end:
                        if issue.user.login in team_usernames or (issue.closed_by and issue.closed_by.login in team_usernames):
                            closer = issue.closed_by.login if issue.closed_by else issue.user.login
                            engagement["issues_closed"][closer].append({
                                "issue": issue.number,
                                "title": issue.title,
                                "url": issue.html_url,
                                "repo": repo_name
                            })
                            engagement["total_closed"] += 1

                print(f"[OK] Processed customer engagement for {repo_name}")
            except Exception as e:
                print(f"[X] Error processing {repo_name}: {e}")

        return engagement

    def generate_report(self, output_format='html'):
        """Generate the complete dashboard report"""
        print(f"\n[DASHBOARD] Generating dashboard for week {self.week_start.strftime('%Y-%m-%d')} to {self.week_end.strftime('%Y-%m-%d')}\n")

        # Fetch all data
        pr_metrics = self.get_pr_metrics()
        jira_metrics = self.get_jira_tickets()
        features = self.get_key_features()
        model_support = self.get_model_support()
        customer_engagement = self.get_customer_engagement()

        # Save report
        output_dir = Path(self.config['report'].get('output_dir', 'reports'))
        output_dir.mkdir(exist_ok=True)

        output_paths = []

        # Generate HTML report (default)
        if output_format in ['html', 'both']:
            html_report = self.format_html_report(pr_metrics, jira_metrics, features, model_support, customer_engagement)
            html_filename = f"weekly_dashboard_{self.week_start.strftime('%Y-%m-%d')}.html"
            html_path = output_dir / html_filename
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_report)
            output_paths.append(html_path)
            print(f"SUCCESS! HTML report generated: {html_path}")

        # Generate markdown report (optional)
        if output_format in ['markdown', 'both']:
            md_report = self.format_report(pr_metrics, jira_metrics, features, model_support, customer_engagement)
            md_filename = f"weekly_dashboard_{self.week_start.strftime('%Y-%m-%d')}.md"
            md_path = output_dir / md_filename
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_report)
            output_paths.append(md_path)
            print(f"SUCCESS! Markdown report generated: {md_path}")

        return output_paths

    def format_report(self, pr_metrics, jira_metrics, features, model_support, customer_engagement):
        """Format the dashboard report as markdown"""
        report = []

        # Header
        report.append(f"# Team Weekly Dashboard")
        report.append(f"**Week of {self.week_start.strftime('%B %d, %Y')} - {self.week_end.strftime('%B %d, %Y')}**\n")
        report.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        report.append("---\n")

        # 1. PR Metrics
        report.append("## PR Pull Request Metrics\n")
        report.append(f"- **Total PRs Submitted:** {pr_metrics.get('total_submitted', 0)}")
        report.append(f"- **Total PRs Merged:** {pr_metrics.get('total_merged', 0)}\n")

        if pr_metrics.get('submitted'):
            report.append("### PRs Submitted by Team Member\n")
            for member, prs in pr_metrics['submitted'].items():
                report.append(f"**{member}** ({len(prs)} PRs)")
                for pr in prs:
                    report.append(f"  - [{pr['repo']}#{pr['number']}]({pr['url']}): {pr['title']}")
                report.append("")

        if pr_metrics.get('merged'):
            report.append("### PRs Merged by Team Member\n")
            for member, prs in pr_metrics['merged'].items():
                report.append(f"**{member}** ({len(prs)} PRs)")
                for pr in prs:
                    report.append(f"  - [{pr['repo']}#{pr['number']}]({pr['url']}): {pr['title']}")
                report.append("")

        report.append("---\n")

        # 2. Key Features
        report.append("## FEATURES Key Working Features\n")
        if features:
            for feature in features:
                status_emoji = "[DONE]" if feature.get('status') == 'Completed' else "[IN PROGRESS]" if feature.get('status') == 'In Progress' else "[PLANNED]"
                report.append(f"- {status_emoji} **{feature['name']}**")
                report.append(f"  - Lead: {feature.get('lead', 'Unassigned')}")
                report.append(f"  - Status: {feature.get('status', 'Unknown')}\n")
        else:
            report.append("*No features tracked this week*\n")

        report.append("---\n")

        # 3. JIRA Tickets
        report.append("## JIRA JIRA Ticket Progress\n")
        report.append(f"- **Tickets Completed:** {jira_metrics.get('total_completed', 0)}")
        report.append(f"- **Tickets In Progress:** {jira_metrics.get('total_in_progress', 0)}\n")

        if jira_metrics.get('completed'):
            report.append("### Completed Tickets\n")
            for member, tickets in jira_metrics['completed'].items():
                report.append(f"**{member}** ({len(tickets)} tickets)")
                for ticket in tickets:
                    report.append(f"  - [{ticket['key']}]({ticket['url']}): {ticket['summary']}")
                report.append("")

        if jira_metrics.get('in_progress'):
            report.append("### In Progress Tickets\n")
            for member, tickets in jira_metrics['in_progress'].items():
                report.append(f"**{member}** ({len(tickets)} tickets)")
                for ticket in tickets:
                    report.append(f"  - [{ticket['key']}]({ticket['url']}): {ticket['summary']}")
                report.append("")

        report.append("---\n")

        # 4. Model Support
        report.append("## MODEL New Model Support\n")
        if not model_support.get('error'):
            new_models = model_support.get('new_models', [])
            if new_models:
                for model in new_models:
                    report.append(f"- **{model.get('name')}**")
                    report.append(f"  - Provider: {model.get('provider', 'N/A')}")
                    report.append(f"  - Added by: {model.get('added_by', 'N/A')}")
                    report.append(f"  - Date: {model.get('added_date', 'N/A')}\n")
                report.append(f"*Total models supported: {model_support.get('total_models', 0)}*\n")
            else:
                report.append("*No new models added this week*\n")
        else:
            report.append(f"*{model_support.get('error')}*\n")

        report.append("---\n")

        # 5. Customer Engagement
        report.append("## CUSTOMER Customer Issue Engagement\n")
        report.append(f"- **Issues Responded To:** {customer_engagement.get('total_responded', 0)}")
        report.append(f"- **Issues Closed:** {customer_engagement.get('total_closed', 0)}\n")

        if customer_engagement.get('issues_responded'):
            report.append("### Issues Responded To\n")
            for member, issues in customer_engagement['issues_responded'].items():
                report.append(f"**{member}** ({len(issues)} responses)")
                for issue in issues[:5]:  # Limit to first 5
                    report.append(f"  - [{issue['repo']}#{issue['issue']}]({issue['url']}): {issue['title']}")
                if len(issues) > 5:
                    report.append(f"  - *...and {len(issues) - 5} more*")
                report.append("")

        if customer_engagement.get('issues_closed'):
            report.append("### Issues Closed\n")
            for member, issues in customer_engagement['issues_closed'].items():
                report.append(f"**{member}** ({len(issues)} closed)")
                for issue in issues[:5]:
                    report.append(f"  - [{issue['repo']}#{issue['issue']}]({issue['url']}): {issue['title']}")
                if len(issues) > 5:
                    report.append(f"  - *...and {len(issues) - 5} more*")
                report.append("")

        report.append("---\n")

        # Footer
        report.append(f"\n*Dashboard generated automatically by Team Dashboard Generator*")

        return '\n'.join(report)

    def format_html_report(self, pr_metrics, jira_metrics, features, model_support, customer_engagement):
        """Format the dashboard report as HTML"""
        # Load HTML template
        template_path = Path(__file__).parent / 'dashboard_template.html'

        if not template_path.exists():
            print(f"⚠ Template not found at {template_path}, falling back to markdown")
            return self.format_report(pr_metrics, jira_metrics, features, model_support, customer_engagement)

        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        template = Template(template_content)

        # Prepare data for template
        context = {
            'week_start': self.week_start.strftime('%B %d, %Y'),
            'week_end': self.week_end.strftime('%B %d, %Y'),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'pr_metrics': pr_metrics,
            'jira_metrics': jira_metrics,
            'features': features,
            'model_support': model_support,
            'customer_engagement': customer_engagement
        }

        # Render template
        html_output = template.render(**context)
        return html_output


def main():
    parser = argparse.ArgumentParser(description='Generate team weekly dashboard')
    parser.add_argument('--config', default='config.yaml', help='Path to config file')
    parser.add_argument('--weeks-ago', type=int, default=0, help='Generate report for N weeks ago (0 = current week)')
    parser.add_argument('--format', choices=['html', 'markdown', 'both'], default='html', help='Output format (default: html)')
    args = parser.parse_args()

    generator = DashboardGenerator(args.config)
    generator.set_week_range(args.weeks_ago)
    generator.setup_clients()
    generator.generate_report(output_format=args.format)


if __name__ == '__main__':
    main()
