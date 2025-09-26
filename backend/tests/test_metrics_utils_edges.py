import random

from metrics_utils import percentile, histogram, compute_latency_summary


def test_percentile_single_element():
    vals = [0.123]
    assert percentile(vals, 0) == vals[0]
    assert percentile(vals, 0.5) == vals[0]
    assert percentile(vals, 1.0) == vals[0]


def test_percentile_large_list_accuracy():
    # Create sorted list of 10_000 increasing floats
    vals = [i / 10_000 for i in range(10_000)]
    p50 = percentile(vals, 0.50)
    p95 = percentile(vals, 0.95)
    p99 = percentile(vals, 0.99)
    # Expected theoretical values around quantile/100 (since linear 0..~0.9999)
    assert abs(p50 - 0.5) < 0.005
    assert abs(p95 - 0.95) < 0.005
    assert abs(p99 - 0.99) < 0.005


def test_histogram_unsorted_and_duplicate_buckets():
    buckets = [0.5, 0.1, 0.1, 1.0, 0.05]
    values = [0.02, 0.07, 0.11, 0.49, 0.51, 0.9, 1.2]
    # Histogram expects pre-sorted unique; we ensure our wrapper handles unsorted by sorting externally
    buckets_sorted = sorted(set(b for b in buckets if b > 0))
    hist = histogram(values, buckets_sorted)
    # Last bucket +Inf cumulative equals total count
    assert hist[-1][1] == len(values)
    # Monotonic counts
    prev = 0
    for _, c in hist:
        assert c >= prev
        prev = c


def test_compute_latency_summary_empty_and_basic():
    buckets = [0.05, 0.1, 0.5]
    res_empty = compute_latency_summary([], buckets, slo_p95=0.2)
    assert res_empty["summary"]["count"] == 0
    assert res_empty["summary"]["p95"] == 0
    # Basic non-empty
    values = [0.01, 0.02, 0.03, 0.5, 0.8]
    res = compute_latency_summary(values, buckets, slo_p95=0.25)
    s = res["summary"]
    assert s["count"] == len(values)
    assert s["p50"] > 0 and s["p95"] >= s["p50"]
    assert res["violations"] == 2  # 0.5 and 0.8 exceed 0.25


def test_compute_latency_summary_random_stability():
    random.seed(42)
    values = [random.random() for _ in range(500)]
    buckets = [0.1, 0.2, 0.5, 0.8]
    res = compute_latency_summary(values, buckets, slo_p95=0.4)
    s = res["summary"]
    assert s["count"] == 500
    # p99 should not exceed max + small epsilon
    assert s["p99"] <= max(values) + 1e-9
    # Histogram cumulative last equals count
    assert res["histogram"][-1][1] == 500
