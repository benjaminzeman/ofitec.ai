from datetime import datetime

import pytest

from services.conciliacion_bancaria.core.ml_engine import (
    FeatureBuilder,
    MLScorer,
    MovimientoBanco,
    MovimientoOfitec,
)


def test_feature_builder_derives_identity_and_alias_confidence():
    builder = FeatureBuilder()
    banco = MovimientoBanco(
        id=1,
        fecha=datetime(2024, 2, 5),
        monto=100000.0,
        descripcion="Transferencia 12345678-9 por factura",
        rut=None,
        proyecto_hint="P-1",
    )
    ofitec = MovimientoOfitec(
        id=10,
        fecha=datetime(2024, 2, 5),
        monto=100000.0,
        descripcion="Factura 12345678-9",
        rut="12345678-9",
        proyecto_id="P-1",
    )
    alias_key = (
        ofitec.rut,
        builder.normalize_text(banco.descripcion),
    )
    alias_dict = {alias_key: 90}

    features = builder.make_features(banco, ofitec, alias_dict)

    assert features["delta_abs"] == 0
    assert features["rut_exact"] == 1
    assert features["project_match"] == 1
    assert features["alias_conf"] == pytest.approx(0.9)


def test_ml_scorer_caps_high_scores():
    scorer = MLScorer()
    features = {
        "delta_abs": 0,
        "delta_rel": 0,
        "ddays": 0,
        "rut_exact": 1,
        "alias_conf": 0,
        "name_sim": 0.9,
        "has_folio_both": 1,
        "project_match": 1,
        "same_sign": 1,
        "keyword_overlap": 3,
    }

    score, reasons = scorer.score_pair(features)

    assert score == 100  # Capped max
    assert "Monto exacto" in reasons
    assert "Misma fecha" in reasons
    assert "RUT coincidente" in reasons
    assert "Folio detectado" in reasons
    assert "Proyecto coincidente" in reasons


def test_ml_scorer_uses_name_similarity_when_no_rut_match():
    scorer = MLScorer()
    features = {
        "delta_abs": 0,
        "delta_rel": 0.001,
        "ddays": 1,
        "rut_exact": 0,
        "alias_conf": 0,
        "name_sim": 0.85,
        "has_folio_both": 0,
        "project_match": 0,
        "same_sign": 1,
        "keyword_overlap": 0,
    }

    score, reasons = scorer.score_pair(features)

    assert score > 0
    assert "Nombre similar" in reasons

