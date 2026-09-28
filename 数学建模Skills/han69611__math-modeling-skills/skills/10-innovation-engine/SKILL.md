---
name: "10-innovation-engine"
description: "创新方案生成+Innovation Score数字评分系统。对每个候选方案五维打分（创新性/可解释性/复杂度/严谨性/国赛契合度），加权排序自动推荐，用数字代替文字描述。"
---

# Skill: 10-innovation-engine — 创新方案生成 [v2.2 升级]

> 不是找Bug，而是主动优化。Reviewer找错，Innovation Engine做得更好。

## 核心理念

旧版本：文字描述每个方案的优缺点
新版本：对每个方案打分（0-100），自动加权排序，用数字说话

## 工作流程

### Step 1：5个核心问题
### Step 2：五维 Innovation Score 打分
### Step 3：打分输出格式
### Step 4：5条创新路径
### Step 5：确认

## 阶段边界

- 本阶段只生成候选方案和评分，不修改代码
- 用户确认后，由04-coding实现选定方案
- 评分结果记录到06-experiment-manager
