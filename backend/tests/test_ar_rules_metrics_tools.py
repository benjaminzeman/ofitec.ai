import math


# Reusar funciones copiando implementaciones ligeras (evita import ejecución de scripts main)

def wma(values):
    if not values:
        return 0.0
    weights = list(range(1, len(values) + 1))
    total_w = sum(weights)
    return sum(v * w for v, w in zip(values, weights)) / total_w


def aggregate(rows):
    if not rows:
        return {
            'window_size': 0,
            'rows': 0,
            'assign_min': None,
            'assign_max': None,
            'assign_avg': None,
            'coverage_min': None,
            'coverage_max': None,
            'coverage_avg': None,
        }
    assigns = [r[0] for r in rows]
    covs = [r[1] for r in rows]
    return {
        'window_size': len(rows),
        'rows': len(rows),
        'assign_min': min(assigns),
        'assign_max': max(assigns),
        'assign_avg': sum(assigns)/len(assigns),
        'coverage_min': min(covs),
        'coverage_max': max(covs),
        'coverage_avg': sum(covs)/len(covs),
    }


def stdev(values):
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    var = sum((v - m) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def test_wma_basic():
    # simple sequence 1..4 -> weighted mean = (1*1+2*2+3*3+4*4)/(1+2+3+4)= (1+4+9+16)/10 = 30/10 = 3.0
    vals = [1, 2, 3, 4]
    assert abs(wma(vals) - 3.0) < 1e-9


def test_wma_empty():
    assert wma([]) == 0.0


def test_weekly_aggregate():
    rows = [(0.5, 0.4), (0.7, 0.6), (0.6, 0.5)]
    agg = aggregate(rows)
    assert agg['assign_min'] == 0.5
    assert agg['assign_max'] == 0.7
    assert abs(agg['assign_avg'] - (0.5+0.7+0.6)/3) < 1e-9
    assert agg['rows'] == 3


def test_weekly_aggregate_empty():
    agg = aggregate([])
    assert agg['rows'] == 0
    assert agg['assign_avg'] is None


def test_stdev():
    # Sample stdev of [1,2,3,4] -> mean=2.5; variance=((1.5^2)+(0.5^2)+(0.5^2)+(1.5^2))/3 = (2.25+0.25+0.25+2.25)/3=5/3; sqrt=1.2909944487
    vals = [1, 2, 3, 4]
    sd = stdev(vals)
    assert abs(sd - 1.2909944487) < 1e-9


def test_stdev_insufficient():
    assert stdev([1]) == 0.0
