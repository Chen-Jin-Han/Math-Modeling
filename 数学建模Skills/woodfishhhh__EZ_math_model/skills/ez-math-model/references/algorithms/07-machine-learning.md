# 07 机器学习算法

> 监督 / 集成 / 不平衡 / 解释性 / 异常检测 / 调参的"教材级"参考。
> 算法层面已在 02 预测 / 05 统计中覆盖；本篇聚焦"建模题里的 ML 实战"。

## 1. 分类基线五件套（按"先简单后复杂"顺序实践）

### 1.1 Logistic 回归

**何时**：线性可分 / 解释性强 / 大样本 / 稀疏特征。

**关键参数**：
- `C`（正则强度倒数；`0.01-100`，默认 1）
- `class_weight`（不平衡）
- `penalty`（`l1` / `l2` / `elasticnet`）

**输出**：可解释系数 + 概率（用 `predict_proba`）。

```python
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("clf", LogisticRegression(C=1.0, class_weight='balanced', max_iter=1000)),
])
pipe.fit(X_train, y_train)
proba = pipe.predict_proba(X_test)[:, 1]
```

### 1.2 朴素贝叶斯

**何时**：文本分类 / 特征条件独立 / 小样本 / 实时预测。

```python
from sklearn.naive_bayes import GaussianNB, MultinomialNB, BernoulliNB
clf = GaussianNB(var_smoothing=1e-9)         # 连续特征
clf = MultinomialNB(alpha=1.0)                # 计数特征（文本 BoW / TF-IDF）
clf = BernoulliNB(alpha=1.0)                  # 二值特征
```

### 1.3 决策树

**何时**：解释性优先 / 非线性 / 中小样本。

**关键参数**：
- `max_depth=4-10`（关键，过深过拟合）
- `min_samples_leaf=10-50`
- `criterion='gini' / 'entropy'`

```python
from sklearn.tree import DecisionTreeClassifier, plot_tree
clf = DecisionTreeClassifier(max_depth=6, min_samples_leaf=20, random_state=42)
clf.fit(X_train, y_train)
plot_tree(clf, feature_names=features, max_depth=3)
```

### 1.4 随机森林

**何时**：强非线性 / 默认即不错 / 不需仔细调参。

**关键参数**：
- `n_estimators=200-500`
- `max_depth=None or 10-20`
- `max_features='sqrt'`（分类）/ `1/3`（回归）

```python
from sklearn.ensemble import RandomForestClassifier
rf = RandomForestClassifier(
    n_estimators=300, max_depth=None, max_features='sqrt',
    n_jobs=-1, random_state=42, class_weight='balanced',
)
rf.fit(X_train, y_train)
```

### 1.5 XGBoost / LightGBM

**何时**：表格数据 SOTA、需调参精度。

**关键参数**：

| 参数 | XGB | LGB |
|---|---|---|
| `learning_rate` | 0.05-0.1 | 同 |
| `max_depth` / `num_leaves` | 4-8 | 31-127 |
| `n_estimators` | 200-2000 (用早停) | 同 |
| `subsample` | 0.7-0.9 | 同 |
| `colsample_bytree` | 0.7-0.9 | 同 |
| `reg_alpha` / `reg_lambda` | 0-1 / 1-10 | 同 |

```python
import xgboost as xgb
m = xgb.XGBClassifier(
    n_estimators=2000, learning_rate=0.05, max_depth=6,
    subsample=0.8, colsample_bytree=0.8,
    reg_lambda=1.0, eval_metric='auc',
    early_stopping_rounds=50, random_state=42,
)
m.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
```

### 选型对照

| 数据特征 | 首选 |
|---|---|
| 线性可分、需解释 | Logistic |
| 文本 / 高维稀疏 | Multinomial NB / Logistic + TF-IDF |
| 解释性 + 中等性能 | 决策树 |
| 默认起点 | RandomForest |
| 表格 SOTA | XGBoost / LightGBM |
| 类别特征多 | CatBoost |
| 大样本（>1M） | LightGBM > XGBoost |

---

## 2. 类别不平衡（关键）

正负样本比 > 5:1 时必须处理。

### 处理方法

| 方法 | 适用 |
|---|---|
| `class_weight='balanced'` | 任何 sklearn 模型；最简单 |
| 过采样 SMOTE | 数据少；imblearn 库 |
| 欠采样 | 数据多、负样本充足 |
| Focal Loss | 深度模型 |
| 阈值调整 | 部署时根据业务调 |
| Ensemble（BalancedRandomForest） | 综合 |

### SMOTE 正确用法

**关键纪律**：SMOTE **必须**在交叉验证内做（用 `imblearn.pipeline`），否则
泄露。

```python
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE
from sklearn.model_selection import StratifiedKFold, cross_val_score

pipe = ImbPipeline([
    ("smote", SMOTE(random_state=42)),
    ("clf", LogisticRegression()),
])
scores = cross_val_score(pipe, X, y, cv=StratifiedKFold(5),
                          scoring='f1', n_jobs=-1)
```

### 评估指标（不平衡场景）

不要用 accuracy，改用：
- **F1 / F2**（Recall 重要）
- **AUC**（整体排序能力）
- **PR-AUC**（不平衡更敏感）
- **Cohen's Kappa**

---

## 3. SVM

### 何时

样本中等（< 50k）、特征经过降维或较少、需要核技巧。

### 核函数

| 核 | 适用 |
|---|---|
| linear | 高维稀疏（文本） |
| RBF（默认） | 一般非线性 |
| poly | 多项式关系 |
| sigmoid | 类似神经网络的浅层 |

### 关键参数

- `C`：正则倒数；`0.1-100`
- `gamma`：RBF 核宽度；`'scale'`（推荐）/ 手动 `0.001-1`

### 常见坑

- **不标准化 → 灾难**（核基于距离）
- 大样本（> 100k）训练超慢 → 改 LinearSVC / 树模型
- gamma 太大过拟合，太小欠拟合 → 用 GridSearchCV

```python
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV

param_grid = {'C': [0.1, 1, 10, 100], 'gamma': ['scale', 0.01, 0.1, 1]}
grid = GridSearchCV(SVC(kernel='rbf', class_weight='balanced'),
                    param_grid, cv=5, scoring='f1', n_jobs=-1)
grid.fit(X_train_scaled, y_train)
```

---

## 4. 神经网络

### 何时

图像 / 文本 / 多模态 / 表格大数据（≥ 100k）。

### 表格数据基线对比铁律

**必须**给 XGBoost 基线对比。表格数据 MLP 经常输给 XGBoost。

### 架构选型

| 数据类型 | 推荐 |
|---|---|
| 表格 | TabNet / FT-Transformer / 仍优先 XGBoost |
| 图像 | CNN（ResNet / EfficientNet） |
| 文本 | BERT / RoBERTa / fastText |
| 时序 | LSTM / Transformer / TCN |
| 图结构 | GCN / GAT / GraphSAGE |
| 多模态 | CLIP / 双塔 |

### 训练纪律

- **固定随机种子**（PyTorch 用 `torch.manual_seed` + cudnn deterministic）
- **早停**（监控验证 loss）
- **画 loss 曲线**（必须）
- **混合精度**（`torch.cuda.amp`，省显存）
- **学习率调度器**（CosineAnnealing / ReduceLROnPlateau）

```python
import torch
import torch.nn as nn
import pytorch_lightning as pl

class Classifier(pl.LightningModule):
    def __init__(self, in_dim, hidden=128, out=2, lr=1e-3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(hidden, hidden), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(hidden, out),
        )
        self.lr = lr
    def training_step(self, batch, _):
        x, y = batch
        loss = nn.functional.cross_entropy(self.net(x), y)
        self.log('train_loss', loss)
        return loss
    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self.lr)
```

---

## 5. 解释性（论文必备）

模型表现是一面，可解释是另一面。论文里**至少做一项**：

| 工具 | 用途 |
|---|---|
| 特征重要性（`feature_importances_`） | 树模型自带 |
| Permutation Importance | 任何模型，更鲁棒 |
| SHAP | 全局 + 局部解释（标准） |
| Partial Dependence Plot | 单特征边际效应 |
| LIME | 单样本局部解释 |
| Counterfactual | "怎么改输入能改变预测" |

```python
import shap
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# 全局 summary
shap.summary_plot(shap_values, X_test, feature_names=features)

# 单样本（force plot）
shap.force_plot(explainer.expected_value, shap_values[0], X_test.iloc[0])

# Permutation Importance（任何模型）
from sklearn.inspection import permutation_importance
result = permutation_importance(model, X_test, y_test, n_repeats=10, random_state=42)
```

---

## 6. 异常检测

| 算法 | 思路 | 适用 |
|---|---|---|
| Isolation Forest | 随机划分树，路径短 = 异常 | 高维、大样本 |
| LOF | 局部密度比 | 局部异常 |
| One-Class SVM | 学正常样本边界 | 小样本 |
| Autoencoder | 重构误差大 = 异常 | 复杂模式 |
| Robust Covariance | 椭圆包络 | 多元正态 |

```python
from sklearn.ensemble import IsolationForest
iso = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
labels = iso.fit_predict(X)
scores = -iso.score_samples(X)  # 越大越异常
```

---

## 7. 模型选择与超参调优

### 调参方法对比

| 方法 | 适用 | 备注 |
|---|---|---|
| GridSearchCV | 超参 ≤ 4 维 | 完整搜索 |
| RandomizedSearchCV | 超参多 | 给每个超参分布 |
| Optuna（TPE 贝叶斯） | 推荐 | 早停剪枝 |
| Hyperopt | 早期 TPE | 老牌 |
| HalvingGridSearchCV / HalvingRandomSearchCV | 超参多、训练贵 | sklearn ≥ 0.24 |

### Optuna 模板

```python
import optuna

def objective(trial):
    lr = trial.suggest_float('lr', 1e-3, 0.3, log=True)
    max_depth = trial.suggest_int('max_depth', 3, 10)
    n_est = trial.suggest_int('n_est', 100, 2000)
    m = xgb.XGBClassifier(learning_rate=lr, max_depth=max_depth, n_estimators=n_est,
                          early_stopping_rounds=50)
    m.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    return roc_auc_score(y_val, m.predict_proba(X_val)[:, 1])

study = optuna.create_study(direction='maximize',
                             pruner=optuna.pruners.MedianPruner())
study.optimize(objective, n_trials=100, n_jobs=-1)
print(study.best_params)
```

### 训练 / 验证 / 测试纪律

1. 切分**前**保存原始数据。
2. 时序必须按时间切，禁止 `shuffle`。
3. 仅用训练集做：归一化 fit、目标编码统计、特征选择。
4. 验证集选超参与早停。
5. **测试集只在论文最终一次使用**。

---

## 8. 评估指标速查

| 任务 | 指标 |
|---|---|
| 二分类（平衡） | Accuracy + AUC + F1 |
| 二分类（不平衡） | PR-AUC + F1 + Recall |
| 多分类 | Macro-F1 + 混淆矩阵 |
| 排序 | NDCG + MAP |
| 回归 | R² + RMSE + MAE + MAPE |
| 时序 | MAE + sMAPE + 与朴素法对比 |
| 异常检测 | PR-AUC + Top-k Precision |
| 聚类（外部） | ARI + NMI |
| 聚类（内部） | Silhouette + DB Index |

### 混淆矩阵衍生指标

```
TP / FN
FP / TN

Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 PR / (P + R)
Specificity = TN / (TN + FP)
NPV       = TN / (TN + FN)
MCC       = (TP·TN − FP·FN) / √[(TP+FP)(TP+FN)(TN+FP)(TN+FN)]
```

---

## 9. 模型选择决策树

```
有标签？
  否 → 聚类（K-Means / DBSCAN / GMM） + 异常检测
  是：
    特征数 < 100 + 解释性优先 → Logistic / 决策树
    解释性 + 性能折中 → RandomForest
    表格 SOTA → XGBoost / LightGBM
    图像 → CNN
    文本 → BERT / Logistic + TF-IDF
    时序 → 02 预测的 LSTM / ARIMA / Prophet
    图结构 → GCN / GAT
    类别极不平衡 → 加 class_weight 或 SMOTE 或 Focal Loss
    特征跨尺度大 → 必须 StandardScaler

样本 < 1000？
  优先简单模型 + 交叉验证 + Bootstrap 置信区间
样本 1000-100k？
  树模型为主
样本 > 100k？
  LightGBM 或考虑深度学习
```

---

## 10. 训练 → 部署的完整流程示例

```python
# 1. 切分（时序 / 分层）
from sklearn.model_selection import StratifiedKFold

# 2. Pipeline（防泄露）
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("select", SelectKBest(k=20)),
    ("clf", xgb.XGBClassifier(...)),
])

# 3. 调参（Optuna）

# 4. 评估（交叉验证 + 测试集）
from sklearn.model_selection import cross_val_score
scores = cross_val_score(pipe, X_train, y_train, cv=5, scoring='roc_auc')
print(f"CV AUC: {scores.mean():.4f} ± {scores.std():.4f}")

# 5. 测试集最终评估（仅 1 次）
pipe.fit(X_train, y_train)
test_auc = roc_auc_score(y_test, pipe.predict_proba(X_test)[:, 1])

# 6. 解释性（SHAP）

# 7. 持久化
import joblib
joblib.dump(pipe, 'model.pkl')
```

---

## 选型对照表

| 任务 | 首选 | 备选 |
|---|---|---|
| 表格分类 / 回归 | XGBoost / LightGBM | RandomForest |
| 解释性强 | Logistic / 决策树 | RuleFit |
| 文本 | TF-IDF + Logistic | BERT |
| 图像 | CNN（PyTorch） | TIMM 预训练 |
| 类别不平衡 | XGBoost + class_weight + 阈值调整 | SMOTE + sklearn |
| 可解释 | SHAP + Partial Dependence | LIME |
| 小样本 + 高维 | LASSO + 交叉验证 | XGBoost + 早停 |
| 异常检测 | Isolation Forest | LOF / Autoencoder |

## 关键文献

| 作者 | 题目 | 出处 | 年份 |
|---|---|---|---|
| Cortes, C. & Vapnik, V. | Support-Vector Networks | Machine Learning | 1995 |
| Breiman, L. | Random Forests | ML | 2001 |
| Chen, T. & Guestrin, C. | XGBoost | KDD | 2016 |
| Ke, G. et al. | LightGBM | NIPS | 2017 |
| Lundberg, S.M. & Lee, S.I. | A Unified Approach to Interpreting Model Predictions (SHAP) | NeurIPS | 2017 |
| Liu, F.T.; Ting, K.M.; Zhou, Z.H. | Isolation Forest | ICDM | 2008 |
| Akiba, T. et al. | Optuna | KDD | 2019 |

## 常见全栈错误

| ❌ 错误 | ✅ 正确 |
|---|---|
| Accuracy 报不平衡分类 | F1 / AUC / PR-AUC |
| SMOTE 在 CV 外做 | imblearn.pipeline 内做 |
| 表格直接上 MLP 不给 XGBoost 基线 | 必须有 XGBoost 对比 |
| 不做交叉验证 | 必做 ≥ 5 折 |
| 神经网络不画 loss | 必画训练 / 验证曲线 |
| 测试集多次使用 | 只用 1 次 |
| 只报点估计、无置信区间 | Bootstrap / CV 标准差 |
| 不做特征解释 | SHAP / Permutation 至少一项 |
| 时序数据用 train_test_split | TimeSeriesSplit |
| 高维下用 SVM RBF 大样本 | LinearSVC 或树模型 |
