---
name: solve-model
description: Formulate, implement, solve, and validate mathematical models with the repository algorithm library. Use when Codex needs to translate assumptions into equations, call or extend algorithms, optimize parameters, run simulations, or perform sensitivity and robustness analysis.
---

# Solve Model

Turn an agreed route into results that can be explained, checked and used in a competition paper.

## Workflow

1. Confirm each question's objective, variables, units, constraints, assumptions, output and upstream model-selection rationale.
2. Read `references/reasoning-and-validation.md` and the relevant part of `references/algorithm-api.md`.
3. Formulate the real relationship before choosing a solver. Use analytical derivation for conservation, geometry, feasible ranges, reduction, scale or monotonicity whenever available.
4. Implement a simple baseline before the complex route. Make data slicing, parameters, seed and units explicit; preserve failed runs and limitations. If a decision uses a model-generated forecast, create predictions with rolling origins using only observations available at each issue time, preserve the issued predictions, and estimate forecast-error or risk terms only from previously completed targets.
5. For a critical event, define the event function, locate a first bracket, refine it and save left/right states. For a search, establish its prerequisites before bisection or Brent.
6. Audit hard constraints independently. Compare with the declared baseline and, where risk warrants it, with an algorithm that does not share the same key implementation path.
7. Separate parameter sensitivity from numerical convergence. Explain whether a perturbation changes a decision threshold rather than merely reporting a changed digit. Predeclare final holdout or extrapolation checks and do not repeatedly tune against them.
8. Save structured results, source tables and validation evidence so figures and prose can be regenerated without copying numbers by hand.

## Writing Handoff

Give `write-model-paper` plain-language material for each question: the relation being modeled, formulas with variable definitions, solving logic, representative results, comparison, mechanism, evidence, applicable range and limitation. Backend status labels, hashes and logs remain outside the paper.

## Resources

- `references/algorithm-api.md` — repository APIs.
- `references/validation-checklist.md` — baseline checks.
- `references/reasoning-and-validation.md` — event, search and validation reasoning.

## Executable Contract

For repository-managed `competition` and `audit` projects, inspect the bundled contract with `python <skill-directory>/scripts/_runtime/skill_contracts.py --skill solve-model --profile competition` (or `audit`) and run this Skill through `scripts/execute_skill.py` with every contracted input and output role. In `rapid`, save the baseline, parameters or seed, result artifact, and limitation; do not represent an exploratory run as a validated decision.
