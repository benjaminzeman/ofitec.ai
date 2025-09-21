from importlib import import_module
from pathlib import Path


def test_conciliacion_stub_redirects_to_clean_bp():
    module = import_module('backend.conciliacion_api')
    clean = import_module('backend.conciliacion_api_clean')
    # Allow different object instances as long as they share same name & import name
    bp_mod = getattr(module, 'bp')
    bp_clean = getattr(clean, 'bp')
    assert getattr(bp_mod, 'name', None) == getattr(bp_clean, 'name', None)
    expected_all = [
        "bp",
        "suggest_for_movement",
        "_load_persisted",
        "_SUGGEST_LATENCIES",
        "_SUGGEST_SLO_VIOLATION_TOTAL",
        "_SUGGEST_LAT_LAST_RESET",
    ]
    assert module.__all__ == expected_all


def test_conciliacion_stub_has_no_trailing_legacy():
    module = import_module('backend.conciliacion_api')
    source = Path(module.__file__).read_text(encoding='utf-8')
    sentinel = '# SENTINEL (nothing should follow)'
    assert sentinel in source
    trailing = source.split(sentinel, 1)[1].strip()
    assert trailing == '', f'Trailing content after sentinel: {trailing!r}'
