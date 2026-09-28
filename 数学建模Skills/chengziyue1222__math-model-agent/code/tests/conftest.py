"""Pytest 共享配置。

`pythonpath` 由 pyproject.toml 的 [tool.pytest.ini_options] 配置，
无需手动 sys.path.insert。
"""
import numpy as np

# 固定随机种子，确保测试可复现
np.random.seed(42)
