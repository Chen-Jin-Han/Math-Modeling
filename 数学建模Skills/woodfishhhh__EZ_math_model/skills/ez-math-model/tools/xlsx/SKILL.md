---
name: xlsx
description: Use when EZ_math_model needs to read, preview, clean, write, or summarize CSV, XLS, or XLSX attachments and result tables for modeling tasks.
---

# xlsx — 表格数据读写

## 何时使用

- 读取 `.xlsx`、`.xls`、`.csv` 附件。
- 写出 `results/qN_summary.csv` 或 `.xlsx`。
- 生成 `intake.json.attachments[i].preview`。
- 大 CSV 需要分块处理。

## 预览契约

输出到 intake preview：

```json
{
  "shape": [1024, 8],
  "columns": ["timestamp", "value"],
  "head_3": [{"timestamp": "2024-01-01", "value": 12.3}],
  "missing_per_col": {"value": 5}
}
```

## 优先链路

1. `pandas` 读写和清洗。
2. `openpyxl` 写公式或保留 Excel 格式。
3. 宿主 `xlsx` skill 处理公式刷新、LibreOffice 重算等高级场景。

## pandas 模板

```python
import pandas as pd

df = pd.read_excel("attachments/data.xlsx")
preview = {
    "shape": list(df.shape),
    "columns": df.columns.tolist(),
    "head_3": df.head(3).to_dict("records"),
    "missing_per_col": {c: int(n) for c, n in df.isna().sum().items() if n > 0},
}
df.to_csv("results/q1_summary.csv", index=False, encoding="utf-8")
```

CSV 编码尝试顺序：`utf-8` → `gbk` → `gb2312` → `latin-1`。

## 大文件协议

- `pd.read_csv(path, chunksize=200_000)`。
- 提前指定 `dtype`。
- 必要时抽样 5% 做 EDA。
- 处理完及时释放分块 DataFrame。

## 失败诊断

| 情况 | 处理 |
|---|---|
| 编码全失败 | 写诊断，建议用户提供 utf-8 版 |
| 列名含非法字符 | 生成 ASCII 安全别名并保留 `column_alias.json` |
| 文件超过 1GB | chunksize 分块处理 |
