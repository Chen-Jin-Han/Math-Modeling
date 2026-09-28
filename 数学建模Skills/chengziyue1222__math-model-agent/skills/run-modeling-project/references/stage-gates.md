# Modeling Project Stage Gates

Stages are strictly ordered. All evidence paths are project-relative. Competition requires existing checked artifacts; audit additionally records and revalidates SHA-256 for every accepted artifact.

| Enter stage | Required evidence roles | Exit question |
|---|---|---|
| `intake` | none | Has the project been initialized? |
| `analysis` | `problem_source`, `task_decomposition` | Is every subproblem, objective, constraint, datum, unit, and ambiguity explicit? |
| `modeling` | `data_audit`, `model_selection`, `decision_contract` | Is there a leakage-safe data contract, a fair baseline, and a justified model route for every question? |
| `validation` | `implementation`, `machine_results`, `quality_validation`, `run_manifest` | Can the solver be rerun with recorded parameters and seeds, and are balance, uncertainty, baseline, and trade-off checks appropriate to the declared decisions? |
| `writing` | Competition: `validation_report`, `quality_validation`, `paper_spec`, `evidence_index`, `figure_registry`. Audit adds `claim_registry`, `table_registry`, `formula_registry`. | Is the project `READY_FOR_DRAFT`, and does each question have a decision-grade result and validation artifact? |
| `review` | Competition: `manuscript`, PDF or DOCX (PDF default), its render report, `decision_contract`, `quality_validation`, `figure_inventory`, `cumcm_layout_validation`, `visual_layout_audit`, `paper_review_report`, `submission_preflight`, `submission_readiness`, support archive/manifest/reproduction report, `run_manifest`. Audit adds both rendered formats, `independent_content_review`, `review_hash_binding`, producer registry and signed Skill trace. | Did format, pagination, size, anonymity, support-manifest and clean reproduction checks pass, with the profile-specific review evidence present? |
| `release` | `review_report`, `submission_checklist`, `run_manifest` | Is the project `FORMAL_PAPER_APPROVED`, with no review failure or stale evidence? |

## Transition Rules

- Advance exactly one stage at a time.
- In competition, require every accepted evidence file to remain present; in audit, hash it on entry and re-hash all earlier evidence with `project_state.py verify` before every transition.
- Apply the profile's Skill role contract before execution. Rapid has no complete role-contract obligation; audit retains the complete contract. A required preflight failure is recorded as `BLOCKED`.
- Never reuse a stale `run_manifest` record after changing an input or artifact; audit proves this with full hashes.
- A failed or partial run remains in the manifest and is not silently replaced by a later success.
- A blocker freezes transitions but does not erase completed-stage history.
- Paper status is one of `NOT_READY`, `READY_FOR_DRAFT`, `DRAFT_GENERATED`, `REVIEW_FAILED`, `RETURNED_TO_MODELING`, or `FORMAL_PAPER_APPROVED`. A failed review must return to modeling/validation or writing; it cannot advance to release.
- Gate completion means evidence exists and is internally consistent; it does not guarantee a prize or publication outcome.

## Recommended Artifact Paths

Use stable names where practical:

```text
docs/problem-source.md
docs/task-decomposition.md
reports/data-audit.json
docs/model-selection.md
reports/decision-contract.json
src/solve.py
results/results.json
run-manifest.json
reports/validation.json
reports/quality-validation.json
reports/sensitivity.json
paper/main.tex
figures/figure-inventory.json
reports/review.md
reports/submission-checklist.md
```
