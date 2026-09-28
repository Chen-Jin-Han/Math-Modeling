# Project Handoff Schema

Every pause, stage transition, or final delivery should communicate the same compact contract.

```yaml
project_id: stable-project-id
current_stage: validation
status: active | blocked | complete
completed_stages: [intake, analysis, modeling]
run_manifest: run-manifest.json
verified_evidence:
  - role: machine_results
    path: results/results.json
    sha256: 64-lowercase-hex-characters
decision_summary:
  model: selected model and version
  baseline: comparison method
  metric: primary metric and split
decision_contract: reports/decision-contract.json
quality_validation: reports/quality-validation.json
failed_runs:
  - run_id: stable-run-id
    reason: concise factual cause
blocker: null
limitations: []
next_action: one concrete action
next_gate_requires: [validation_report, sensitivity_report]
```

## Rules

- Generate state fields from the project state file; do not rewrite history from memory.
- Take model, metric, seed, failure, and artifact details from the verified run manifest.
- Use `null` for no active blocker. Do not omit prior blocker history from the state file.
- Keep `next_action` executable and smaller than a full stage.
- A handoff may say `blocked` or `partial`; it must not inflate readiness.
