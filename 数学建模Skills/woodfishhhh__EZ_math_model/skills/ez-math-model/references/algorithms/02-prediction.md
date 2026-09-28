# 02 预测类算法

> 回归 / 时间序列 / 灰色预测 / 树模型 / 深度学习的"教材级"参考。
> 适用：预测未来数值、补全缺失、外推趋势。

## 概述

预测类问题的核心是从历史数据学规律，外推到未见过的输入。流程：

```
原始数据
   ↓ 1. EDA + 缺失/异常值处理
   ↓ 2. 切分（时序按时间，非时序可随机）
   ↓ 3. 特征工程（滞后、滚动、差分、对数、独热）
   ↓ 4. 模型选型（线性 → 树 → 时序专用 → 深度学习）
   ↓ 5. 训练 + 验证（交叉验证 / 滚动预测）
   ↓ 6. 评估（R² / MAE / RMSE / MAPE / 区间预测）
   ↓ 7. 解释（特征重要性 / SHAP / 置信区间）
```

## 通用预处理

### 缺失值

| 缺失率 | 处理 |
|---|---|
| < 5% | 删除 / 中位数 / 众数填充 |
| 5%-30% | KNN / 多重插补（MICE） |
| > 30% | 删字段；保留则加"缺失指示位"（变量 + 是否缺失） |

**关键约束**：填充必须**在训练集上 fit，再 transform 测试集**；否则数据泄露。

### 异常值

- 单变量：IQR 1.5 倍 / Z-score |z|>3
- 多变量：Isolation Forest / LOF / 马氏距离
- 时序：STL 分解残差

### 标准化

| 方法 | 公式 | 适用 |
|---|---|---|
| Z-score | $z=(x-\mu)/\sigma$ | 近正态 |
| Min-Max | $z=(x-\min)/(\max-\min)$ | 神经网络 / 距离类 |
| Robust | $z=(x-\text{med})/\text{IQR}$ | 含异常值 |
| Log1p | $z=\ln(1+x)$ | 右偏 |

---

## 1. 线性回归 / Ridge / Lasso / ElasticNet

### 何时选

自变量与因变量近似线性、特征 < 100、需要可解释。

### 核心公式

$$
\min_{\beta} \; \frac{1}{2n} \|y - X\beta\|_2^2 + \alpha \cdot \mathcal{R}(\beta)
$$

| 模型 | 正则项 $\mathcal{R}(\beta)$ |
|---|---|
| OLS | 0 |
| Ridge | $\|\beta\|_2^2$ |
| Lasso | $\|\beta\|_1$（产生稀疏解） |
| ElasticNet | $\rho \|\beta\|_1 + (1-\rho) \|\beta\|_2^2$ |

### 关键参数

- `alpha`（Ridge / Lasso 正则强度）：用 LassoCV / RidgeCV 自动选。
- `l1_ratio`（ElasticNet 中 L1 占比）：默认 0.5。
- `fit_intercept`：是否拟合截距（已标准化数据可设 False）。

### 常见坑

- 多重共线性 → Ridge 或先 PCA。
- 特征尺度不齐 → 必须**先标准化再正则**。
- 残差异方差 / 自相关 → 改稳健回归 / GLS。
- Lasso 不稳定（小扰动权重大变） → 用 Stability Selection。

### 验证

- R²、RMSE、MAE
- 残差正态性（Shapiro-Wilk）
- 残差异方差（Breusch-Pagan）
- 残差自相关（Durbin-Watson）
- VIF 共线性检查（通常 VIF > 10 警惕）

### Python 入口

```python
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet, RidgeCV, LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("model", RidgeCV(alphas=[0.01, 0.1, 1, 10, 100], cv=5)),
])
pipe.fit(X_train, y_train)
print(f"alpha = {pipe['model'].alpha_:.3f}")
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Tibshirani, R. | Regression shrinkage and selection via the Lasso | JRSS-B | 1996 |
| Hoerl, A.E. & Kennard, R.W. | Ridge regression: biased estimation for nonorthogonal problems | Technometrics | 1970 |

---

## 2. ARIMA / SARIMA

### 何时选

单变量时间序列，长度 ≥ 50，有明显趋势 / 季节性。

### 核心公式

ARIMA(p, d, q)：先差分 d 次使序列平稳，再用 AR(p) 与 MA(q) 拟合：

$$
(1 - \sum_{i=1}^{p} \phi_i L^i)(1-L)^d y_t = (1 + \sum_{j=1}^{q} \theta_j L^j) \varepsilon_t
$$

SARIMA(p,d,q)(P,D,Q,s) 加季节项，$s$ 是季节周期。

### 选阶流程

```
1. ADF 检验确定 d（直到平稳）
2. 看 ACF 拖尾、PACF 截尾 → AR(p)
   ACF 截尾、PACF 拖尾 → MA(q)
   都拖尾 → ARMA
3. 用 AIC / BIC 在候选 (p,q) 中选最小
4. Ljung-Box 检验残差白噪声
```

### 关键参数

- (p, d, q)：用 `pmdarima.auto_arima` 自动；也可手 + AIC。
- 季节项 (P, D, Q, s)：常见 s = 12（月）/ 7（周）/ 24（小时）。

### 常见坑

- 不平稳直接套 ARIMA → 必须先 ADF + 差分。
- AIC 最低 ≠ 最优（可能过拟合） → 看残差检验。
- 长程预测置信区间爆炸 → 用 Prophet 或滚动预测。
- 把 ARIMA 套在多变量上 → 改 VAR / VARMAX。

### 验证

- Ljung-Box 残差检验
- 滚动预测（rolling forecast）
- 与持久性基线 / 季节朴素法对比

### Python 入口

```python
from statsmodels.tsa.arima.model import ARIMA
import pmdarima as pm

# 自动选阶
model = pm.auto_arima(y, seasonal=True, m=12, stepwise=True, suppress_warnings=True)
print(model.summary())

# 手动指定
model = ARIMA(y, order=(2, 1, 2), seasonal_order=(1, 1, 1, 12)).fit()
forecast = model.get_forecast(steps=12)
ci = forecast.conf_int(alpha=0.05)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Box, G.E.P. & Jenkins, G.M. | Time Series Analysis: Forecasting and Control | Wiley | 1970 |
| Hyndman, R.J. & Khandakar, Y. | Automatic time series forecasting: the forecast package for R | JSS | 2008 |

---

## 3. Prophet（Facebook 2017）

### 何时选

商业预测、有节假日效应、缺失值不少、不要求最优精度。

### 核心思路

可加分解：$y(t) = g(t) + s(t) + h(t) + \varepsilon_t$
- $g(t)$ 趋势（线性 / 逻辑斯蒂）
- $s(t)$ 周期（傅里叶级数表示年、周、日）
- $h(t)$ 节假日（用户给清单）

### 关键参数

- `changepoint_prior_scale`（趋势变点强度，默认 0.05；过拟合则减小）
- `seasonality_prior_scale`（季节强度）
- `holidays_prior_scale`（节假日强度）
- `seasonality_mode = 'additive' or 'multiplicative'`

### 常见坑

- 不擅长高频 / 极短序列。
- 训练集结尾的 changepoint 易过拟合 → 减小 prior。
- 没指定节假日 → 漏掉关键峰值。

### Python 入口

```python
from prophet import Prophet

m = Prophet(yearly_seasonality=True, weekly_seasonality=True,
            changepoint_prior_scale=0.05)
m.fit(df)  # df 必须有 ds (date) 与 y 列
future = m.make_future_dataframe(periods=30)
forecast = m.predict(future)
m.plot(forecast); m.plot_components(forecast)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Taylor, S.J. & Letham, B. | Forecasting at Scale | The American Statistician | 2018 |

---

## 4. 指数平滑 / ETS

### 何时选

序列短、想简单可解释、SARIMA 太重。

### 核心公式

```
水平：l_t = α y_t + (1-α)(l_{t-1} + b_{t-1})
趋势：b_t = β (l_t - l_{t-1}) + (1-β) b_{t-1}
季节：s_t = γ (y_t - l_t) + (1-γ) s_{t-m}
预测：ŷ_{t+h} = l_t + h b_t + s_{t+h-m}
```

### 关键参数

- `trend ∈ {add, mul, None}`
- `seasonal ∈ {add, mul, None}`
- 季节周期 `seasonal_periods`

### 常见坑

- 乘法季节配负值 / 零值序列 → 改加法。
- damped trend（阻尼趋势）适合长程预测衰减。

### Python 入口

```python
from statsmodels.tsa.holtwinters import ExponentialSmoothing
m = ExponentialSmoothing(y, trend='add', seasonal='add',
                          seasonal_periods=12, damped_trend=True).fit()
forecast = m.forecast(steps=12)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Hyndman, R.J., Koehler, A.B., Ord, J.K. & Snyder, R.D. | Forecasting with Exponential Smoothing | Springer | 2008 |

---

## 5. 灰色预测 GM(1,1)（Deng 1982）

### 何时选

数据极少（4-15 点）、单调趋势、无周期。

### 核心思路

```
1. 原始序列 X^(0) = (x^(0)_1, ..., x^(0)_n)
2. 1-AGO 累加：x^(1)_k = ∑_{i=1}^{k} x^(0)_i
3. 微分方程：dx^(1)/dt + a x^(1) = b
4. 最小二乘估 (a, b)
5. 时间响应函数：
     x̂^(1)_{k+1} = (x^(0)_1 - b/a) e^{-ak} + b/a
6. 累减还原：x̂^(0)_{k+1} = x̂^(1)_{k+1} - x̂^(1)_k
```

### 模型适用性检验

- 级比检验：$\lambda(k) = x^{(0)}_{k-1} / x^{(0)}_k \in (e^{-2/(n+1)}, e^{2/(n+1)})$
- 后验差比 C 与小误差概率 P：

| C | P | 等级 |
|---|---|---|
| < 0.35 | > 0.95 | 优 |
| < 0.50 | > 0.80 | 良 |
| < 0.65 | > 0.70 | 合格 |
| ≥ 0.65 | ≤ 0.70 | 不合格 |

### 常见坑

- 数据有明显波动 → 不适合，强用必扣分。
- 未做后验差检验直接给预测 → 论文薄。
- 长程外推 → 误差累积，控制在原数据长度的 30% 内。

### Python 入口

```python
import numpy as np

def gm11(x0: np.ndarray, predict: int = 1):
    n = len(x0)
    x1 = np.cumsum(x0)
    z1 = (x1[:-1] + x1[1:]) / 2
    B = np.column_stack([-z1, np.ones(n - 1)])
    Y = x0[1:].reshape(-1, 1)
    a, b = np.linalg.pinv(B) @ Y
    a, b = float(a), float(b)
    pred = []
    for k in range(n + predict):
        x1_k = (x0[0] - b / a) * np.exp(-a * k) + b / a
        pred.append(x1_k)
    pred = np.array(pred)
    x0_pred = np.diff(pred, prepend=0)
    return x0_pred[1:], (a, b)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| 邓聚龙 | 灰色控制系统 | 华中工学院出版社 | 1985 |
| 刘思峰等 | 灰色系统理论及其应用 | 科学出版社 | 2017 |

---

## 6. 随机森林 / XGBoost / LightGBM

### 何时选

表格数据、强非线性、特征 10-1000、样本 1k-1M。

### 核心思路

| 模型 | 思路 |
|---|---|
| RandomForest | Bagging：多棵树独立训练 + 平均 |
| XGBoost | Boosting：顺序训练，每棵树修正上一棵的残差，二阶泰勒展开 + 正则 |
| LightGBM | XGBoost 优化版：直方图算法 + Leaf-wise 生长 |
| CatBoost | 处理类别特征好，对称树 |

### 关键参数

```
RandomForest:
  n_estimators       200-500
  max_depth          None or 10-20
  min_samples_leaf   3-10
  max_features       sqrt(n_features)

XGBoost / LightGBM:
  learning_rate      0.05-0.1
  n_estimators       200-2000 (用早停决定)
  max_depth (XGB)    4-8
  num_leaves (LGB)   31-127
  reg_alpha          0-1   (L1)
  reg_lambda         1-10  (L2)
  subsample          0.7-0.9
  colsample_bytree   0.7-0.9
```

### 常见坑

- 时序数据用 train_test_split → 必须按时间切，禁止 shuffle。
- 类别特征不编码直接喂 → LightGBM 可传 `categorical_feature`；其他要 OneHot。
- 调参贪多 → 用 Optuna 调关键 4-5 个超参。
- 不用早停 → 早停 + 验证集是必须的。

### 验证

- 交叉验证 R² / MAE / RMSE
- 与线性基线对比（树模型 < 线性 → 数据可能过简单）
- SHAP / Permutation Importance 看特征贡献

### Python 入口

```python
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)
for train_idx, val_idx in tscv.split(X):
    m = xgb.XGBRegressor(
        n_estimators=2000, learning_rate=0.05, max_depth=6,
        subsample=0.8, colsample_bytree=0.8,
        early_stopping_rounds=50,
    )
    m.fit(X[train_idx], y[train_idx],
          eval_set=[(X[val_idx], y[val_idx])], verbose=False)
```

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Breiman, L. | Random Forests | Machine Learning | 2001 |
| Chen, T. & Guestrin, C. | XGBoost: A Scalable Tree Boosting System | KDD | 2016 |
| Ke, G. et al. | LightGBM: A Highly Efficient Gradient Boosting Decision Tree | NIPS | 2017 |

---

## 7. LSTM / GRU / Transformer

### 何时选

长序列、多变量、非线性强、数据量足够（≥ 数千窗口）。

### 关键参数

- `hidden_size` 32-256
- `num_layers` 1-3
- `dropout` 0.1-0.3
- `learning_rate` 1e-3
- `window_size` 10-100（输入历史长度）

### 常见坑

- 数据少还硬上深度模型 → ARIMA / XGB 通常更好。
- 没标准化 → 不收敛。
- look-ahead bias（用未来信息） → 切分必须严格按时间。
- 不用早停 → 必过拟合。

### Python 入口

```python
import torch
import torch.nn as nn

class LSTMReg(nn.Module):
    def __init__(self, input_size, hidden_size=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                            batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_size, 1)
    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])
```

建议优先 `pytorch-lightning` 简化训练循环；表格数据先 XGBoost 基线再考虑 LSTM。

### 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Hochreiter, S. & Schmidhuber, J. | Long Short-Term Memory | Neural Computation | 1997 |
| Vaswani, A. et al. | Attention Is All You Need | NeurIPS | 2017 |

---

## 8. 数据泄露防范（关键纪律）

| 操作 | 错误 | 正确 |
|---|---|---|
| 滞后特征 | `shift(-1)` | `shift(1)` |
| 滚动统计 | `rolling(w).mean()` | `rolling(w).mean().shift(1)` |
| 标准化 | 全数据 fit | **仅训练集** fit，测试集 transform |
| 目标编码 | 全数据计算统计 | 仅训练集 |
| 时序切分 | `train_test_split(shuffle=True)` | `TimeSeriesSplit` 或手动按时间切 |

## 选型对照表

| 数据特征 | 首选 | 备选 |
|---|---|---|
| 单变量、长度足、无明显非线性 | ARIMA | ETS |
| 单变量、需鲁棒、有节假日 | Prophet | SARIMA |
| 单变量、极少（<15） | 灰色预测 | 移动平均 |
| 多变量、表格、解释性优先 | 线性 / Ridge | XGBoost |
| 多变量、强非线性、特征多 | XGBoost / LightGBM | RandomForest |
| 多变量、超长序列、数据量大 | LSTM / Transformer | XGBoost + 滞后特征 |
| 多变量 + 不确定性 | XGBoost + Bootstrap | Quantile Regression |

## 评估指标速查

| 指标 | 公式 | 适用 |
|---|---|---|
| R² | $1 - SS_{res}/SS_{tot}$ | 通用 |
| MAE | $\frac{1}{n}\sum\|y-\hat y\|$ | 异常值不敏感 |
| RMSE | $\sqrt{\frac{1}{n}\sum(y-\hat y)^2}$ | 重视大误差 |
| MAPE | $\frac{1}{n}\sum\|(y-\hat y)/y\| \times 100\%$ | 尺度无关；y=0 时不可用 |
| sMAPE | $\frac{2}{n}\sum\|y-\hat y\|/(\|y\|+\|\hat y\|) \times 100\%$ | y=0 时仍可用 |

## 可视化建议

| 内容 | 推荐图 |
|---|---|
| 拟合 vs 真实 | 折线 + 预测线，区分训练/验证/预测段 |
| 残差 | 残差直方图 + 残差时序图 + Q-Q 图 |
| 不确定性 | 折线 + 95% 置信带（fill_between） |
| 特征重要性 | SHAP summary plot / 水平条形图 |
| 滚动预测 | 滚动 RMSE 折线 |
| 季节分解 | STL plot（trend / seasonal / resid 三合一） |

## 常见全栈错误

| ❌ 错误 | ✅ 正确 |
|---|---|
| 时序用 `train_test_split(shuffle=True)` | `TimeSeriesSplit` |
| 全数据标准化后切分 | 切分后仅在训练集 fit |
| 灰色预测套在波动数据 | 看是否单调；不单调用 ARIMA |
| LSTM 跑 50 个样本 | 至少几千窗口；少用线性 / 树模型 |
| 不做残差检验直接报 R²=0.9 | 必做 Ljung-Box / 残差正态性 |
| 长程预测无置信区间 | 用 Bootstrap / Quantile / Prophet 自带 CI |
