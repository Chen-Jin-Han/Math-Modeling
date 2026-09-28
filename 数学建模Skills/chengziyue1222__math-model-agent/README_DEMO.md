# 智感Nova本地比赛演示版

本目录提供“校园负荷预测模型可信诊断智能体”的本地比赛演示入口。运行过程只使用本机 Python、Nova API 服务层和 Nova Core；不需要服务器、公网、腾讯云账号或 DeepSeek Key。

## 一键启动（比赛现场推荐）

双击 `demo\\start_demo.bat` 即可启动本地展示页。它优先使用项目中的 `.venv`，没有虚拟环境时使用系统 Python；不需要独立 FastAPI 服务、不连接公网。

首次在新电脑上使用时，先在项目根目录执行一次：

```powershell
python -m pip install -r requirements.txt
```

## 命令行启动

在项目根目录执行：

```powershell
streamlit run ui/app.py
```

## 命令行演示

```powershell
python demo/run_demo.py --case CASE-DEMO-001
python demo/run_demo.py --case CASE-DEMO-002
python demo/run_demo.py --case NEEDS-REVIEW-001
```

可加 `--save-report`，将 Markdown 报告保存到对应运行产物目录。

三案例含义如下：

| 案例 | 预期 Gate | 展示重点 |
|---|---|---|
| `CASE-DEMO-001` | `READY_FOR_REVIEW` | 基线与高负荷证据已闭合，仍需人工复核。 |
| `CASE-DEMO-002` | `BLOCKED` | 检测到未来时点特征，阻断高风险辅助研判。 |
| `NEEDS-REVIEW-001` | `NEEDS_REVIEW` | 无阻断反证，但稳定性/高负荷证据未闭合。 |

## 页面展示内容

页面按真实诊断链展示：DecisionContract → Risk → Experiment → Evidence → Gate，并提供追溯校验和 Markdown 报告下载。所有结果均由本地 Nova Core 生成；展示层不改写实验、Evidence 或 Gate。

## 运行产物

每次执行会在 `demo/outputs/` 创建独立运行目录，保留输入、ToolResult、Evidence、manifest 与完整 `diagnosis_run.json`。该目录默认不纳入 Git；提交比赛材料时应单独打包三个案例各自的 `competition_report.md`、`manifest.json` 与代表性 Evidence/ToolResult。

## 展示边界

- Nova 判断的是模型是否具备可信证据，不是重新训练或替代预测模型。
- `READY_FOR_REVIEW` 表示证据闭合后可进入人工复核，不代表自动批准。
- 腾讯云设计材料保留在项目中，但不是本地演示版运行依赖。
- 本地演示版未接入 DeepSeek。
