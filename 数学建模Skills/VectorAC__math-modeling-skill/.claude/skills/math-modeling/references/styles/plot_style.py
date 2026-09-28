# -*- coding: utf-8 -*-
"""国赛图表全局风格模板（matplotlib）。

用法：每个出图脚本开头 `import sys; sys.path.insert(0, '<项目内 styles 路径>'); from plot_style import apply_style`
或直接 `apply_style()` 后按需求画图。MATLAB 出图时按本文件标注的配色/字号手动落地。

覆盖点（用户历史痛点）：默认蓝橙配色丑、中文豆腐块、字号过小、线宽太细、图例遮挡。
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 中文必须设置，否则豆腐块（xelatex 编译的是系统字体；SimHei/SimSun 在多数 Windows 上可用）
FONT_NOTE = "中文字体须存在；Linux 用 'Noto Sans CJK SC'；修改后重跑"

COLORS = {
    "primary":   "#1f4e79",   # 深蓝 主线/主柱
    "secondary": "#ed7d31",   # 橙   对比线/副柱
    "accent":    "#70ad47",   # 绿   第三序列/标注
    "gray":      "#7f7f7f",   # 灰   基准线/背景
}

def apply_style(font="SimHei", figsize=(6.4, 3.2), dpi=300, fontsize=11):
    plt.rcParams.update({
        # 中文与负号
        "font.sans-serif": [font, "SimSun", "Noto Sans CJK SC", "DejaVu Sans"],
        "axes.unicode_minus": False,
        # 尺寸与精度（A4 打印：图宽 ≤0.8 版心，300 dpi）
        "figure.figsize": figsize,
        "figure.dpi": dpi,
        "savefig.dpi": dpi,
        "font.size": fontsize,
        "axes.labelsize": fontsize,
        "axes.titlesize": fontsize + 1,
        "xtick.labelsize": fontsize - 1,
        "ytick.labelsize": fontsize - 1,
        "legend.fontsize": fontsize - 1,
        # 线宽与边框
        "lines.linewidth": 2.0,
        "axes.linewidth": 1.2,
        "grid.linewidth": 0.8,
        "grid.alpha": 0.3,
        # 图例/网格默认
        "legend.framealpha": 0.9,
        "axes.grid": False,
        # 配色循环（色盲友好：蓝-橙-绿-紫-棕，避免红绿并列）
        "axes.prop_cycle": matplotlib.cycler(color=[
            COLORS["primary"], COLORS["secondary"], COLORS["accent"],
            "#7030a0", "#a0522d"]),
        # 边框去顶右（学术风格）
        "axes.spines.top": False,
        "axes.spines.right": False,
    })
    return plt

if __name__ == "__main__":
    # 冒烟自检：生成一张示例图，确认中文字体/循环配色/无边线生效
    p = apply_style()
    fig, ax = p.subplots()
    ax.plot([0, 1, 2], [1, 3, 2], label="方案 A")
    ax.plot([0, 1, 2], [2, 2, 4], label="方案 B")
    ax.set_xlabel("参数 α")
    ax.set_ylabel("目标值")
    ax.set_title("示例（图注不入图，此处仅为渲染自检）")
    ax.legend()
    fig.savefig("_style_check.png", bbox_inches="tight")
    print("风格自检图已生成：_style_check.png（请视觉确认无豆腐块后删除）")
