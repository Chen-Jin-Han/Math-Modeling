---
name: make-model-figures
description: Design, generate, improve, audit, and export evidence-centered figures for mathematical modeling analysis and competition papers. Use for data or model visualizations, multi-panel result figures, mechanism and workflow diagrams, sensitivity or robustness graphics, palette redesign, print-size QA, and reproducible vector/raster delivery; do not route ordinary data analysis here when no figure is requested.
---

# Make Model Figures

Build a visual argument, not a gallery of available variables. Every formal figure must support one modeling claim and remain truthful to the saved data, model, units, and uncertainty.

## Choose the operating mode

- **Create:** design a new figure from machine-readable data or saved model results.
- **Improve:** preserve the source data, statistical meaning, units, filtering, and conclusion while revising layout, chart type, typography, palette, or annotations. Record any changed scale, aggregation, normalization, or encoding.
- **Audit:** inspect the source and rendered output; report evidence or readability defects without silently redrawing it.
- **Explore:** make lightweight diagnostic plots. Do not represent them as submission-ready until the formal contract and export checks are completed.

Proceed directly when the user's goal and data mapping are clear. Ask only when a missing choice would change the scientific meaning, such as which columns represent the requested comparison.

## Required workflow

1. **State the visual claim.** Read `references/paper-figure-language.md` and write the one-sentence conclusion, figure role, evidence, source paths, units, sample definition, statistic, uncertainty, model/scenario, and review risks. Use `FigureContract` for a formal figure; use a shortened claim/evidence note for exploration or a cosmetic-only edit.
2. **Protect data integrity.** Use all relevant user-provided observations. Never silently select representative rows, replace real data with illustrative values, or drop inconvenient groups. For dense rendering, prefer rasterized marks, hexbin/density views, or transparent points; if aggregation, filtering, imputation, winsorization, or normalization changes what is shown, record it and keep the unmodified source.
3. **Route by information task.** Read `references/figure-standards.md`. When the chart type is unclear, specialized, or multi-panel, also read `references/design-and-routing.md`. Prefer the smallest set of non-redundant panels that proves the claim; avoid duplicate views of the same fact.
4. **Design before coding.** Fix the final physical width and approximate aspect ratio first. For two or more panels, create a `FigureDesignBrief`: core message, layout recipe, hero panel where appropriate, support sequence, and stable color roles. A hero panel should be larger only when its evidence is genuinely more important or denser.
5. **Assign semantic style.** For new figures or recoloring, read `references/palette-system.md`. Use one named palette or a user-supplied palette, bind colors to meanings before plotting, keep that mapping stable across panels and figures, and retain line/marker/label redundancy for critical distinctions. Do not change data or statistics during recoloring.
6. **Generate reproducibly.** Plot from saved data/results with `algorithms.sci_figures` or `algorithms.diagram` when available; otherwise use an equivalent local implementation and record it. Apply `publication_rc_params` or `paper_figure_rc_params`, exact `publication_size`, consistent `add_panel_label`, and `export_publication_figure`. Do not assume the project contains a `code/algorithms` checkout.
7. **Run the quality gate.** For a formal figure, read `references/publication-workflow.md` and `references/visual-qa-checklist.md`. Run the programmatic audit, export the vector master and 450 DPI proof, then actually open the proof at final paper size. Fix clipping, overlaps, missing glyphs, misleading scales, unstable color meanings, weak hierarchy, and illegible details before delivery.
8. **Close the evidence loop.** Introduce the figure in the manuscript, explain its pattern and modeling meaning after it, and state limitations. Confirm every plotted optimum, ranking, threshold, sample size, interval, and annotation against the saved result and surrounding tables/text.

## Visual language

Use a white background, near-black text, restrained semantic colors, one deliberate emphasis role, thin axes, and only necessary guide lines. Prefer direct labels over a legend when practical. Avoid rainbow/jet maps, decorative 3-D perspective, default dashboard palettes, unexplained dual axes, hidden truncation, and effects that compete with the evidence.

Unless the user requests another language, use Chinese for filenames, titles, axes, legends, annotations, captions, and unit descriptions. Preserve standard mathematical symbols and recognized unit abbreviations. Configure a Chinese-capable font stack and verify the rendered proof contains neither missing-glyph boxes nor broken minus signs.

## Deliverables

For a formal figure, return:

- reproducible plotting code and the machine-readable source/result path;
- editable PDF/SVG master plus 450 DPI RGB PNG proof;
- `.figure.json` containing the contract, design brief, palette, transformations, randomness, and audit;
- a concise QA note distinguishing passed checks, warnings, and any review risk still requiring judgment.

Do not claim submission readiness from source-code inspection alone. A rendered visual check is mandatory.

## Resources

- `references/paper-figure-language.md` — claim-to-figure grammar for modeling papers.
- `references/figure-standards.md` — chart and export invariants.
- `references/design-and-routing.md` — information-task routing and multi-panel composition; read when needed.
- `references/palette-system.md` — named themes and semantic color rules; read for creation or recoloring.
- `references/publication-workflow.md` — reproducible implementation and bundle export; read for formal figures.
- `references/visual-qa-checklist.md` — four-pass review; read for audit or final delivery.
- `scripts/preview_palettes.py` — render any built-in theme before choosing or personalizing colors.

## Executable contract

For repository-managed `competition` and `audit` projects, inspect the bundled contract with `python <skill-directory>/scripts/_runtime/skill_contracts.py --skill make-model-figures --profile competition` (or `audit`) and run this Skill through `scripts/execute_skill.py` with every contracted input and output role. In `rapid`, retain the plotted source data, claim, units, palette, transformations, and generation parameters; reserve the formal registry and full bundle audit for a stricter profile.
