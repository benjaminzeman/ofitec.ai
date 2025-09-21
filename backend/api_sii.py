"""SII (Servicio de Impuestos Internos) integration endpoints."""

from __future__ import annotations

import json
import time
from datetime import datetime, UTC
from typing import Any, Dict

from flask import Blueprint, Response, jsonify, request, stream_with_context

from backend.db_utils import db_conn
from backend.sii_service import (
    SiiClient,
    ensure_schema,
    log_event,
    summarize_rcv_counts,
    upsert_rcv_purchases,
    upsert_rcv_sales,
)

bp = Blueprint("sii", __name__)


def _validate_period(payload: Dict[str, Any]) -> tuple[int, int]:
    now_utc = datetime.now(UTC)
    year = int(payload.get("year", now_utc.year))
    month = int(payload.get("month", now_utc.month))
    if year < 2000 or year > 2100:
        raise ValueError("year_out_of_range")
    if month < 1 or month > 12:
        raise ValueError("month_out_of_range")
    return year, month


@bp.get("/api/sii/token")
def get_sii_token():
    """Obtain (or preview) the current SII token for the configured ambiente."""
    with db_conn() as con:
        ensure_schema(con)
        client = SiiClient()
        try:
            token, expires_at, cached = client.get_or_refresh_token(con)
        except NotImplementedError as exc:  # pragma: no cover - until real integration
            return (
                jsonify(
                    {
                        "error": "sii_not_implemented",
                        "detail": str(exc),
                        "ambiente": client.ambiente,
                    }
                ),
                501,
            )
        preview = token[:6] + "..." if token else ""
        return jsonify(
            {
                "ambiente": client.ambiente,
                "token_preview": preview,
                "expires_at": expires_at.replace(microsecond=0).isoformat() + "Z",
                "cached": cached,
            }
        )


@bp.post("/api/sii/rcv/import")
def import_rcv():
    payload = request.get_json(silent=True) or {}
    try:
        year, month = _validate_period(payload)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400

    client = SiiClient()
    try:
        sales = client.fetch_rcv_sales(year, month)
        purchases = client.fetch_rcv_purchases(year, month)
    except NotImplementedError as exc:  # pragma: no cover - until real integration
        return (
            jsonify(
                {
                    "error": "sii_not_implemented",
                    "detail": str(exc),
                    "ambiente": client.ambiente,
                }
            ),
            501,
        )

    periodo = f"{year:04d}-{month:02d}"
    with db_conn() as con:
        ensure_schema(con)
        ins_sales, upd_sales = upsert_rcv_sales(con, sales)
        ins_pur, upd_pur = upsert_rcv_purchases(con, purchases)
        log_event(
            con,
            "rcv_import",
            json.dumps(
                {
                    "periodo": periodo,
                    "ventas": len(sales),
                    "compras": len(purchases),
                    "inserted_sales": ins_sales,
                    "updated_sales": upd_sales,
                    "inserted_purchases": ins_pur,
                    "updated_purchases": upd_pur,
                },
                ensure_ascii=False,
            ),
        )
        con.commit()
    return jsonify(
        {
            "periodo": periodo,
            "ventas": len(sales),
            "compras": len(purchases),
            "inserted_sales": ins_sales,
            "updated_sales": upd_sales,
            "inserted_purchases": ins_pur,
            "updated_purchases": upd_pur,
        }
    )


@bp.get("/api/sii/rcv/summary")
def rcv_summary():
    with db_conn() as con:
        ensure_schema(con)
        summary = summarize_rcv_counts(con)
    return jsonify(summary)


@bp.get("/api/sii/events")
def sii_events_stream():
    last_id = request.args.get("last_id", default=0, type=int)

    def event_stream():
        nonlocal last_id
        while True:
            with db_conn() as con:
                ensure_schema(con)
                rows = con.execute(
                    "SELECT id, envio_id, tipo, detalle, created_at FROM sii_eventos WHERE id>? "
                    "ORDER BY id ASC LIMIT 50",
                    (last_id,),
                ).fetchall()
            if rows:
                for row in rows:
                    last_id = row["id"]
                    payload = {
                        "id": row["id"],
                        "envio_id": row["envio_id"],
                        "tipo": row["tipo"],
                        "detalle": row["detalle"],
                        "created_at": row["created_at"],
                    }
                    yield f"id: {last_id}\n"
                    yield "event: sii\n"
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            else:
                yield "event: ping\ndata: {}\n\n"
            time.sleep(2)

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return Response(stream_with_context(event_stream()), mimetype="text/event-stream", headers=headers)
