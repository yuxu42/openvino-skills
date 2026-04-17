# JIRA Ticket Counting Logic

## Overview

The dashboard counts JIRA tickets based on **status changes within the weekly timeframe**, specifically tracking tickets that moved to "Implemented" or "Closed" status during the week.

---

## Counting Criteria

### ✅ Completed Tickets

A ticket is counted as "completed" if:

1. **Current status** is `"Implemented"` OR `"Closed"`
2. **Status changed** to one of these states **during the week**
3. **Assigned** to a team member

### 📊 In Progress Tickets

A ticket is counted as "in progress" if:

1. **Current status** is one of:
   - `"In Progress"`
   - `"In Review"`
   - `"In Development"`
2. **Assigned** to a team member

---

## Technical Implementation

### JIRA Query

```jql
project = OpenVINO AND 
assignee in (yxu28, zhangyi7, mangguo, liubo2, 
             yuanhu1, xiuchuan, xuchen, chenhuwa) AND 
updated >= -7d
```

### Changelog Analysis

For each ticket, the system:

1. **Fetches the changelog** (history of status changes)
2. **Checks each status transition** for dates within the week
3. **Identifies transitions** to "Implemented" or "Closed"
4. **Counts only** if the transition occurred within the weekly timeframe

### Code Logic

```python
def get_jira_tickets(self):
    # Query JIRA for tickets updated this week
    jql = f'project = {project_key} AND assignee in ({team_filter}) AND updated >= -7d'
    issues = jira_client.search_issues(jql, expand='changelog')
    
    for issue in issues:
        current_status = issue.fields.status.name
        
        # Check changelog for status changes this week
        for history in issue.changelog.histories:
            history_date = parse_date(history.created)
            
            if week_start <= history_date < week_end:
                for item in history.items:
                    if item.field == 'status':
                        if item.toString in ["Implemented", "Closed"]:
                            # Count this ticket as completed
                            metrics["completed"].append(issue)
```

---

## Why This Approach?

### ❌ **Wrong Approach:** Count by Current Status Only

```python
# DON'T DO THIS
if current_status in ["Implemented", "Closed"]:
    count += 1  # This counts ALL tickets in that status, not just this week!
```

**Problem:** This would count tickets that were completed weeks or months ago, not just this week.

### ✅ **Correct Approach:** Count by Status Change Date

```python
# DO THIS
if current_status in ["Implemented", "Closed"] and status_changed_this_week:
    count += 1  # Only counts tickets completed THIS WEEK
```

**Benefit:** Accurate weekly reporting of team productivity.

---

## Examples

### Example 1: Ticket Counted ✅

**Ticket:** OV-12345
- **Assigned to:** xuchen
- **Status:** Implemented
- **Status changed:** Monday, April 14, 2026
- **Week:** April 13-20, 2026

**Result:** ✅ **Counted** - Status changed to "Implemented" within the week

---

### Example 2: Ticket NOT Counted ❌

**Ticket:** OV-11111
- **Assigned to:** xuchen
- **Status:** Implemented
- **Status changed:** March 15, 2026 (3 weeks ago)
- **Week:** April 13-20, 2026

**Result:** ❌ **Not Counted** - Status changed outside the weekly timeframe

---

### Example 3: Multiple Transitions

**Ticket:** OV-12346
- **Assigned to:** zhangyi7
- **Status History:**
  - April 10: "In Progress"
  - April 14: "In Review"
  - April 16: "Closed"
- **Week:** April 13-20, 2026

**Result:** ✅ **Counted** - Final transition to "Closed" happened within the week

---

## Team Member Mapping

### GitHub Usernames → JIRA Usernames

| Team Member | GitHub | JIRA |
|-------------|--------|------|
| Chen Xu | xuchen-intel | xuchen |
| Xiuchuan Zhai | azhai219 | xiuchuan |
| Zhang Yi | zhangYiIntel | zhangyi7 |
| Chenhu Wang | chenhu-wang | chenhuwa |
| Cecilia Peng | ceciliapeng2011 | yxu28 |
| Bo Liu | liubo-intel | liubo2 |
| Yuan Hu | tiger100256-hu | yuanhu1 |
| Mang Guo | mangguo321 | mangguo |

---

## Weekly Cadence

### Week Definition

- **Starts:** Monday at 00:00:00
- **Ends:** Sunday at 23:59:59
- **Duration:** 7 days

### Example Week

```
Week of April 13, 2026:
├─ Start: Monday, April 13, 2026 00:00:00
├─ Mon │ Tue │ Wed │ Thu │ Fri │ Sat │ Sun
└─ End:   Sunday, April 20, 2026 23:59:59
```

### Historical Weeks

```bash
# Current week (default)
python generate_dashboard.py

# Last week
python generate_dashboard.py --weeks-ago 1

# 2 weeks ago
python generate_dashboard.py --weeks-ago 2
```

---

## Dashboard Output

### Completed Tickets Section

```
JIRA Ticket Progress
────────────────────────────────────────────────────────────
Tickets Completed: 15 (Implemented or Closed this week)
Tickets In Progress: 8

Completed Tickets:
  xuchen (3 tickets)
  • OV-12345: Implement Llama 3 support [Implemented]
  • OV-12346: Fix memory management issues [Closed]
  • OV-12347: Update GenAI documentation [Implemented]
  
  zhangyi7 (2 tickets)
  • OV-12351: Benchmark new models [Implemented]
  • OV-12352: Performance optimization [Closed]
```

**Key Points:**
- Shows status badge: `[Implemented]` or `[Closed]`
- Only includes tickets completed within the week
- Grouped by team member
- Direct links to JIRA

---

## Validation

### How to Verify Counts Are Correct

1. **Run the JIRA filter:**
   ```
   https://jira.devtools.intel.com/issues/?jql=
   project=OpenVINO AND 
   assignee in (yxu28, zhangyi7, mangguo, liubo2, 
                yuanhu1, xiuchuan, xuchen, chenhuwa) AND
   updated >= -7d
   ```

2. **Manually check each ticket:**
   - Click on ticket
   - View "History" tab
   - Check when status changed to "Implemented" or "Closed"
   - Verify it was within the week

3. **Compare with dashboard:**
   - Dashboard count should match manual count
   - Each ticket should be listed under correct team member

---

## Configuration

### Customize Status Names

If your JIRA uses different status names, update in `generate_dashboard.py`:

```python
# In get_jira_tickets() method:

# For completed tickets
if item.toString in ["Implemented", "Closed", "Your Custom Status"]:
    status_changed_this_week = True

# For in-progress tickets
elif current_status in ["In Progress", "In Review", "Your Custom Status"]:
    metrics["in_progress"][assignee].append(issue_data)
```

### Adjust Timeframe

Default is weekly (7 days). To change:

```python
# In set_week_range() method:
week_start = today - timedelta(days=today.weekday())
week_end = week_start + timedelta(days=7)  # Change this number
```

---

## Troubleshooting

### Issue: No Tickets Counted

**Possible Causes:**
1. Tickets don't have correct assignee
2. No status changes happened this week
3. Status names don't match exactly

**Solution:**
- Check JIRA usernames in `config.yaml`
- Verify ticket status names
- Check date range

### Issue: Wrong Count

**Possible Causes:**
1. Changelog not accessible
2. Date parsing issues
3. Multiple status transitions

**Solution:**
- Ensure JIRA API token has read access
- Check `expand='changelog'` in query
- Review ticket history manually

---

## API Requirements

### Permissions Needed

- **JIRA API Token:** Read access to OpenVINO project
- **Permissions:** Browse project, view issues, read issue details

### Rate Limits

- JIRA API: Typically 1000-5000 requests/hour
- Dashboard uses ~1-2 requests per 10 tickets
- Weekly report: ~10-50 API calls total

---

## Summary

✅ **Counts:** Tickets with status changed to "Implemented" or "Closed" within the week
✅ **Timeframe:** Weekly (Monday to Sunday)
✅ **Team Filter:** Only your 8 team members
✅ **Accuracy:** Uses changelog to verify transition dates
✅ **Output:** Beautiful HTML dashboard with per-member breakdown

This ensures accurate, weekly productivity tracking for your team!
