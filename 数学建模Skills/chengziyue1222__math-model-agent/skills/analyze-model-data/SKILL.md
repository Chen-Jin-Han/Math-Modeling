---
name: analyze-model-data
description: Inspect, clean, analyze, and model tabular data for mathematical modeling tasks. Use when Codex needs exploratory analysis, missing-value or anomaly handling, feature engineering, statistical testing, regression or classification, train/test evaluation, or reproducible data artifacts.
---

# Analyze Model Data

Produce a reproducible evidence trail from raw data to model-ready outputs.

## Workflow

1. Preserve the raw files and identify schema, units, provenance, missingness, duplicates, sampling coverage, and target leakage risks. Decide whether the observed data can identify the requested quantity before filling gaps or fitting a model. A missing forecast column is not by itself proof that a forecasting task is impossible: distinguish an externally supplied forecast from a forecast that the problem expects the modeler to generate from prior observations.
2. Run `scripts/profile_csv.py` for CSV inputs, then inspect domain-specific anomalies manually.
3. Define the analysis question and evaluation metric before choosing transformations or models. For entity-by-time planning data, call `algorithms.data_diagnostics.panel_diagnostics` (or an equivalent registered implementation) to quantify temporal dependence, cross-entity correlation, support/zero inflation, and a time-ordered holdout before choosing an uncertainty model.
4. Split train/test data before fitting imputers, scalers, encoders, or feature selectors.
5. Compare against a simple baseline and report uncertainty, not only point metrics.
6. Save cleaned data, analysis code, configuration, figures, and a machine-readable result summary.
7. Document every exclusion, imputation, transformation, random seed, and the evidence for or against independent sampling. Preserve a time-aware holdout or stress slice when the task contains future planning; never replace it with a random split merely because the random split scores better.

## Guardrails

- Never overwrite raw data.
- Do not remove outliers solely because they weaken the result.
- Never present simulated, interpolated or assumed values as observations. Label their origin and keep them out of held-out evaluation unless the evaluation design explicitly permits them.
- Do not infer causality from association without an identification strategy.
- Use Python or R according to the project context; do not force one language.
- Unless the user explicitly requests another language, use Chinese for chart filenames, titles, axis labels, legends, annotations, and unit descriptions. Keep standard mathematical symbols and internationally recognized unit abbreviations where they improve precision.

## Resources

Read `references/analysis-standards.md` before modeling. Use `scripts/profile_csv.py` for deterministic first-pass profiling.

## Executable Contract

For repository-managed `competition` and `audit` work, use `scripts/execute_skill.py` with the bundled runtime. Supply the `raw_data`, `data_dictionary`, and `official_problem` inputs, and produce every contracted output role: `data_profile`, `data_quality_report`, `cleaning_actions`, `eda_findings`, `leakage_report`, `processed_data_manifest`, and `data_analysis`. The profile and EDA findings must include the applicable panel/time diagnostics, not only row counts and missingness. A missing runtime blocks only the executable-contract claim, not an otherwise valid read-only analysis; report the two statuses separately. In `audit`, do not register the artifact without a successful signed Skill run.
