import pytest

from openevals.stats.bootstrap import bootstrap_ci


def test_ci_ordering():
    data = [0.8, 0.9, 0.7, 0.85, 0.75, 0.9]
    mean, lower, upper = bootstrap_ci(data, n_iterations=500)
    assert lower <= mean <= upper


def test_ci_bounds_in_range():
    data = [0.5, 0.6, 0.7, 0.8, 0.9]
    mean, lower, upper = bootstrap_ci(data)
    assert 0.0 <= lower <= 1.0
    assert 0.0 <= upper <= 1.0


def test_single_value():
    mean, lower, upper = bootstrap_ci([0.8])
    assert mean == pytest.approx(0.8, abs=1e-6)


def test_deterministic_with_seed():
    data = [0.1, 0.5, 0.9, 0.3, 0.7]
    r1 = bootstrap_ci(data, random_seed=42)
    r2 = bootstrap_ci(data, random_seed=42)
    assert r1 == r2
