import os
from datetime import datetime, UTC
from types import SimpleNamespace

import pytest
import requests

import backend.sii_service as sii_service

SiiClient = sii_service.SiiClient


class _DummyResponse:
    def __init__(self, *, status: int, text: str = "", json_data=None):
        self.status_code = status
        self._text = text
        self._json = json_data if json_data is not None else {}
        self.content = text.encode("utf-8")

    @property
    def text(self):
        return self._text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(self._text or f"status {self.status_code}")

    def json(self):
        return self._json


def _make_client(monkeypatch):
    monkeypatch.delenv("SII_FAKE_MODE", raising=False)
    monkeypatch.setenv("SII_AMBIENTE", "cert")
    monkeypatch.setenv("SII_RUT", "76000000-0")
    client = SiiClient()
    client._cert_cache = None
    return client


def test_fetch_token_real_uses_signed_seed(monkeypatch):
    client = _make_client(monkeypatch)
    fixed_now = datetime(2024, 1, 2, 12, 0, tzinfo=UTC)
    monkeypatch.setenv("SII_TOKEN_TTL_MINUTES", "45")
    monkeypatch.setattr(sii_service, "_now", lambda: fixed_now)

    captured = {
        "seed_host": None,
        "signed_inputs": None,
        "post_payload": None,
    }

    def fake_request_seed(self, host: str):
        captured["seed_host"] = host
        return "seed-123"

    def fake_sign_seed(self, seed: str):
        captured["signed_inputs"] = seed
        return b"<signed/>"

    response_payload = "<TOKEN>  REAL-TOKEN  </TOKEN>"

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["post_payload"] = data
        assert "GetTokenFromSeed" in url
        assert headers["Content-Type"].startswith("text/xml")
        return _DummyResponse(status=200, text=response_payload)

    class DummyRoot:
        def __init__(self, raw: bytes):
            self._raw = raw

        def findtext(self, path: str):
            assert path == ".//TOKEN"
            return "  REAL-TOKEN  "

    fake_etree = SimpleNamespace(fromstring=lambda raw: DummyRoot(raw))
    monkeypatch.setattr(sii_service, "etree", fake_etree)
    monkeypatch.setattr(SiiClient, "_request_seed", fake_request_seed, raising=False)
    monkeypatch.setattr(SiiClient, "_sign_seed", fake_sign_seed, raising=False)
    monkeypatch.setattr(sii_service.requests, "post", fake_post)

    token, expires_at = client._fetch_token_real()

    assert token == "REAL-TOKEN"
    assert expires_at == fixed_now + sii_service.timedelta(minutes=45)
    assert captured["seed_host"] == "palena.sii.cl"
    assert captured["signed_inputs"] == "seed-123"
    assert captured["post_payload"] == b"<signed/>"


def test_request_rcv_returns_empty_on_not_found(monkeypatch):
    client = _make_client(monkeypatch)

    monkeypatch.setattr(SiiClient, "_ensure_token", lambda self: "tok123", raising=False)
    invalidations = []
    monkeypatch.setattr(SiiClient, "_invalidate_token", lambda self: invalidations.append(True), raising=False)

    def fake_get(url, headers=None, params=None, timeout=None):
        assert headers["Authorization"] == "Bearer tok123"
        assert "recursos/v1" in url
        return _DummyResponse(status=404)

    monkeypatch.setattr(sii_service.requests, "get", fake_get)

    payload = client._request_rcv("ventas", "2024-07")
    assert payload == {}
    assert invalidations == []


def test_request_rcv_raises_for_unexpected_error(monkeypatch):
    client = _make_client(monkeypatch)
    monkeypatch.setattr(SiiClient, "_ensure_token", lambda self: "tok123", raising=False)

    def fake_get(url, headers=None, params=None, timeout=None):
        return _DummyResponse(status=500, text="boom")

    monkeypatch.setattr(sii_service.requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        client._request_rcv("compras", "2024-07")


def test_load_certificate_requires_path(monkeypatch):
    monkeypatch.delenv("SII_CERT_P12_PATH", raising=False)
    client = SiiClient()
    with pytest.raises(RuntimeError, match="Define SII_CERT_P12_PATH"):
        client._load_certificate()


def test_load_certificate_requires_existing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("SII_CERT_P12_PATH", str(tmp_path / "missing.p12"))
    client = SiiClient()
    with pytest.raises(RuntimeError, match="no encontrado"):
        client._load_certificate()


def test_normalize_rcv_payload_handles_nested_structure(monkeypatch):
    monkeypatch.setenv("SII_RUT", "76123456-7")
    client = SiiClient()
    payload = {
        "data": {
            "detalle": [
                {
                    "tipoDte": "33",
                    "folio": " 15 ",
                    "rutReceptor": "98765432-1",
                    "fechaEmision": "2024-07-05",
                    "montoNeto": "1000",
                    "montoIva": 190,
                    "montoExento": 0,
                    "montoTotal": 1190,
                    "estadoSii": "ACEPTADO",
                    "hash": "abc",
                },
                {"tipoDte": "", "folio": "99"},
            ]
        }
    }

    items = client._normalize_rcv_payload(payload, "2024-07", is_sales=True)
    assert len(items) == 1
    entry = items[0]
    assert entry["tipo_dte"] == "33"
    assert entry["folio"] == "15"
    assert entry["rut_emisor"] == "76123456-7"
    assert entry["rut_receptor"] == "98765432-1"
    assert entry["neto"] == "1000"
    assert entry["estado_sii"] == "ACEPTADO"
    assert entry["xml_hash"] == "abc"


def test_normalize_rcv_payload_skips_invalid_entries(monkeypatch):
    monkeypatch.setenv("SII_RUT", "76123456-7")
    client = SiiClient()
    payload = {
        "data": [
            {"tipoDte": "34", "folio": None},
            "not-a-dict",
            {"tipo_dte": "52", "folio": "88", "rut_emisor": "123"},
        ]
    }

    items = client._normalize_rcv_payload(payload, "2024-07", is_sales=False)
    assert len(items) == 1
    assert items[0]["rut_receptor"] == "76123456-7"
    assert items[0]["rut_emisor"] == "123"
    assert items[0]["tipo_dte"] == "52"
    assert items[0]["folio"] == "88"
