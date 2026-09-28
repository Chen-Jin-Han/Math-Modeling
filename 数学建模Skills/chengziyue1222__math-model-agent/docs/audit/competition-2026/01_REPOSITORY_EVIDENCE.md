# 仓库证据与运行基线

## 审计范围与保护措施

- 目标仓库：`C:\Users\Blake\math-model`
- 审计时间：2026-07-25（Asia/Shanghai）。
- 业务代码未修改；本审计只新增 `docs/audit/competition-2026/`。
- 未执行 `reset`、`clean`、`checkout`、`restore`、`stash`、提交、推送或分支切换。
- 隔离复跑目录：`%TEMP%\math-model-audit-20260725-replay`；隔离虚拟环境：`%TEMP%\math-model-audit-20260725-venv`。它们不属于交付物。

## 初始 Git 与环境状态

| 项 | 实测值 | 证据 |
|---|---|---|
| 分支 | `codex/workflow-productionization` | `git branch --show-current` |
| HEAD | `673694b6341dccd2bdfa189e5312b040566e2bb2` | `git log -1` |
| 最近提交 | `refactor: archive legacy command library`，2026-07-18 | `git log -1 --format=...` |
| 标签 | HEAD 指向 `v6.6.0` | `git tag --points-at HEAD` |
| 初始 dirty | `?? examples/`；无已跟踪文件 diff | `git status --short`、`git diff --stat`、`git diff --name-status` |
| 默认 Python | `3.14.2` | `python --version` |
| 声明兼容版本 | `>=3.10`；CI 覆盖 3.10、3.11、3.12、3.13 | `pyproject.toml`、`.github/workflows/ci.yml` |
| 依赖管理 | `pyproject.toml` + `requirements.txt`，Setuptools build backend | `pyproject.toml` |

`examples/` 是用户已有、未跟踪的完整演示工程；审计未覆盖、移动或重写其中任何文件。完成审计写入报告后，工作区应新增审计目录，原有 `examples/` 仍保留。

## 目录职责图

| 位置 | 实测职责 | 关键入口/备注 |
|---|---|---|
| `code/algorithms/` | 可安装的算法库 | 17 个实现模块 + `__init__.py` 聚合公开 API |
| `code/tests/` | pytest 测试 | 27 个测试文件；完整运行收集 244 项 |
| `skills/` | 8 个标准 Codex Skills | 每个包含 `SKILL.md` 与 `agents/openai.yaml` |
| `skills/run-modeling-project/` | 工作流说明与状态机 | `scripts/project_state.py`，并非独立服务 |
| `scripts/` | Manifest、技能、benchmark、覆盖率校验 | `run_manifest.py`、`validate_skills.py` 等 |
| `schemas/` | Manifest JSON Schema | `run-manifest.schema.json` |
| `benchmarks/` | 12 题 CUMCM 元数据与量表 | 题面只外部链接，不含题目数据或可运行解法 |
| `legacy/` | 兼容归档 | 56 个旧命令文档和 `command-map.yaml` |
| `patterns/`、`template/` | 写作/排版资产 | 非运行时产品入口 |
| `examples/` | 三个未跟踪演示 | `demand_forecasting`、`supplier_allocation`、`queue_risk` |
| `.github/workflows/ci.yml` | CI 质量门 | 安装、技能/benchmark/legacy 校验、Ruff、覆盖率、构建 |

依赖关系可概括为：`examples/*/solve.py` → `algorithms` 与 `examples/_common.py` → `scripts/run_manifest.py`；`run-modeling-project/SKILL.md` 以文本指令调用其他 Skill，并用 `project_state.py` 记录阶段；没有 Web/UI 服务把这些组件整合为普通学生可直接使用的产品。

## 用户声明核验

| 声明 | 实测 | 状态 | 证据 |
|---|---:|---|---|
| 17 个算法模块 | `code/algorithms/` 中 17 个非 `__init__.py` 文件 | 一致 | `git ls-files code/algorithms/*.py` |
| 129 个公开导出 | `algorithms.__all__` 静态解析为 129 且无重复 | 一致 | `code/algorithms/__init__.py`；AST 审计 |
| 8 个标准 Skills | 8 个目录；`python scripts/validate_skills.py skills` 通过 | 一致 | `skills/`；命令输出 `Validated 8...` |
| 56 个 legacy 命令 | `python scripts/validate_legacy_archive.py` 通过 | 一致 | `legacy/command-map.yaml`；命令输出 `Validated 56...` |
| 2020--2023、12 题 benchmark | 12 个 case 元数据被校验 | 部分一致 | `benchmarks/catalog.yaml`；`validate_benchmarks.py`；无题面/数据/解法 |
| 65% 总覆盖率和五模块 80% 门槛 | 实测 65.50%；五模块均 91.25%--98.07% | 一致 | `%TEMP%/math-model-audit-20260725-coverage.json`；`coverage-policy.json` |
| 三个完整示例 | 三个源码均存在且隔离复跑成功；源目录仅前两例有结果和 Manifest | 部分一致 | `examples/`；见下文及 `02_TECHNICAL_AUDIT.md` |
| 可普通学生端到端使用 | 未发现 UI、Web 服务、CLI entry point 或角色流程 | 不一致 | `pyproject.toml`、`README.md`、`git grep`；仅 `python -m examples...` 开发入口 |

## 实际运行结果

| 命令 | 结果 |
|---|---|
| `python scripts/validate_skills.py skills` | 通过，8 Skills |
| `python scripts/validate_benchmarks.py` | 通过，12 benchmark case 元数据 |
| `python scripts/validate_legacy_archive.py` | 通过，56 legacy 文档 |
| `python -m pytest code/tests -q` | 244 passed，14.67 s（全局环境） |
| 隔离 venv：`ruff check code skills scripts` | 通过 |
| 隔离 venv：`pytest ... --cov=algorithms` | 244 passed，14.15 s；总覆盖率 65.50% |
| `scripts/check_coverage.py` | 通过；关键模块：98.07%、91.25%、96.55%、96.63%、95.02% |
| 隔离 venv：`python -m build --no-isolation` | 成功生成 sdist 与 wheel |
| 三例隔离复跑与 Manifest 验证 | 三例运行和新生成 Manifest 均通过；详情见技术审计 |

## 未验证事项

- 未在 Python 3.10--3.13 的本地环境复跑；CI 文件声明矩阵，但本次没有获取远端 Actions 结果。
- 未验证 benchmark 中每个官方 URL 当前可访问，也未验证其外部题面许可；仓库只校验 YAML 结构。
- 未验证第三方上游实现的许可证兼容性或逐行来源；仓库仅有名称级参考。
- 未验证真实校园数据、教师用户、学生用户或真实比赛规则原文；本报告只基于仓库和用户提供的评分约束。

