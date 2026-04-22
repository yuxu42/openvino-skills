---
name: generate-presentation
description: End-to-end PowerPoint presentation generation from raw materials. Use when the user wants to create, edit, or revise .pptx slide decks from notes, tables, emails, or requirements — covers summarization, markdown outline, PPTX generation, visual QA, and review-driven revision loops.
---

Source: https://github.com/yuxu42/frameworks.ai.openvino.llm.prc-skills (skills under `skills/pptx/`, `skills/summarize-materials-for-presentation/`, `skills/generate-slide-markdown/`, `skills/convert-markdown-to-pptx/`, `skills/revise-presentation-from-review/`, `skills/generate-presentation-from-materials/`, `skills/presentation-generation-agent/`)

## Overview

A suite of 7 interconnected Claude Code skills that form a pipeline for generating management-ready PowerPoint presentations from raw input materials. The pipeline runs four phases — summarize, outline, generate, revise — with an optional autonomous agent wrapper that drives all phases with minimal user interaction.

## Architecture

The system is organized in layers:

| Layer | Skill | Purpose |
|-------|-------|---------|
| **Core** | `pptx` | Low-level .pptx reading, editing, and creation with design guidance and QA |
| **Phase 1** | `summarize-materials-for-presentation` | Distill raw notes/tables/emails into executive-ready messaging |
| **Phase 2** | `generate-slide-markdown` | Convert summary into structured slide markdown with `---` delimiters |
| **Phase 3** | `convert-markdown-to-pptx` | Render markdown into .pptx with content and visual QA |
| **Phase 4** | `revise-presentation-from-review` | Map review feedback to edits, regenerate, and re-verify |
| **Orchestrator** | `generate-presentation-from-materials` | Chains phases 1-4 as a pipeline with iteration loop |
| **Agent** | `presentation-generation-agent` | Autonomous wrapper managing workspace, revision logs, and end-to-end execution |

## Pipeline Workflow

```
Raw Materials (notes, tables, emails)
        │
        ▼
  Phase 1: Summarize
  - Extract core message, supporting themes, key metrics
  - Rewrite in audience-appropriate language
        │
        ▼
  Phase 2: Generate Slide Markdown
  - Build storyline (title → summary → results → ask → close)
  - 3-5 bullets per slide, insight-oriented titles
        │
        ▼
  Phase 3: Convert to PPTX
  - Generate .pptx via PptxGenJS (from scratch) or python-pptx
  - Content QA: extract text, check for placeholders
  - Visual QA: render slides to images, inspect with subagents
        │
        ▼
  Phase 4: Review & Revise
  - Accept feedback on content, wording, layout, styling
  - Decide edit layer (markdown vs. PPTX styling)
  - Regenerate and re-verify until approved
```

## Core PPTX Capability

The `pptx` skill provides three workflows:

| Task | Approach |
|------|----------|
| Read/analyze | `python -m markitdown presentation.pptx` for text extraction |
| Edit from template | Unpack .pptx ZIP → manipulate XML → validate → repack |
| Create from scratch | PptxGenJS (Node.js) for full visual control |

### Python Scripts

- **`add_slide.py`** — Duplicate or create slides from layouts, handling Content_Types.xml and relationship IDs
- **`clean.py`** — Remove orphaned slides, unreferenced media/charts/diagrams, and stale .rels files
- **`thumbnail.py`** — Generate visual grid of all slides using LibreOffice + Poppler
- **`office/unpack.py`** — Extract and pretty-print .pptx XML
- **`office/pack.py`** — Validate, auto-repair, and repack into valid .pptx
- **`office/validate.py`** — CLI schema validation against OOXML XSD schemas with differential error reporting
- **`office/soffice.py`** — LibreOffice helper with sandbox workaround (LD_PRELOAD shim for AF_UNIX socket restrictions)

### Validators

- **`BaseSchemaValidator`** — XML well-formedness, namespace validation, unique ID checks, XSD validation, Content_Types verification
- **`PPTXSchemaValidator`** — PPTX-specific: UUID validation, slide layout ID checks, notes slide references, duplicate layout detection

### QA Process (Required)

1. **Content QA**: Extract text via markitdown, grep for placeholder text (`xxxx`, `lorem`, `ipsum`)
2. **Visual QA**: Convert to images via LibreOffice + pdftoppm, inspect with subagents for overlapping elements, text overflow, spacing issues, low contrast
3. **Verification loop**: Generate → inspect → fix → re-verify until clean. At least one fix-and-verify cycle required before declaring success.

## Design Guidance

The skill includes opinionated visual design rules:

- **10 color palettes** (Midnight Executive, Forest & Moss, Coral Energy, Warm Terracotta, Ocean Gradient, etc.)
- **Typography pairings** (Georgia/Calibri, Arial Black/Arial, Cambria/Calibri, etc.) with sizing rules (titles 36-44pt, body 14-16pt)
- **Layout options**: two-column, icon grids, half-bleed images, stat callouts, 2x2/2x3 grids
- **Spacing**: 0.5" minimum margins, 0.3-0.5" between content blocks
- **Anti-patterns**: no accent lines under titles, no text-only slides, no centered body text, no default-blue palettes

## Agent Wrapper

The `presentation-generation-agent` adds autonomous operation:

- **Workspace scaffolding** via `init_presentation_workspace.py`:
  ```
  deck-folder/
  ├── input/          # source materials
  ├── working/        # summary.md, deck.md, revision-log.md
  ├── output/         # deck.pptx, rendered-slides/
  └── scripts/        # generate_ppt.py
  ```
- **Revision tracking** via `append_review_round.py` — structured log of each review round
- **Two modes**: initial generation (phases 1-4) and revision round (collect feedback → edit → regenerate → QA)

## Dependencies

| Package | Source | Purpose |
|---------|--------|---------|
| `markitdown[pptx]` | pip | Text extraction from .pptx |
| `Pillow` | pip | Thumbnail grid generation |
| `defusedxml` | pip | Safe XML parsing |
| `lxml` | pip | XSD schema validation |
| `pptxgenjs` | npm (global) | Creating presentations from scratch |
| `react-icons`, `sharp` | npm | Icon rendering for slides |
| LibreOffice (`soffice`) | system | PDF conversion |
| Poppler (`pdftoppm`) | system | PDF to image rasterization |

## Usage

### Recommended entry point

Use `generate-presentation-from-materials` for step-by-step control, or `presentation-generation-agent` for autonomous end-to-end execution.

### Example prompts

- "Create a management deck from these materials and save all artifacts in this folder."
- "Generate markdown first, then PowerPoint after I review the markdown."
- "Revise the deck using these review comments and regenerate the .pptx."
- "Run the full presentation workflow autonomously and keep a revision log."
