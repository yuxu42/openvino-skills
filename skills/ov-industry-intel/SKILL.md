---
name: ov-industry-intel
description: Generate a weekly OpenVINO industry intelligence dashboard tracking trending models (with VRAM/edge suitability), inference frameworks, agent ecosystem integration status, OpenVINO gap analysis, and new architecture topology gaps for iGPU/dGPU deployment. Performs live web searches to stay current.
---

# OpenVINO Industry Intelligence Dashboard

## Overview

A weekly-updated, fully self-contained HTML dashboard for OpenVINO PMs to monitor the AI inference ecosystem. Claude performs live web searches each week to populate:

- **Trending open-weight models** — with VRAM footprint, edge suitability, and OV support status
- **Inference framework activity** — latest versions, key features, OV integration status
- **Agent ecosystem** — which agent frameworks have OV integration and what's missing
- **OpenVINO gap tracker** — high-impact gaps requiring engineering action
- **New architecture tech analysis** — deep-dive on new model topologies, focused on models fitting ≤32GB VRAM (client iGPU/dGPU), with specific OV op-level gap analysis

## When To Use

- **Weekly review**: What models/frameworks dropped this week that OpenVINO should respond to?
- **Gap identification**: Which new architectures can't run on OpenVINO (or run with quality gaps)?
- **Edge deployment planning**: Which new models fit on client iGPU/dGPU (<32GB VRAM)?
- **Stakeholder reporting**: Clear visual summary of OpenVINO's ecosystem position vs. competitors

## Invoking the Skill

```
/ov-industry-intel
```

Or prompt Claude naturally:
```
Update the OpenVINO industry intelligence dashboard for this week
```

Claude will:
1. Web-search for new model releases (past 1–2 weeks)
2. Identify models fitting ≤32GB VRAM as iGPU/dGPU targets
3. Fetch latest versions and features for tracked inference frameworks
4. Analyze new model architectures for OV topology gaps (op-level)
5. Update the HTML file DATA SECTION and confirm the output

## Dashboard Sections

### 1. KPI Summary Cards
Four at-a-glance metrics auto-computed from the data:
- P1 models with OV gaps
- High-impact engineering gaps
- Agent frameworks with gaps
- Inference frameworks with OV integration

### 2. Trending Models Table
Focus: open-weight models released in the past 1–4 weeks, prioritizing those fitting ≤32GB VRAM.

| Column | Values |
|---|---|
| Model / Maker + date | name, lab, release month |
| Type | LLM (Dense), LLM (MoE), SLM, ASR, Diffusion, etc. |
| Size | param count + active params + context window |
| Modality | Text, Vision, Audio, Video combinations |
| OpenVINO Status | Supported / Partial / Testing / Gap |
| Priority | P1 (must support) / P2 (important) / P3 (track) |
| Notes | Key architecture notes, OV-specific caveats |

### 3. Inference Framework Activity
Tracks: vLLM, SGLang, llama.cpp, Ollama, ONNX Runtime, TensorRT-LLM, HuggingFace TGI.

Per entry: latest version, latest major features, OV integration status, actionable notes.

### 4. Agent Ecosystem
Tracks: LangChain/LangGraph, LlamaIndex, AutoGen/MS Agent Framework, smolagents, CrewAI, OpenAI Agents SDK.

Per entry: version, OV support status, specific integration gaps.

### 5. OpenVINO Gap Tracker
Structured gap entries: area name, impact (High/Medium/Low), status (Gap/In-Progress/Investigating/Planned), affected models, detailed description.

### 6. New Architecture Tech Analysis
Deep technical analysis of new model topologies appearing in the past 1–2 months, with focus on models that fit ≤32GB VRAM (client iGPU/dGPU targets).

Per topology card:
- **Severity**: Critical / Partial / Optimization (see taxonomy below)
- **Affected models** with estimated VRAM footprint
- **Technical mechanism** — how the topology works (2–4 sentences)
- **OpenVINO gaps** — specific missing ops, graph patterns, or pipeline mismatches
- **OV Status** — actionable one-liner

### 7. Action Items + Weekly Notes
Browser-persisted checklist (localStorage, keyed by week — auto-resets each new week). Add, check off, or remove items in the browser without editing the file.

## Architecture Gap Taxonomy

| Severity | Meaning | Typical Examples |
|---|---|---|
| **Critical** | Model cannot run — missing op or graph incompatible | Mamba-2 SSM op, encoder-free multimodal VLM pipeline |
| **Partial** | Model runs but with correctness or quality issues | Dual RoPE falls back to single-θ, PLE embedding fusing |
| **Optimization** | Model runs correctly but with efficiency gap vs hardware | MXFP4 → must dequantize to FP16, doubles VRAM cost |

### Key OV Primitives to Check for New Topologies

| Category | OV Status (Nov 2026) |
|---|---|
| Standard MHA / GQA attention | Supported |
| Sliding-window (local) attention | Partial — no native mask |
| Gated Delta Net (GDN) linear attention | Supported (SDPA backend); PA backend bug in 2026.4 |
| Mamba-2 / SSM selective scan | Not supported |
| Standard MoE routing | Supported (Qwen3-30B-A3B, Gemma 4 26B) |
| Latent MoE routing (Nemotron 3.5) | Not supported |
| Per-Layer Embeddings (PLE) | Partial — may fuse incorrectly |
| Dual RoPE (global + local freq) | Partial — single-θ only |
| Encoder-free multimodal backbone | Not supported |
| INT4 / FP8 quantization | Supported |
| MXFP4 / NVFP4 quantization | Not supported (dequantize path only) |
| MTP multi-token prediction heads | Not supported |
| Shared KV cache across layers | Not supported |

## Data Update Guide

Open `industry-intelligence-dashboard.html`, find the `DATA SECTION` and update:

```javascript
const WEEK    = "WW46";        // ← change each week
const YEAR    = "2026";
const UPDATED = "2026-11-12";  // ← today's date

const trendingModels   = [ ... ];  // 8–12 entries
const frameworkActivity = [ ... ]; // 6–8 entries
const agentFrameworks  = [ ... ];  // 6–8 entries
const gaps             = [ ... ];  // 5–8 entries
const archAnalysis     = [ ... ];  // 3–6 entries (new topologies this week)
const defaultActions   = [ ... ];  // 4–8 items
```

Only the content inside the arrays changes — the rendering code below the `RENDERING` comment is never touched.

### Status Value Reference

```javascript
// trendingModels.ovinoStatus / frameworkActivity.integration / agentFrameworks.ovinoSupport
"supported"  // green  — works in OV GenAI pipeline
"partial"    // amber  — works with workarounds or feature gaps
"testing"    // blue   — validation in progress
"gap"        // red    — not yet supported
"none"       // gray   — no integration at all
"na"         // gray   — not applicable (e.g. archived framework)

// archAnalysis.severity
"critical"      // red border  — cannot run
"partial"       // amber border — quality/correctness gap
"optimization"  // blue border  — runs but inefficient

// gaps.impact / gaps.status
"high" | "medium" | "low"
"gap" | "in-progress" | "investigating" | "planned"
```

## File Structure

```
ov-industry-intel/
├── SKILL.md                             # This file — skill documentation
├── README.md                            # Quick start guide
└── industry-intelligence-dashboard.html # Standalone dashboard (open in any browser)
```

## Related Skills

- `team-dashboard`: Weekly team PR/JIRA activity metrics
- `jira-cpu-issue-tracker`: CPU bug/issue tracking from JIRA

## Notes

- Dashboard is fully offline — no API calls at runtime; all data is embedded in the HTML
- Action items and notes are stored in browser `localStorage`, keyed by `ov-intel-actions-{WEEK}-{YEAR}` — changes each week so the board starts fresh automatically
- Recommended update cadence: Wednesday or Thursday before weekly team syncs
- The HTML file is ~1600 lines; only the DATA SECTION (~250 lines at the top of `<script>`) changes weekly
- When Claude updates the dashboard, it performs at least 4 web searches: (1) recent model releases, (2) framework versions, (3) OV release notes, (4) architecture deep-dives for new topologies
