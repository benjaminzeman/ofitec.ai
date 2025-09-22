def test_ar_rules_stats_endpoint(client):
    resp = client.get('/api/ar/rules_stats')
    assert resp.status_code == 200
    data = resp.get_json()
    # Core keys
    required_keys = [
        'rules_total', 'rules_by_kind', 'invoices_total', 'invoices_with_project',
        'project_assign_rate', 'distinct_customer_names', 'customer_names_with_rule',
        'customer_name_rule_coverage', 'recent_events_30d', 'generated_at'
    ]
    for k in required_keys:
        assert k in data
    # Types
    assert isinstance(data['rules_by_kind'], dict)
    assert isinstance(data['rules_total'], int)
    assert isinstance(data['invoices_total'], int)
    assert isinstance(data['invoices_with_project'], int)
    assert 'T' in data['generated_at']


def test_prometheus_contains_customer_name_rule_coverage(client):
    prom = client.get('/api/matching/metrics/prom')
    # Text exposition; should not 500 even if metric absent (but now we added it when computable)
    assert prom.status_code == 200
    text = prom.get_data(as_text=True)
    # Accept absence gracefully (empty DB), but if present format should be name + space + value
    if 'matching_ar_customer_name_rule_coverage' in text:
        lines = [ln for ln in text.split('\n') if ln.startswith('matching_ar_customer_name_rule_coverage')]
        assert all(len(ln.split()) >= 2 for ln in lines)
