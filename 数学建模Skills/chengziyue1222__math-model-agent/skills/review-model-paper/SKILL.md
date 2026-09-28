---
name: review-model-paper
description: Audit mathematical-modeling papers for reasoning, evidence, figures/tables, citations and final layout. Use when Codex needs a pre-submission review, revision plan, claim verification, or LaTeX/Typst/Markdown inspection.
---

# Review Model Paper

Review in read-only mode unless revision is explicitly requested. First judge the reader-visible paper, then run backend consistency checks.

## Workflow

1. Collect the problem, manuscript, selected paper delivery (PDF by default; PDF or DOCX for competition, both for audit), result files, figures/tables, validation material, citations, support archive/manifest and contest template.
2. Read `references/paper-quality-review.md` and `references/review-rubric.md`. For CUMCM 2026, also read `references/cumcm-2026-preflight.md` and label each finding as official compliance or quality advice.
3. Check abstract, problem analysis, unified-core decision, formula explanation, per-question model/solution/result coverage, result reasoning and limitation disclosure.
4. Check that figures and tables have different evidentiary roles, are readable on A4 pages, and receive useful surrounding prose.
5. Check citations for relevance and verifiability. Require the appendix to list every support-package file and contain every complete self-authored runnable source file; third-party libraries belong in a versioned dependency list with installation instructions, not as copied source or binaries.
6. Render and inspect layout: the abstract is electronic page 1; the restatement follows with continuous numbering; no contents or blank contents page exists; references and appendices begin cleanly; the body excluding the abstract page contains no more than 30 pages before the appendix. Treat typography and heading alignment as local quality defaults unless the venue explicitly mandates them.
7. Keep ordinary review read-only. For a final anonymity preflight, use a user-supplied private identity dictionary outside the support tree or explicit `--identity-term` values when available. Do not create or populate an identity file during review. If no private dictionary is supplied, still run generic identity-label, path, filename and metadata checks and report the personalized term scan as not run rather than failing the whole review.
8. Run structural, value-consistency, 20-MiB, anonymity/path and PDF/DOCX metadata checks. Verify the support manifest exactly matches ZIP/RAR entries and rerun it from a clean extracted temporary directory. For CUMCM 2026, require the AI declaration before references and, when AI was used, the exact support file `AI工具使用详情.pdf`. Reconcile disclosure against records rather than guessing from writing style. RAR review requires `rarfile` plus a detected extraction backend and records that backend in the report. Any missing local import/data/config/font/plot dependency, confirmed identity leak or absolute user path blocks readiness.
9. Report findings by severity with direct evidence, impact and the smallest repair. A PASS means the visible paper and its evidence both meet the declared standard, not that it will win a contest.

## Guardrails

- Do not claim a citation or numerical result is verified without checking its source.
- Do not use a fixed count of equations, figures or references as a proxy for quality.
- Do not use an AI-text detector or prose style as proof of AI use, and do not tune validation repeatedly until a holdout threshold passes.
- Do not edit, publish or submit the paper without authorization.

## Resources

- `references/paper-quality-review.md` — reader-visible quality checklist.
- `references/review-rubric.md` — modeling quality rubric.
- `references/cumcm-2026-preflight.md` — official 2026 compliance and AI-disclosure checks.

## Executable Contract

For repository-managed work, select the contract explicitly with `python <skill-directory>/scripts/_runtime/skill_contracts.py --skill review-model-paper --profile competition` (or `audit`). Competition requires the paper/support preflight and permits a PDF-only delivery; audit additionally requires independent content review, HMAC-signed traces, complete hashes/registries, review hash binding and both PDF/DOCX. In `rapid`, provide a labelled peer-style critique; do not issue a submission-ready or formally verified verdict.
