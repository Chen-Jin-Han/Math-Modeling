from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


SUPPLEMENT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUPPLEMENT_DIR))

import appendix1_rotation_prediction as rotation
import appendix1_trajectory_filter as filtering
import appendix2_delay_compensation as compensation


class TrajectoryFilterTests(unittest.TestCase):
    def test_generation_is_reproducible_and_well_shaped(self) -> None:
        first = filtering.generate_trajectories(seed=7)
        second = filtering.generate_trajectories(seed=7)
        self.assertTrue(all(array.shape == (filtering.N, 2) for array in first))
        for left, right in zip(first, second):
            np.testing.assert_array_equal(left, right)

    def test_filter_and_global_fit_improve_measurements(self) -> None:
        _, noisy, ideal = filtering.generate_trajectories(seed=42)
        filtered = filtering.kalman_filter(noisy)
        fitted = filtering.fit_constant_velocity(noisy)
        noisy_rmse = filtering.position_rmse(ideal, noisy)
        self.assertLess(filtering.position_rmse(ideal, filtered), noisy_rmse)
        self.assertLess(filtering.position_rmse(ideal, fitted), noisy_rmse)

    def test_invalid_measurement_shape_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            filtering.kalman_filter(np.zeros((1, 2)))


class RotationPredictionTests(unittest.TestCase):
    def test_rotation_preserves_drag_range(self) -> None:
        true, _, ideal, alpha = rotation.generate_trajectories(seed=4)
        predicted = rotation.predict_rotated_trajectory(true, ideal, alpha)
        distances = np.linalg.norm(predicted - true, axis=1)
        np.testing.assert_allclose(distances, filtering.DRAG_RANGE, rtol=0.0, atol=1e-9)

    def test_zero_angle_returns_ideal_trajectory(self) -> None:
        true, _, ideal, alpha = rotation.generate_trajectories(seed=4, sigma_alpha_deg=0.0)
        predicted = rotation.predict_rotated_trajectory(true, ideal, alpha)
        np.testing.assert_allclose(predicted, ideal, rtol=0.0, atol=1e-10)


class DelayCompensationTests(unittest.TestCase):
    def test_delay_optimization_reduces_rmse(self) -> None:
        _, ideal, actual, optimized, delay = compensation.generate_trajectory(seed=42)
        actual_rmse, _, _ = compensation.calculate_metrics(ideal, actual)
        optimized_rmse, _, _ = compensation.calculate_metrics(ideal, optimized)
        self.assertLess(optimized_rmse, actual_rmse)
        self.assertTrue(np.all(delay >= 0.0))
        self.assertTrue(np.all(delay <= compensation.DELAY_SECONDS + 1e-15))

    def test_zero_angle_needs_no_adjustment(self) -> None:
        _, ideal, actual, optimized, delay = compensation.generate_trajectory(sigma_alpha_deg=0.0)
        np.testing.assert_allclose(actual, ideal, rtol=0.0, atol=1e-10)
        np.testing.assert_allclose(optimized, ideal, rtol=0.0, atol=1e-10)
        np.testing.assert_allclose(delay, compensation.DELAY_SECONDS, rtol=0.0, atol=1e-15)


if __name__ == "__main__":
    unittest.main()
