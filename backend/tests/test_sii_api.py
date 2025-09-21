import os
import uuid
from pathlib import Path

import pytest
import json
from datetime import datetime, timedelta, UTC

import requests

from backend.db_utils import db_conn
from backend.sii_service import SiiClient, ensure_schema, log_event

from backend import server


@pytest.fixture(name="client")
def _client(monkeypatch):
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / f"test_sii_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("SII_FAKE_MODE", "1")
    server.app.config["TESTING"] = True
    with server.app.test_client() as c:
        yield c


def test_get_token_fake_mode(client):
    r = client.get("/api/sii/token")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ambiente"] == (os.getenv("SII_AMBIENTE") or "cert")
    assert data["token_preview"].endswith("...")


def test_import_rcv_and_summary(client):
    r = client.post("/api/sii/rcv/import", json={"year": 2025, "month": 8})
    assert r.status_code == 200
    data = r.get_json()
    assert data["ventas"] >= 1
    assert data["compras"] >= 1

    summary = client.get("/api/sii/rcv/summary")
    assert summary.status_code == 200
    summary_data = summary.get_json()
    assert summary_data["ventas"] >= data["ventas"]
    assert summary_data["compras"] >= data["compras"]


def test_token_refresh_uses_cache(client, monkeypatch):
    monkeypatch.delenv("SII_FAKE_MODE", raising=False)
    calls = []

    def fake_fetch(self):
        calls.append('x')
        return (f"TOKEN-{len(calls)}", datetime.now(UTC) + timedelta(minutes=30))

    monkeypatch.setattr(SiiClient, "_fetch_token", fake_fetch, raising=False)
    instance = SiiClient()
    with db_conn(os.environ["DB_PATH"]) as con:
        ensure_schema(con)
        token1, _, cached1 = instance.get_or_refresh_token(con)
        token2, _, cached2 = instance.get_or_refresh_token(con)
    assert not cached1
    assert cached2
    assert token1 == token2
    assert len(calls) == 1


def test_request_rcv_retries_on_unauthorized(monkeypatch):
    monkeypatch.delenv("SII_FAKE_MODE", raising=False)
    monkeypatch.setenv("SII_RUT", "76000000-0")
    monkeypatch.setenv("SII_AMBIENTE", "cert")

    tokens = ["tok1", "tok2"]
    ensure_calls: list[str] = []

    def fake_ensure(self):
        token = tokens.pop(0)
        ensure_calls.append(token)
        return token

    invalidated: list[bool] = []

    def fake_invalidate(self):
        invalidated.append(True)

    class FakeResponse:
        def __init__(self, status: int, payload):
            self.status_code = status
            self._payload = payload
            self.text = json.dumps(payload)

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400 and self.status_code not in (401, 404):
                raise requests.HTTPError(self.text)

    responses = iter(
        [
            FakeResponse(401, {"error": "unauthorized"}),
            FakeResponse(
                200,
                {
                    "data": [
                        {
                            "tipoDte": "33",
                            "folio": "15",
                            "rutEmisor": "12345678-9",
                            "rutReceptor": "98765432-1",
                            "fechaEmision": "2025-08-01",
                            "montoNeto": 1000,
                            "montoIva": 190,
                            "montoExento": 0,
                            "montoTotal": 1190,
                            "estadoSii": "ACEPTADO",
                            "hash": "abc",
                        }
                    ]
                },
            ),
        ]
    )

    captured: list[tuple[int, str]] = []

    def fake_get(url, headers=None, params=None, timeout=None):
        resp = next(responses)
        captured.append((resp.status_code, headers["Authorization"]))
        return resp

    monkeypatch.setattr(SiiClient, "_ensure_token", fake_ensure, raising=False)
    monkeypatch.setattr(SiiClient, "_invalidate_token", fake_invalidate, raising=False)
    monkeypatch.setattr(requests, "get", fake_get)

    instance = SiiClient()
    result = instance._request_rcv("ventas", "2025-08")

    assert invalidated == [True]
    assert ensure_calls == ["tok1", "tok2"]
    assert captured[0] == (401, "Bearer tok1")
    assert captured[1][1] == "Bearer tok2"
    assert result and result[0]["rut_emisor"] == "12345678-9"
    assert result[0]["rut_receptor"] == "98765432-1"
    assert result[0]["tipo_dte"] == "33"
    assert result[0]["folio"] == "15"


def test_sii_events_stream_emits_events(client):
    with db_conn(os.environ["DB_PATH"]) as con:
        ensure_schema(con)
        log_event(con, "rcv_import", json.dumps({"periodo": "2025-08"}))
        con.commit()

    response = client.get("/api/sii/events", buffered=False)
    iterator = response.response
    chunks: list[str] = []
    for _ in range(6):
        try:
            chunk = next(iterator)
        except StopIteration:
            break
        decoded = chunk.decode("utf-8")
        chunks.append(decoded)
        normalized_tail = decoded.replace("\r", "")
        if normalized_tail.endswith("\n\n"): 
            break
            break
    response.close()
    payload = "".join(chunks)
    assert "rcv_import" in payload

def test_get_token_real_mode_not_implemented(client, monkeypatch):
    monkeypatch.setenv("SII_FAKE_MODE", "0")

    def fake_get(self, con):
        raise NotImplementedError("cert missing")

    monkeypatch.setattr(SiiClient, "get_or_refresh_token", fake_get, raising=False)

    resp = client.get("/api/sii/token")
    assert resp.status_code == 501
    payload = resp.get_json()
    assert payload["error"] == "sii_not_implemented"
    assert payload["ambiente"] == SiiClient().ambiente


def test_import_rcv_real_mode_not_implemented(client, monkeypatch):
    monkeypatch.setenv("SII_FAKE_MODE", "0")

    def fake_sales(self, *_args, **_kwargs):
        raise NotImplementedError("no prod")

    monkeypatch.setattr(SiiClient, "fetch_rcv_sales", fake_sales, raising=False)
    monkeypatch.setattr(SiiClient, "fetch_rcv_purchases", lambda self, *_a, **_k: [], raising=False)

    resp = client.post("/api/sii/rcv/import", json={"year": 2024, "month": 7})
    assert resp.status_code == 501
    body = resp.get_json()
    assert body["error"] == "sii_not_implemented"
    assert body["ambiente"] == SiiClient().ambiente


def test_import_rcv_real_mode_persists_data(client, monkeypatch):
    monkeypatch.setenv("SII_FAKE_MODE", "0")
    monkeypatch.setenv("SII_RUT", "76000010-1")

    sales_rows = [
        {
            "periodo": "2024-07",
            "rut_emisor": "76000010-1",
            "rut_receptor": "96543210-5",
            "tipo_dte": "33",
            "folio": "15",
            "fecha_emision": "2024-07-01",
            "neto": 1000,
            "iva": 190,
            "exento": 0,
            "total": 1190,
            "estado_sii": "ACEPTADO",
            "xml_hash": "hash-1",
        }
    ]

    purchases_rows = [
        {
            "periodo": "2024-07",
            "rut_emisor": "96543210-5",
            "rut_receptor": "76000010-1",
            "tipo_dte": "33",
            "folio": "88",
            "fecha_emision": "2024-07-05",
            "neto": 5000,
            "iva": 950,
            "exento": 0,
            "total": 5950,
            "estado_sii": "ACEPTADO",
            "xml_hash": "hash-2",
        }
    ]

    monkeypatch.setattr(SiiClient, "fetch_rcv_sales", lambda self, *_a: sales_rows, raising=False)
    monkeypatch.setattr(SiiClient, "fetch_rcv_purchases", lambda self, *_a: purchases_rows, raising=False)

    resp = client.post("/api/sii/rcv/import", json={"year": 2024, "month": 7})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ventas"] == 1
    assert body["compras"] == 1
    assert body["inserted_sales"] == 1
    assert body["inserted_purchases"] == 1

    with db_conn(os.environ["DB_PATH"]) as con:
        sales_db = con.execute("SELECT rut_emisor, rut_receptor, tipo_dte, folio FROM sii_rcv_sales").fetchall()
        purchases_db = con.execute("SELECT rut_emisor, rut_receptor, tipo_dte, folio FROM sii_rcv_purchases").fetchall()
        event_row = con.execute("SELECT tipo, detalle FROM sii_eventos ORDER BY id DESC LIMIT 1").fetchone()

    assert len(sales_db) == 1 and sales_db[0]["folio"] == "15"
    assert len(purchases_db) == 1 and purchases_db[0]["folio"] == "88"
    assert event_row["tipo"] == "rcv_import"
    assert "inserted_sales" in event_row["detalle"]


def test_import_rcv_real_mode_raises_runtime_errors(client, monkeypatch):
    monkeypatch.setenv("SII_FAKE_MODE", "0")

    def boom(self, *_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(SiiClient, "fetch_rcv_sales", boom, raising=False)
    monkeypatch.setattr(SiiClient, "fetch_rcv_purchases", lambda self, *_a, **_k: [], raising=False)

    with pytest.raises(RuntimeError):
        client.post("/api/sii/rcv/import", json={"year": 2024, "month": 7})
