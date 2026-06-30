import pytest
from openevals.stats.significance import welch_ttest


def test_large_significant_difference():
    a = [0.9, 0.88, 0.92, 0.87, 0.91] * 10
    b = [0.5, 0.48, 0.52, 0.47, 0.50] * 10
    result = welch_ttest(a, b)
    assert result["significant"]
    assert result["cohens_d"] > 0.8
    assert result["effect_size"] == "large"


def test_no_difference_not_significant():
    a = [0.80, 0.81, 0.79, 0.80, 0.80]
    b = [0.80, 0.80, 0.80, 0.81, 0.79]
    result = welch_ttest(a, b)
    assert not result["significant"]


def test_result_has_required_keys():
    result = welch_ttest([0.5] * 5, [0.6] * 5)
    for key in ["t_statistic", "p_value", "significant", "cohens_d", "effect_size", "mean_a", "mean_b", "difference"]:
        assert key in result
