---
name: paper-orchestra
description: EZMM writer-stage adapter for the vendored PaperOrchestra skill pack. Use by default during pipeline/04-paper-writing for outline-first paper drafting, literature-review planning, section writing, and refinement discipline. The adapter maps EZMM runtime artifacts to PaperOrchestra-style inputs, runs PaperOrchestra-first writing automatically, and returns EZMM-compatible paper.md.
---

# paper-orchestra adapter for EZ Math Model

This is the EZMM-facing adapter for the vendored upstream PaperOrchestra pack at
`external/paper-orchestra/`. It lets the EZMM writer call PaperOrchestra's
writing skills without changing EZMM's contest-paper contract.

Upstream source: `https://github.com/Ar9av/PaperOrchestra`

Paper citation: Song et al., "PaperOrchestra: A Multi-Agent Framework for
Automated AI Research Paper Writing", arXiv:2604.05018, 2026.

## When writer calls this

Load this adapter in `pipeline/04-paper-writing` before drafting `paper.md`.
Use it to create a structured writing workspace, generate or refresh a paper
outline, organize literature-review tasks, draft the body, and run a refinement
pass.

Do not use this adapter to bypass EZMM hard rules. The final `paper.md` must
still satisfy `prompts/writer.md`, `references/roles/writer-guide.md`, and
`pipeline/05-quality-audit.md`.

## Source roots

All paths below are relative to `skills/ez-math-model/`.

| Purpose | Path |
|---|---|
| EZMM adapter | `tools/paper-orchestra/SKILL.md` |
| Vendored upstream pack | `external/paper-orchestra/` |
| Upstream orchestrator | `external/paper-orchestra/skills/paper-orchestra/SKILL.md` |
| Upstream outline agent | `external/paper-orchestra/skills/outline-agent/SKILL.md` |
| Upstream literature agent | `external/paper-orchestra/skills/literature-review-agent/SKILL.md` |
| Upstream section writer | `external/paper-orchestra/skills/section-writing-agent/SKILL.md` |
| Upstream refinement agent | `external/paper-orchestra/skills/content-refinement-agent/SKILL.md` |
| Upstream shared writing checks | `external/paper-orchestra/skills/shared/writing_quality_check.md` |

When running upstream helper scripts, set the working directory to
`external/paper-orchestra/` so upstream examples like
`python skills/paper-orchestra/scripts/validate_inputs.py ...` resolve
correctly.

## Default mode: PaperOrchestra-first writing

The writer runs PaperOrchestra-first by default. Do not wait for a separate
PaperOrchestra request. Build the PaperOrchestra workspace automatically from
EZMM runtime artifacts, run the upstream outline,
literature, section-writing, and refinement protocol as far as the local inputs
and tools allow, then bridge the result back to EZMM's required
`runtime/{task_id}/paper.md`.

When a usable LaTeX template and TeX toolchain are available or can be safely
scaffolded, also produce the upstream-style package under
`runtime/{task_id}/paper_orchestra/final/`. The EZMM-compatible `paper.md`
remains mandatory because downstream quality audit and packaging consume it.

Create a local workspace:

```text
runtime/{task_id}/paper_orchestra/
├── inputs/
│   ├── idea.md
│   ├── experimental_log.md
│   ├── conference_guidelines.md
│   └── figures/
├── outline.json
├── refs/
├── drafts/
│   ├── paper.tex
│   └── paper.md
├── refinement/
│   └── worklog.json
├── final/
│   ├── paper.tex
│   └── paper.pdf
└── adapter_report.md
```

Map EZMM inputs into PaperOrchestra-style inputs:

| PaperOrchestra input | EZMM source |
|---|---|
| `idea.md` | `problem.md`, `intake.json`, `modeling_plan.md`, and the intended contribution of each quesN |
| `experimental_log.md` | `execution_log.md`, `src/*.py` final print blocks, `results/*.csv|json`, and accepted chart manifest entries |
| `conference_guidelines.md` | contest name, language, run_mode, section requirements from `templates/chapter_outline.toml`, plus EZMM no-bullet and no-leakage rules |
| `inputs/figures/` | copies or references to `figures/*.png` with `usable_in_paper=true` |

The adapter report must record which EZMM files were consumed, which accepted
figures must appear in the paper, and whether any PaperOrchestra sub-step was
degraded or skipped.

## Writing workflow

1. Read upstream `outline-agent/SKILL.md` and use its schema discipline to
   produce `paper_orchestra/outline.json`. For EZMM, `section_plan` must map to
   the contest sections in `templates/chapter_outline.toml`.
2. Read upstream `literature-review-agent/SKILL.md` for search, verification,
   deduplication, and citation-pool discipline. Prefer EZMM
   `tools/scholar/SKILL.md` or `tools/paper_search/SKILL.md` for actual
   metadata retrieval, because those tools already follow the EZMM env and
   setup policy.
3. Read upstream `section-writing-agent/SKILL.md` for single-pass global
   coherence, table construction, figure-text alignment, and citation-key
   discipline. Prefer the upstream LaTeX draft path when the workspace has a
   usable template; then convert or mirror the accepted content into EZMM
   Markdown. If LaTeX inputs or tools are unavailable, adapt LaTeX-only
   instructions directly to Markdown:
   - figures stay as `![描述](figures/name.png)`;
   - tables stay as Markdown tables unless `paper_*.md` template requires
     otherwise;
   - formulas stay in pandoc-compatible `$...$` / `$$...$$`;
   - do not introduce LaTeX preamble, `\section`, `\cite`, or BibTeX in
     `paper.md`.
4. Read upstream `content-refinement-agent/SKILL.md` and run refinement by
   default unless the draft is blocked by missing factual inputs. Accept a
   revision only when it improves correctness, figure-text binding, citation
   integration, or clarity without weakening EZMM constraints.
5. Write the final Markdown to `runtime/{task_id}/paper.md` only after the
   adapter's self-check passes.

## Upstream LaTeX package

Run the upstream orchestrator automatically when the required
`workspace/inputs/template.tex` and `workspace/inputs/conference_guidelines.md`
can be supplied from EZMM templates or local contest metadata. Use
`external/paper-orchestra/skills/paper-orchestra/SKILL.md` unchanged for that
sub-run and write outputs under `paper_orchestra/final/`.

If the full LaTeX route is not runnable, do not ask the user. Record the reason
in `adapter_report.md`, continue with the Markdown adaptation path, and keep the
same PaperOrchestra outline/literature/section/refinement discipline.

## Required self-check before returning to writer

Before this adapter hands control back to the writer stage, confirm:

- `paper_orchestra/outline.json` exists or `adapter_report.md` explains why it
  was skipped.
- `adapter_report.md` records whether the full upstream LaTeX route ran or
  which missing input/tool caused an automatic Markdown adaptation.
- Every `chart_manifest.json` entry with `status=accepted` and
  `usable_in_paper=true` is listed in `adapter_report.md`.
- `paper.md` references only figures allowed by EZMM chart manifest.
- No PaperOrchestra workspace paths, upstream script paths, `runtime/`,
  `adapter_report.md`, or `outline.json` leak into the paper body.
- Citations are unique and compatible with EZMM's `{[^N] ...}` protocol.
- Any skipped PaperOrchestra sub-step is recorded as a quality-audit note.

## Licensing note

The vendored upstream pack is MIT licensed. Keep the upstream `LICENSE`,
`CITATION.cff`, and README under `external/paper-orchestra/`, and cite
PaperOrchestra when its workflow materially shapes the final paper.
