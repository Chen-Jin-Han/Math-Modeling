# 数模国赛 Claude Code Skills

一套面向**数学建模国赛（高教社杯 / CUMCM）**的 Claude Code skill 家族，覆盖 **A / B / C 三题型**的完整解题方法、代码模板与论文写作规范。基于 2025 年 C 题（NIPT 时点选择与胎儿异常判定）实战验证，支持**离线使用**——比赛期间断网也能配合推进。

> CUMCM = China Undergraduate Mathematical Contest in Modeling（高教社杯全国大学生数学建模竞赛）

## 包含的 skill

| Skill | 题型 | 内容 |
|---|---|---|
| [`cumcm-workflow`](cumcm-workflow/SKILL.md) | 通用 | 建模流程、论文八段式、时间规划、团队分工 |
| [`cumcm-a`](cumcm-a/SKILL.md) | A 题 | 物理/工程/微分方程/数值模拟 |
| [`cumcm-b`](cumcm-b/SKILL.md) | B 题 | 优化/运筹/规划（含完整 GA/SA/PSO 代码） |
| [`cumcm-c`](cumcm-c/SKILL.md) | C 题 | 数据/统计/机器学习/评价（含 2025 NIPT 案例） |

## 安装

1. 确保已安装 [Claude Code](https://claude.com/claude-code)
2. 把四个 `cumcm-*` 文件夹复制到用户级 skills 目录：
   - Windows：`C:\Users\<用户名>\.claude\skills\`
   - macOS / Linux：`~/.claude/skills/`
3. 重启 Claude Code 或新开会话

最终路径形如 `~/.claude/skills/cumcm-b/SKILL.md`。

### 命令行一键安装

```bash
# Linux / macOS
mkdir -p ~/.claude/skills
for d in cumcm-workflow cumcm-a cumcm-b cumcm-c; do
  cp -r "$d" ~/.claude/skills/
done
```

```powershell
# Windows (PowerShell)
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse cumcm-workflow, cumcm-a, cumcm-b, cumcm-c "$env:USERPROFILE\.claude\skills"
```

## 使用

在 Claude Code 对话中直接提到「数模国赛 / CUMCM」或具体题型，对应 skill 会自动触发；也可用 `/` 手动选择。

- 比赛开始 → 触发 `cumcm-workflow`（选题、审题、论文框架）
- 确定题型 → 触发 `cumcm-a/b/c` 选模型、写代码
- 写论文 → 回到 `cumcm-workflow`（摘要、假设、符号、敏感性分析）

## 特点

- **离线自足**：numpy / scipy / pandas / sklearn / statsmodels 覆盖 95% 需求，比赛断网也能推进
- **实战验证**：2025 年 C 题（NIPT 时点选择与胎儿异常判定）完整案例已沉淀进 `cumcm-c`
- **可迭代**：每次实战后把新踩的坑、新方法回写进对应 skill，越用越强

## 核心心法

1. 先选题审题、问题分解，再建模，最后才写代码
2. 契合度 > 严谨性 > 可读性 > 算法新颖度（不堆砌算法，讲清"为什么用它"）
3. 敏感性分析 + 模型检验是拉开差距的关键
4. 摘要写数字结论 + 模型名，是评阅第一关

## 借鉴与致谢

本 skill 家族的「模型选择方法论（先识别输出再识别算法 / 六维结构诊断 / 三方案 A-B-C / 硬筛选条件）」「验证与稳健性方法论（验证从主张开始 / 最低验证包 / 四类不确定性）」「子问题依赖图与误差传播」「创新点与证据阶梯」等**通用建模方法论思路**，部分借鉴自：

- [skillforCUMCM/math-modeling-skill-pro](https://github.com/skillforCUMCM/math-modeling-skill-pro)

**借鉴范围**：仅借鉴其**通用建模方法论的框架思想**（属于方法/流程层面），已按本家族风格用自己的表述重写，**未复制其原文、案例卡、代码或第三方论文内容**。各 `SKILL.md` 相应小节已就地标注出处。

> 说明：该项目采用专有许可（All rights reserved），其案例卡基于国赛公开论文页结构化整理，相关权利归原作者/组委会。本仓库不包含、不转载其任何受保护文本或第三方材料，仅致谢其方法论的启发。详见 [THIRD-PARTY-NOTICE.md](THIRD-PARTY-NOTICE.md)。

## 说明

- 四个 skill 互相引用，请**一起安装**（单独安装会断链）
- `dataviz` 为 Claude Code 内置 skill，无需安装
