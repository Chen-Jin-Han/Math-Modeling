# Math Modeling Skill（数学建模技能）

一个 Claude Code skill，用于辅助数学建模竞赛全流程，同时支持国赛（CUMCM）和美赛（MCM/ICM）。

**定位：教学辅助**——不代选模型、不代用户拍板；每阶段由独立子 agent 执行、经质量门审阅（生成→审阅→修改→再审），关键决策处设交互门；文献宁少勿假；内置四空间（打磨/解释/教学/组装）随口令切换。

## 安装

```bash
cd your-project
# 将 skill 复制到项目目录
cp -r .claude/skills/math-modeling .claude/skills/
```

或直接 clone 本仓库后，在 Claude Code 中使用 `/math-modeling` 触发。

## 依赖

本 skill 运行时需要以下技能/插件：

### 核心依赖（必须）
- `subagent-driven-development` — 派生子 agent 执行各阶段
- `dispatching-parallel-agents` — 并行任务调度
- `verification-before-completion` — 质量门控

### 推荐依赖
- `code-quality` plugin — 代码审查模板
- `requesting-code-review` — 论文审查
- `systematic-debugging` — 代码调试

在项目目录下用以下命令安装：
```bash
claude plugin install <name>@<source> --scope project
```

## 使用方法

1. 在 Claude Code 中输入 `/math-modeling`，或直接给出数学建模题目
2. 确认项目目录与模式后，AI 分阶段推进：初始化（模式/技术栈/依赖确认）→ 题目信息抽取（视觉识读为主，产出题目信息卡）→ 问题分析 → 模型设计（≥2 方案对比，用户选型）→ 建模实现（冒烟先行/长任务拆片/每图一脚本）→ 论文写作（阅读门禁 + 理论/结果二分）→ 最终验证（机械脚本门禁 + AI 合规检查）；收尾可选「模拟评委评审」（美赛 AE/MR/PS/RBA 四维打分，只读报告）
3. 除比赛流程外，可用四空间口令切换模式：
   -「进入打磨」——只建议不改动论文
   -「讲解一下」——解释空间，大白话答疑
   -「进入教学」——多轮交互式方法论教学（不代做）
   -「进入组装」——多人协作收尾拼接（内容冻结，只拼结构）
4. 比赛类型（国赛/美赛）自动检测，切换评阅标准与格式规范

## 比赛支持

- **国赛（CUMCM）** — 全国大学生数学建模竞赛
- **美赛（MCM/ICM）** — 美国大学生数学建模竞赛

自动检测比赛类型并切换评阅标准和格式规范。

## 文件结构

```
.claude/skills/math-modeling/
  SKILL.md                              # 薄总纲：定位/阶段地图/红线
  references/
    agent-prompts/                      # 子 agent 提示模板（每阶段一个角色）
      phase0-init.md                    #   初始化：模式/技术栈/依赖确认
      phase05-problem-info.md           #   题目信息抽取（视觉识读→题目信息卡）
      phase1-analysis.md                #   问题分析（四步叙事/硬约束/假设三件套）
      phase2-model-design.md            #   模型设计（2-3 方案对比/创新点二分类）
      phase3-implementation.md          #   建模实现（冒烟/拆片/每图一脚本）
      phase4-paper-writing.md           #   论文写作（阅读门禁/理论结果二分/多人分发）
      phase5-final-verification.md      #   最终验证（机械门禁/三方核对/AI 合规）
      reviewer.md                       #   通用审阅者（对照质量门，只读不修复）
      judge-review.md                   #   模拟评委（美赛四维/国赛六维打分，只读报告）
    checklists/
      quality-gates.md                  # 各阶段质量门（含 2026 国赛 AI 合规核查）
      contest-format.md                 # 比赛格式检查
    scripts/                            # 机械门禁脚本
      preflight_check.py                #   LaTeX 预检（占位符/图片/公式上限…）
      citecheck.py                      #   引用机制统一
      combinecheck.py                   #   跨部件合并检查
      tricheck.py                       #   三方核对（checkpoint vs 论文 vs 结果）
      handback-check.py                 #   组装交回核对
      extract_input.py                  #   题目文件抽取（PDF/docx/xlsx→md）
    contest-diff.md                     # 国赛 vs 美赛差异对照
    model-selection-guide.md            # 题型判定 + 场景→算法→检验速查表
    2401445-paper-analysis.md           # 美赛 O 奖论文五维度分析（写作必读）
    cumcm-template/                     # 国赛 LaTeX 底稿（cumcm2025_template.tex + cumcmthesis.cls）
    assembly/                           # 多人协作部件骨架模板
    polishing-space.md                  # 打磨空间（只建议不改动）
    explanation-space.md                # 解释空间（从容答疑）
    teaching-space.md                   # 教学空间（多轮交互教学，不代做）
    assembly-space.md                   # 组装空间（多人收尾拼接）
```

## 扩展

本 skill 的论文写作核心层可扩展用于：
- 课程论文 / 实验报告
- 文献综述
- 其他学术写作

## License

MIT
