# Math Modeling Skills

数学建模竞赛全流程 Claude Skills 系统，适用于 CUMCM（国赛）/ MCM/ICM（美赛）/ 华为杯 / 华中杯等。

## Overview

37 个 Skills 覆盖从读题到提交的完整建模流程，包含两套工作流（v2.x 12阶段 + Legacy 5阶段）和 12 个专项 Skill。

## Architecture

```
00-system (总规则)
  └─ 01-start-mathmodel (工作流入口)
       ├─ 02-analysis-modeling → 03-hypothesis → 03-model-selection
       ├─ 04-coding / 04-coding-visual
       ├─ 05-result-analysis / 05-visualization
       ├─ 06-drawio / 06-experiment-manager
       ├─ 07-result-analysis / 07-writing
       ├─ 08-reviewer-mode
       ├─ 09-verify / 09-writing
       ├─ 10-innovation-engine
       ├─ 11-reviewer-mode
       └─ 12-verify
```

## Skills Index

### Core v2.x Workflow (19 skills)

| Stage | Skill | Description |
|-------|-------|-------------|
| Root | `00-system` | Agent总规则：角色、原则、数据真实性、审批节点 |
| Entry | `01-start-mathmodel` | 工作流入口v2.1，12阶段完整流程 |
| 02 | `02-analysis-modeling` | 赛题分析与建模设计v2.0 |
| 03 | `03-hypothesis` | 假设设计引擎，假设决定模型 |
| 03 | `03-model-selection` | 自动推荐决策树v2.2 |
| 04 | `04-coding` | 编程实现（纯代码） |
| 04 | `04-coding-visual` | 编程实现+图表生成v2.0 |
| 05 | `05-result-analysis` | 五层递进结果分析 |
| 05 | `05-visualization` | 论文级图表生成 |
| 06 | `06-drawio` | 非数据型图示绘制v2.0 |
| 06 | `06-experiment-manager` | 结构化实验记录管理 |
| 07 | `07-result-analysis` | 结果分析+Baseline对比+统计检验 |
| 07 | `07-writing` | 论文撰写v2.0（融合anti-ai+cumcm+图表审查） |
| 08 | `08-reviewer-mode` | 评委审稿模式（8维度） |
| 09 | `09-verify` | 最终验证v2.0（融合paper-score） |
| 09 | `09-writing` | 论文撰写v2.1（修复摘要范式） |
| 10 | `10-innovation-engine` | 创新方案生成v2.2+Innovation Score |
| 11 | `11-reviewer-mode` | 评委审稿v2.1（9维度+可读性） |
| 12 | `12-verify` | 最终验证v2.2（100分制+风险等级） |

### Legacy Workflow (6 skills)

| Skill | Description |
|-------|-------------|
| `1start-mathmodel` | 5阶段工作流入口 |
| `2analysis-modeling` | 赛题分析与建模设计 |
| `3coding-visual` | 编程实现与图表生成 |
| `4drawio` | 非数据型图示绘制 |
| `5writing` | 竞赛论文撰写（Typst/LaTeX） |
| `6verity` | 最终验证和验收 |

### Specialized Skills (12 skills)

| Skill | Description |
|-------|-------------|
| `anti-ai-writing` | 15条规则消除AI模板语言 |
| `challenge-yourself` | 六问自检法+防堆砌检查 |
| `cumcm-paper-writing` | 17条一等奖写作规范 |
| `domain-knowledge` | 9大领域建模知识库 |
| `innovation-engine` | 创新方案生成引擎（5条路径） |
| `latex-cjk-setup` | LaTeX中文排版配置 |
| `math-modeling` | 综合建模知识大全（决策树+代码+模板） |
| `model-selection` | 诊断决策树引擎（6类问题） |
| `paper-score` | 8维度100分自动评分系统 |
| `project-manager` | 项目目录自动管理器 |
| `reviewer-mode` | 独立评委审稿（8维度） |
| `visualization-review` | 12项图表质量审查 |

## Key Features

- **审批节点机制**: 每阶段完成后必须呈现产出，等待用户确认再继续
- **数据真实性红线**: 绝不编造数据，所有数值必须来自代码运行结果
- **拒绝模板化**: 每个模型选择必须有理由，禁止套模板
- **自动决策树**: Agent根据数据特征自动遍历决策树，输出推荐方案
- **Innovation Score**: 五维数字评分系统，自动排序候选方案
- **风险等级标注**: 每个维度同时给分数和风险等级，高风险项优先修复
- **领域知识自动加载**: 根据赛题特征自动加载对应领域知识

## Directory Convention

```
Project/
├── docs/          # 文档与报告
├── code/          # Python代码
├── data/          # 数据（raw/processed/external）
├── paper/         # 论文源文件
├── figures/       # 图表PDF
├── results/       # 运行结果JSON
├── experiments/   # 实验记录
├── reports/       # 阶段报告
└── references/    # 参考文献
```

## License

MIT
