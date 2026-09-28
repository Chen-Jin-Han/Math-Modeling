# PaperWritingBench Overview

Source: arXiv:2604.05018, §3 ("Task and Dataset"), App. C ("Dataset Details").

## Composition

| Venue | Papers | Cutoff | Avg figs | Avg tables | Avg cites |
|---|---|---|---|---|---|
| CVPR 2025 | 100 | 2024-11-01 | 5.20 ± 1.73 | 4.20 ± 1.65 | 58.52 ± 17.55 |
| ICLR 2025 | 100 | 2024-10-01 | 9.19 ± 5.39 | 8.13 ± 5.19 | 59.18 ± 20.01 |

ICLR 2025 papers exhibit "higher visual and analytical density than CVPR 2025"
(App. C.1) — roughly twice as many figures and tables, and substantially
longer experimental logs (mean 2,387 vs 1,530 words).

## Idea variant statistics

| Variant | Avg word count CVPR | Avg word count ICLR |
|---|---|---|
| Dense  | 1,082.82 ± 263.45 | 1,056.78 ± 165.62 |
| Sparse |   591.42 ±  52.68 |   586.96 ±  53.81 |

Sparse ideas are roughly half the length of Dense ideas. Both are kept
deliberately constrained — the bench tests whether the pipeline can
reconstruct a full paper from sparse human notes, not from a complete
draft.

## Construction pipeline

Per App. C.2:

1. **Sample** papers from OpenReview (ICLR) and the CVF Open Access
   repository (CVPR).
2. **Extract** with MinerU (Wang et al., 2024) for the markdown body and
   PDFFigures 2.0 (Clark and Divvala, 2016) for visual entities and
   captions. Discard incomplete or misparsed samples.
3. **Reverse-engineer** raw materials with Gemini-3.1-Pro (or any capable
   LLM in your host) using the three verbatim prompts in this skill's
   `references/`:
   - `sparse-idea-prompt.md`
   - `dense-idea-prompt.md`
   - `experimental-log-prompt.md`
4. **Anonymize**: strip authors, titles, citations, URLs, figure/table
   references. The result must be self-contained.
5. **Inject visual context** (App. C.2 "Structured Context Injection"):
   when generating the experimental log, the paper passes the actual
   figure images alongside the text to the extraction LLM, so the model
   can convert visual insights into standalone factual observations
   (e.g., "training loss converged after 200 epochs"). This avoids the
   common failure mode of "naive text-only extraction corrupts tabular
   and mathematical data."

## Why two variants

The Dense vs Sparse split tests robustness to input granularity:

- **Dense**: closer to a real research note from a scientist — preserves
  the math, the architectural specifics, the variable definitions. Tests
  whether the system can faithfully translate detailed technical content
  into a polished manuscript.
- **Sparse**: closer to a brainstorming note — high-level concept only.
  Tests whether the system can fill in formal mathematical structure
  from a rough sketch.

The paper's ablation (Table 5) shows Dense wins more on "Overall Paper
Quality" (43-56% Dense win vs 18-24% Sparse win) but the gap is much
smaller for "Lit Review" (32-40% Dense win vs 33-40% Sparse win) —
demonstrating that the literature search step is robust to input density.

## Cutoff dates

The paper aligns research cutoff with venue submission deadline:

| Venue | Submission deadline | Cutoff used |
|---|---|---|
| CVPR 2025 | November 2024 | `2024-11-01` |
| ICLR 2025 | October 2024  | `2024-10-01` |

For other venues, use one month before the stated submission deadline as
the cutoff. Encode as `YYYY-MM-DD`. Months default to day-1 (e.g., "October"
→ `2024-10-01`).

## Using the bench with your own pipeline

To benchmark a coding agent's paper-writing skill, run:

```
1. Pick a paper from your held-out set (NOT in the LLM's training data
   ideally — the paper notes pre-training contamination is an inherent
   risk; use unpublished or recent work to mitigate).
2. Run paper-writing-bench to extract idea_sparse.md / idea_dense.md /
   experimental_log.md.
3. Run paper-orchestra on those inputs (with the venue's template and
   guidelines).
4. Run paper-autoraters to compare the generated paper to the original.
```

The autoraters skill ships the four metrics from App. F.3:

- **Citation F1** (P0 must-cite, P1 good-to-cite) — checks the generated
  bibliography against the ground truth.
- **Literature Review Quality** (6-axis 0-100) — scores Intro + Related Work.
- **SxS Overall Paper Quality** — full-paper side-by-side comparison.
- **SxS Literature Review Quality** — Intro+Related Work side-by-side.
