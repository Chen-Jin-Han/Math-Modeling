"""
数学建模算法工具箱
==================

149 个公开导出，25 个算法与质量模块，覆盖数学建模竞赛全流程。
全部基于 numpy/scipy 实现，无深度学习框架依赖。

来源:
- Algorithms_MathModels (HuangCongQing) — MATLAB → Python 转写
- ravenxrz/Mathematical-Modeling — 补充算法
- MathModelAgent (jihe520) — 论文检查、科研图表
- 自研 — 蒙特卡罗、图像处理

使用方式::

    from algorithms import *
    weights, lambda_max, CR, passed = ahp_weight(matrix)
    result = gm11_predict(data, predict_count=5)
"""

# ── 1. 决策与评价 (23) ────────────────────────────────────────
from .ahp import ahp_weight, consistency_check, hierarchical_ahp, build_judgment_matrix
from .fuzzy_math import (
    fuzzy_comprehensive_evaluation, fuzzy_cmeans, multi_level_fuzzy_evaluation,
    gaussmf, trimf, trapmf,
)
from .evaluation import (
    entropy_weight, topsis, ahp_topsis, dea, pca, rsr, fahp,
    grey_relational, combined_weight,
    TOPSISResult, DEAResult, PCAResult, RSRResult,
)

# ── 2. 预测与回归 (27) ────────────────────────────────────────
from .grey_system import (
    gm11_predict, gm21_predict, verhulst_predict,
    grey_correlation, grey_correlation_rank, grey_clustering, grey_auto_predict,
)
from .regression import (
    linear_regression, polynomial_regression, ridge_regression,
    stepwise_regression, nonlinear_regression, logistic_regression,
)
from .interpolation import lagrange_interp, newton_interp, cubic_spline_interp, piecewise_linear_interp
from .time_series import (
    simple_moving_average, weighted_moving_average, trend_moving_average,
    single_exponential_smoothing, double_exponential_smoothing, triple_exponential_smoothing,
    gompertz_curve, logistic_curve, modified_exponential_curve, adaptive_filter,
)

# ── 3. 优化与规划 (9) ─────────────────────────────────────────
from .metaheuristic import (
    genetic_algorithm, particle_swarm, simulated_annealing,
    ant_colony_tsp, artificial_fish_swarm,
)
from .math_programming import linear_programming, integer_programming, goal_programming, nonlinear_programming

# ── 4. 图论与网络 (11) ────────────────────────────────────────
from .graph_theory import (
    dijkstra, floyd, floyd_get_path, get_path, prim_mst, max_flow, critical_path,
    min_cost_flow, graph_coloring, euler_path, hungarian_matching,
)

# ── 5. 随机模拟 (8) ───────────────────────────────────────────
from .monte_carlo import (
    monte_carlo_integration, monte_carlo_pi, monte_carlo_optimization,
    monte_carlo_simulation, queuing_simulation, queuing_mmsk, random_walk, MCResult,
)

# ── 6. 机器学习与神经网络 (4) ─────────────────────────────────
from .neural_network import BPNeuralNetwork, RBFNetwork, SOM, miv_variable_importance

# ── 7. 元胞自动机 (6) ─────────────────────────────────────────
from .cellular_automata import GameOfLife, ForestFire, ElementaryCA, DLA, SIRSModel, NaSchTraffic

# ── 8. 图像处理 (7) ───────────────────────────────────────────
from .image_processing import (
    noise_filter, edge_detection, image_segmentation, morphological_ops,
    histogram_analysis, histogram_equalization, feature_extraction,
)

# ── 9. 论文与图表 (34) ────────────────────────────────────────
from .paper_check import PaperChecker, check_paper
from .paper_readiness import ReadinessReview, review_paper, write_review_report
from .sci_figures import (
    TaylorDiagram, PairedRaincloud, CvRocCurve, CorrelationPairgrid,
    PredictionMarginal, HyperparamSurface, CorrSplitViolin,
    CircularHeatmap, ComboComparison, ChordDiagram, ShapBeeswarm,
    TaylorPoint, RocModelSpec, PredModelPanel, HeatmapTrait, HeatmapGroup,
    ChordNode, FigureContract, FigureDesignBrief, FigureAuditReport, PUBLICATION_WIDTH_MM,
    MODELING_PALETTE, MODELING_PALETTES, MODELING_PAPER_THEME,
    get_modeling_palette, resolve_cjk_font, add_panel_label, mm_to_inches, publication_size,
    publication_rc_params, paper_figure_rc_params, audit_publication_figure,
    export_publication_figure, save_figure as save_sci_figure,
)
from .diagram import (
    FlowchartLayout, ERDiagramLayout, SystemModuleLayout,
    AcademicTable, SQLParser, save_svg, save_drawio, save_html,
)
from .data_diagnostics import panel_diagnostics
from .modeling_contracts import (
    validate_decision_contract, validate_contract_artifacts,
    validate_quality_validation, validate_source_records, records_to_bibtex,
)
from .modeling_quality import (
    validate_state_balance, service_level_metrics,
    compare_policy_metrics, lexicographic_order,
)

# ── 公开接口 ──────────────────────────────────────────────────
__all__ = [
    # ── 决策与评价 (23) ──
    'ahp_weight', 'consistency_check', 'hierarchical_ahp', 'build_judgment_matrix',
    'fuzzy_comprehensive_evaluation', 'fuzzy_cmeans', 'multi_level_fuzzy_evaluation',
    'gaussmf', 'trimf', 'trapmf',
    'entropy_weight', 'topsis', 'ahp_topsis', 'dea', 'pca', 'rsr', 'fahp',
    'grey_relational', 'combined_weight',
    'TOPSISResult', 'DEAResult', 'PCAResult', 'RSRResult',

    # ── 预测与回归 (27) ──
    'gm11_predict', 'gm21_predict', 'verhulst_predict',
    'grey_correlation', 'grey_correlation_rank', 'grey_clustering', 'grey_auto_predict',
    'linear_regression', 'polynomial_regression', 'ridge_regression',
    'stepwise_regression', 'nonlinear_regression', 'logistic_regression',
    'lagrange_interp', 'newton_interp', 'cubic_spline_interp', 'piecewise_linear_interp',
    'simple_moving_average', 'weighted_moving_average', 'trend_moving_average',
    'single_exponential_smoothing', 'double_exponential_smoothing', 'triple_exponential_smoothing',
    'gompertz_curve', 'logistic_curve', 'modified_exponential_curve', 'adaptive_filter',

    # ── 优化与规划 (9) ──
    'genetic_algorithm', 'particle_swarm', 'simulated_annealing',
    'ant_colony_tsp', 'artificial_fish_swarm',
    'linear_programming', 'integer_programming', 'goal_programming', 'nonlinear_programming',

    # ── 图论与网络 (11) ──
    'dijkstra', 'floyd', 'floyd_get_path', 'get_path', 'prim_mst', 'max_flow', 'critical_path',
    'min_cost_flow', 'graph_coloring', 'euler_path', 'hungarian_matching',

    # ── 随机模拟 (8) ──
    'monte_carlo_integration', 'monte_carlo_pi', 'monte_carlo_optimization',
    'monte_carlo_simulation', 'queuing_simulation', 'queuing_mmsk', 'random_walk', 'MCResult',

    # ── 机器学习与神经网络 (4) ──
    'BPNeuralNetwork', 'RBFNetwork', 'SOM', 'miv_variable_importance',

    # ── 元胞自动机 (6) ──
    'GameOfLife', 'ForestFire', 'ElementaryCA', 'DLA', 'SIRSModel', 'NaSchTraffic',

    # ── 图像处理 (7) ──
    'noise_filter', 'edge_detection', 'image_segmentation', 'morphological_ops',
    'histogram_analysis', 'histogram_equalization', 'feature_extraction',

    # ── 论文与图表 (34) ──
    'PaperChecker', 'check_paper', 'ReadinessReview', 'review_paper', 'write_review_report',
    'TaylorDiagram', 'PairedRaincloud', 'CvRocCurve', 'CorrelationPairgrid',
    'PredictionMarginal', 'HyperparamSurface', 'CorrSplitViolin',
    'CircularHeatmap', 'ComboComparison', 'ChordDiagram', 'ShapBeeswarm',
    'TaylorPoint', 'RocModelSpec', 'PredModelPanel', 'save_sci_figure',
    'FigureContract', 'FigureDesignBrief', 'FigureAuditReport', 'PUBLICATION_WIDTH_MM',
    'MODELING_PALETTE', 'MODELING_PALETTES', 'MODELING_PAPER_THEME',
    'get_modeling_palette', 'resolve_cjk_font', 'add_panel_label', 'mm_to_inches', 'publication_size',
    'publication_rc_params', 'paper_figure_rc_params', 'audit_publication_figure', 'export_publication_figure',
    'FlowchartLayout', 'ERDiagramLayout', 'SystemModuleLayout',
    'AcademicTable', 'SQLParser', 'save_svg', 'save_drawio', 'save_html',
    # Reusable evidence and quality contracts
    'panel_diagnostics',
    'validate_decision_contract', 'validate_contract_artifacts',
    'validate_quality_validation', 'validate_source_records', 'records_to_bibtex',
    'validate_state_balance', 'service_level_metrics',
    'compare_policy_metrics', 'lexicographic_order',
]
