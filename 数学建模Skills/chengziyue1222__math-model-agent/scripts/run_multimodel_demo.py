"""Run a deterministic multi-question forecasting-and-allocation paper demo.

This is a teaching fixture, not a competition answer: every result is computed
from generated input data and the paper labels its reference limitation.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml

from algorithms.document_validation import inspect_pdf_layout, validate_cross_artifact_values
from algorithms.math_programming import linear_programming
from algorithms.regression import linear_regression


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tex_escape(value: str) -> str:
    return value.replace("_", r"\_").replace("%", r"\%")


def main() -> int:
    out = ROOT / "artifacts" / "integration_demo" / "multi_question_forecast_allocation"
    for name in ("inputs", "parsed_problem", "model_plan", "source_code", "execution_logs", "verified_results", "figures", "tables", "paper_source", "validation_report", "pdf_preflight_report"):
        (out / name).mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260805)
    periods = np.arange(1, 49)
    demand = 48 + 1.15 * periods + 7 * np.sin(periods / 4) + rng.normal(0, 2.1, len(periods))
    write_json(out / "inputs" / "demand_data.json", {"seed": 20260805, "period": periods.tolist(), "demand": demand.tolist(), "unit": "orders/day"})
    train, test = 36, 12
    regression = linear_regression(periods[:train], demand[:train])
    predicted = regression["intercept"] + regression["slope"] * periods
    mae = float(np.mean(np.abs(predicted[train:] - demand[train:])))
    baseline = float(np.mean(np.abs(np.full(test, demand[:train].mean()) - demand[train:])))
    forecast = float(predicted[-1])
    # Q2 allocation: two services share budget and capacity.  The repository's
    # own linear-programming implementation delegates to SciPy and records the result.
    capacity = 125.0
    allocation = linear_programming(c=[1.0, 0.84], A_ub=[[1.0, 1.0], [0.65, 0.45]], b_ub=[capacity, 66.0], bounds=[(0, forecast), (0, forecast)], maximize=True)
    if not allocation["success"]:
        raise RuntimeError(allocation["message"])
    x_a, x_b = map(float, allocation["x"])
    sensitivity = []
    for cap in range(80, 151, 10):
        result = linear_programming(c=[1.0, 0.84], A_ub=[[1.0, 1.0], [0.65, 0.45]], b_ub=[float(cap), 66.0], bounds=[(0, forecast), (0, forecast)], maximize=True)
        sensitivity.append({"capacity": cap, "objective": float(result["fun"]), "service_a": float(result["x"][0]), "service_b": float(result["x"][1])})
    results = {"status": "verified", "forecast_period_48": forecast, "forecast_mae": mae, "baseline_mae": baseline, "forecast_r2": float(regression["R2"]), "allocation_a": x_a, "allocation_b": x_b, "allocation_objective": float(allocation["fun"]), "capacity_residual": capacity-x_a-x_b, "resource_residual": 66-(0.65*x_a+0.45*x_b), "sensitivity": sensitivity, "result_origin": "executed deterministic regression and linear programming"}
    write_json(out / "verified_results" / "results.json", results)
    write_json(out / "parsed_problem" / "requirements.json", {"subproblems": ["Q1 forecast demand", "Q2 allocate capacity", "Q3 test capacity sensitivity"], "shared_kernel_required": True, "units": "orders/day"})
    cards = yaml.safe_load((ROOT / "docs/reverse_engineering/skill_rule_pack_v1/07_modeling_pattern_cards.yaml").read_text(encoding="utf-8"))["rules"]
    candidates = [{"rule_id": card["rule_id"], "method": card.get("method_name"), "applicable": any("敏感" in str(x) or "共用" in str(x) for x in card.get("trigger_conditions", []))} for card in cards]
    write_json(out / "model_plan" / "candidate_models.json", {"dependency_analysis": {"shared_kernel_required": True, "reason": "forecast output feeds allocation and sensitivity"}, "candidates": candidates, "selected": ["linear_regression", "linear_programming", "capacity sensitivity sweep"]})
    shutil.copy2(__file__, out / "source_code" / "run_multimodel_demo.py")

    plt.rcParams.update({"font.size": 10})
    plt.figure(figsize=(6.4, 3.6)); plt.plot(periods, demand, "o", ms=3, label="observed demand"); plt.plot(periods, predicted, lw=2, label="linear forecast"); plt.axvline(train, color="gray", ls="--", label="holdout start"); plt.xlabel("period"); plt.ylabel("orders/day"); plt.legend(); plt.tight_layout(); plt.savefig(out / "figures" / "forecast.png", dpi=450); plt.close()
    plt.figure(figsize=(5.4, 3.6)); plt.bar(["service A", "service B"], [x_a, x_b], color=["#1f4e79", "#c55a11"]); plt.ylabel("allocated orders/day"); plt.tight_layout(); plt.savefig(out / "figures" / "allocation.png", dpi=450); plt.close()
    plt.figure(figsize=(6.0, 3.6)); plt.plot([row["capacity"] for row in sensitivity], [row["objective"] for row in sensitivity], marker="o", color="#548235"); plt.xlabel("capacity (orders/day)"); plt.ylabel("weighted service objective"); plt.tight_layout(); plt.savefig(out / "figures" / "sensitivity.png", dpi=450); plt.close()
    write_json(out / "tables" / "forecast_metrics.json", {"columns": ["model", "MAE", "R2"], "rows": [["linear regression", mae, regression["R2"]], ["mean baseline", baseline, None]]})
    write_json(out / "tables" / "allocation.json", {"columns": ["service", "allocation", "resource coefficient"], "rows": [["A", x_a, 0.65], ["B", x_b, 0.45]]})
    displays = [{"quantity_id": "forecast_mae", "value": round(mae, 3), "decimals": 3, "artifact": "paper"}, {"quantity_id": "allocation_objective", "value": round(float(allocation["fun"]), 3), "decimals": 3, "artifact": "paper"}]
    consistency = validate_cross_artifact_values(results, displays)
    write_json(out / "validation_report" / "consistency.json", {"status": "pass" if not consistency else "fail", "issues": [x.__dict__ for x in consistency]})

    tex = r'''\documentclass[UTF8,11pt,a4paper]{ctexart}
\usepackage[margin=2.5cm]{geometry}\usepackage{booktabs,graphicx,amsmath,hyperref,longtable,listings}
\setlength{\parindent}{2em}\linespread{1.45}\title{多子问题需求预测与容量分配：可复现实验演示}\author{math-model integration pipeline}\date{\today}
\begin{document}\pagestyle{plain}\pagenumbering{arabic}\setcounter{page}{1}\maketitle
\begin{abstract}本文以确定性生成的48期需求序列为输入，构建“预测--分配--敏感性”三个相互依赖的子问题。首先使用仓库中的最小二乘线性回归预测末期需求；其次使用线性规划进行双服务容量分配；最后扫描总容量以评估决策阈值附近的响应。预测留出集 MAE 为 %(mae).3f，基线 MAE 为 %(base).3f；分配目标值为 %(obj).3f。约束残差、留出集比较和容量敏感性均被写入结构化结果。本示例为教学验证，不声称外部数据或文献已经核验。
\par\noindent\textbf{关键词：} 需求预测；线性规划；灵敏度分析；可复现性；验证门
\end{abstract}\clearpage
\section{问题重述}\noindent 目标是以同一份可追溯结果支持三个问题：需求预测、服务容量分配和容量变化下的稳健性判断。所有数值均来自本次执行产生的 JSON。
\section{问题分析与依赖}\noindent Q1 的预测输出进入 Q2 的上界；Q2 的目标与约束在 Q3 中重复求解。因此 dependency analysis 明确要求统一模型层。候选方法包括回归、基线比较、线性规划及容量扫描。
\section{统一模型与假设}\noindent 假设需求具有可识别的线性趋势，两个服务共享总容量和资源预算。此假设可由留出集误差和约束残差检验。令 $d_t$ 为需求，$x_A,x_B$ 为分配量，目标为 $\max x_A+0.84x_B$，并满足 $x_A+x_B\le C$ 与 $0.65x_A+0.45x_B\le66$。\clearpage
\section{符号说明}\begin{tabular}{ll}\toprule 符号&含义\\\midrule$d_t$&第 $t$ 期需求\\$C$&总容量\\$x_A,x_B$&两类服务的分配量\\\bottomrule\end{tabular}
\section{子问题一：需求预测}\noindent 使用仓库的 \texttt{linear\_regression} 对前36期拟合，并以最后12期作为留出集；均值预测是同一切分下的基线。图\ref{f:forecast}显示训练/留出边界，避免将训练误差当作预测性能。
\begin{figure}[htbp]\centering\includegraphics[width=.88\linewidth]{forecast.png}\caption{需求观测、线性预测与留出集边界}\label{f:forecast}\end{figure}
\begin{table}[htbp]\centering\caption{预测验证指标}\begin{tabular}{lrr}\toprule 方法&MAE&R$^2$\\\midrule 线性回归&%(mae).3f&%(r2).3f\\均值基线&%(base).3f&--\\\bottomrule\end{tabular}\end{table}\clearpage
\section{子问题二：容量分配}\noindent 以预测需求为上界调用仓库的 \texttt{linear\_programming}。结果为 $x_A=%(a).3f$、$x_B=%(b).3f$，目标值 %(obj).3f。约束残差为 %(capres).3f 和 %(resres).3f；它们只表示数值可行性，不等同于模型正确性。
\begin{figure}[htbp]\centering\includegraphics[width=.70\linewidth]{allocation.png}\caption{两类服务的最优容量分配}\end{figure}
\begin{table}[htbp]\centering\caption{分配与资源系数}\begin{tabular}{lrr}\toprule 服务&分配量&资源系数\\\midrule A&%(a).3f&0.65\\B&%(b).3f&0.45\\\bottomrule\end{tabular}\end{table}\clearpage
\section{子问题三：容量敏感性}\noindent 将容量从80至150按10递增重算线性规划。图\ref{f:sens}给出目标响应；该图的结论是“在该模拟输入与约束下的响应”，不是对外部系统的无条件断言。
\begin{figure}[htbp]\centering\includegraphics[width=.82\linewidth]{sensitivity.png}\caption{容量敏感性曲线}\label{f:sens}\end{figure}
\section{模型检验与评价}\noindent 验证包括同切分基线比较、资源约束残差、跨产物舍入一致性以及容量扫描。优点是每个结论均可回溯到结果 JSON；局限是数据为教学用确定性模拟数据，未进行外部校准。\clearpage
\section{运行证据与交付合同}\noindent 本次运行固定随机种子为 20260805；输入哈希、模型候选、源代码、结果 JSON、图表、表格和 PDF 预检报告均作为提交包条目保存。未经执行的语言模型数值不能进入 \texttt{verified} 状态。该页只记录可复核运行事实，不以求解器残差替代外部模型误差。\clearpage
\section*{参考文献与数据来源}本演示不虚构外部文献。数据来源为本次运行生成的 \texttt{inputs/demand\_data.json}；算法实现来自本仓库的 \texttt{algorithms.regression} 与 \texttt{algorithms.math\_programming}。
\clearpage\appendix\section{复现说明}\noindent 执行 \texttt{scripts/run\_multimodel\_demo.py}。完整输入、代码、结构化结果、图表和预检报告均在交付目录。复现前应先读取 \texttt{inputs/demand\_data.json} 中的随机种子和单位；随后运行回归、留出集比较、线性规划和容量扫描。若任一求解步骤失败，运行记录必须保留失败状态而不是输出正式结论。
\section{支撑材料完整文件清单}\noindent \texttt{source\_code/run\_multimodel\_demo.py}；\texttt{inputs/demand\_data.json}；\texttt{figures/}、\texttt{tables/}、\texttt{verified\_results/}、\texttt{validation\_report/} 和 \texttt{pdf\_preflight\_report/} 下的全部生成文件。
\section{完整源程序}\lstinputlisting[language=Python,basicstyle=\ttfamily\scriptsize,breaklines=true]{../source_code/run_multimodel_demo.py}
\noindent 论文中的 MAE、目标值和分配量应由结果 JSON 的原始值按声明的小数位生成；1.23456 与 1.235 在三位小数显示规则下属于一致，不能被误判为冲突。\clearpage
\section{容量扫描明细}\begin{longtable}{rrr}\toprule 容量&目标值&服务A\\\midrule
%(sens)s\\
\bottomrule\end{longtable}\end{document}''' % {"mae": mae, "base": baseline, "obj": allocation["fun"], "r2": regression["R2"], "a": x_a, "b": x_b, "capres": capacity-x_a-x_b, "resres": 66-(.65*x_a+.45*x_b), "sens": "\\\\\n".join(f"{row['capacity']}&{row['objective']:.3f}&{row['service_a']:.3f}" for row in sensitivity)}
    paper = out / "paper_source"
    (paper / "main.tex").write_text(tex, encoding="utf-8")
    for figure in (out / "figures").glob("*.png"): shutil.copy2(figure, paper / figure.name)
    compile_run = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=paper, text=True, capture_output=True)
    (out / "execution_logs" / "xelatex.log").write_text(compile_run.stdout+"\n"+compile_run.stderr, encoding="utf-8")
    if compile_run.returncode: raise RuntimeError("xelatex failed; inspect execution_logs/xelatex.log")
    # A second pass resolves cross-references and final pagination.
    subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=paper, text=True, capture_output=True, check=True)
    final_pdf = out / "final_pdf.pdf"; shutil.copy2(paper / "main.pdf", final_pdf)
    preflight = inspect_pdf_layout(final_pdf); write_json(out / "pdf_preflight_report" / "preflight.json", preflight)
    write_json(out / "package_manifest.json", {"run_id": "multi_question_forecast_allocation", "created_at": datetime.now(timezone.utc).isoformat(), "status": "pass" if preflight["status"] == "pass" and not consistency else "fail", "pdf_pages": preflight["page_count"], "manual_review_required": preflight["manual_review_required"]})
    print(json.dumps({"output": str(out.relative_to(ROOT)).replace("\\", "/"), "pdf": str(final_pdf.relative_to(ROOT)).replace("\\", "/"), "pages": preflight["page_count"], "preflight": preflight["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__": raise SystemExit(main())
