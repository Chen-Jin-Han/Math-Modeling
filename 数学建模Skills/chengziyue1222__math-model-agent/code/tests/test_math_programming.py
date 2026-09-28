import numpy as np

from algorithms.math_programming import (
    goal_programming,
    integer_programming,
    linear_programming,
    nonlinear_programming,
)


def test_linear_programming_maximize():
    result = linear_programming(
        c=[3, 2],
        A_ub=[[1, 1]],
        b_ub=[4],
        bounds=[(0, 4), (0, 4)],
        maximize=True,
    )
    assert result["success"]
    assert np.isclose(result["fun"], 12.0)
    assert np.allclose(result["x"], [4.0, 0.0])


def test_integer_programming_respects_integrality():
    result = integer_programming(
        c=[3, 2],
        A_ub=[[2, 1]],
        b_ub=[4],
        bounds=[(0, 2), (0, 1)],
        maximize=True,
    )
    assert result["success"]
    assert np.allclose(result["x"], np.round(result["x"]))
    assert np.isclose(result["fun"], 6.0)


def test_goal_programming_hits_reachable_target():
    result = goal_programming(
        targets=[5],
        A=[[1]],
        bounds=[(0, 10)],
    )
    assert result["success"]
    assert np.allclose(result["x"], [5.0])
    assert np.isclose(result["total_deviation"], 0.0)


def test_nonlinear_programming_quadratic_minimum():
    result = nonlinear_programming(
        lambda x: (x[0] - 2.0) ** 2,
        x0=np.array([0.0]),
        bounds=[(-5, 5)],
    )
    assert result["success"]
    assert np.allclose(result["x"], [2.0], atol=1e-4)
    assert np.isclose(result["fun"], 0.0, atol=1e-8)
