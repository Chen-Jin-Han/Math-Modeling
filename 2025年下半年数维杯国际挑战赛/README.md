# 2025年下半年数维杯国际挑战赛

项目研究“PSO-UKF Based Model for Centrifugal Vibration Suppression”，以双电机离心执行器为对象，对车辆横向振动进行主动控制。论文依次建立动力学仿真、PSO/fmincon 混合优化和 UKF 状态观测控制模型。

## 目录结构

- `题目及相关附件/`：英文 A 题、数据表、题目压缩包和论文模板。
- `论文/`：编号 `ASHUWEICUP2541783` 的最终 PDF 与 Word 源稿。
- `论文补充材料和附件/`：MATLAB 代码、AI 使用说明、承诺/说明文件、提交压缩包及三次样条资料。

## 代码入口

主要代码位于：

```text
论文补充材料和附件/ASHUWEICUP2541783fj/ASHUWEICUP2541783fj/
├─ Problem_1.m
├─ Problem_2.m
└─ Problem_3.m
```

在 MATLAB 中将该目录设为当前目录后执行：

```matlab
Problem_1
Problem_2
Problem_3
```

`Problem_2.m` 使用粒子群与 `fmincon`，`Problem_3.m` 使用粒子群和 UKF，因此通常需要 Global Optimization Toolbox 与 Optimization Toolbox。代码还会从题目 Excel 数据中读取参数；若提示找不到文件，请将 `Problem A：Data.xlsx` 复制或加入 MATLAB 搜索路径。

多个嵌套目录和压缩包来自原始提交结构，为便于追溯已原样保留。
