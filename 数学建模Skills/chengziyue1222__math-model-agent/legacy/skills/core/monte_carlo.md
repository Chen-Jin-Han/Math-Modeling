---
name: monte_carlo
description: 蒙特卡罗算法 — 随机模拟、数值积分、风险分析、排队仿真
---

# 蒙特卡罗算法 (Monte Carlo)

> 来源: zhanwen/MathModel 十类算法之一 + MathModelAgent

## 决策规则

```text
IF 问题涉及随机过程 / 概率估算 / 无解析解的复杂积分 / 风险评估
THEN
  模型: monte_carlo
  方法: 根据问题类型选择
ELSE
  继续判断
```

## 方法选择

| 场景 | 方法 | 代码入口 |
|------|------|----------|
| 数值积分 ∫f(x)dx | `monte_carlo_integration` | `algorithms.monte_carlo` |
| 概率/频率估算 | `monte_carlo_pi` 或自定义仿真 | `algorithms.monte_carlo` |
| 无梯度优化 | `monte_carlo_optimization` | `algorithms.monte_carlo` |
| 通用仿真 | `monte_carlo_simulation` | `algorithms.monte_carlo` |
| 排队系统分析 | `queuing_simulation` | `algorithms.monte_carlo` |
| 随机游走/扩散 | `random_walk` | `algorithms.monte_carlo` |

## 使用模板

### 蒙特卡罗数值积分

```python
from algorithms.monte_carlo import monte_carlo_integration
import numpy as np

# 估算 ∫₀^π sin(x) dx ≈ 2.0
result = monte_carlo_integration(
    f=lambda x: np.sin(x),
    a=0, b=np.pi,
    n_samples=100000
)
print(result.summary())
```

### 蒙特卡罗优化

```python
from algorithms.monte_carlo import monte_carlo_optimization

# 求解 min f(x,y) = x² + y², x,y ∈ [-5, 5]
best_x, best_val, result = monte_carlo_optimization(
    objective=lambda x: x[0]**2 + x[1]**2,
    bounds=[(-5, 5), (-5, 5)],
    n_samples=100000,
    minimize=True
)
print(f"最优解: {best_x}, 最优值: {best_val}")
```

### 排队论仿真

```python
from algorithms.monte_carlo import queuing_simulation

# M/M/1 排队系统: λ=5, μ=8
result = queuing_simulation(
    arrival_rate=5,
    service_rate=8,
    n_customers=10000,
    n_servers=1
)
print(f"平均等待时间: {result['avg_wait_time']:.2f}")
print(f"利用率: {result['utilization']:.2%}")
```

### 通用蒙特卡罗仿真

```python
from algorithms.monte_carlo import monte_carlo_simulation
import numpy as np

# 投资组合风险分析
def portfolio_return(weights):
    returns = np.random.normal([0.08, 0.12], [0.15, 0.25])
    return np.dot(weights, returns)

result = monte_carlo_simulation(
    model=portfolio_return,
    input_distributions=[
        lambda: np.random.uniform(0, 1),
        lambda: np.random.uniform(0, 1),
    ],
    n_samples=10000
)
print(result)
```

## 蒙特卡罗方法论

1. **问题定义**: 明确需要估算的量
2. **随机建模**: 将问题转化为随机变量的期望值
3. **采样**: 根据概率分布生成随机样本
4. **统计**: 计算样本均值、方差、置信区间
5. **验证**: 增加样本量检验收敛性

## 关键原理

- **大数定律**: 样本均值依概率收敛于期望值
- **中心极限定理**: 估计误差服从正态分布
- **标准误**: SE = σ/√n，样本量增大100倍，精度提高10倍
- **置信区间**: 95% CI = 估计值 ± 1.96 × SE

## 与其他模块的关系

- 配合 `evaluation.py` 中的 DEA 使用（随机前沿分析）
- 配合 `metaheuristic.py` 使用（模拟退火本身就是蒙特卡罗方法）
- 配合 `cellular_automata.py` 使用（随机元胞自动机）
