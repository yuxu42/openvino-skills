# OpenVINO Industry Intelligence Dashboard

Weekly-updated HTML dashboard for OpenVINO PMs tracking the AI inference ecosystem — trending models, framework activity, agent integration gaps, and new architecture topology analysis for client iGPU/dGPU deployment.

## Quick Start

**Update this week's dashboard:**
```
/ov-industry-intel
```
Or tell Claude: *"Update the OpenVINO industry intelligence dashboard for this week"*

**Open the dashboard:**
```bash
# Windows
start industry-intelligence-dashboard.html

# macOS / Linux
open industry-intelligence-dashboard.html
```

## What Claude Does Each Week

1. Web-searches for new model releases (past 1–2 weeks)
2. Identifies models fitting ≤32GB VRAM as iGPU/dGPU targets
3. Fetches latest inference framework versions and features
4. Analyzes new architectures for OV op-level gaps
5. Updates the `DATA SECTION` in the HTML file and reports a summary

## Dashboard Contents

| Section | What it covers |
|---|---|
| KPI Cards | P1 model gaps · high-impact gaps · agent gaps · framework integrations |
| Trending Models | Open-weight models (past 1–4 weeks) with VRAM, OV status, priority |
| Inference Frameworks | vLLM, SGLang, llama.cpp, Ollama, ONNX Runtime, TRT-LLM, TGI |
| Agent Ecosystem | LangChain, LangGraph, LlamaIndex, AutoGen, smolagents, CrewAI, OAI Agents SDK |
| Gap Tracker | High-impact OV engineering gaps with status |
| Architecture Analysis | New topologies for ≤32GB models — missing ops, graph gaps, OV status |
| Action Items | Browser-persisted checklist (localStorage, resets weekly) |

## Manual Data Update

Edit only the `DATA SECTION` at the top of `<script>` in `industry-intelligence-dashboard.html`:

```javascript
const WEEK    = "WW46";
const YEAR    = "2026";
const UPDATED = "2026-11-12";

const trendingModels    = [ ... ]; // 8–12 entries
const frameworkActivity = [ ... ]; // 6–8 entries
const agentFrameworks   = [ ... ]; // 6–8 entries
const gaps              = [ ... ]; // 5–8 entries
const archAnalysis      = [ ... ]; // 3–6 new topology entries
const defaultActions    = [ ... ]; // 4–8 action items
```

The rendering code below the `// RENDERING` comment never needs to change.

## Documentation

See `SKILL.md` for the full skill reference including:
- Architecture gap taxonomy (Critical / Partial / Optimization)
- OV primitive support table (Nov 2026)
- Status value reference for all data fields
- Related skills
