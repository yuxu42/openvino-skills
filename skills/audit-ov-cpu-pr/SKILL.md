name: audit-ov-cpu-open-pullrequests
description: This skill audits open pull requests in the OV CPU repository.

Repository: https://github.com/openvinotoolkit/openvino
PR category: "CPU"
PR state: "open"
PR author: from PRC contributor list

**Output:**
- A list of open pull requests in the OV CPU repository, including:
  - PR title
  - PR author
  - PR link
  - PR creation date
  - PR description (if available)
  - Whether PR is reviewed or not (if available)
  - Whether PR has any comments or not (if available)
  - Whether PR is approved by any reviewers or not (if available)

- Save the output in a structured format (e.g., CSV) for further analysis.