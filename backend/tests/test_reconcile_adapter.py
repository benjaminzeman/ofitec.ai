from backend import reconcile_adapter as ra


def test_build_source_and_defaults():
    payload = {
        'id': 10,
        'amount': 1234.56,
        'date': '2025-09-01',
        'currency': 'USD',
        'ref': 'TRX-99',
        'extra': {'bank': 'X'}
    }
    # internal helper indirectly used via suggest
    out = ra.suggest('bank_tx', payload)
    # Fallback engine returns empty normalized list
    assert out == []


def test_suggest_normalizes_candidates(monkeypatch):
    # Provide a fake smart_suggest returning heterogeneous shapes
    def fake_engine(_src, _opts):  # noqa: D401
        return [
            {
                'candidate': {
                    'target_kind': 'invoice',
                    'doc': 'F123',
                    'fecha': '2025-09-10',
                    'amount': 1000,
                },
                'confidence': 0.9,
                'reasons': ['match:amount', 'match:date']
            },
            {
                'candidate': {
                    'kind': 'expense',
                    'id': 'E55',
                    'date': '2025-09-11',
                    'valor': 500,
                },
                'score': 0.65,
                'reasons': ['heuristic']
            },
            {
                # Missing candidate fields -> many None
                'candidate': {'tipo': 'ap_invoice'},
                'score': 0.10,
            },
        ]

    monkeypatch.setattr(ra, 'smart_suggest', fake_engine)
    res = ra.suggest(
        'bank_tx', {'id': 1, 'amount': 1000, 'date': '2025-09-15'}
    )
    assert len(res) == 3
    # Ordered by score desc
    assert res[0]['score'] >= res[1]['score'] >= res[2]['score']
    # Normalized keys exist
    for r in res:
        assert {
            'target_kind', 'doc', 'fecha', 'amount', 'score', 'reasons'
        } <= set(r.keys())


def test_suggest_truncates_to_10(monkeypatch):
    def fake_many(_src, _opts):
        base = {
            'candidate': {
                'target_kind': 'invoice',
                'doc': 'X',
                'fecha': '2025-09-01',
                'amount': 1,
            },
            'score': 0.5,
        }
        items = []
        for i in range(25):
            it = dict(base)
            it['candidate'] = dict(base['candidate'])
            it['candidate']['doc'] = f'DOC{i}'
            it['score'] = 1 - (i * 0.01)
            items.append(it)
        return items

    monkeypatch.setattr(ra, 'smart_suggest', fake_many)
    r = ra.suggest('bank_tx', {'id': 2})
    assert len(r) == 10
    # Ensure descending order trimmed
    scores = [x['score'] for x in r]
    assert scores == sorted(scores, reverse=True)
