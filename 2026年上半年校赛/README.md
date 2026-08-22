# 2026年上半年校赛

项目论文题为“基于耦合动力系统和高斯混合模型的玩家留存及收入策略优化”。研究围绕玩家注册后 30 天生命周期，完成留存预测、资源与成长瓶颈识别、玩家软分群、礼包组合优化及后续数据采集优先级分析。

## 目录结构

- `题目及相关附件/`：B 题题目文档。原始玩家数据集未包含在当前目录中。
- `论文/`：最终论文 `Final.pdf`。
- `论文补充材料和附件/`：四问模型代码、分析报告脚本、依赖文件、各问 CSV 输出及项目许可证。

## 方法概览

- Kaplan–Meier 型生存函数、离散风险率与 Bootstrap 区间
- 耦合动力系统特征和 GRU 留存预测
- 资源压力、成长停滞、逻辑回归与状态转移分析
- 高斯混合模型软分群、礼包响应模型和组合/价格网格搜索
- 灵敏度分析与数据采集优先级评估

## 环境与运行

建议使用 Python 3.13，并在补充材料目录中安装依赖：

```powershell
cd 论文补充材料和附件
python -m pip install -r requirements.txt
```

按以下顺序运行：

```powershell
python -X utf8 q1_retention_model.py
python -X utf8 q2_resource_payment_model.py
python -X utf8 q3_strategy_optimization.py
python -X utf8 q4_data_collection_closure.py
python -X utf8 model_analysis_report.py
```

脚本需要原始数据目录，其中应包含 `pickdata1.csv` 和 `pickdata2.csv`。大体积原始数据未随当前归档提供；现有 `q1_outputs` 至 `q4_outputs` 保存了已生成的核心结果，可在缺少原始数据时直接用于结果复核。

本项目保留了原独立仓库的 `.git` 元数据；补充材料中的代码许可证见 `LICENSE`。
