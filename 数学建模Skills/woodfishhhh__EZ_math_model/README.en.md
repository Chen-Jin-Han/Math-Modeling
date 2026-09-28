# EZ Math Model

[中文说明](README.md) | [Skill Star Map](STAR_MAP.md) | [SkillsMP entry](https://skillsmp.com)

EZ Math Model is a publish-ready Agent Skill for mathematical modeling contests. It turns a problem statement and attachments into a complete modeling workflow: setup authorization, intake, model selection, Python solving, figures, paper writing, quality audit, and standardized packaging.

It is designed for CUMCM, MCM, ICM, graduate mathematical modeling contests, and course projects that look like contest-style modeling tasks.

## What It Does

- Parses PDF, DOCX, Markdown, CSV, XLSX, and mixed attachments.
- Creates the standard project layout: `用户输入/`, `runtime/`, and `output/`.
- Enforces the first-run setup gate; permanent tool decisions are written only after user confirmation.
- Explicitly separates `formal`, `demo`, and `blocked` runs, so missing required data cannot silently become synthetic formal results.
- Detects contest signals such as contest, year, problem number, subtasks, data files, and output language.
- Chooses models from a built-in algorithm library covering optimization, prediction, evaluation, graph theory, statistics, comprehensive modeling, and machine learning.
- Writes and runs Python scripts, exports result tables, and generates figures.
- Writes chart manifest v2 and filters all-zero, all-equal, flat, compressed, unreadable, or language-inconsistent figures.
- Drafts a modeling paper in Chinese or English from structured templates and extracts style rules from exemplar papers before formal writing.
- Uses a built-in PaperOrchestra writing orchestration sub-skill for outline, literature, section drafting, and refinement discipline.
- Runs executable quality gates for figure-text binding, formulas, tables, template residue, and pipeline artifact leakage.
- Audits exported DOCX/PDF objects, including embedded images, Word formulas, Word tables, and PDF fallback status.
- Publishes through a staging directory so `output/`, `manifest.json`, and `output.zip` stay consistent.
- Produces `output/paper/paper.md`, `paper.docx`, `paper.txt`, `paper.pdf`, and packages the whole project folder as `output.zip`.

## SkillsMP-Ready Layout

```text
EZ_math_model/
├── README.md                # Chinese primary README
├── README.en.md             # English README
├── STAR_MAP.md              # visual capability map
├── package.json             # marketplace/package metadata
├── marketplace.json         # SkillsMP-facing metadata
├── manifest.json            # internal resource index
├── VERSION
└── skills/
    └── ez-math-model/
        ├── SKILL.md         # main skill entry
        ├── pipeline/        # seven workflow stages
        ├── prompts/         # coordinator/modeler/coder/writer prompts
        ├── references/      # algorithms, role guides, fault tolerance
        ├── templates/       # paper and workdir templates
        ├── tools/           # sub-skills, each with SKILL.md
        ├── scripts/         # install/runtime helpers
        └── external/        # runtime-only external references and user corpus
```

## Install

Codex:

```powershell
gh skill install woodfishhhh/EZ_math_model skills/ez-math-model --agent codex --scope user
```

Claude Code:

```bash
gh skill install woodfishhhh/EZ_math_model skills/ez-math-model --agent claude-code --scope user
```

If an older local copy already exists, overwrite it with `--force`:

```powershell
gh skill install woodfishhhh/EZ_math_model skills/ez-math-model --agent codex --scope user --force
```

Then ask:

```text
Use ez-math-model to solve this mathematical modeling problem.
```

Attach the problem statement and data files in the same turn.

## Standard Usage

1. Create a project root folder.
2. Put the problem statement, requirements, notes, and data attachments into `用户输入/`.
3. Open Codex / Claude Code in the project root and invoke ez-math-model.
4. Complete setup on the first run. If temporary defaults are used, the final status is provisional.
5. After the run, inspect `output/`; the deliverable is `output.zip` at the project root.

Standard runtime layout:

```text
ProjectRoot/
├── 用户输入/
├── runtime/
└── output/
    ├── source code/
    ├── paper/
    │   ├── paper.md
    │   ├── paper.docx
    │   ├── paper.txt
    │   └── paper.pdf
    └── 附件文件夹/
```

## Core Pipeline

Paths in this section are relative to `skills/ez-math-model/`.

| Stage | File | Output |
|---|---|---|
| 00 Setup + Environment | `pipeline/00-environment-setup.md` | setup status, `runtime/`, standard directories |
| 01 Intake | `pipeline/01-problem-intake.md` | `problem.md`, `intake.json`, `run_state.json`, attachments preview |
| 02 Modeling | `pipeline/02-modeling-plan.md` | `modeling_plan.md` |
| 03 Solving | `pipeline/03-coding-solve.md` | `src/*.py`, `results/*`, `figures/*.png`, `chart_manifest.json` |
| 04 Writing | `pipeline/04-paper-writing.md` | `paper.md` |
| 05 Quality | `pipeline/05-quality-audit.md` | `quality_report.md` |
| 06 Packaging | `pipeline/06-packaging-output.md` | four paper formats, `output/manifest.json`, `output.zip` |

## Built-In Sub-Skills

Paths in this section are relative to `skills/ez-math-model/`.

| Area | Entry |
|---|---|
| PDF and OCR fallback | `tools/pdf/SKILL.md`, `tools/mineru/SKILL.md` |
| Word and spreadsheets | `tools/docx/SKILL.md`, `tools/xlsx/SKILL.md` |
| Literature and web context | `tools/paper_search/SKILL.md`, `tools/scholar/SKILL.md`, `tools/webcrawl/SKILL.md` |
| Dataset discovery | `tools/dataset/SKILL.md` |
| User corpus indexing | `tools/user-corpus-explorer/SKILL.md` |
| Paper writing orchestration | `tools/paper-orchestra/SKILL.md` |
| Workflow support | `tools/brainstorming/SKILL.md`, `tools/systematic-debugging/SKILL.md`, `tools/verification-before-completion/SKILL.md` |
| Optional polish | `tools/humanizer/SKILL.md`, `tools/simplify/SKILL.md`, `tools/scientific-slides/SKILL.md` |
| Agent orchestration | `tools/dispatching-parallel-agents/SKILL.md`, `tools/subagent-driven-development/SKILL.md`, `tools/external-context/SKILL.md` |

See [STAR_MAP.md](STAR_MAP.md) for the full capability constellation.

## Runtime Policy

The repository does not vendor upstream contest papers or user files. Tool decisions and optional reference resources are placed under `skills/ez-math-model/external/` and ignored by git:

- `skills/ez-math-model/external/zhanwen-mathmodel/` for optional upstream exemplar papers.
- `skills/ez-math-model/external/paper-orchestra/` for the vendored PaperOrchestra writing skill pack.
- `skills/ez-math-model/external/user-corpus/` for user-provided references.
- `skills/ez-math-model/external/tools/` for local tool decisions.

Secrets use `EZMM_` environment variables and should live outside the repository.

User project runtime files are written to the project root `runtime/` and `output/`, not to the skill installation directory.

## License

MIT. See [LICENSE](LICENSE).

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=woodfishhhh/EZ_math_model&type=Date)](https://www.star-history.com/#woodfishhhh/EZ_math_model&Date)
