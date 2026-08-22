# 2025年上半年校赛

本项目研究“基于多模态融合的干扰吊舱假目标生成优化模型”。论文分析雷达站址定位误差对假目标位置与轨迹的影响，并使用最小二乘、卡尔曼滤波、旋转几何和时延补偿改善假目标生成精度。

## 目录结构

- `题目及相关附件/`：暂未找到原题，按归档约定保留为空目录。
- `论文/`：`F031队数学建模B题论文.docx`。
- `论文补充材料和附件/`：从论文附录恢复并完善的代码、测试、依赖与运行结果。

## 附录代码

- `appendix1_trajectory_filter.py`：轨迹生成、全局最小二乘拟合和 NumPy 卡尔曼滤波。
- `appendix1_rotation_prediction.py`：逐帧测角误差下的旋转几何预测。
- `appendix2_delay_compensation.py`：沿测得方向求解最小欧氏误差的时延补偿。

原论文附录中的代码位于 Word 表格内，存在换行破损。完善版还修正了问题一逐帧四参数拟合仅有两个残差的欠定问题，并以 NumPy 实现卡尔曼滤波，从而移除未随论文提供的 `filterpy` 依赖。问题二原补偿公式会恒等返回理想轨迹；完善版在“只能调节时延、不能改变测角方向”的约束下，把理想拖引向量投影到测得方向，得到可执行的最小误差补偿。

## 运行

在 `论文补充材料和附件` 目录中执行：

```powershell
python appendix1_trajectory_filter.py
python appendix1_rotation_prediction.py
python appendix2_delay_compensation.py
python -m unittest discover -s tests -v
```

三个脚本默认以固定随机种子运行，并把指标、CSV 数据和 PNG 图保存到 `outputs/`。需要交互显示图像时可添加 `--show`。

## 验证状态

自动化测试共 7 项，覆盖轨迹生成确定性、拟合与滤波改进、旋转几何和时延补偿，当前均已通过。已生成的复现实验结果保存在 `论文补充材料和附件/outputs/`。
