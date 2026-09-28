---
name: dataset
description: |
  公开数据集发现入口。覆盖 Kaggle / UCI / HuggingFace / 天池。题目要求"自行
  查找数据"或"补充外部数据"时启用；附件已含数据时**不调用**。
read_when:
  - 题目明确要求查找类似公开数据
  - 需要历史基准数据集做对比
---

# dataset — 公开数据集发现

## 何时使用

- 题目附件**没有**数据集，但题面要求"查找类似公开数据"。
- 需要历史基准数据集（如 MNIST / Iris / 波士顿房价）做模型对比。
- **不要**在已有附件数据时启用本子 skill。

## 入口

| 数据源 | 入口 | 配置 |
|---|---|---|
| Kaggle | `kaggle datasets list -s <kw>` / `kaggle datasets download -d <user/name>` | `~/.kaggle/kaggle.json`（注册免费下载） |
| UCI ML | 直接 HTTPS `pd.read_csv(url)` | 无 |
| HuggingFace | `from datasets import load_dataset` | `EZMM_HF_TOKEN`（私有数据集） |
| 天池 | 浏览器 + 手动下载 | 无 |

## 命令模板

```powershell
# Kaggle 搜索 + 下载
kaggle datasets list -s "vegetable retail price"
kaggle datasets download -d <user/dataset-name> -p workdir/.../attachments/external/kaggle --unzip

# HuggingFace
python -c "from datasets import load_dataset; ds = load_dataset('squad', split='train[:1%]')"

# UCI（直接 URL）
python -c "import pandas as pd; df = pd.read_csv('https://archive.ics.uci.edu/...'); df.to_csv('workdir/.../attachments/external/uci/iris.csv', index=False)"
```

## 落盘规范

外部下载的数据放在：

```
workdir/{task_id}/attachments/external/<source>/<dataset>/
```

并在同目录写 `SOURCES.md`：

```markdown
- 数据集名: <name>
- 来源: <kaggle url>
- License: <CC0 / CC-BY / Apache-2.0 / 其他>
- 下载时间: <ISO timestamp>
- 用途说明: <一句话>
```

## 失败诊断

| 情况 | 处理 |
|---|---|
| Kaggle token 未配置 | 提示用户 `~/.kaggle/kaggle.json` 配置 |
| License 不允许商用 | 数据可用于学术建模报告；论文中标明出处 + license |
| 文件 > 1GB | coder 阶段用 chunksize 处理（参考 `prompts/coder.md`） |
| 网络受限 | 写诊断；建议用户手动下载放入 attachments/ |
