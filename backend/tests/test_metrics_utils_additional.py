from metrics_utils import compute_latency_summary, percentile


def test_p95_monotonic_adjustment_skewed():
    # Need raw p95 below average. To do this make 96% extremely small, 4% huge.
    # With 100 samples: p95 index ~ 94.05 -> still small, while average lifted by outliers.
    small = [0.001] * 96
    big = [10.0] * 4
    values = small + big
    srt = sorted(values)
    raw_p95 = percentile(srt, 0.95)
    avg = sum(values) / len(values)
    assert raw_p95 < avg  # precondition for adjustment
    res = compute_latency_summary(values, buckets=[0.01, 0.1, 1, 5, 10], slo_p95=0)
    s = res["summary"]
    # Adjustment ensures p95 not below avg
    assert s["p95"] >= avg
    # And monotonic with p99
    assert s["p99"] >= s["p95"]


def test_slo_violation_boundary_inclusive():
    values = [0.1, 0.2, 0.3]
    threshold = 0.2
    res = compute_latency_summary(values, buckets=[0.1, 0.2, 0.3], slo_p95=threshold)
    # Only values strictly greater than slo_p95 count; exact threshold should not
    # 0.3 is the only violation
    assert res["violations"] == 1
    # p95 above threshold but that's unrelated to counting rule
    assert res["summary"]["p95"] >= threshold
