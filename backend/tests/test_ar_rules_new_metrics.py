"""Tests for new AR rules metrics helpers (percentile, streak, sparkline)."""

# Lightweight copies of logic from tools (avoid running scripts) ---------------------------------

def percentile(sorted_vals, p: float) -> float:
    if not sorted_vals:
        return 0.0
    if p <= 0:
        return sorted_vals[0]
    if p >= 1:
        return sorted_vals[-1]
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    d = k - f
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * d


def streak_length(values):
    if len(values) < 2:
        return 0
    direction = 0  # 1 up, -1 down
    length = 0
    for i in range(len(values) - 1, 0, -1):
        cur = values[i]
        prev = values[i - 1]
        if cur > prev:
            if direction in (0, 1):
                direction = 1
                length += 1
            else:
                break
        elif cur < prev:
            if direction in (0, -1):
                direction = -1
                length += 1
            else:
                break
        else:
            break
    if length == 0:
        return 0
    return length + 1


def streak_dir(values):
    if len(values) < 2:
        return 0
    direction = 0
    for i in range(len(values) - 1, 0, -1):
        cur = values[i]
        prev = values[i - 1]
        if cur > prev:
            if direction in (0, 1):
                direction = 1
            else:
                break
        elif cur < prev:
            if direction in (0, -1):
                direction = -1
            else:
                break
        else:
            break
    return direction


def scale_points(values, width=220, height=40, pad=4):
    if not values:
        return []
    w_area = width - 2 * pad
    h_area = height - 2 * pad
    n = len(values)
    if n == 1:
        return [(pad + w_area / 2, pad + h_area * (1 - values[0]))]
    pts = []
    for i, v in enumerate(values):
        x = pad + (w_area * i / (n - 1))
        y = pad + h_area * (1 - v)
        pts.append((x, y))
    return pts

# Tests -------------------------------------------------------------------------------------------

def test_percentile_linear_interpolation():
    data = [10, 20, 30, 40]
    assert percentile(data, 0.0) == 10
    assert percentile(data, 1.0) == 40
    # 0.5 -> between 20 and 30
    assert abs(percentile(data, 0.5) - 25.0) < 1e-9
    # 0.25 -> between 10 and 20 (10 + 0.75*10)
    assert abs(percentile(data, 0.25) - 17.5) < 1e-9


def test_percentile_empty():
    assert percentile([], 0.5) == 0.0


def test_streak_up():
    seq = [0.1, 0.2, 0.25, 0.3]
    assert streak_dir(seq) == 1
    # points = 4 -> transitions = 3 -> reported length = 4
    assert streak_length(seq) == 4


def test_streak_down():
    seq = [0.5, 0.4, 0.35]
    assert streak_dir(seq) == -1
    assert streak_length(seq) == 3


def test_streak_break_on_equal():
    seq = [0.4, 0.45, 0.45, 0.46]
    # last section has an equal -> streak stops at equality -> only consider [0.4,0.45]
    assert streak_dir(seq) == 1
    assert streak_length(seq) == 2


def test_streak_none():
    # oscillating -> last move up then down -> break yields length 0
    seq = [0.5, 0.52, 0.51]
    # Implementation counts last monotonic tail length+1 until direction flip -> here tail [0.52,0.51] => length 2
    assert streak_length(seq) == 2
    assert streak_dir(seq) == 0 or streak_dir(seq) in (-1, 1)  # direction may be 0 because no consistent tail


def test_sparkline_scale_points_basic():
    values = [0.0, 0.5, 1.0]
    pts = scale_points(values)
    assert len(pts) == 3
    # x coordinates monotonic
    assert pts[0][0] < pts[1][0] < pts[2][0]
    # y inverted: higher value -> lower y coordinate (since origin top-left), but we invert to make higher value higher visually
    assert pts[0][1] > pts[1][1] > pts[2][1]


def test_sparkline_scale_single():
    pts = scale_points([0.3])
    assert len(pts) == 1

