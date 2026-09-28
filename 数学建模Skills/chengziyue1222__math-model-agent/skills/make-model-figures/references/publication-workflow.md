# 数学建模图表交付工作流

出版规格是交付约束，不是本 Skill 的目标。目标是让数据、模型、验证和决策结论形成可追溯的证据链。

## 图表契约

绘图前记录以下信息：

- 核心结论：读者看完图后应相信什么。
- 建模角色：数据概览、假设检查、结果、诊断、比较、灵敏度、稳健性、优化或决策。
- 证据链：哪些变量、面板、统计量或比较支持结论。
- 交付约束：目标赛事或期刊、单栏/双栏、文件格式和分辨率。
- 可追溯性：源数据或结果文件路径、样本量定义、统计量、不确定性。
- 审稿风险：外推、样本不平衡、缺失值、异常点、尺度或多重比较等。
- 设计简报：画布比例、布局配方、英雄面板、支持顺序和颜色角色；单面板可省略。
- 图形变换：过滤、聚合、归一化、平滑、截轴、对数变换和未展示数据。

使用 `FigureContract` 将契约和最终文件一起保存。若图仅用于探索，可以先缩短契约；进入论文或提交阶段时必须补齐。

## Matplotlib 基线

```python
import matplotlib as mpl
import matplotlib.pyplot as plt

from algorithms import (
    FigureContract,
    FigureDesignBrief,
    get_modeling_palette,
    export_publication_figure,
    publication_rc_params,
    publication_size,
)

palette = get_modeling_palette("nature-accessible")

brief = FigureDesignBrief(
    core_message="方案 A 在统一测试集上误差更低，且优势在重采样中稳定",
    canvas_ratio="3:2",
    layout_recipe="hero-plus-proof",
    hero_panel="(a) 测试集误差与区间",
    support_sequence=("(b) 残差分布", "(c) 稳健性复核"),
    color_roles=("基线=灰", "方案A=蓝", "强调=朱红阈值", "背景=浅灰"),
)

contract = FigureContract(
    claim="方案 A 在测试集上误差更低",
    evidence=("测试集 MAE", "95% bootstrap CI"),
    source_paths=("results/model_metrics.csv",),
    target_venue="数学建模竞赛论文",
    column="single",
    figure_role="model-comparison",
    model_name="XGBoost v3 vs baseline linear model",
    scenario="统一测试集基准情景",
    parameter_source="results/best_params.json",
    randomness="random_seed = 42；数据划分种子 = 42",
    n_definition="n = 200 个独立测试样本",
    statistic="MAE",
    uncertainty="10,000 次 bootstrap 的 95% CI",
    panel_evidence=("(a) MAE 与 95% CI", "(b) 残差分布", "(c) 重采样胜率"),
    data_transformations=("按统一测试集筛选；未改变原始误差",),
    theme_name="nature-accessible",
    design_brief=brief,
)

with mpl.rc_context(publication_rc_params(language="zh")):
    fig, ax = plt.subplots(
        figsize=publication_size("single", 65), constrained_layout=True
    )
    ax.plot(x, y, color=palette["categorical"][0])
    ax.set(xlabel="时间 (d)", ylabel="误差")
    export_publication_figure(fig, "figures/model_error", contract)
```

不要使用 `bbox_inches="tight"` 补救版面，因为它会改变精确栏宽。应调整边距、标签或布局本身。

## 四轮审查

1. 反模式：拒绝装饰性 3D、彩虹色图、双轴误导、未说明的截轴和只展示均值。
2. 代码与导出：检查 89/183 mm 宽度、字号下限、字体嵌入、矢量主稿和 450 dpi 校样。
3. 模型与数据：核对模型版本、参数来源、约束、基准情景、源文件、过滤规则、样本量、误差线、检验和随机种子；图中最优解与指标必须匹配保存结果。
4. 成图检查：实际打开 PNG 与至少一种矢量主稿，检查裁切、重叠、图例遮挡、中文缺字、灰度辨识、设计简报一致性和缩小后的可读性。

自动审查只能拦截可机器判定的问题，不能代替对结论、统计口径和视觉层次的人工判断。

## 设计来源

本工作流吸收并重新实现了 [Starry-cz/academic-data-visualization](https://github.com/Starry-cz/academic-data-visualization) 的图表契约、出版尺寸、无障碍配色、多面板设计和多阶段 QA 思路。原项目采用 Apache License 2.0；本仓库未复制其生产图形素材或脚本实现。
