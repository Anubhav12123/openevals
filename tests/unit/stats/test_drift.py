from openevals.stats.drift import detect_distributional_shift


def test_identical_distributions_no_shift():
    data = [0.8, 0.7, 0.9, 0.75, 0.85] * 20
    result = detect_distributional_shift(data, data)
    assert not result["shift_detected"]
    assert result["psi"] < 0.1


def test_shifted_distributions_detected():
    ref = [0.9, 0.85, 0.92, 0.88] * 25
    cur = [0.4, 0.35, 0.42, 0.38] * 25
    result = detect_distributional_shift(ref, cur)
    assert result["shift_detected"]
    assert result["mean_shift"] < -0.4


def test_result_has_required_keys():
    result = detect_distributional_shift([0.5] * 10, [0.6] * 10)
    for key in [
        "shift_detected",
        "ks_statistic",
        "p_value",
        "psi",
        "severity",
        "reference_mean",
        "current_mean",
        "mean_shift",
    ]:
        assert key in result
