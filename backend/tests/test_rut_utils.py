from backend.rut_utils import normalize_rut, validate_rut, compute_dv, format_rut


def test_compute_dv_basic():
    assert compute_dv("1") == "9"  # 1-9 es válido
    assert compute_dv("76000000") == "0"  # conocido


def test_normalize_and_validate():
    raw = "76.000.000-0"
    norm = normalize_rut(raw)
    assert norm == "76000000-0"  # sin puntos
    assert validate_rut(raw)
    assert format_rut(raw) == "76.000.000-0"


def test_missing_dv_computed():
    # Falta DV -> se calcula
    norm = normalize_rut("76000000")
    assert norm.endswith("-0")
    assert validate_rut(norm)


def test_invalid_rut():
    # DV incorrecto
    assert not validate_rut("76000000-1")
    # Entrada ruidosa
    assert normalize_rut("@@") == ""


def test_lowercase_k():
    norm = normalize_rut("1234567k")  # ejemplo sintético
    assert norm.endswith("-K") or norm.endswith("-k")
