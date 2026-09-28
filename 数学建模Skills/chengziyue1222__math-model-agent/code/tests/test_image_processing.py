"""图像处理模块测试"""
import numpy as np
import pytest
from algorithms.image_processing import (
    noise_filter,
    edge_detection,
    image_segmentation,
    histogram_analysis,
    histogram_equalization,
    feature_extraction,
)


@pytest.fixture
def test_image():
    """生成测试图像：左黑右白"""
    img = np.zeros((100, 100), dtype=np.uint8)
    img[:, 50:] = 255
    return img


@pytest.fixture
def gradient_image():
    """渐变图像"""
    return np.tile(np.linspace(0, 255, 256, dtype=np.uint8), (256, 1))


class TestNoiseFilter:
    """噪声滤波测试"""

    def test_gaussian_filter(self, test_image):
        result = noise_filter(test_image, method='gaussian', kernel_size=3)
        assert result.shape == test_image.shape

    def test_median_filter(self, test_image):
        result = noise_filter(test_image, method='median', kernel_size=3)
        assert result.shape == test_image.shape

    def test_preserves_shape(self, test_image):
        for method in ['gaussian', 'median', 'mean']:
            result = noise_filter(test_image, method=method)
            assert result.shape == test_image.shape


class TestEdgeDetection:
    """边缘检测测试"""

    def test_sobel(self, test_image):
        edges = edge_detection(test_image, method='sobel')
        assert edges.shape == test_image.shape
        # 垂直边缘应出现在 x=50 附近
        assert np.max(edges[:, 48:52]) > 0

    def test_canny(self, test_image):
        edges = edge_detection(test_image, method='canny')
        assert edges.shape == test_image.shape

    def test_laplacian(self, test_image):
        edges = edge_detection(test_image, method='laplacian')
        assert edges.shape == test_image.shape

    def test_no_edge_on_uniform(self):
        """均匀图像应无边缘"""
        uniform = np.ones((50, 50), dtype=np.uint8) * 128
        edges = edge_detection(uniform, method='sobel')
        assert np.max(edges) < 1e-5

    @pytest.mark.parametrize('method', ['sobel', 'prewitt', 'roberts'])
    def test_mirrored_gradient_has_same_edge_count(self, gradient_image, method):
        ascending = edge_detection(gradient_image, method=method, threshold=0.3)
        descending = edge_detection(np.fliplr(gradient_image), method=method, threshold=0.3)

        assert np.count_nonzero(ascending) == np.count_nonzero(descending)


class TestImageSegmentation:
    """图像分割测试"""

    def test_otsu(self, test_image):
        result = image_segmentation(test_image, method='otsu')
        assert result.shape == test_image.shape
        # 应该分成两类
        unique = np.unique(result)
        assert len(unique) <= 2

    def test_kmeans(self, test_image):
        result = image_segmentation(test_image, method='kmeans', n_clusters=2)
        assert result.shape == test_image.shape


class TestHistogramAnalysis:
    """直方图分析测试"""

    def test_returns_all_fields(self, test_image):
        result = histogram_analysis(test_image)
        assert 'histogram' in result
        assert 'mean' in result
        assert 'std' in result

    def test_uniform_image(self):
        """均匀图像标准差应接近0"""
        uniform = np.ones((50, 50), dtype=np.uint8) * 128
        result = histogram_analysis(uniform)
        assert result['std'] < 1.0


class TestHistogramEqualization:
    """直方图均衡化测试"""

    def test_improves_contrast(self, gradient_image):
        eq = histogram_equalization(gradient_image)
        # 均衡化后标准差应更大（对比度增强）
        assert np.std(eq) >= np.std(gradient_image) - 1

    def test_preserves_shape(self, test_image):
        result = histogram_equalization(test_image)
        assert result.shape == test_image.shape


class TestFeatureExtraction:
    """特征提取测试"""

    def test_hu_moments(self, test_image):
        result = feature_extraction(test_image)
        assert 'hu_moments' in result
        assert len(result['hu_moments']) == 7

    def test_texture_features(self, test_image):
        result = feature_extraction(test_image)
        assert 'texture' in result
        assert 'contrast' in result['texture']
