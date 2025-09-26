from metrics_utils import percentile, histogram


def test_percentile_basic_cases():
    data = [1.0, 2.0, 3.0, 4.0]
    assert percentile([], 0.5) == 0.0
    assert percentile(data, 0) == 1.0
    assert percentile(data, 1) == 4.0
    # Median linear interpolation (even count)
    mid = percentile(data, 0.5)
    assert 2.4 < mid < 2.6
    p95 = percentile(data, 0.95)
    assert p95 <= 4.0


def test_percentile_monotonic():
    import random
    vals = sorted(random.random() for _ in range(50))
    last = -1.0
    for q in [i/20 for i in range(21)]:
        v = percentile(vals, q)
        assert last <= v <= vals[-1]
        last = v


def test_histogram_cumulative():
    values = [0.5, 0.7, 1.1, 1.5]
    buckets = [0.5, 1.0, 2.0]
    hist = histogram(values, buckets)
    # Ensure +inf bucket appended
    assert hist[-1][0] == float('inf')
    # Cumulative counts expectation
    assert hist[0][1] == 1  # <=0.5
    assert hist[1][1] == 2  # <=1.0
    assert hist[2][1] == 4  # <=2.0
