"""
图像处理 (Image Processing)
============================
边缘检测、图像分割、特征提取、形态学操作、噪声滤波。

包含函数:
- edge_detection: 边缘检测 (Sobel/Canny/Roberts/Prewitt)
- image_segmentation: 图像分割 (阈值/K-means/分水岭)
- morphological_ops: 形态学操作 (膨胀/腐蚀/开运算/闭运算)
- histogram_analysis: 直方图分析与增强
- histogram_equalization: 直方图均衡化
- feature_extraction: 图像特征提取 (纹理/形状/Hu矩)
- noise_filter: 噪声滤波 (均值/中值/高斯/双边)

竞赛场景:
- 遥感图像分析、医学影像处理
- 图像去噪、边缘检测、目标分割
- 纹理特征提取用于分类

参考: Algorithms_MathModels/MATLAB图像处理源文件/
"""

from __future__ import annotations

import numpy as np


# ========== 基础操作 ==========

def _to_gray(image: np.ndarray) -> np.ndarray:
    """将图像转换为灰度图"""
    if image.ndim == 3:
        return np.dot(image[..., :3], [0.299, 0.587, 0.114]).astype(np.float64)
    return image.astype(np.float64)


def _normalize(image: np.ndarray) -> np.ndarray:
    """归一化到 [0, 255]"""
    img = image.astype(np.float64)
    img = img - img.min()
    if img.max() > 0:
        img = img / img.max() * 255
    return img.astype(np.uint8)


def _normalize_unit(values: np.ndarray) -> np.ndarray:
    """Safely scale a response magnitude to [0, 1]."""
    values = np.asarray(values, dtype=np.float64)
    scale = np.max(np.abs(values))
    if scale == 0 or not np.isfinite(scale):
        return np.zeros_like(values)
    return values / scale


# ========== 噪声滤波 ==========

def noise_filter(
    image: np.ndarray,
    method: str = "gaussian",
    kernel_size: int = 3,
    sigma: float = 1.0,
) -> np.ndarray:
    """图像噪声滤波

    Args:
        image: 输入图像 (灰度或RGB)
        method: 滤波方法 'mean'/'median'/'gaussian'/'bilateral'
        kernel_size: 核大小 (奇数)
        sigma: 高斯核标准差

    Returns:
        滤波后的图像
    """
    gray = _to_gray(image)
    pad = kernel_size // 2

    if method == "mean":
        kernel = np.ones((kernel_size, kernel_size)) / (kernel_size**2)
        return _convolve2d(gray, kernel)

    elif method == "gaussian":
        ax = np.arange(-pad, pad + 1)
        xx, yy = np.meshgrid(ax, ax)
        kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
        kernel /= kernel.sum()
        return _convolve2d(gray, kernel)

    elif method == "median":
        padded = np.pad(gray, pad, mode='edge')
        result = np.zeros_like(gray)
        for i in range(gray.shape[0]):
            for j in range(gray.shape[1]):
                region = padded[i:i+kernel_size, j:j+kernel_size]
                result[i, j] = np.median(region)
        return result.astype(np.uint8)

    elif method == "bilateral":
        # 简化版双边滤波
        padded = np.pad(gray, pad, mode='edge')
        result = np.zeros_like(gray)
        for i in range(gray.shape[0]):
            for j in range(gray.shape[1]):
                region = padded[i:i+kernel_size, j:j+kernel_size]
                center = padded[i+pad, j+pad]
                spatial = np.exp(-((np.arange(kernel_size) - pad)**2).sum() / (2*sigma**2))
                intensity = np.exp(-(region - center)**2 / (2*sigma**2))
                weight = spatial * intensity
                result[i, j] = np.sum(region * weight) / weight.sum()
        return result.astype(np.uint8)

    else:
        raise ValueError(f"未知滤波方法: {method}")


def _convolve2d(
    image: np.ndarray, kernel: np.ndarray, *, normalize_output: bool = True
) -> np.ndarray:
    """2D卷积"""
    kh, kw = kernel.shape
    pad_h, pad_w = kh // 2, kw // 2
    padded = np.pad(image, ((pad_h, pad_h), (pad_w, pad_w)), mode='edge')
    result = np.zeros_like(image)
    for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            region = padded[i:i+kh, j:j+kw]
            result[i, j] = np.sum(region * kernel)
    return _normalize(result) if normalize_output else result


# ========== 边缘检测 ==========

def edge_detection(
    image: np.ndarray,
    method: str = "sobel",
    threshold: float = 0.3,
) -> np.ndarray:
    """边缘检测

    Args:
        image: 输入图像
        method: 'sobel'/'roberts'/'prewitt'/'laplacian'/'canny'
        threshold: 阈值比例 (0-1)

    Returns:
        边缘图像

    Examples:
        >>> edges = edge_detection(img, method='sobel', threshold=0.2)
    """
    gray = _to_gray(image)

    if method == "sobel":
        gx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=float)
        gy = gx.T
        ex = _convolve2d(gray, gx, normalize_output=False)
        ey = _convolve2d(gray, gy, normalize_output=False)
        magnitude = np.sqrt(ex.astype(float)**2 + ey.astype(float)**2)
        magnitude = _normalize_unit(magnitude)

    elif method == "roberts":
        gx = np.array([[1, 0], [0, -1]], dtype=float)
        gy = np.array([[0, 1], [-1, 0]], dtype=float)
        ex = _convolve2d(gray, gx, normalize_output=False)
        ey = _convolve2d(gray, gy, normalize_output=False)
        magnitude = np.sqrt(ex.astype(float)**2 + ey.astype(float)**2)
        magnitude = _normalize_unit(magnitude)

    elif method == "prewitt":
        gx = np.array([[-1, 0, 1], [-1, 0, 1], [-1, 0, 1]], dtype=float)
        gy = gx.T
        ex = _convolve2d(gray, gx, normalize_output=False)
        ey = _convolve2d(gray, gy, normalize_output=False)
        magnitude = np.sqrt(ex.astype(float)**2 + ey.astype(float)**2)
        magnitude = _normalize_unit(magnitude)

    elif method == "laplacian":
        kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=float)
        magnitude = _convolve2d(gray, kernel, normalize_output=False)
        magnitude = _normalize_unit(np.abs(magnitude))

    elif method == "canny":
        # 简化版Canny：高斯平滑 + Sobel + 非极大值抑制 + 双阈值
        blurred = noise_filter(gray, method='gaussian', kernel_size=5, sigma=1.4)
        gx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=float)
        gy = gx.T
        ex = _convolve2d(blurred, gx, normalize_output=False)
        ey = _convolve2d(blurred, gy, normalize_output=False)
        magnitude = np.sqrt(ex**2 + ey**2)
        magnitude = _normalize_unit(magnitude)

        # 非极大值抑制 (简化版)
        angle = np.arctan2(ey, ex) * 180 / np.pi
        angle[angle < 0] += 180
        suppressed = np.zeros_like(magnitude)

        for i in range(1, magnitude.shape[0] - 1):
            for j in range(1, magnitude.shape[1] - 1):
                a = angle[i, j]
                if (0 <= a < 22.5) or (157.5 <= a <= 180):
                    neighbors = [magnitude[i, j-1], magnitude[i, j+1]]
                elif 22.5 <= a < 67.5:
                    neighbors = [magnitude[i-1, j+1], magnitude[i+1, j-1]]
                elif 67.5 <= a < 112.5:
                    neighbors = [magnitude[i-1, j], magnitude[i+1, j]]
                else:
                    neighbors = [magnitude[i-1, j-1], magnitude[i+1, j+1]]
                if magnitude[i, j] >= max(neighbors):
                    suppressed[i, j] = magnitude[i, j]

        magnitude = suppressed

    else:
        raise ValueError(f"未知边缘检测方法: {method}")

    # 阈值化
    edges = (magnitude > threshold).astype(np.uint8) * 255
    return edges


# ========== 图像分割 ==========

def image_segmentation(
    image: np.ndarray,
    method: str = "otsu",
    n_clusters: int = 2,
) -> np.ndarray:
    """图像分割

    Args:
        image: 输入图像
        method: 'otsu'/'kmeans'/'watershed'
        n_clusters: 聚类数 (K-means)

    Returns:
        分割后的标签图像
    """
    gray = _to_gray(image)

    if method == "otsu":
        # OTSU阈值分割
        hist, bins = np.histogram(gray.ravel(), 256, [0, 256])
        total = gray.size
        sum_total = np.sum(np.arange(256) * hist)

        sum_bg = 0.0
        w_bg = 0
        max_variance = 0
        best_threshold = 0

        for t in range(256):
            w_bg += hist[t]
            if w_bg == 0:
                continue
            w_fg = total - w_bg
            if w_fg == 0:
                break

            sum_bg += t * hist[t]
            mean_bg = sum_bg / w_bg
            mean_fg = (sum_total - sum_bg) / w_fg

            variance = w_bg * w_fg * (mean_bg - mean_fg) ** 2
            if variance > max_variance:
                max_variance = variance
                best_threshold = t

        return (gray > best_threshold).astype(np.uint8)

    elif method == "kmeans":
        # K-means聚类分割
        pixels = gray.ravel().astype(np.float64)
        # 初始化聚类中心
        centers = np.linspace(pixels.min(), pixels.max(), n_clusters)

        for _ in range(20):
            # 分配
            distances = np.abs(pixels[:, None] - centers[None, :])
            labels = np.argmin(distances, axis=1)
            # 更新
            new_centers = np.array([pixels[labels == k].mean() if np.sum(labels == k) > 0
                                    else centers[k] for k in range(n_clusters)])
            if np.allclose(centers, new_centers, atol=1e-6):
                break
            centers = new_centers

        return labels.reshape(gray.shape).astype(np.uint8)

    elif method == "watershed":
        # 简化版分水岭
        from scipy import ndimage
        binary = image_segmentation(image, method="otsu")
        distance = ndimage.distance_transform_edt(binary)
        # 标记连通区域
        markers, _ = ndimage.label(distance > distance.max() * 0.5)
        return markers.astype(np.int32)

    else:
        raise ValueError(f"未知分割方法: {method}")


# ========== 形态学操作 ==========

def morphological_ops(
    image: np.ndarray,
    operation: str = "dilate",
    kernel_size: int = 3,
    iterations: int = 1,
) -> np.ndarray:
    """形态学操作

    Args:
        image: 二值图像
        operation: 'dilate'/'erode'/'open'/'close'
        kernel_size: 结构元素大小
        iterations: 迭代次数

    Returns:
        处理后的图像
    """
    binary = (image > 0).astype(np.uint8)
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    pad = kernel_size // 2

    for _ in range(iterations):
        if operation == "dilate":
            padded = np.pad(binary, pad, mode='constant', constant_values=0)
            result = np.zeros_like(binary)
            for i in range(binary.shape[0]):
                for j in range(binary.shape[1]):
                    region = padded[i:i+kernel_size, j:j+kernel_size]
                    result[i, j] = np.any(region & kernel).astype(np.uint8)
            binary = result

        elif operation == "erode":
            padded = np.pad(binary, pad, mode='constant', constant_values=1)
            result = np.zeros_like(binary)
            for i in range(binary.shape[0]):
                for j in range(binary.shape[1]):
                    region = padded[i:i+kernel_size, j:j+kernel_size]
                    result[i, j] = np.all(region | (1 - kernel)).astype(np.uint8)
            binary = result

        elif operation == "open":
            binary = morphological_ops(binary, "erode", kernel_size, 1)
            binary = morphological_ops(binary, "dilate", kernel_size, 1)
            return binary

        elif operation == "close":
            binary = morphological_ops(binary, "dilate", kernel_size, 1)
            binary = morphological_ops(binary, "erode", kernel_size, 1)
            return binary

    return binary * 255


# ========== 直方图分析 ==========

def histogram_analysis(image: np.ndarray) -> dict:
    """直方图分析

    Args:
        image: 输入图像

    Returns:
        字典包含直方图、统计量、熵等
    """
    gray = _to_gray(image).astype(np.uint8)
    hist, _ = np.histogram(gray.ravel(), 256, [0, 256])
    prob = hist / hist.sum()

    # 熵
    prob_nonzero = prob[prob > 0]
    entropy = -np.sum(prob_nonzero * np.log2(prob_nonzero))

    return {
        "histogram": hist,
        "probability": prob,
        "mean": float(gray.mean()),
        "std": float(gray.std()),
        "median": float(np.median(gray)),
        "entropy": float(entropy),
        "min": int(gray.min()),
        "max": int(gray.max()),
    }


def histogram_equalization(image: np.ndarray) -> np.ndarray:
    """直方图均衡化

    Args:
        image: 输入图像

    Returns:
        均衡化后的图像
    """
    gray = _to_gray(image).astype(np.uint8)
    hist, _ = np.histogram(gray.ravel(), 256, [0, 256])

    # 累积分布函数
    cdf = hist.cumsum()
    cdf_min = cdf[cdf > 0].min()
    total = gray.size

    # 映射
    lut = ((cdf - cdf_min) / (total - cdf_min) * 255).clip(0, 255).astype(np.uint8)
    return lut[gray]


# ========== 特征提取 ==========

def feature_extraction(image: np.ndarray) -> dict:
    """图像特征提取

    Args:
        image: 输入图像

    Returns:
        字典包含几何矩、Hu矩、纹理特征等
    """
    gray = _to_gray(image).astype(np.float64)
    rows, cols = gray.shape

    # 几何矩
    y, x = np.mgrid[0:rows, 0:cols]
    m00 = gray.sum()
    m10 = (x * gray).sum()
    m01 = (y * gray).sum()

    if m00 == 0:
        return {"error": "空白图像"}

    cx = m10 / m00
    cy = m01 / m00

    # 中心矩
    def central_moment(p, q):
        return ((x - cx)**p * (y - cy)**q * gray).sum()

    mu20 = central_moment(2, 0)
    mu02 = central_moment(0, 2)
    mu11 = central_moment(1, 1)
    # 归一化中心矩
    def eta(p, q):
        return central_moment(p, q) / (m00 ** (1 + (p + q) / 2))

    # Hu矩
    h1 = eta(2, 0) + eta(0, 2)
    h2 = (eta(2, 0) - eta(0, 2))**2 + 4 * eta(1, 1)**2
    h3 = (eta(3, 0) - 3*eta(1, 2))**2 + (3*eta(2, 1) - eta(0, 3))**2
    h4 = (eta(3, 0) + eta(1, 2))**2 + (eta(2, 1) + eta(0, 3))**2
    h5 = (eta(3, 0) - 3*eta(1, 2)) * (eta(3, 0) + eta(1, 2)) * \
         ((eta(3, 0) + eta(1, 2))**2 - 3*(eta(2, 1) + eta(0, 3))**2) + \
         (3*eta(2, 1) - eta(0, 3)) * (eta(2, 1) + eta(0, 3)) * \
         (3*(eta(3, 0) + eta(1, 2))**2 - (eta(2, 1) + eta(0, 3))**2)
    h6 = (eta(3, 0) + eta(1, 2)) * ((eta(3, 0) + eta(1, 2))**2 - 3*(eta(2, 1) + eta(0, 3))**2) + \
         (eta(0, 3) - 3*eta(2, 1)) * (eta(2, 1) + eta(0, 3)) * \
         (3*(eta(3, 0) + eta(1, 2))**2 - (eta(2, 1) + eta(0, 3))**2)
    h7 = (3*eta(2, 1) - eta(0, 3)) * (eta(3, 0) + eta(1, 2)) * \
         ((eta(3, 0) + eta(1, 2))**2 - (eta(2, 1) + eta(0, 3))**2) + \
         (eta(3, 0) - 3*eta(1, 2)) * (eta(2, 1) + eta(0, 3)) * \
         (3*(eta(3, 0) + eta(1, 2))**2 - (eta(2, 1) + eta(0, 3))**2)

    # 纹理特征 (灰度共生矩阵简化版)
    glcm = np.zeros((16, 16), dtype=np.int32)
    quantized = (gray / 16).astype(np.int32).clip(0, 15)
    for i in range(rows):
        for j in range(cols - 1):
            glcm[quantized[i, j], quantized[i, j+1]] += 1

    glcm = glcm / glcm.sum() if glcm.sum() > 0 else glcm

    # 纹理统计量
    i_idx, j_idx = np.meshgrid(np.arange(16), np.arange(16), indexing='ij')
    contrast = np.sum(glcm * (i_idx - j_idx)**2)
    energy = np.sum(glcm**2)
    glcm_prob = glcm[glcm > 0]
    entropy = -np.sum(glcm_prob * np.log2(glcm_prob)) if glcm_prob.size > 0 else 0

    return {
        "area": float(m00),
        "centroid": (float(cx), float(cy)),
        "central_moments": {
            "mu20": float(mu20), "mu02": float(mu02), "mu11": float(mu11),
        },
        "hu_moments": [float(h1), float(h2), float(h3), float(h4),
                       float(h5), float(h6), float(h7)],
        "texture": {
            "contrast": float(contrast),
            "energy": float(energy),
            "entropy": float(entropy),
        },
    }
