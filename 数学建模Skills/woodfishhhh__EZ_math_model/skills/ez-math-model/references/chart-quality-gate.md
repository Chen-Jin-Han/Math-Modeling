# Chart Quality Gate

图表不是“有 PNG 就算完成”。每一次绘图尝试都必须经过数据有效性、视觉语义和
论文可读性检查，并生成 chart manifest。无信息图表比没有图更糟：单色块、平线、
被坐标轴压扁的轨迹、主体占满画面但不可解释的截图，都不得进入正式论文。

## chart manifest v2

每张图生成后，必须在 `runtime/{task_id}/figures/chart_manifest.json` 中登记。
manifest 可以是数组，或包含 `charts` 数组的对象。每个对象至少包含：

```json
{
  "schema_version": "2.0",
  "figure": "fig_q2_spill_movement.png",
  "status": "accepted",
  "chart_type": "line",
  "source": "results/q2_summary.csv",
  "source_hash": "sha256:...",
  "metric_columns": ["spill_area_km2"],
  "x_label": "时间 t / s",
  "y_label": "污染物覆盖面积 / km^2",
  "unit": "km^2",
  "caption_intent": "展示污染物扩散面积随时间的变化趋势",
  "width_px": 1800,
  "height_px": 1100,
  "dpi": 300,
  "figure_exists": true,
  "rows_before": 6,
  "rows_after_filter": 4,
  "filtered_zero_rows": 2,
  "all_zero": false,
  "all_equal": false,
  "near_flat": false,
  "axis_compressed": false,
  "dominant_single_color": false,
  "label_language": "zh",
  "synthetic": false,
  "usable_in_paper": true,
  "reason_code": "",
  "reason_detail": ""
}
```

`status` 只能取 `accepted`、`rejected`、`skipped`。被拒图可以不保存 PNG，但必须
登记 `status=rejected`、`reason_code` 和 `reason_detail`，便于质量审查复盘。

## 必须过滤

| 情况 | 处理 |
|---|---|
| 指标列全为 0 | 不画图，写诊断，改用文字说明 |
| 指标列全相等 | 不画柱状图，改用表格或文字说明 |
| 曲线近似水平且无统计解释 | `status=rejected`，改用表格或补充差异放大图 |
| 坐标范围使主体被压扁 | 调整局部视窗或分面；不能调整则 `status=rejected` |
| 图像主体占满画面但不可读 | `status=rejected`，必须重画 |
| 中文论文中图轴/图例为英文 | 重画为中文；无法重画则 formal 失败 |
| 缺少横轴、纵轴、单位或图例语义 | 图表不可入论文 |
| 任务行 `synthetic=true` 且 run_mode=formal | 阻塞，不能入论文 |
| 过滤后有效行 < 2 | 不画对比图，写诊断 |
| 缺少单位或指标名 | 图表不可入论文 |

## coder 约束

生成图前必须先构造待绘图数据，并写出：

```text
rows_before
rows_after_filter
filtered_zero_rows
all_zero
all_equal
near_flat
axis_compressed
usable_in_paper
```

writer 只能引用 `usable_in_paper=true` 的图。若图不可用，writer 应引用结果表或诊断，
不得为了凑图把无信息图写入正文。

所有 `figures/*.png` 必须 100% 有 manifest 记录；所有 `accepted` 图必须 100%
实际存在。manifest 中 `accepted` 图的 `figure_exists=false`、缺少 v2 必填字段、
或 `usable_in_paper=false` 与 `status=accepted` 冲突时，formal 质量门失败。

## quality audit 约束

质量门必须读取 `chart_manifest.json`，并把以下情况标为失败或警告：

- `paper.md` 引用了 `usable_in_paper=false` 的图；
- `figures/` 有图但未登记 manifest；
- chart manifest 显示全 0 / 全相等仍被画成柱状图；
- demo/synthetic 图被用于 formal 结论。
- `accepted` 图缺少 `chart_type`、`x_label`、`y_label`、`unit`、
  `caption_intent`、`source_hash` 等语义字段；
- `paper.md` 中图片路径不是 `figures/文件名.png`；
- 图前后缺少足够解释，或解释没有可追溯数值证据；
- 渲染后的 DOCX/PDF 中缺少对应嵌入图片。
