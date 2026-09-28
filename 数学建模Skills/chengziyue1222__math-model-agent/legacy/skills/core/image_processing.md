---
name: image_processing
description: 图像处理 — 边缘检测、图像分割、形态学操作、特征提取
---

# 图像处理

> 来源: zhanwen/MathModel 十类算法之一

## 决策规则

```text
IF 问题涉及图像分析 / 遥感数据 / 医学图像 / 计算机视觉 / 目标识别
THEN
  模型: image_processing
  方法: 根据任务类型选择
ELSE
  继续判断
```

## 方法选择

| 任务 | 方法 | 代码入口 |
|------|------|----------|
| 图像去噪 | `noise_filter` | `algorithms.image_processing` |
| 边缘检测 | `edge_detection` | `algorithms.image_processing` |
| 目标分割 | `image_segmentation` | `algorithms.image_processing` |
| 形态学处理 | `morphological_ops` | `algorithms.image_processing` |
| 直方图分析 | `histogram_analysis` / `histogram_equalization` | `algorithms.image_processing` |
| 特征提取 | `feature_extraction` | `algorithms.image_processing` |

## 使用模板

### 边缘检测

```python
from algorithms.image_processing import edge_detection
import cv2

img = cv2.imread('image.jpg')
edges = edge_detection(img, method='canny', threshold=0.2)
```

### 图像分割

```python
from algorithms.image_processing import image_segmentation

# OTSU自动阈值分割
binary = image_segmentation(img, method='otsu')

# K-means聚类分割
labels = image_segmentation(img, method='kmeans', n_clusters=3)
```

### 图像去噪

```python
from algorithms.image_processing import noise_filter

# 高斯滤波
denoised = noise_filter(img, method='gaussian', kernel_size=5, sigma=1.4)

# 中值滤波 (去除椒盐噪声)
denoised = noise_filter(img, method='median', kernel_size=3)
```

### 特征提取

```python
from algorithms.image_processing import feature_extraction

features = feature_extraction(img)
print(f"Hu矩: {features['hu_moments']}")
print(f"纹理对比度: {features['texture']['contrast']}")
```

### 形态学操作

```python
from algorithms.image_processing import morphological_ops

# 开运算: 去除小噪点
cleaned = morphological_ops(binary, operation='open', kernel_size=3)

# 闭运算: 填充小孔洞
filled = morphological_ops(binary, operation='close', kernel_size=5)
```

## 常见竞赛应用

### 遥感图像分类

1. 图像预处理: `noise_filter` 去噪
2. 特征提取: `feature_extraction` 提取纹理特征
3. 分割: `image_segmentation` 区域划分
4. 分类: 配合 `neural_network` 或 `metaheuristic`

### 医学图像处理

1. 增强: `histogram_equalization` 提升对比度
2. 去噪: `noise_filter(method='bilateral')` 保边去噪
3. 分割: `image_segmentation(method='otsu')` 提取目标区域
4. 形态学: `morphological_ops(operation='close')` 平滑边界

### 交通标志识别

1. 预处理: `noise_filter` + `histogram_equalization`
2. 边缘检测: `edge_detection(method='canny')`
3. 形态学: `morphological_ops` 提取连通区域
4. 特征提取: `feature_extraction` 的 Hu矩用于形状匹配

## 边缘检测方法对比

| 方法 | 特点 | 适用场景 |
|------|------|----------|
| Sobel | 一阶导数，计算快 | 一般边缘检测 |
| Roberts | 对角线敏感 | 细节丰富图像 |
| Prewitt | 均匀权重 | 噪声较多图像 |
| Laplacian | 二阶导数，各向同性 | 精细边缘 |
| Canny | 多级处理，最优检测 | 高质量边缘 |

## 分割方法对比

| 方法 | 特点 | 适用场景 |
|------|------|----------|
| OTSU | 自动阈值，快速 | 双峰分布图像 |
| K-means | 聚类分割 | 多类目标 |
| Watershed | 分水岭，适合粘连目标 | 细胞、颗粒等 |
