#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OFITEC.AI SERVER - VERSIÓN ORGANIZADA
================================================

Servidor Flask reorganizado, alineado con Ley de Puertos y estructura nueva.

Puerto: 5555 (OFICIAL)
URL: http://localhost:5555
"""

from __future__ import annotations
# pylint: disable=line-too-long,too-many-locals,too-many-branches,too-many-statements,too-many-return-statements
# pylint: disable=missing-function-docstring,wrong-import-order,ungrouped-imports,broad-exception-caught,import-outside-toplevel,redefined-outer-name
# pylint: disable=too-many-lines,import-error,invalid-name,global-statement,too-many-arguments,too-many-positional-arguments,no-else-return,chained-comparison,reimported,consider-using-in

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request
from flask import send_from_directory, Response
from flask_cors import CORS
import unicodedata
from backend.db_utils import db_conn  # standardized connection manager


# ----------------------------------------------------------------------------
# Logging básico
# ----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Carga ligera de .env (sin dependencias externas)
# ----------------------------------------------------------------------------

def _load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
    except Exception:
        # Silencioso: si falla, seguimos con el entorno actual
        pass


ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_load_env_file(ENV_PATH)


# ----------------------------------------------------------------------------
# Rutas organizadas (nuevo repo) y configuración por entorno
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DOCS_OFICIALES_DIR = PROJECT_ROOT / "docs"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
REPORTES_DIR = BASE_DIR / "reportes"
BADGES_DIR = PROJECT_ROOT / "badges"

_raw_db = os.getenv("DB_PATH")
if _raw_db:
    try:
        _p = Path(_raw_db)
        if not _p.is_absolute():
            _p = PROJECT_ROOT / _p
        DB_PATH = str(_p.resolve())
    except Exception:
        # Fallback to PROJECT_ROOT/data to align with Docker volume /app/data
        DB_PATH = str((PROJECT_ROOT / "data" / "chipax_data.db").resolve())
else:
    # Prefer PROJECT_ROOT/data (in Docker this is /app/data)
    DB_PATH = str((PROJECT_ROOT / "data" / "chipax_data.db").resolve())

PORT = int(os.getenv("PORT", "5555"))
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS", "http://localhost:3001")
CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS_ENV.split(",")]


# ----------------------------------------------------------------------------
# Flask app
# ----------------------------------------------------------------------------
app = Flask(__name__)
try:
    from ep_api import ep_bp  # type: ignore
    app.register_blueprint(ep_bp)
    logger.info(" EP blueprint registrada (local module)")
except Exception as _e_local:  # noqa: BLE001
    logger.warning("EP blueprint no disponible (local): %s", _e_local)
    try:
        from backend.ep_api import ep_bp  # type: ignore
        app.register_blueprint(ep_bp)
        logger.info(" EP blueprint registrada (package path)")
    except Exception as _e_pkg:  # noqa: BLE001
        logger.warning("❌ EP blueprint no disponible: %s", _e_pkg)

# Subcontractor EP blueprint (local-first, then package path)
try:
    from sc_ep_api import sc_ep_bp  # type: ignore
    app.register_blueprint(sc_ep_bp)
    logger.info(" SC EP blueprint registrada (local module)")
except Exception as _e_local:  # noqa: BLE001
    logger.warning("SC EP blueprint (local) no disponible: %s", _e_local)
    try:
        from backend.sc_ep_api import sc_ep_bp  # type: ignore
        app.register_blueprint(sc_ep_bp)
        logger.info(" SC EP blueprint registrada (package path)")
    except Exception as _e_pkg:  # noqa: BLE001
        logger.warning("❌ SC EP blueprint no disponible: %s", _e_pkg)
CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})
app.config["SECRET_KEY"] = "ofitec_ai_2025"
app.config["JSON_AS_ASCII"] = False

# Conciliación blueprint
# Prefer always the new clean implementation; fallback to legacy only if clean fails and not forced off.
_FORCE_CLEAN = os.getenv("RECONCILIACION_CLEAN", "").strip().lower() in {"1", "true", "yes", "on"}
try:
    import sys as _sys  # local path ensure
    if str(BASE_DIR) not in _sys.path:
        _sys.path.append(str(BASE_DIR))
    # Try clean module first
    try:
        from conciliacion_api_clean import bp as recon_bp  # type: ignore
        app.register_blueprint(recon_bp)
        logger.info(" Conciliacion (CLEAN) blueprint registrada (local module)")
    except Exception as _e_clean_local:  # noqa: BLE001
        logger.warning("Clean conciliacion local import fallo: %s", _e_clean_local)
        try:
            from backend.conciliacion_api_clean import bp as recon_bp  # type: ignore
            app.register_blueprint(recon_bp)
            logger.info(" Conciliacion (CLEAN) blueprint registrada (package path)")
        except Exception as _e_clean_pkg:  # noqa: BLE001
            if _FORCE_CLEAN:
                raise
            logger.warning("Clean conciliacion no disponible, intentando legacy: %s", _e_clean_pkg)
            # Legacy fallback (may be corrupted) only if not forced clean
            try:
                from conciliacion_api import bp as recon_bp  # type: ignore
                app.register_blueprint(recon_bp)
                logger.info(" Conciliacion (legacy) blueprint registrada (local module)")
            except Exception as _e_legacy_local:  # noqa: BLE001
                logger.warning("Conciliacion legacy local no disponible: %s", _e_legacy_local)
                try:
                    from backend.conciliacion_api import bp as recon_bp  # type: ignore
                    app.register_blueprint(recon_bp)
                    logger.info(" Conciliacion (legacy) blueprint registrada (package path)")
                except Exception as _e_legacy_pkg:  # noqa: BLE001
                    logger.warning("❌ Conciliacion blueprint no disponible (clean ni legacy): %s", _e_legacy_pkg)
except Exception as _fatal_recon:  # noqa: BLE001
    logger.error("❌ Error inicializando conciliacion blueprint: %s", _fatal_recon)

# Sales invoices blueprint (local-first, then package path)
try:
    from api_sales_invoices import bp as sales_bp  # type: ignore
    app.register_blueprint(sales_bp)
    logger.info(" Sales invoices blueprint registrada (local module)")
except Exception as _e_local:  # noqa: BLE001
    logger.warning("Sales invoices (local) no disponible: %s", _e_local)
    try:
        from backend.api_sales_invoices import bp as sales_bp  # type: ignore
        app.register_blueprint(sales_bp)
        logger.info(" Sales invoices blueprint registrada (package path)")
    except Exception as _e_pkg:  # noqa: BLE001
        logger.warning("❌ Sales invoices blueprint no disponible: %s", _e_pkg)

# AR map blueprint (local-first, then package path)
try:
    from api_ar_map import bp as ar_map_bp  # type: ignore
    app.register_blueprint(ar_map_bp)
    logger.info(" AR map blueprint registrada (local module)")
except Exception as _e_local:  # noqa: BLE001
    logger.warning("AR map (local) no disponible: %s", _e_local)
    try:
        from backend.api_ar_map import bp as ar_map_bp  # type: ignore
        app.register_blueprint(ar_map_bp)
        logger.info(" AR map blueprint registrada (package path)")
    except Exception as _e_pkg:  # noqa: BLE001
        logger.warning("❌ AR map blueprint no disponible: %s", _e_pkg)

# SII integration blueprint (local-first, then package path)
try:
    from api_sii import bp as sii_bp  # type: ignore
    app.register_blueprint(sii_bp)
    logger.info('SII blueprint registrada (local module)')
except Exception as _e_local:  # noqa: BLE001
    logger.warning('SII blueprint (local) no disponible: %s', _e_local)
    try:
        from backend.api_sii import bp as sii_bp  # type: ignore
        app.register_blueprint(sii_bp)
        logger.info('SII blueprint registrada (package path)')
    except Exception as _e_pkg:  # noqa: BLE001
        logger.warning('SII blueprint no disponible: %s', _e_pkg)

# AP match blueprint
try:
    from backend.api_ap_match import bp as ap_match_bp  # type: ignore
    app.register_blueprint(ap_match_bp)
except Exception as _e:  # noqa: BLE001
    logger.warning("AP match blueprint no disponible: %s", _e)

# Matching metrics unified blueprint (AP + AR KPIs)
try:
    from backend.api_matching_metrics import matching_metrics_bp  # type: ignore
    app.register_blueprint(matching_metrics_bp)
    logger.info(" Matching metrics blueprint registrada")
except Exception as _e_mm:  # noqa: BLE001
    logger.warning("Matching metrics blueprint no disponible: %s", _e_mm)


# (EP blueprint is already registered above in a guarded try/except)


logger.info("📁 Directorio base: %s", str(BASE_DIR))
logger.info("📊 Base de datos: %s", DB_PATH)
logger.info("📚 Documentos oficiales: %s", str(DOCS_OFICIALES_DIR))

# Optional utils (pure helpers) for route/db inspection
try:  # pragma: no cover - defensive import
    from backend import server_utils as _su  # type: ignore
except Exception:  # noqa: BLE001
    _su = None  # type: ignore

# Default for build stamp to satisfy linters; assigned lazily in get_status
BUILD_STAMP: str | None = None

# Verificar que la BD existe
def _data_available() -> bool:
    return os.path.exists(DB_PATH)


if _data_available():
    logger.info(" Base de datos encontrada")
else:
    logger.warning(" Base de datos NO encontrada en %s", DB_PATH)

# Cargar datos certificados si existen
CERTIFIED_PROJECTS_PATH = REPORTES_DIR / "nasa_certified_projects.json"
if CERTIFIED_PROJECTS_PATH.exists():
    with open(CERTIFIED_PROJECTS_PATH, "r", encoding="utf-8") as f:
        CERTIFIED_PROJECTS = json.load(f)
    logger.info(
        " Datos certificados cargados: %d proyectos", len(CERTIFIED_PROJECTS)
    )
else:
    CERTIFIED_PROJECTS = []
    logger.info("ℹ️ Datos certificados no encontrados (opcional)")

# Manual contract overrides (file-based, last resort)
MANUAL_CONTRACTS: dict[str, dict] = {}
try:
    manual_path = BASE_DIR / "manual_contracts.json"
    if manual_path.exists():
        with open(manual_path, "r", encoding="utf-8") as f:
            _mc = json.load(f)
        if isinstance(_mc, dict):
            # Store as-is (raw keys). We'll normalize at lookup time.
            for k, v in _mc.items():
                if isinstance(v, dict):
                    MANUAL_CONTRACTS[str(k)] = v
        logger.info("📝 Manual contracts loaded: %d", len(MANUAL_CONTRACTS))
    else:
        logger.info("📝 manual_contracts.json not found (optional)")
except Exception as e:  # noqa: BLE001
    logger.warning("manual_contracts.json load error: %s", e)


# ----------------------------------------------------------------------------
# Rutas web/API
# ----------------------------------------------------------------------------


@app.route("/api/health")
def api_health() -> tuple:
    """Simple healthcheck endpoint with basic dependency diagnostics."""
    checks: dict[str, str] = {}
    status = "ok"
    # Database check (SQLite path by default)
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            conn.execute("SELECT 1")
            checks['database'] = 'available'
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        status = "degraded"
        checks['database'] = 'error'
        checks['database_error'] = str(exc)
    payload = {"status": status, "checks": checks}
    code = 200 if status == 'ok' else 503
    return jsonify(payload), code


@app.route("/api/admin/db")
def admin_db_status():
    """Diagnóstico simple del estado de la base de datos."""
    try:
        exists = os.path.exists(DB_PATH)
        size = None
        tables = []
        if exists:
            try:
                size = os.path.getsize(DB_PATH)
            except Exception:
                size = None
            # Use shared context manager to guarantee closure
            try:
                with db_conn(DB_PATH) as con:
                    cur = con.execute(
                        (
                            "SELECT name, type FROM sqlite_master "
                            "WHERE type IN ('table','view') "
                            "ORDER BY type, name"
                        )
                    )
                    tables = [dict(r) for r in cur.fetchall()]
            except Exception:
                # Defensive: ignore table enumeration errors
                pass
        return jsonify(
            {
                "db_path": DB_PATH,
                "exists": exists,
                "size_bytes": size,
                "base_dir": str(BASE_DIR),
                "project_root": str(PROJECT_ROOT),
                "tables": tables[:50],
                "certified_projects_count": len(CERTIFIED_PROJECTS),
            }
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Error en admin db status: %s", e)
        return jsonify({"db_path": DB_PATH, "error": "inspect_failed"}), 500


@app.route("/api/admin/routes")
def admin_routes():
    """Listar rutas registradas para diagnóstico rápido."""
    try:
        rules = []
        for r in app.url_map.iter_rules():
            rules.append(
                {
                    "rule": str(r.rule),
                    "methods": sorted(
                        m for m in r.methods if m not in {"HEAD", "OPTIONS"}
                    ),
                    "endpoint": r.endpoint,
                }
            )
        # Ordenar por ruta para lectura fácil
        rules.sort(key=lambda x: x["rule"])
        return jsonify({"count": len(rules), "routes": rules})
    except Exception as e:  # noqa: BLE001
        logger.error("Error listando rutas: %s", e)
        return jsonify({"error": "routes_inspect_failed"}), 500

@app.route("/")
def home():
    """Página principal del portal."""
    return jsonify(
        {
            "name": "ofitec.ai API",
            "version": "2.0-organizada",
            "status": "ok",
            "docs": "/api/status",
            "endpoints": [
                "/api/projects",
                "/api/providers",
                "/api/financial",
                "/api/dashboard",
                "/api/finanzas/facturas_compra",
                "/api/finanzas/facturas_venta",
                "/api/finanzas/cartola_bancaria",
                "/api/purchase_orders",
                "/api/purchase_orders/<id>",
                "/api/purchase_orders/<id>/lines",
                "/api/reportes/proyectos",
                "/api/reportes/proveedores",
                "/api/tesoreria/saldos",
                "/api/cashflow/semana",
                "/api/subcontratos/resumen",
                "/api/riesgos/resumen",
                "/api/hse/resumen",
                "/api/proyectos/kpis",
                "/api/proyectos/<id>/resumen",
            ],
        }
    )

@app.route("/api/projects")
def get_projects():
    """API para obtener proyectos consolidando órdenes por proyecto."""
    try:
        logger.info("🚀 API /api/projects llamada")
        data_available = _data_available()

        # Preferir datos certificados si existen
        if CERTIFIED_PROJECTS and not data_available:
            logger.info(
                "📊 Devolviendo %d proyectos certificados",
                len(CERTIFIED_PROJECTS),
            )
            return jsonify(CERTIFIED_PROJECTS)

        if not data_available:
            logger.info(" BD no disponible, devolviendo datos mock")
            return jsonify(get_mock_projects())

        logger.info("📂 Conectando a BD: %s", DB_PATH)
        with db_conn(DB_PATH) as conn:
            cursor = conn.cursor()
            authorized_query = (
                "SELECT COALESCE(p.zoho_project_name, pm.zoho_project_name) as project_name, "
                "COUNT(*) as total_orders, SUM(p.total_amount) as total_amount, "
                "COUNT(DISTINCT p.vendor_rut) as unique_providers, MIN(p.po_date) as start_date, "
                "MAX(p.po_date) as end_date FROM purchase_orders_unified p "
                "LEFT JOIN projects_analytic_map pm ON CAST(p.zoho_project_id AS TEXT) = "
                "CAST(pm.zoho_project_id AS TEXT) WHERE COALESCE(p.zoho_project_name, pm.zoho_project_name) IS NOT NULL "
                "AND TRIM(COALESCE(p.zoho_project_name, pm.zoho_project_name)) != '' "
                "AND LOWER(TRIM(COALESCE(p.zoho_project_name, pm.zoho_project_name))) NOT IN ('null') "
                "GROUP BY COALESCE(p.zoho_project_name, pm.zoho_project_name) ORDER BY total_amount DESC"
            )
            cursor.execute(authorized_query)
            projects_raw = cursor.fetchall()

            # Compute progress map while connection open
            progress_map: dict[str, float] = {}
            try:
                if _table_exists(cursor.connection, "daily_reports"):
                    cols = _table_columns(cursor.connection, "daily_reports")
                    if "project_name" in cols:
                        cur = cursor.connection.execute(
                            "SELECT LOWER(TRIM(COALESCE(project_name,''))) "
                            "       AS pname, "
                            "       AVG(COALESCE(avance_pct,0)) AS avgp "
                            "  FROM daily_reports GROUP BY pname"
                        )
                        for pname, avgp in cur.fetchall():
                            if pname:
                                progress_map[pname] = float(avgp or 0)
                    elif "project_id" in cols and _table_exists(
                        cursor.connection, "projects_analytic_map"
                    ):
                        cur = cursor.connection.execute(
                            "SELECT LOWER(TRIM(COALESCE(pm.zoho_project_name,''))) AS pname, "
                            "       AVG(COALESCE(dr.avance_pct,0)) AS avgp "
                            "  FROM daily_reports dr  JOIN projects_analytic_map pm ON CAST(dr.project_id AS TEXT) = CAST(pm.zoho_project_id AS TEXT) "
                            " GROUP BY pname"
                        )
                        for pname, avgp in cur.fetchall():
                            if pname:
                                progress_map[pname] = float(avgp or 0)
            except Exception:
                progress_map = {}
            logger.info(" %d proyectos encontrados en BD", len(projects_raw))

        # Formato de salida API
        api_projects = []
        for i, row in enumerate(projects_raw):
            (
                project_name,
                orders,
                total_amount,
                providers,
                start_date,
                end_date,
            ) = row
            total_amount = float(total_amount or 0)
            orders = int(orders or 0)
            providers = int(providers or 0)
            pname_norm = _norm_name(project_name)
            project = {
                "id": f"PROJ-{i+1:03d}",
                "name": project_name,
                "client": "Cliente Externo",
                "status": "active",
                "progress": progress_map.get(pname_norm, 0),
                "startDate": start_date,
                "endDate": end_date,
                "budget": total_amount * 1.25,
                "spent": total_amount,
                "remaining": total_amount * 0.25,
                "risk": "low" if total_amount > 10000000 else "medium",
                "manager": "Gerente de Proyecto",
                "description": (
                    f"Proyecto con {orders} órdenes y {providers} proveedores"
                ),
                "location": "Chile",
                "orders": orders,
                "providers": providers,
            }
            api_projects.append(project)

        logger.info("🚀 Devolviendo %d proyectos", len(api_projects))
        return jsonify(api_projects)

    except Exception as e:  # noqa: BLE001 - simplificado para endpoint demo
        logger.error("❌ Error obteniendo proyectos: %s", e)
        return jsonify(get_mock_projects())


@app.route("/api/dashboard")
def get_dashboard():
    """Dashboard principal con métricas agregadas."""
    try:
        if _data_available() and CERTIFIED_PROJECTS:
            total_budget = sum(p.get("budget", 0) for p in CERTIFIED_PROJECTS)
            total_spent = sum(p.get("spent", 0) for p in CERTIFIED_PROJECTS)
            return jsonify(
                {
                    "totalProjects": len(CERTIFIED_PROJECTS),
                    "activeProjects": len(CERTIFIED_PROJECTS),
                    "totalBudget": total_budget,
                    "totalSpent": total_spent,
                    "status": "operational",
                    "lastUpdate": datetime.now().isoformat(),
                }
            )
        else:
            return jsonify(
                {
                    "totalProjects": 3,
                    "activeProjects": 3,
                    "totalBudget": 71000000,
                    "totalSpent": 68000000,
                    "status": "mock_data",
                    "lastUpdate": datetime.now().isoformat(),
                }
            )
    except Exception as e:  # noqa: BLE001 - simplificado para endpoint demo
        logger.error("Error en dashboard: %s", e)
        return jsonify({"error": "Dashboard error"})


def get_mock_projects():
    """Datos mock para desarrollo."""
    return [
        {
            "id": "PROJ-001",
            "name": "Proyecto Mock 1",
            "client": "Cliente Mock",
            "status": "active",
            "progress": 75,
            "startDate": "2025-01-01",
            "endDate": "2025-12-31",
            "budget": 1000000,
            "spent": 750000,
            "remaining": 250000,
            "risk": "low",
            "manager": "Manager Mock",
            "description": "Proyecto de prueba",
            "location": "Chile",
            "orders": 10,
            "providers": 5,
        }
    ]


# ----------------------------------------------------------------------------
# Endpoints adicionales para alinear contrato Frontend
# ----------------------------------------------------------------------------

@app.route("/api/projects_v2")
def api_projects_v2():
    """Lista de proyectos con filtros y paginación.

    Parámetros opcionales:
    - q: búsqueda por nombre
    - limit (1..200), offset (>=0)
    - order: total_amount|project_name (desc por defecto)
    - with_meta: si está presente, se incluye {items, meta}
    """
    try:
        data_available = _data_available()
        if CERTIFIED_PROJECTS and not data_available:
            items = [
                {
                    "id": f"PROJ-{i+1:03d}",
                    "name": p.get("name"),
                    "budget": p.get("budget"),
                    "spent": p.get("spent"),
                    "orders": p.get("orders", 0),
                    "providers": p.get("providers", 0),
                }
                for i, p in enumerate(CERTIFIED_PROJECTS)
            ]
            return jsonify(
                {
                    "items": items,
                    "meta": {
                        "total": len(items),
                        "limit": len(items),
                        "offset": 0,
                    },
                }
            )

        if not data_available:
            return jsonify(
                {
                    "items": get_mock_projects(),
                    "meta": {"total": 1, "limit": 1, "offset": 0},
                }
            )

        args = request.args
        q = args.get("q", type=str)
        limit = max(1, min(200, args.get("limit", default=25, type=int)))
        offset = max(0, args.get("offset", default=0, type=int))
        order = (args.get("order", "total_amount") or "").lower()
        order_map = {
            "total_amount": "total_amount",
            "project_name": "project_name",
            "name": "project_name",
        }
        order_sql = order_map.get(order, "total_amount") + " DESC"

        with db_conn(DB_PATH) as conn:
            cur = conn.cursor()
            where = [
                (
                    "COALESCE(p.zoho_project_name, pm.zoho_project_name) "
                    "IS NOT NULL"
                ),
                (
                    (
                        "TRIM(COALESCE(p.zoho_project_name, pm.zoho_project_name)) "
                        "<> ''"
                    )
                ),
                (
                    (
                        "LOWER(TRIM(COALESCE(p.zoho_project_name, pm.zoho_project_name))) "
                        "NOT IN ('null')"
                    )
                ),
            ]
            params = []
            if q:
                where.append(
                    (
                        "COALESCE(p.zoho_project_name, pm.zoho_project_name) "
                        "LIKE ?"
                    )
                )
                params.append(f"%{q}%")
            where_sql = " AND ".join(where)

            count_sql = (
                "SELECT COUNT(1) FROM ("  # subquery for distinct project names
                "SELECT 1 FROM purchase_orders_unified p "
                " LEFT JOIN projects_analytic_map pm ON "
                "     CAST(p.zoho_project_id AS TEXT) = "
                "     CAST(pm.zoho_project_id AS TEXT) "
                f" WHERE {where_sql} GROUP BY COALESCE(p.zoho_project_name, pm.zoho_project_name)"  # noqa: E501
                ") t"
            )
            cur.execute(count_sql, params)
            total = cur.fetchone()[0]

            data_sql = (
                "SELECT COALESCE(p.zoho_project_name, pm.zoho_project_name) "
                "       AS project_name, COUNT(*) AS total_orders, "
                "       SUM(p.total_amount) AS total_amount, "
                "       COUNT(DISTINCT p.vendor_rut) AS unique_providers, "
                "       MIN(p.po_date) AS start_date, "
                "       MAX(p.po_date) AS end_date "
                "  FROM purchase_orders_unified p "
                "  LEFT JOIN projects_analytic_map pm ON "
                "       CAST(p.zoho_project_id AS TEXT) = "
                "       CAST(pm.zoho_project_id AS TEXT) "
                f" WHERE {where_sql} "
                " GROUP BY COALESCE(p.zoho_project_name, "
                "          pm.zoho_project_name) "
                f" ORDER BY {order_sql} LIMIT OFFSET ?"
            )
            cur.execute(data_sql, [*params, limit, offset])
            rows = cur.fetchall()

        # Second connection for budgets & progress (reduce lock duration)
        budgets: dict[str, float] = {}
        progress_map: dict[str, float] = {}
        try:
            with db_conn(DB_PATH) as conn2:
                c2 = conn2.cursor()
                c2.execute(
                    "SELECT pr.nombre AS project_name, COALESCE(v.total_presupuesto, 0) AS budget "
                    "FROM proyectos pr "
                    "LEFT JOIN presupuestos pb ON pb.id = (SELECT MAX(id) FROM presupuestos WHERE proyecto_id = pr.id) "
                    "LEFT JOIN v_presupuesto_totales v ON v.presupuesto_id = pb.id"
                )
                for pname, b in c2.fetchall():
                    if pname:
                        budgets[_norm_name(pname)] = float(b or 0)
                if _table_exists(conn2, "daily_reports"):
                    cols2 = _table_columns(conn2, "daily_reports")
                    if "project_name" in cols2:
                        c2.execute(
                            "SELECT LOWER(TRIM(COALESCE(project_name,''))) "
                            "       AS pname, "
                            "       AVG(COALESCE(avance_pct,0)) AS p "
                            "  FROM daily_reports GROUP BY pname"
                        )
                        for pname, p in c2.fetchall():
                            if pname:
                                progress_map[str(pname)] = float(p or 0)
                    elif "project_id" in cols2 and _table_exists(
                        conn2, "projects_analytic_map"
                    ):
                        c2.execute(
                            "SELECT LOWER(TRIM(COALESCE(pm.zoho_project_name,''))) AS pname, "
                            "       AVG(COALESCE(dr.avance_pct,0)) AS p "
                            "  FROM daily_reports dr JOIN projects_analytic_map pm ON "
                            "       CAST(dr.project_id AS TEXT) = CAST(pm.zoho_project_id AS TEXT) "
                            " GROUP BY pname"
                        )
                        for pname, p in c2.fetchall():
                            if pname:
                                progress_map[str(pname)] = float(p or 0)
        except Exception:
            budgets = {}
            progress_map = {}
        # conn closed automatically by context manager

        items = []
        for i, (
            name,
            orders,
            total_amount,
            providers,
            start_date,
            end_date,
        ) in enumerate(rows, start=offset + 1):
            key = _norm_name(name)
            budget_val = budgets.get(key)
            if budget_val is None:
                budget_val = (total_amount or 0) * 1.25  # fallback heurístico
            items.append(
                {
                    "id": f"PROJ-{i:03d}",
                    "name": name,
                    "orders": orders,
                    "providers": providers,
                    "budget": budget_val,
                    "spent": total_amount or 0,
                    "progress": progress_map.get(key, 0),
                    "startDate": start_date,
                    "endDate": end_date,
                }
            )

        return jsonify(
            {
                "items": items,
                "meta": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            }
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects_v2: %s", e)
        return (
            jsonify(
                {
                    "items": [],
                    "meta": {"total": 0, "limit": 25, "offset": 0},
                }
            ),
            500,
        )

@app.route("/api/providers")
def api_providers():
    """Agregados por proveedor a partir de purchase_orders_unified.

    Devuelve el contrato esperado por el frontend (ProviderData):
    id, rut, name, category, status, rating, totalAmount, lastOrder,
    ordersCount, paymentTerms, contact, email.
    """
    try:
        if not _data_available():
            return jsonify([])

        with db_conn(DB_PATH) as conn:
            cur = conn.execute(
                "SELECT vendor_rut AS rut, "
                "COALESCE(zoho_vendor_name, vendor_rut, 'Proveedor') AS name, "
                "COUNT(1) AS orders_count, "
                "SUM(COALESCE(total_amount, 0)) AS total_amount, "
                "MAX(po_date) AS last_order "
                "FROM purchase_orders_unified "
                "WHERE COALESCE(vendor_rut, '') <> '' "
                "GROUP BY vendor_rut, name "
                "ORDER BY total_amount DESC"
            )
            rows = cur.fetchall()

        providers = []
        for i, (
            rut,
            name,
            orders_count,
            total_amount,
            last_order,
        ) in enumerate(rows, start=1):
            rut_norm = _rut_normalize(rut)
            providers.append(
                {
                    "id": rut_norm or f"prov-{i:04d}",
                    "rut": rut_norm,
                    "name": name or "Proveedor",
                    "category": "servicios",
                    "status": "active",
                    "rating": 4.2,
                    "totalAmount": float(total_amount or 0),
                    "lastOrder": last_order or "",
                    "ordersCount": int(orders_count or 0),
                    "paymentTerms": "30 dias",
                    "contact": "",
                    "email": "",
                }
            )

        return jsonify(providers)
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/providers: %s", e)
        return jsonify([])


@app.route("/api/financial")
def api_financial():
    """Resumen financiero basico y movimientos recientes.

    Usa purchase_orders_unified como proxy de egresos (spend)
    segun DB_SCHEMA_AND_OPS.md. Revenue se reporta como 0 por ahora.
    """
    try:
        total_expenses = 0.0
        movements = []

        if _data_available():
            with db_conn(DB_PATH) as conn:
                # Totales
                cur = conn.execute(
                    "SELECT SUM(COALESCE(total_amount,0)) AS total, "
                    "MIN(po_date) AS start_date, MAX(po_date) AS end_date, "
                    "COUNT(1) AS cnt FROM purchase_orders_unified"
                )
                row = cur.fetchone()
                total_expenses = float(row["total"] or 0)

                # Movimientos recientes (proxy desde OC)
                cur = conn.execute(
                    "SELECT po_date AS date, "
                    "COALESCE(zoho_vendor_name, vendor_rut, 'Proveedor') AS description, "
                    "COALESCE(total_amount, 0) AS amount, "
                    "po_number AS reference FROM purchase_orders_unified "
                    "ORDER BY po_date DESC, rowid DESC LIMIT 50"
                )
                for r in cur.fetchall():
                    movements.append(
                        {
                            "id": f"mov-{len(movements)+1:04d}",
                            "date": r["date"] or "",
                            "description": r["description"],
                            "amount": float(r["amount"] or 0),
                            "type": "debit",
                            "account": "Cuenta Operativa",
                            "reference": r["reference"] or "",
                            "category": "purchase",
                        }
                    )

        total_revenue = 0.0
        net_profit = total_revenue - total_expenses
        profit_margin = (
            0.0
            if total_revenue == 0
            else round((net_profit / total_revenue) * 100, 2)
        )

        payload = {
            "summary": {
                "totalRevenue": round(total_revenue, 2),
                "totalExpenses": round(total_expenses, 2),
                "netProfit": round(net_profit, 2),
                "profitMargin": profit_margin,
                "cashflow": round(-total_expenses, 2),
                "pendingReceivables": 0,
                "pendingPayables": 0,
            },
            "bankAccounts": [
                {
                    "id": "acct-1",
                    "name": "Cuenta Operativa",
                    "bank": "Banco",
                    "balance": round(-total_expenses, 2),
                    "currency": "CLP",
                    "lastUpdate": datetime.now().isoformat(),
                }
            ],
            "movements": movements,
            "siiStatus": {
                "lastSync": datetime.now().isoformat(),
                "pendingInvoices": 0,
                "pendingBooks": 0,
                "status": "pending" if total_expenses == 0 else "synced",
            },
        }
        return jsonify(payload)
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/financial: %s", e)
        # Fallback minimo valido
        return jsonify(
            {
                "summary": {
                    "totalRevenue": 0,
                    "totalExpenses": 0,
                    "netProfit": 0,
                    "profitMargin": 0,
                    "cashflow": 0,
                    "pendingReceivables": 0,
                    "pendingPayables": 0,
                },
                "bankAccounts": [],
                "movements": [],
                "siiStatus": {
                    "lastSync": datetime.now().isoformat(),
                    "pendingInvoices": 0,
                    "pendingBooks": 0,
                    "status": "pending",
                },
            }
        )


# ----------------------------------------------------------------------------
# Control Financiero minimal endpoints (to satisfy tests)
# ----------------------------------------------------------------------------

@app.route("/api/projects/control")
def api_projects_control():
    """Entrega lista de proyectos con presupuesto, comprometido y disponible.

    Acepta with_meta=1 para retornar {projects:[...], meta:{...}}
    """
    try:
        args = request.args
        with_meta = args.get("with_meta") is not None
        items: list[dict] = []
        with db_conn(DB_PATH) as conn:
            cur = conn.cursor()
            # Intentar desde vistas canónicas si existen
            if _table_exists(conn, "v_presupuesto_totales"):
                cur.execute(
                    """
                    SELECT COALESCE(project_id, proyecto) AS project_key,
                           COALESCE(total_presupuesto, 0) AS budget_cost
                    FROM v_presupuesto_totales
                    """
                )
                pc_map = {
                    str(r[0]): float(r[1] or 0)
                    for r in cur.fetchall()
                    if r[0] is not None
                }
            else:
                pc_map = {}

            committed_map: dict[str, float] = {}
            if _table_exists(conn, "purchase_orders_unified"):
                cur.execute(
                    """
              SELECT COALESCE(zoho_project_id, zoho_project_name) AS
                  project_key,
                           SUM(COALESCE(total_amount,0)) AS committed
                    FROM purchase_orders_unified
                    GROUP BY project_key
                    """
                )
                for pid, committed in cur.fetchall():
                    if pid is not None:
                        committed_map[str(pid)] = float(committed or 0)

            # Unir claves de ambos mapas
            keys = set(pc_map.keys()) | set(committed_map.keys())
            for key in keys:
                budget_cost = float(pc_map.get(key, 0))
                committed = float(committed_map.get(key, 0))
                available_conservative = round(budget_cost - committed, 2)
                items.append(
                    {
                        "project_name": key,
                        "budget_cost": round(budget_cost, 2),
                        "committed": round(committed, 2),
                        "available_conservative": available_conservative,
                    }
                )


        if with_meta:
            return jsonify({
                "projects": items,
                "meta": {"total": len(items)}
            })
        else:
            return jsonify(items)
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/control: %s", e)
        payload = {"projects": [], "meta": {"total": 0}}
        return jsonify(payload if request.args.get("with_meta") else []), 200


@app.route("/api/aliases/project", methods=["POST"])
def api_aliases_project():
    """Registra (en memoria) un alias de proyecto 'from' -> 'to'.

    Para demo/test: persiste en MANUAL_CONTRACTS bajo clave 'project_aliases'.
    """
    try:
        data = request.get_json(silent=True) or {}
        src = (data.get("from") or "").strip()
        dest = (data.get("to") or "").strip()
        if not src or not dest:
            return jsonify({"ok": False, "error": "invalid_payload"}), 400
        aliases = MANUAL_CONTRACTS.get("project_aliases") or {}
        aliases[src] = dest
        MANUAL_CONTRACTS["project_aliases"] = aliases
        return jsonify({"ok": True, "from": src, "to": dest}), 201
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/aliases/project: %s", e)
        return jsonify({"ok": False}), 500


@app.route("/api/status")
def get_status():
    """Estado del sistema."""
    # Build stamp calculado una sola vez por proceso o entregado vía env
    global BUILD_STAMP
    if not BUILD_STAMP:
        BUILD_STAMP = (
            os.getenv("BUILD_STAMP")
            or f"Build: {datetime.now().isoformat()}"
        )
    return jsonify(
        {
            "version": "2.0-organizada",
            "database": "disponible" if _data_available() else "no_disponible",
            "certified_projects": len(CERTIFIED_PROJECTS),
            "docs_oficiales": DOCS_OFICIALES_DIR.exists(),
            "puerto_oficial": 5555,
            "cumple_ley_puertos": True,
            "timestamp": datetime.now().isoformat(),
            "build_stamp": BUILD_STAMP,
        }
    )


# ----------------------------------------------------------------------------
# Finanzas: Endpoints canónicos basados en vistas (Artículo IX)
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# Dashboards de Overview (Proyectos, Finanzas, CEO)
# ----------------------------------------------------------------------------

@app.route("/api/projects/overview")
def api_projects_overview():
    """Resumen ejecutivo de Proyectos (landing /proyectos/overview).

    Payload esperado por frontend (ideas/dashboard):
    {
      "portfolio": {"activos":N, "pc_total":0, "po":0, "disponible":0,
                     "ejecucion": {"grn":0, "ap":0, "pagado":0}},
      "salud": {"on_budget":0, "over_budget":0, "without_pc":0,
                 "tres_way":0, "riesgo": {"score":0, "reasons":[]}},
      "wip": {"ep_aprobados_sin_fv":0, "ep_en_revision":0},
      "acciones": [{"title":"…","cta":"/…"}]
    }
    """
    try:
        with db_conn(DB_PATH) as conn:
            cur = conn.cursor()

            # Proyectos activos (aprox): distintos proyectos con OC
            activos = 0
            po_total = 0.0
            if _table_exists(conn, "purchase_orders_unified"):
                try:
                    cur.execute(
                        (
                            "SELECT COUNT(DISTINCT COALESCE(zoho_project_id, "
                            "zoho_project_name)) FROM purchase_orders_unified"
                        )
                    )
                    activos = int(cur.fetchone()[0] or 0)
                except Exception:
                    activos = 0
                try:
                    cur.execute(
                        (
                            "SELECT SUM(COALESCE(total_amount,0)) FROM "
                            "purchase_orders_unified"
                        )
                    )
                    po_total = float(cur.fetchone()[0] or 0)
                except Exception:
                    po_total = 0.0

            # Presupuesto de Costos total (pc_total) desde vista si existe
            pc_total = 0.0
            if _table_exists(conn, "v_presupuesto_totales"):
                try:
                    cur.execute(
                        "SELECT SUM(COALESCE(total_presupuesto,0)) FROM v_presupuesto_totales"
                    )
                    pc_total = float(cur.fetchone()[0] or 0)
                except Exception:
                    pc_total = 0.0

            disponible = round(pc_total - po_total, 2)

            # Ejecución (fallbacks): GRN/AP/Pagado
            grn_total = 0.0
            ap_facturado = 0.0
            ap_pagado = 0.0
            # GRN: si existiese una vista de recepciones (no obligatoria)
            if _table_exists(conn, "v_recepciones_compra"):
                try:
                    cur.execute(
                        "SELECT SUM(COALESCE(monto,0)) FROM v_recepciones_compra"
                    )
                    grn_total = float(cur.fetchone()[0] or 0)
                except Exception:
                    grn_total = 0.0
            # AP facturado
            if _table_exists(conn, "v_facturas_compra"):
                try:
                    cur.execute(
                        "SELECT SUM(COALESCE(monto_total,0)) FROM v_facturas_compra"
                    )
                    ap_facturado = float(cur.fetchone()[0] or 0)
                except Exception:
                    ap_facturado = 0.0
            # AP pagado (proxy desde cartola si existe tipo/ categoría)
            if _table_exists(conn, "bank_movements"):
                try:
                    cur.execute(
                        "SELECT SUM(COALESCE(monto,0)) FROM bank_movements WHERE LOWER(COALESCE(tipo,''))='debit'"
                    )
                    ap_pagado = abs(float(cur.fetchone()[0] or 0))
                except Exception:
                    ap_pagado = 0.0

            portfolio = {
                "activos": activos,
                "pc_total": round(pc_total, 2),
                "po": round(po_total, 2),
                "disponible": round(disponible, 2),
                "ejecucion": {
                    "grn": round(grn_total, 2),
                    "ap": round(ap_facturado, 2),
                    "pagado": round(ap_pagado, 2),
                },
            }

            # Salud del portafolio
            without_pc = 0
            on_budget = None
            over_budget = None
            tres_way = None
            # Calcular proyectos con OC pero sin presupuesto
            try:
                if _table_exists(conn, "purchase_orders_unified"):
                    cur.execute(
                        "SELECT DISTINCT COALESCE(zoho_project_id, zoho_project_name) AS pid FROM purchase_orders_unified WHERE pid IS NOT NULL"
                    )
                    po_projects = {str(r[0]) for r in cur.fetchall() if r[0] is not None}
                else:
                    po_projects = set()
                if _table_exists(conn, "v_presupuesto_totales"):
                    cur.execute("SELECT DISTINCT project_id FROM v_presupuesto_totales")
                    pc_projects = {str(r[0]) for r in cur.fetchall() if r[0] is not None}
                else:
                    pc_projects = set()
                without_pc = max(0, len(po_projects - pc_projects))
            except Exception:
                without_pc = 0

            # Riesgo preliminar: falta de PC eleva score
            riesgo_score = 70 if without_pc > 0 else 40
            riesgo_reasons = (
                ["Falta presupuesto cargado en parte del portafolio"] if without_pc > 0 else []
            )

            salud = {
                "on_budget": on_budget,
                "over_budget": over_budget,
                "without_pc": without_pc,
                "tres_way": tres_way,
                "riesgo": {"score": riesgo_score, "reasons": riesgo_reasons},
            }

            # WIP de EP (ventas): requiere tablas de EP si existen
            ep_aprobados_sin_fv = 0
            ep_en_revision = 0
            try:
                if _table_exists(conn, "ep_headers"):
                    # aprobados sin factura de venta vinculada (si existiera ep->fv)
                    cur.execute(
                        "SELECT COUNT(1) FROM ep_headers WHERE LOWER(COALESCE(status,''))='approved'"
                    )
                    ep_aprobados_sin_fv = int(cur.fetchone()[0] or 0)
                if _table_exists(conn, "ep_headers"):
                    cur.execute(
                        "SELECT COUNT(1) FROM ep_headers WHERE LOWER(COALESCE(status,'')) IN ('draft','review')"
                    )
                    ep_en_revision = int(cur.fetchone()[0] or 0)
            except Exception:
                pass

            # EP metrics (ventas) a nivel portfolio usando vistas si existen
            ep_metrics = {"approved_amount": 0.0, "pending_invoice": 0.0}
            try:
                if _table_exists(conn, "v_ep_approved_project"):
                    cur.execute(
                        "SELECT SUM(COALESCE(ep_amount_net,0)) "
                        "FROM v_ep_approved_project"
                    )
                    row = cur.fetchone()
                    ep_metrics["approved_amount"] = float(row[0] or 0)
                if (
                    _table_exists(conn, "ep_headers")
                    and _table_exists(conn, "ep_lines")
                ):
                    # Pending invoice: approved lines minus invoiced/paid
                    cur.execute(
                        "SELECT COALESCE(SUM(l.amount_period),0) - "
                        "COALESCE((SELECT SUM(l2.amount_period) FROM "
                        "ep_lines l2 "
                        "JOIN ep_headers h2 ON h2.id=l2.ep_id "
                        "WHERE h2.status IN ('invoiced','paid')),0) AS pending "
                        "FROM ep_lines l JOIN ep_headers h ON h.id=l.ep_id "
                        "WHERE h.status='approved'"
                    )
                    row = cur.fetchone()
                    ep_metrics["pending_invoice"] = round(
                        float(row[0] or 0), 2
                    )
            except Exception:
                pass

            wip = {
                "ep_aprobados_sin_fv": ep_aprobados_sin_fv,
                "ep_en_revision": ep_en_revision,
                "ep_metrics": ep_metrics,
            }

            # Acciones sugeridas
            acciones = []
            if without_pc > 0:
                acciones.append(
                    {
                        "title": f"Falta presupuesto en {without_pc} proyectos",
                        "cta": "/presupuestos/importar",
                    }
                )
            if po_total > 0 and ap_facturado == 0:
                acciones.append(
                    {
                        "title": "Sin facturas AP vinculadas a compras (revisar migración)",
                        "cta": "/finanzas/facturas-compra",
                    }
                )

            return jsonify({
                "portfolio": portfolio,
                "salud": salud,
                "wip": wip,
                "acciones": acciones,
            })
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/overview: %s", e)
        return (
            jsonify(
                {
                    "portfolio": {"activos": 0, "pc_total": 0, "po": 0, "disponible": 0, "ejecucion": {"grn": 0, "ap": 0, "pagado": 0}},
                    "salud": {"on_budget": None, "over_budget": None, "without_pc": 0, "tres_way": None, "riesgo": {"score": 0, "reasons": []}},
                    "wip": {"ep_aprobados_sin_fv": 0, "ep_en_revision": 0},
                    "acciones": [],
                }
            ),
            200,
        )


@app.route("/api/finance/overview")
def api_finance_overview():
    """Resumen ejecutivo de Finanzas (landing /finanzas/overview)."""
    try:
        with db_conn(DB_PATH) as conn:
            cur = conn.cursor()

            # Caja hoy (placeholder: TODO fetch real bank balances)
            cash_today = 0.0
            try:
                if _table_exists(conn, "purchase_orders_unified"):
                    # Using PO totals as very rough proxy (improve later)
                    cur.execute(
                        "SELECT SUM(COALESCE(total_amount,0)) FROM purchase_orders_unified"
                    )
                    val = cur.fetchone()[0]
                    cash_today = float(val or 0)
            except Exception:
                cash_today = 0.0

            cash = {
                "today": round(cash_today, 2),
                "d7": None,
                "d30": None,
                "d60": None,
                "d90": None,
                "shortfall_7": None,
                "shortfall_30": None,
            }

            # Ingresos reales (ventas)
            month_rev = 0.0
            ytd_rev = 0.0
            if _table_exists(conn, "v_facturas_venta"):
                try:
                    cur.execute(
                        "SELECT SUM(monto_total) FROM v_facturas_venta "
                        "WHERE strftime('%Y-%m', fecha)=strftime('%Y-%m','now')"
                    )
                    month_rev = float(cur.fetchone()[0] or 0)
                    cur.execute(
                        "SELECT SUM(monto_total) FROM v_facturas_venta "
                        "WHERE date(fecha)>=date(strftime('%Y-01-01','now'))"
                    )
                    ytd_rev = float(cur.fetchone()[0] or 0)
                except Exception:
                    month_rev = 0.0
                    ytd_rev = 0.0

            revenue = {
                "month": {
                    "real": round(month_rev, 2),
                    "plan": None,
                    "delta_pct": None,
                },
                "ytd": {
                    "real": round(ytd_rev, 2),
                    "plan": None,
                    "delta_pct": None,
                },
                "spark": [],
            }

            # AR aging (fallback 0 si no hay datos)
            ar = {"d1_30": 0, "d31_60": 0, "d60_plus": 0, "top_clientes": []}
            if _table_exists(conn, "v_facturas_venta"):
                try:
                    # Top clientes por monto
                    cur.execute(
                        "SELECT COALESCE(cliente_nombre,'Cliente'), "
                        "SUM(COALESCE(monto_total,0)) AS total "
                        "FROM v_facturas_venta GROUP BY cliente_nombre "
                        "ORDER BY total DESC LIMIT 5"
                    )
                    for nombre, total in cur.fetchall():
                        ar["top_clientes"].append({
                            "nombre": nombre or "Cliente",
                            "pendiente": float(total or 0),
                        })
                except Exception:
                    pass

            # AP schedule (pagos próximos) desde facturas de compra
            ap = {"d7": 0, "d14": 0, "d30": 0, "top_proveedores": []}
            if _table_exists(conn, "v_facturas_compra"):
                try:
                    cur.execute(
                        "SELECT COALESCE(proveedor_nombre, proveedor_rut, 'Proveedor') "
                        "AS nombre, "
                        "SUM(COALESCE(monto_total,0)) AS total FROM "
                        "v_facturas_compra "
                        "GROUP BY nombre ORDER BY total DESC LIMIT 5"
                    )
                    for nombre, total in cur.fetchall():
                        ap["top_proveedores"].append({
                            "nombre": nombre or "Proveedor",
                            "por_pagar": float(total or 0),
                        })
                except Exception:
                    pass

            # Conciliación (placeholder si no existen vistas)
            conciliacion = {"porc_conciliado": 0, "auto_match": 0}
            if _table_exists(conn, "v_kpi_conciliacion"):
                try:
                    cur.execute(
                        "SELECT AVG(COALESCE(porc_conciliado,0)), AVG(COALESCE(auto_match,0)) FROM v_kpi_conciliacion"
                    )
                    row = cur.fetchone()
                    if row:
                        conciliacion = {
                            "porc_conciliado": round(float(row[0] or 0), 2),
                            "auto_match": round(float(row[1] or 0), 2),
                        }
                except Exception:
                    pass

            # EP / AR metrics integración cashflow básico
            ep_sales = {
                "approved_net": 0.0,
                "expected_inflow": 0.0,
                "actual_collections": 0.0,
                "pending_invoice": 0.0,
            }
            try:
                if _table_exists(conn, "v_ep_approved_project"):
                    cur.execute(
                        "SELECT SUM(COALESCE(ep_amount_net,0)) "
                        "FROM v_ep_approved_project"
                    )
                    row = cur.fetchone()
                    ep_sales["approved_net"] = float(row[0] or 0)
                if _table_exists(conn, "v_ar_expected_project"):
                    cur.execute(
                        "SELECT SUM(COALESCE(expected_inflow,0)) "
                        "FROM v_ar_expected_project"
                    )
                    row = cur.fetchone()
                    ep_sales["expected_inflow"] = float(row[0] or 0)
                if _table_exists(conn, "v_ar_actual_project"):
                    cur.execute(
                        "SELECT SUM(COALESCE(actual_inflow,0)) "
                        "FROM v_ar_actual_project"
                    )
                    row = cur.fetchone()
                    ep_sales["actual_collections"] = float(row[0] or 0)
                if (
                    _table_exists(conn, "ep_headers")
                    and _table_exists(conn, "ep_lines")
                ):
                    cur.execute(
                        "SELECT COALESCE(SUM(l.amount_period),0) - "
                        "COALESCE((SELECT SUM(l2.amount_period) FROM ep_lines l2 "
                        "JOIN ep_headers h2 ON h2.id=l2.ep_id "
                        "WHERE h2.status IN ('invoiced','paid')),0) AS pending "
                        "FROM ep_lines l JOIN ep_headers h ON h.id=l.ep_id "
                        "WHERE h.status='approved'"
                    )
                    row = cur.fetchone()
                    ep_sales["pending_invoice"] = round(
                        float(row[0] or 0), 2
                    )
            except Exception:
                pass

            acciones = []
            if ytd_rev == 0:
                acciones.append({"title": "No hay facturas de venta cargadas (AR)", "cta": "/finanzas/facturas-venta"})
            if not ar["top_clientes"]:
                acciones.append({"title": "Cargar AR (Chipax/SII) para aging de Cobros", "cta": "/finanzas/facturas-venta"})

            return jsonify({
                "cash": cash,
                "revenue": revenue,
                "margin": {"month_pct": None, "plan_pct": None, "delta_pp": None},
                "ar": ar,
                "ap": ap,
                "conciliacion": conciliacion,
                "ep_sales": ep_sales,
                "acciones": acciones,
            })
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/finance/overview: %s", e)
        return (
            jsonify(
                {
                    "cash": {"today": 0, "d7": None, "d30": None, "d60": None, "d90": None, "shortfall_7": None, "shortfall_30": None},
                    "revenue": {"month": {"real": 0, "plan": None, "delta_pct": None}, "ytd": {"real": 0, "plan": None, "delta_pct": None}, "spark": []},
                    "margin": {"month_pct": None, "plan_pct": None, "delta_pp": None},
                    "ar": {"d1_30": 0, "d31_60": 0, "d60_plus": 0, "top_clientes": []},
                    "ap": {"d7": 0, "d14": 0, "d30": 0, "top_proveedores": []},
                    "conciliacion": {"porc_conciliado": 0, "auto_match": 0},
                    "acciones": [],
                }
            ),
            200,
        )


@app.route("/api/ceo/overview")
def api_ceo_overview():
    """CEO overview minimal, alineado al builder (ideas/dashboard)."""
    try:
        with db_conn(DB_PATH) as conn:
            cur = conn.cursor()
            # Cash hoy
            cash_today = 0.0
            if _table_exists(conn, "bank_movements"):
                rows = conn.execute(
                    "SELECT bank_name, account_number, MAX(date(fecha)) AS last_date FROM bank_movements GROUP BY bank_name, account_number"
                ).fetchall()
                for bank_name, account_number, last_date in rows:
                    if not last_date:
                        continue
                    cur.execute(
                        """
                        SELECT saldo FROM bank_movements
                         WHERE bank_name IS AND account_number IS AND date(fecha)=?
                         ORDER BY datetime(fecha) DESC, rowid DESC LIMIT 1
                        """,
                        (bank_name, account_number, last_date),
                    )
                    r = cur.fetchone()
                    if r and r[0] is not None:
                        cash_today += float(r[0] or 0)

            # Revenue
            month = 0.0
            ytd = 0.0
            if _table_exists(conn, "v_facturas_venta"):
                cur.execute(
                    "SELECT SUM(monto_total) FROM v_facturas_venta WHERE strftime('%Y-%m', fecha)=strftime('%Y-%m','now')"
                )
                month = float(cur.fetchone()[0] or 0)
                cur.execute(
                    "SELECT SUM(monto_total) FROM v_facturas_venta WHERE date(fecha)>=date(strftime('%Y-01-01','now'))"
                )
                ytd = float(cur.fetchone()[0] or 0)

            proj_total = 0
            with_pc = 0
            if _table_exists(conn, "v_ordenes_compra"):
                cur.execute("SELECT COUNT(DISTINCT project_id) FROM v_ordenes_compra WHERE project_id IS NOT NULL")
                proj_total = int(cur.fetchone()[0] or 0)
            elif _table_exists(conn, "purchase_orders_unified"):
                # Detect columns safely
                cols = []
                try:
                    cur.execute(
                        "PRAGMA table_info(purchase_orders_unified)"
                    )
                    cols = [r[1] for r in cur.fetchall()]
                except Exception:
                    cols = []
                if (
                    "zoho_project_id" in cols and
                    "zoho_project_name" in cols
                ):
                    cur.execute(
                        "SELECT COUNT(DISTINCT COALESCE("  # noqa: E501
                        "zoho_project_id, zoho_project_name)) "
                        "FROM purchase_orders_unified"
                    )
                elif "zoho_project_name" in cols:
                    cur.execute(
                        "SELECT COUNT(DISTINCT zoho_project_name) "
                        "FROM purchase_orders_unified "
                        "WHERE zoho_project_name IS NOT NULL"
                    )
                else:
                    cur.execute(
                        "SELECT COUNT(DISTINCT vendor_rut) "
                        "FROM purchase_orders_unified"
                    )
                proj_total = int(cur.fetchone()[0] or 0)
            if _table_exists(conn, "v_presupuesto_totales"):
                cur.execute(
                    "SELECT COUNT(DISTINCT project_id) "
                    "FROM v_presupuesto_totales"
                )
                with_pc = int(cur.fetchone()[0] or 0)
            without_pc = max(0, proj_total - with_pc)

            actions_list = [
                {
                    "title": "Importar presupuestos reales (XLSX)",
                    "cta": "/presupuestos/importar",
                },
                {
                    "title": "Importar facturas de venta desde Chipax/SII",
                    "cta": "/ventas/importar",
                },
            ]
            payload = {
                "generated_at": datetime.now().isoformat() + "Z",
                "cash": {
                    "today": round(cash_today, 2),
                    "d7": None,
                    "d30": None,
                    "d60": None,
                    "d90": None,
                    "shortfall_7": None,
                    "shortfall_30": None,
                },
                "revenue": {
                    "month": {
                        "real": round(month, 2),
                        "plan": None,
                        "delta_pct": None,
                    },
                    "ytd": {
                        "real": round(ytd, 2),
                        "plan": None,
                        "delta_pct": None,
                    },
                    "spark": [],
                },
                "margin": {
                    "month_pct": None,
                    "plan_pct": None,
                    "delta_pp": None,
                    "top_projects": [],
                },
                "working_cap": {
                    "dso": None,
                    "dpo": None,
                    "dio": None,
                    "ccc": None,
                    "ar": {"d1_30": 0, "d31_60": 0, "d60_plus": 0},
                    "ap": {"d7": 0, "d14": 0, "d30": 0},
                },
                "backlog": {
                    "total": None,
                    "cobertura_meses": None,
                    "pipeline_weighted": None,
                    "pipeline_vs_goal_pct": None,
                },
                "projects": {
                    "total": proj_total,
                    "on_budget": None,
                    "over_budget": None,
                    "without_pc": without_pc,
                    "three_way_violations": None,
                    "wip_ep_to_invoice": None,
                },
                "risk": {
                    "score": 70 if without_pc > 0 else 40,
                    "reasons": (
                        ["Falta presupuesto en proyectos"]
                        if without_pc > 0
                        else []
                    ),
                },
                "alerts": (
                    [
                        {
                            "kind": "data_quality",
                            "title": (
                                f"Falta presupuesto en {without_pc} proyectos"
                            ),
                            "cta": "/presupuestos/importar",
                        }
                    ]
                    if without_pc > 0
                    else []
                )
                + (
                    [
                        {
                            "kind": "data_gap",
                            "title": "No hay facturas de venta cargadas (AR)",
                            "cta": "/ventas/importar",
                        }
                    ]
                    if ytd == 0
                    else []
                ),
                "actions": actions_list,
                "acciones": actions_list,
                "diagnostics": {
                    "has_sales_invoices": bool(ytd),
                    "has_budgets": with_pc > 0,
                },
            }
            return jsonify(payload)
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/ceo/overview: %s", e)
        return jsonify({"error": "server_error"}), 500


# -----------------------------
# Roadmap quick-wins endpoints
# -----------------------------

@app.route("/api/finance/treasury/forecast")
def api_treasury_forecast():
    """Daily/weekly simple cash forecast using v_cashflow_semana if present,
    else fallback to last 12 weeks aggregated by bank_movements.
    """
    try:
        with db_conn(DB_PATH) as conn:
            if _table_exists(conn, "v_cashflow_semana"):
                cur = conn.execute(
                    "SELECT semana, categoria, "
                    "SUM(COALESCE(monto,0)) AS monto, "
                    "COALESCE(moneda,'CLP') AS moneda, "
                    "COALESCE(status,'plan') AS status "
                    "FROM v_cashflow_semana "
                    "GROUP BY semana, categoria, moneda, status"
                )
                rows = [dict(r) for r in cur.fetchall()]
                return jsonify({"items": rows})
            # Fallback: weekly net by movement type
            cur = conn.execute(
                "SELECT strftime('%Y-W%W', fecha) AS semana, "
                "SUM(CASE WHEN LOWER(COALESCE(tipo,''))='credit' "
                "THEN COALESCE(monto,0) ELSE -COALESCE(monto,0) END) AS neto "
                "FROM bank_movements GROUP BY semana "
                "ORDER BY semana DESC LIMIT 12"
            )
            rows = [dict(r) for r in cur.fetchall()]
            return jsonify({"items": rows})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en treasury forecast: %s", e)
        return jsonify({"items": []}), 200


@app.post("/api/conciliacion/feedback")
def api_conciliacion_feedback():
    """Registrar evento de feedback de conciliación.

    Acciones soportadas: accept, reject, missing_link.
    Campos opcionales: reconciliation_id, reason, source.
    """
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip().lower()
    if action not in {"accept", "reject", "missing_link"}:
        return jsonify({"error": "invalid_action"}), 422
    rec_id = data.get("reconciliation_id")
    reason = (data.get("reason") or "").strip() or None
    source = (data.get("source") or "manual").strip() or "manual"
    source = source[:32]
    try:
        with db_conn(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS recon_feedback_events (
                  id INTEGER PRIMARY KEY,
                  created_at TEXT DEFAULT (datetime('now')),
                  reconciliation_id INTEGER,
                  action TEXT NOT NULL,
                  reason TEXT,
                  source TEXT
                )
                """
            )
            cur.execute(
                "INSERT INTO recon_feedback_events(reconciliation_id, action, reason, source) VALUES(?,?,?,?)",
                (rec_id, action, reason, source),
            )
            rid = cur.lastrowid
            conn.commit()
            return jsonify({"id": rid, "stored": True})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en conciliacion feedback: %s", e)
        return jsonify({"error": "server_error"}), 500


@app.post("/api/conciliacion/action")
def api_conciliacion_action():
    """Registrar acción placeholder de split / merge (no ejecuta lógica todavía).

    JSON Body:
      action: 'split' | 'merge'
      reconciliation_id (int opcional)
      payload (obj) campos libres (por ejemplo cuentas a dividir, ids a unir)
      user_id (str opcional)
    Respuesta: {id, stored}
    """
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").strip().lower()
    if action not in {"split", "merge"}:
        return jsonify({"error": "invalid_action"}), 422
    rec_id = data.get("reconciliation_id")
    user_id = data.get("user_id")
    payload = data.get("payload") or {}
    try:
        payload_json = json.dumps(payload, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        return jsonify({"error": "invalid_payload"}), 400
    try:
        with db_conn(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS recon_actions (
                  id INTEGER PRIMARY KEY,
                  created_at TEXT DEFAULT (datetime('now')),
                  reconciliation_id INTEGER,
                  action TEXT NOT NULL,
                  payload_json TEXT,
                  user_id TEXT
                )
                """
            )
            cur.execute(
                "INSERT INTO recon_actions(reconciliation_id, action, payload_json, user_id) VALUES(?,?,?,?)",
                (rec_id, action, payload_json, user_id),
            )
            rid = cur.lastrowid
            conn.commit()
            return jsonify({"id": rid, "stored": True})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en conciliacion action: %s", e)
        return jsonify({"error": "server_error"}), 500


@app.get("/api/conciliacion/actions")
def api_conciliacion_actions():
    """Listar acciones split/merge registradas (limit=100 por defecto)."""
    try:
        limit = int(request.args.get("limit", "100"))
    except ValueError:
        limit = 100
    limit = max(1, min(limit, 500))
    try:
        with db_conn(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS recon_actions (
                  id INTEGER PRIMARY KEY,
                  created_at TEXT DEFAULT (datetime('now')),
                  reconciliation_id INTEGER,
                  action TEXT NOT NULL,
                  payload_json TEXT,
                  user_id TEXT
                )
                """
            )
            cur.execute(
                "SELECT id, created_at, reconciliation_id, action, payload_json, user_id FROM recon_actions ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = []
            for r in cur.fetchall():
                try:
                    payload_obj = json.loads(r[4]) if r[4] else None
                except Exception:  # noqa: BLE001
                    payload_obj = None
                rows.append({
                    "id": r[0],
                    "created_at": r[1],
                    "reconciliation_id": r[2],
                    "action": r[3],
                    "payload": payload_obj,
                    "user_id": r[5],
                })
            return jsonify({"items": rows, "count": len(rows)})
    except Exception as e:  # noqa: BLE001
        logger.error("Error listando recon actions: %s", e)
        return jsonify({"items": [], "error": "server_error"}), 500


@app.route("/api/metrics/matching_summary")
def api_matching_summary():
    """Resumen ligero de métricas AP y AR.

    Reúne:
      - ap_events_total: filas en ap_match_events
      - ap_events_accepted: accepted=1
      - ar_map_events: filas en ar_map_events
      - auto_assign_success: eventos AR con reason que contenga 'auto_assign'

    Cache simple vía snapshot table (match_metrics_snapshots) para evitar
    costo reiterado cuando se consulta desde dashboard: si el último snapshot
    es <15 minutos se devuelve ese.
    """
    try:
        with db_conn(DB_PATH) as conn:
            cur = conn.cursor()
            # Ensure snapshot table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS match_metrics_snapshots (
                  id INTEGER PRIMARY KEY,
                  created_at TEXT DEFAULT (datetime('now')),
                  ap_events_total INTEGER,
                  ap_events_accepted INTEGER,
                  ar_map_events INTEGER,
                  auto_assign_success INTEGER
                )
                """
            )
            # Reuse recent snapshot (<15 min)
            row = cur.execute(
                "SELECT id, created_at, ap_events_total, ap_events_accepted, ar_map_events, auto_assign_success "
                "FROM match_metrics_snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                try:
                    # Compare minutes difference
                    created = datetime.fromisoformat(row[1].replace("Z", "")) if "T" in row[1] else datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S")
                    delta_min = (datetime.now() - created).total_seconds() / 60.0
                except Exception:
                    delta_min = 999
                if delta_min < 15:
                    return jsonify({
                        "cached": True,
                        "generated_at": row[1],
                        "ap_events_total": row[2],
                        "ap_events_accepted": row[3],
                        "ar_map_events": row[4],
                        "auto_assign_success": row[5],
                        "ap_acceptance_rate": (round(row[3] / row[2], 4) if row[2] else None),
                    })
            # Fresh calculation (tables may not exist yet)
            def _count(sql: str) -> int:
                try:
                    r = cur.execute(sql).fetchone()
                    return int(r[0] or 0)
                except Exception:
                    return 0
            ap_events_total = _count("SELECT COUNT(1) FROM ap_match_events")
            ap_events_accepted = _count("SELECT COUNT(1) FROM ap_match_events WHERE accepted=1")
            ar_map_events = _count("SELECT COUNT(1) FROM ar_map_events")
            auto_assign_success = _count("SELECT COUNT(1) FROM ar_map_events WHERE reasons LIKE '%auto_assign%'")
            cur.execute(
                "INSERT INTO match_metrics_snapshots(ap_events_total, ap_events_accepted, ar_map_events, auto_assign_success) VALUES(?,?,?,?)",
                (ap_events_total, ap_events_accepted, ar_map_events, auto_assign_success),
            )
            conn.commit()
            return jsonify({
                "cached": False,
                "generated_at": datetime.now().isoformat() + "Z",
                "ap_events_total": ap_events_total,
                "ap_events_accepted": ap_events_accepted,
                "ar_map_events": ar_map_events,
                "auto_assign_success": auto_assign_success,
                "ap_acceptance_rate": (round(ap_events_accepted / ap_events_total, 4) if ap_events_total else None),
            })
    except Exception as e:  # noqa: BLE001
        logger.error("Error en matching_summary: %s", e)
        return jsonify({"error": "server_error"}), 500


@app.route("/api/threeway/violations")
def api_threeway_violations():
    """Three-way match violations placeholder.
    Returns counts grouped by project if views exist; otherwise empty.
    """
    try:
        with db_conn(DB_PATH) as conn:
            if _table_exists(conn, "v_threeway_violations"):
                cur = conn.execute(
                    "SELECT project_id, COUNT(1) AS violaciones "
                    "FROM v_threeway_violations "
                    "GROUP BY project_id ORDER BY violaciones DESC"
                )
                rows = [dict(r) for r in cur.fetchall()]
                return jsonify({"items": rows})
            # Fallback: no data
            return jsonify({"items": []})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en threeway violations: %s", e)
        return jsonify({"items": []}), 200


# --------------------------------------
# Conciliación: Sync importador de Chipax
# --------------------------------------

@app.post("/api/reconciliaciones/sync_chipax")
def api_sync_chipax():
    """Ejecuta importador Chipax y devuelve métricas.

    Seguro para dev: si el importador no existe o falla, responde vacío.
    """
    try:
        metrics: dict[str, int] = {}
        try:
            import sys as _sys
            tools_dir = str((PROJECT_ROOT / "tools").resolve())
            if tools_dir not in _sys.path:
                _sys.path.append(tools_dir)
            from import_chipax_conciliacion import run as _run  # type: ignore

            metrics = _run() or {}
        except Exception as _e:  # noqa: BLE001
            logger.warning("sync_chipax importer no disponible: %s", _e)
            metrics = {}
        return jsonify({"ok": True, "metrics": metrics})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en sync_chipax: %s", e)
        return jsonify({"ok": False, "metrics": {}}), 200

# Utilidades locales: RUT normalize usando tools/rut_utils si está disponible
def _rut_normalize(val: str | None) -> str | None:
    """Delegar a backend.utils.chile.rut_normalize si existe, fallback simple."""
    try:
        from backend.utils.chile import rut_normalize as _rn  # type: ignore

        return _rn(val)  # type: ignore
    except Exception:  # pragma: no cover - fallback
        if not val:
            return val
        return val.strip().upper().replace(".", "")


def _norm_name(val: str | None) -> str:
    try:
        if val is None:
            return ""
        s = unicodedata.normalize("NFKD", str(val))
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        return s.strip().lower()
    except Exception:
        return (val or "").strip().lower()


def _po_next_number(conn: sqlite3.Connection) -> str:
    """Entrega el siguiente número correlativo de OC (Ofitec).
    Usa ofitec_sequences; crea con defaults si no existe.
    """
    # Ensure table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ofitec_sequences (
          name TEXT PRIMARY KEY,
          prefix TEXT,
          padding INTEGER DEFAULT 0,
          next_value INTEGER NOT NULL,
          enable_manual INTEGER DEFAULT 1,
          updated_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    cur = conn.execute(
        "SELECT prefix, padding, next_value FROM ofitec_sequences WHERE name = ?",
        ("po_number",),
    )
    row = cur.fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO ofitec_sequences(name, prefix, padding, next_value, enable_manual) VALUES(?,?,?,?,?)",
            ("po_number", "PO-", 5, 1, 1),
        )
        prefix, padding, next_value = "PO-", 5, 1
    else:
        prefix = row[0] or ""
        padding = int(row[1] or 0)
        next_value = int(row[2] or 1)
    num = f"{prefix}{next_value:0{padding}d}" if padding and padding > 0 else f"{prefix}{next_value}"
    conn.execute(
        "UPDATE ofitec_sequences SET next_value = ?, updated_at = datetime('now') WHERE name = ?",
        (next_value + 1, "po_number"),
    )
    return num


def _po_peek_number(conn: sqlite3.Connection) -> str:
    """Obtiene el próximo número sin incrementar la secuencia."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ofitec_sequences (
          name TEXT PRIMARY KEY,
          prefix TEXT,
          padding INTEGER DEFAULT 0,
          next_value INTEGER NOT NULL,
          enable_manual INTEGER DEFAULT 1,
          updated_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    cur = conn.execute(
        "SELECT prefix, padding, next_value FROM ofitec_sequences WHERE name = ?",
        ("po_number",),
    )
    row = cur.fetchone()
    if row is None:
        prefix, padding, next_value = "PO-", 5, 1
    else:
        prefix = row[0] or ""
        padding = int(row[1] or 0)
        next_value = int(row[2] or 1)
    return f"{prefix}{next_value:0{padding}d}" if padding and padding > 0 else f"{prefix}{next_value}"


@app.route("/api/purchase_orders/peek_number")
def api_po_peek_number():
    try:
        with db_conn(DB_PATH) as conn:
            nxt = _po_peek_number(conn)
        return jsonify({"next_number": nxt})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en peek_number: %s", e)
        return jsonify({"error": "peek_failed"}), 500


def _query_view(
    view_name: str,
    filters: dict[str, str],
    page: int = 1,
    page_size: int = 50,
    order_by: str | None = None,
    order_dir: str = "DESC",
):
    """Generic SELECT with simple, parameterized filters and pagination."""
    # Per-view specs to avoid referencing non-existent columns
    view_specs = {
        "v_facturas_compra": {
            "columns": {
                "documento_numero",
                "fecha",
                "proveedor_rut",
                "proveedor_nombre",
                "monto_total",
                "moneda",
                "estado",
                "fuente",
            },
            # Columns to use for free-text search
            "search_cols": ["proveedor_nombre", "documento_numero"],
            # Columns to match when filtering by rut
            "rut_cols": ["proveedor_rut"],
            # Allowed ORDER BY fields
            "order_fields": [
                "fecha",
                "monto_total",
                "proveedor_nombre",
                "proveedor_rut",
                "documento_numero",
            ],
        },
        "v_facturas_venta": {
            "columns": {
                "documento_numero",
                "fecha",
                "cliente_rut",
                "cliente_nombre",
                "monto_total",
                "moneda",
                "estado",
                "fuente",
            },
            "search_cols": ["cliente_nombre", "documento_numero"],
            "rut_cols": ["cliente_rut"],
            "order_fields": [
                "fecha",
                "monto_total",
                "cliente_nombre",
                "cliente_rut",
                "documento_numero",
            ],
        },
        "v_cartola_bancaria": {
            "columns": {
                "fecha",
                "banco",
                "cuenta",
                "glosa",
                "monto",
                "moneda",
                "tipo",
                "saldo",
                "referencia",
                "fuente",
                # Campos adicionales de la vista (cuando existen)
                "conciliado",
                "n_docs",
                "monto_conciliado",
                # Campo virtual para filtrar por estado de conciliación
                "estado",
            },
            "search_cols": ["glosa", "referencia"],
            "rut_cols": ["referencia"],
            "order_fields": ["fecha", "monto", "banco", "cuenta", "glosa"],
        },
        "v_gastos": {
            "columns": {
                "gasto_id",
                "fecha",
                "categoria",
                "descripcion",
                "monto",
                "moneda",
                "proveedor_rut",
                "proyecto",
                "fuente",
            },
            "search_cols": ["descripcion", "categoria", "proyecto"],
            "rut_cols": ["proveedor_rut"],
            "order_fields": ["fecha", "monto", "categoria", "proyecto"],
        },
        "v_impuestos": {
            "columns": {
                "periodo",
                "tipo",
                "monto_debito",
                "monto_credito",
                "neto",
                "estado",
                "fecha_presentacion",
                "fuente",
            },
            "search_cols": ["tipo", "estado"],
            "rut_cols": [],
            "order_fields": ["periodo", "neto", "monto_debito", "monto_credito"],
        },
        "v_previred": {
            "columns": {
                "periodo",
                "rut_trabajador",
                "nombre_trabajador",
                "rut_empresa",
                "monto_total",
                "estado",
                "fecha_pago",
                "fuente",
            },
            "search_cols": ["nombre_trabajador", "rut_trabajador"],
            "rut_cols": ["rut_trabajador", "rut_empresa"],
            "order_fields": ["periodo", "monto_total", "fecha_pago"],
        },
        "v_sueldos": {
            "columns": {
                "periodo",
                "rut_trabajador",
                "nombre_trabajador",
                "cargo",
                "bruto",
                "liquido",
                "descuentos",
                "fecha_pago",
                "fuente",
            },
            "search_cols": ["nombre_trabajador", "cargo"],
            "rut_cols": ["rut_trabajador"],
            "order_fields": ["periodo", "bruto", "liquido", "fecha_pago"],
        },
    }

    allowed_order_fields = {
        name: spec["order_fields"] for name, spec in view_specs.items()
    }

    clauses = ["1=1"]
    params: list = []

    spec = view_specs.get(view_name, None)
    cols = spec["columns"] if spec else set()

    # Filters (applied only if relevant columns exist in the view)
    if v := filters.get("rut"):
        # Build OR across rut_cols when present
        if spec and spec.get("rut_cols"):
            or_parts = []
            for c in spec["rut_cols"]:
                if c in cols:
                    or_parts.append("COALESCE(" + c + ", '') = ?")
                    params.append(v)
            if or_parts:
                clauses.append("(" + " OR ".join(or_parts) + ")")
    if v := filters.get("moneda"):
        if "moneda" in cols:
            clauses.append("COALESCE(moneda, 'CLP') = ?")
            params.append(v)
    # Special-case: permitir filtrar estado en cartola bancaria aunque sea un campo virtual
    handled_estado = False
    if v := filters.get("estado"):
        if view_name == "v_cartola_bancaria":
            # Interpretar 'estado' como confirmado/pendiente en base a existencia de links de conciliación
            # Usamos el id de la vista (bm.id AS id) para verificar en recon_links
            if v in ("confirmado", "pendiente"):
                cond = (
                    "CASE WHEN EXISTS(SELECT 1 FROM recon_links rl WHERE rl.bank_movement_id = id) "
                    "THEN 'confirmado' ELSE 'pendiente' END = ?"
                )
                clauses.append(cond)
                params.append(v)
                handled_estado = True
        # Camino estándar: solo si no fue manejado como especial
        if not handled_estado and "estado" in cols:
            clauses.append("COALESCE(estado, 'unknown') = ?")
            params.append(v)
    if v := filters.get("date_from"):
        if "fecha" in cols:
            clauses.append("fecha >= ?")
            params.append(v)
    if v := filters.get("date_to"):
        if "fecha" in cols:
            clauses.append("fecha <= ?")
            params.append(v)
    if v := filters.get("search"):
        if spec and spec.get("search_cols"):
            like = f"%{v}%"
            or_parts = []
            for c in spec["search_cols"]:
                if c in cols:
                    or_parts.append("COALESCE(" + c + ", '') LIKE ?")
                    params.append(like)
            if or_parts:
                clauses.append("(" + " OR ".join(or_parts) + ")")

    where_sql = " AND ".join(clauses)

    # Order by (safelist)
    order_sql = ""
    if order_by and view_name in allowed_order_fields:
        if order_by in allowed_order_fields[view_name]:
            dir_sql = (
                "ASC" if order_dir and order_dir.upper() == "ASC" else "DESC"
            )
            order_sql = f" ORDER BY {order_by} {dir_sql}"

    # Pagination
    page = max(1, int(page))
    page_size = max(1, min(200, int(page_size)))
    offset = (page - 1) * page_size

    # Queries
    data_sql = (
        f"SELECT * FROM {view_name} WHERE {where_sql}{order_sql} "
        "LIMIT OFFSET ?"
    )
    count_sql = f"SELECT COUNT(1) FROM {view_name} WHERE {where_sql}"

    with db_conn(DB_PATH) as conn:
        # count
        cur = conn.execute(count_sql, params)
        total = cur.fetchone()[0]
        # data
        cur = conn.execute(data_sql, [*params, page_size, offset])
        rows = [dict(r) for r in cur.fetchall()]

    return {
        "items": rows,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if page_size else 1,
        },
    }


@app.route("/api/finanzas/facturas_compra")
def api_facturas_compra():
    try:
        args = request.args
        result = _query_view(
            "v_facturas_compra",
            filters={k: v for k, v in {
                "rut": args.get("rut", type=str),
                "moneda": args.get("moneda", type=str),
                "estado": args.get("estado", type=str),
                "date_from": args.get("date_from", type=str),
                "date_to": args.get("date_to", type=str),
                "search": args.get("search", type=str),
            }.items() if v is not None},
            page=args.get("page", default=1, type=int),
            page_size=args.get("page_size", default=50, type=int),
            order_by=args.get("order_by", default="fecha", type=str),
            order_dir=args.get("order_dir", default="DESC", type=str),
        )
        return jsonify(result)
    except Exception as e:  # noqa: BLE001
        logger.error("Error en facturas_compra: %s", e)
        return jsonify(
            {
                "items": [],
                "meta": {
                    "total": 0,
                    "page": 1,
                    "page_size": 50,
                    "pages": 0,
                },
            }
        ), 200


@app.route("/api/finanzas/cartola_bancaria")
def api_cartola_bancaria():
    try:
        args = request.args
        result = _query_view(
            "v_cartola_bancaria",
            filters={k: v for k, v in {
                "rut": args.get("rut", type=str),
                "moneda": args.get("moneda", type=str),
                "estado": args.get("estado", type=str),
                "date_from": args.get("date_from", type=str),
                "date_to": args.get("date_to", type=str),
                "search": args.get("search", type=str),
            }.items() if v is not None},
            page=args.get("page", default=1, type=int),
            page_size=args.get("page_size", default=50, type=int),
            order_by=args.get("order_by", default="fecha", type=str),
            order_dir=args.get("order_dir", default="DESC", type=str),
        )
        return jsonify(result)
    except Exception as e:  # noqa: BLE001
        logger.error("Error en cartola_bancaria: %s", e)
        return jsonify(
            {
                "items": [],
                "meta": {
                    "total": 0,
                    "page": 1,
                    "page_size": 50,
                    "pages": 0,
                },
            }
        ), 200

@app.route("/api/finanzas/facturas_venta")
def api_facturas_venta():
    try:
        args = request.args
        result = _query_view(
            "v_facturas_venta",
            filters={k: v for k, v in {
                "rut": args.get("rut", type=str),
                "moneda": args.get("moneda", type=str),
                "estado": args.get("estado", type=str),
                "date_from": args.get("date_from", type=str),
                "date_to": args.get("date_to", type=str),
                "search": args.get("search", type=str),
            }.items() if v is not None},
            page=args.get("page", default=1, type=int),
            page_size=args.get("page_size", default=50, type=int),
            order_by=args.get("order_by", default="fecha", type=str),
            order_dir=args.get("order_dir", default="DESC", type=str),
        )
        return jsonify(result)
    except Exception as e:  # noqa: BLE001
        logger.error("Error en facturas_venta: %s", e)
        return jsonify(
            {
                "items": [],
                "meta": {
                    "total": 0,
                    "page": 1,
                    "page_size": 50,
                    "pages": 0,
                },
            }
        ), 200

@app.route("/api/finanzas/gastos")
def api_gastos():
    try:
        args = request.args
        result = _query_view(
            "v_gastos",
            filters={k: v for k, v in {
                "rut": args.get("rut", type=str),
                "moneda": args.get("moneda", type=str),
                "estado": args.get("estado", type=str),
                "date_from": args.get("date_from", type=str),
                "date_to": args.get("date_to", type=str),
                "search": args.get("search", type=str),
            }.items() if v is not None},
            page=args.get("page", default=1, type=int),
            page_size=args.get("page_size", default=50, type=int),
            order_by=args.get("order_by", default="fecha", type=str),
            order_dir=args.get("order_dir", default="DESC", type=str),
        )
        return jsonify(result)
    except Exception as e:
        logger.error("Error en gastos: %s", e)
        return jsonify({"items": [], "meta": {"total": 0, "page": 1, "page_size": 50, "pages": 0}})

@app.route("/api/finanzas/impuestos")
def api_impuestos():
    try:
        args = request.args
        result = _query_view(
            "v_impuestos",
            filters={k: v for k, v in {
                "search": args.get("search", type=str),
                "date_from": args.get("periodo_from", type=str),
                "date_to": args.get("periodo_to", type=str),
            }.items() if v is not None},
            page=args.get("page", default=1, type=int),
            page_size=args.get("page_size", default=50, type=int),
            order_by=args.get("order_by", default="periodo", type=str),
            order_dir=args.get("order_dir", default="DESC", type=str),
        )
        return jsonify(result)
    except Exception as e:
        logger.error("Error en impuestos: %s", e)
        return jsonify({"items": [], "meta": {"total": 0, "page": 1, "page_size": 50, "pages": 0}})

@app.route("/api/finanzas/previred")
def api_previred():
    try:
        args = request.args
        result = _query_view(
            "v_previred",
            filters={k: v for k, v in {
                "rut": args.get("rut", type=str),
                "search": args.get("search", type=str),
                "date_from": args.get("date_from", type=str),
                "date_to": args.get("date_to", type=str),
            }.items() if v is not None},
            page=args.get("page", default=1, type=int),
            page_size=args.get("page_size", default=50, type=int),
            order_by=args.get("order_by", default="periodo", type=str),
            order_dir=args.get("order_dir", default="DESC", type=str),
        )
        return jsonify(result)
    except Exception as e:
        logger.error("Error en previred: %s", e)
        return jsonify({"items": [], "meta": {"total": 0, "page": 1, "page_size": 50, "pages": 0}})

@app.route("/api/finanzas/sueldos")
def api_sueldos():
    try:
        args = request.args
        result = _query_view(
            "v_sueldos",
            filters={k: v for k, v in {
                "rut": args.get("rut", type=str),
                "search": args.get("search", type=str),
                "date_from": args.get("date_from", type=str),
                "date_to": args.get("date_to", type=str),
            }.items() if v is not None},
            page=args.get("page", default=1, type=int),
            page_size=args.get("page_size", default=50, type=int),
            order_by=args.get("order_by", default="periodo", type=str),
            order_dir=args.get("order_dir", default="DESC", type=str),
        )
        return jsonify(result)
    except Exception as e:
        logger.error("Error en sueldos: %s", e)
        return jsonify({"items": [], "meta": {"total": 0, "page": 1, "page_size": 50, "pages": 0}})

@app.route("/api/reportes/proyectos")
def api_reportes_proyectos():
    """Reporte de proyectos (usa v_proyectos_resumen si existe, si no agrega desde purchase_orders_unified)."""
    try:
        args = request.args
        with db_conn(DB_PATH) as conn:
            # Try view first
            cur = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='view' AND name='v_proyectos_resumen'"
            )
            if cur.fetchone():
                result = _query_view(
                    "v_proyectos_resumen",
                    filters={
                        "search": args.get("search", type=str),
                    },
                    page=args.get("page", default=1, type=int),
                    page_size=args.get("page_size", default=50, type=int),
                    order_by=args.get("order_by", default="monto_total", type=str),
                    order_dir=args.get("order_dir", default="DESC", type=str),
                )
                return jsonify(result)
            # Fallback aggregation
            page = max(1, int(args.get("page", 1)))
            page_size = max(1, min(200, int(args.get("page_size", 50))))
            offset = (page - 1) * page_size
            where = " WHERE COALESCE(zoho_project_name,'') <> ''"
            q_count = (
                "SELECT COUNT(1) FROM (SELECT 1 FROM purchase_orders_unified"
                + where
                + " GROUP BY zoho_project_name, zoho_project_id) t"
            )
            cur = conn.execute(q_count)
            total = cur.fetchone()[0]
            q = (
                "SELECT zoho_project_name AS proyecto, zoho_project_id AS project_id,"
                " COUNT(1) AS total_ordenes, COUNT(DISTINCT vendor_rut) AS proveedores_unicos,"
                " SUM(COALESCE(total_amount,0)) AS monto_total, MIN(po_date) AS fecha_min, MAX(po_date) AS fecha_max"
                " FROM purchase_orders_unified"
                + where
                + " GROUP BY zoho_project_name, zoho_project_id"
                + " ORDER BY monto_total DESC LIMIT OFFSET ?"
            )
            cur = conn.execute(q, (page_size, offset))
            rows = [dict(r) for r in cur.fetchall()]
            return jsonify({"items": rows, "meta": {"total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1)//page_size}})
    except Exception as e:
        logger.error("Error en /api/reportes/proyectos: %s", e)
        return jsonify({"items": [], "meta": {"total": 0, "page": 1, "page_size": 50, "pages": 0}})


@app.route("/api/reportes/proveedores")
def api_reportes_proveedores():
    """Reporte de proveedores (usa v_proveedores_resumen si existe; si no agrega desde purchase_orders_unified)."""
    try:
        args = request.args
        with db_conn(DB_PATH) as conn:
            cur = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='view' AND name='v_proveedores_resumen'"
            )
            if cur.fetchone():
                result = _query_view(
                    "v_proveedores_resumen",
                    filters={
                        "search": args.get("search", type=str),
                    },
                    page=args.get("page", default=1, type=int),
                    page_size=args.get("page_size", default=50, type=int),
                    order_by=args.get("order_by", default="monto_total", type=str),
                    order_dir=args.get("order_dir", default="DESC", type=str),
                )
                return jsonify(result)
            # Fallback aggregation
            page = max(1, int(args.get("page", 1)))
            page_size = max(1, min(200, int(args.get("page_size", 50))))
            offset = (page - 1) * page_size
            q_count = (
                "SELECT COUNT(1) FROM (SELECT 1 FROM purchase_orders_unified"
                " GROUP BY vendor_rut, COALESCE(zoho_vendor_name, vendor_rut)) t"
            )
            cur = conn.execute(q_count)
            total = cur.fetchone()[0]
            q = (
                "SELECT vendor_rut AS proveedor_rut, COALESCE(zoho_vendor_name, vendor_rut) AS proveedor_nombre,"
                " COUNT(1) AS total_ordenes, SUM(COALESCE(total_amount,0)) AS monto_total, MAX(po_date) AS ultima_orden"
                " FROM purchase_orders_unified"
                " GROUP BY vendor_rut, proveedor_nombre"
                " ORDER BY monto_total DESC LIMIT OFFSET ?"
            )
            cur = conn.execute(q, (page_size, offset))
            rows = [dict(r) for r in cur.fetchall()]
            return jsonify({"items": rows, "meta": {"total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1)//page_size}})
    except Exception as e:
        logger.error("Error en /api/reportes/proveedores: %s", e)
        return jsonify({"items": [], "meta": {"total": 0, "page": 1, "page_size": 50, "pages": 0}})


@app.route("/api/tesoreria/saldos")
def api_tesoreria_saldos():
    """Saldos consolidados por cuenta (usa v_tesoreria_saldos_consolidados si existe; si no calcula)."""
    try:
        args = request.args
        with db_conn(DB_PATH) as conn:
            cur = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='view' AND name='v_tesoreria_saldos_consolidados'"
            )
            if cur.fetchone():
                result = _query_view(
                    "v_tesoreria_saldos_consolidados",
                    filters={
                        "search": args.get("search", type=str),
                    },
                    page=args.get("page", default=1, type=int),
                    page_size=args.get("page_size", default=100, type=int),
                    order_by=args.get("order_by", default="saldo_actual", type=str),
                    order_dir=args.get("order_dir", default="DESC", type=str),
                )
                return jsonify(result)
            # Fallback: calcular por última fecha por cuenta o suma
            q = (
                "SELECT bank_name AS banco, account_number AS cuenta, moneda,"
                "  SUM(CASE WHEN tipo='credit' THEN monto ELSE -monto END) AS saldo_calc,"
                "  COUNT(CASE WHEN fecha >= date('now','-30 days') THEN 1 END) AS movimientos_30d"
                " FROM (SELECT bank_name, account_number, monto, moneda, tipo, fecha FROM bank_movements) bm"
                " GROUP BY banco, cuenta, moneda"
                " ORDER BY saldo_calc DESC"
            )
            cur = conn.execute(q)
            rows = [dict(r) for r in cur.fetchall()]
            total = len(rows)
            return jsonify({"items": rows, "meta": {"total": total, "page": 1, "page_size": total, "pages": 1}})
    except Exception as e:
        logger.error("Error en /api/tesoreria/saldos: %s", e)
        return jsonify({"items": [], "meta": {"total": 0, "page": 1, "page_size": 0, "pages": 0}})


def _week_key(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(str(date_str)[:10])
        return f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"
    except Exception:
        return ""


@app.route("/api/cashflow/semana")
def api_cashflow_semana():
    try:
        args = request.args
        weeks = max(1, min(104, int(args.get("weeks", 12))))
        data: dict[str, dict[str, float]] = {}
        with db_conn(DB_PATH) as conn:
            if _table_exists(conn, "cashflow_planned"):
                cur = conn.execute("SELECT fecha, category, monto FROM cashflow_planned")
                for fecha, category, monto in cur.fetchall():
                    wk = _week_key(fecha)
                    if not wk:
                        continue
                    cat = str(category or "other")
                    amt = float(monto or 0)
                    data.setdefault(wk, {}).setdefault(cat, 0.0)
                    data[wk][cat] += amt
            else:
                if _table_exists(conn, "purchase_orders_unified"):
                    cur = conn.execute("SELECT po_date, total_amount FROM purchase_orders_unified")
                    for d, amt in cur.fetchall():
                        wk = _week_key(d)
                        if not wk:
                            continue
                        data.setdefault(wk, {}).setdefault("purchase", 0.0)
                        data[wk]["purchase"] += -abs(float(amt or 0))
                if _table_exists(conn, "sales_invoices"):
                    cur = conn.execute("SELECT invoice_date, total_amount FROM sales_invoices")
                    for d, amt in cur.fetchall():
                        wk = _week_key(d)
                        if not wk:
                            continue
                        data.setdefault(wk, {}).setdefault("invoice", 0.0)
                        data[wk]["invoice"] += abs(float(amt or 0))

        weeks_sorted = sorted(data.keys())[-weeks:]
        items = []
        for wk in weeks_sorted:
            entry = {"week": wk}
            for cat, val in data[wk].items():
                entry[cat] = round(val, 2)
            entry["total"] = round(sum(data[wk].values()), 2)
            items.append(entry)
        return jsonify({"items": items, "meta": {"weeks": weeks, "categories": list({k for v in data.values() for k in v.keys()})}})
    except Exception as e:
        logger.error("Error en /api/cashflow/semana: %s", e)
        return jsonify({"items": [], "meta": {"weeks": 0, "categories": []}})


@app.route("/api/subcontratos/resumen")
def api_subcontratos_resumen():
    try:
        with db_conn(DB_PATH) as conn:
            if _table_exists(conn, "subcontracts"):
                ep_join = ""
                ep_sum = "0"
                if _table_exists(conn, "subcontract_progress"):
                    ep_sum = "COALESCE(SUM(sp.monto_neto),0)"
                    ep_join = " LEFT JOIN subcontract_progress sp ON sp.subcontract_id = s.id"
                q = (
                    "SELECT s.id AS subcontract_id, s.vendor_rut, s.project_id, s.contract_number AS contrato,"
                    " s.fecha, s.monto_total, s.moneda, " + ep_sum + " AS pagado"
                    " FROM subcontracts s" + ep_join +
                    " GROUP BY s.id, s.vendor_rut, s.project_id, s.contract_number, s.fecha, s.monto_total, s.moneda"
                    " ORDER BY s.fecha DESC"
                )
                cur = conn.execute(q)
                rows = [dict(r) for r in cur.fetchall()]
                return jsonify({"items": rows, "meta": {"total": len(rows)}})
        return jsonify({"items": [], "meta": {"total": 0}})
    except Exception as e:
        logger.error("Error en /api/subcontratos/resumen: %s", e)
        return jsonify({"items": [], "meta": {"total": 0}})


@app.route("/api/riesgos/resumen")
def api_riesgos_resumen():
    try:
        with db_conn(DB_PATH) as conn:
            items = []
            if _table_exists(conn, "risk_matrix"):
                cur = conn.execute("SELECT project_id, riesgo, probabilidad, impacto, nivel, estado, owner FROM risk_matrix")
                items += [dict(r) for r in cur.fetchall()]
            if not items and _table_exists(conn, "risk_predictions"):
                cur = conn.execute("SELECT project_id, categoria AS riesgo, score AS nivel FROM risk_predictions")
                items += [dict(r) for r in cur.fetchall()]
            return jsonify({"items": items, "meta": {"total": len(items)}})
    except Exception as e:
        logger.error("Error en /api/riesgos/resumen: %s", e)
        return jsonify({"items": [], "meta": {"total": 0}})


@app.route("/api/hse/resumen")
def api_hse_resumen():
    try:
        with db_conn(DB_PATH) as conn:
            incidents = 0
            inspections = 0
            epp_pct = None
            last_incident = None
            if _table_exists(conn, "hse_incidents"):
                cur = conn.execute("SELECT COUNT(1), MAX(fecha) FROM hse_incidents")
                row = cur.fetchone()
                incidents = int(row[0] or 0)
                last_incident = row[1]
            if _table_exists(conn, "hse_inspections"):
                cur = conn.execute("SELECT COUNT(1) FROM hse_inspections")
                inspections = int(cur.fetchone()[0] or 0)
            if _table_exists(conn, "epp_detections"):
                cur = conn.execute("SELECT AVG(cumplimiento_pct) FROM epp_detections")
                val = cur.fetchone()[0]
                if val is not None:
                    epp_pct = round(float(val), 2)
            return jsonify({"summary": {"incidentes": incidents, "inspecciones": inspections, "cumplimiento_epp_pct": epp_pct, "ult_incidente_fecha": last_incident}})
    except Exception as e:
        logger.error("Error en /api/hse/resumen: %s", e)
        return jsonify({"summary": {"incidentes": 0, "inspecciones": 0, "cumplimiento_epp_pct": None, "ult_incidente_fecha": None}})


@app.route("/api/proyectos/kpis")
def api_proyectos_kpis():
    """KPIs por proyecto: presupuesto (si existe), compras, ventas, margen, avance, riesgo.
    Fallback: calcula desde purchase_orders_unified, sales_invoices, daily_reports, risk_predictions.
    """
    try:
        with db_conn(DB_PATH) as conn:
            items: list[dict] = []
            # Base de proyectos si existe
            proyectos: dict[str, dict] = {}
            if _table_exists(conn, "projects"):
                cur = conn.execute("SELECT id, COALESCE(zoho_project_id, id) AS pid, name, budget_total FROM projects")
                for row in cur.fetchall():
                    pid = str(row[1])
                    proyectos[pid] = {
                        "project_id": pid,
                        "proyecto": row[2],
                        "presupuesto": float(row[3] or 0),
                        "compras": 0.0,
                        "ventas": 0.0,
                        "margen": 0.0,
                        "avance": None,
                        "riesgo": None,
                    }
            # Compras por proyecto
            if _table_exists(conn, "purchase_orders_unified"):
                cur = conn.execute(
                    "SELECT COALESCE(zoho_project_id, zoho_project_name, '') AS pid, SUM(COALESCE(total_amount,0)) FROM purchase_orders_unified GROUP BY pid"
                )
                for pid, total in cur.fetchall():
                    if not pid:
                        continue
                    pid = str(pid)
                    entry = proyectos.setdefault(pid, {"project_id": pid, "proyecto": pid, "presupuesto": 0.0, "compras": 0.0, "ventas": 0.0, "margen": 0.0, "avance": None, "riesgo": None})
                    entry["compras"] = float(total or 0)
            # Ventas por proyecto
            if _table_exists(conn, "sales_invoices"):
                cur = conn.execute(
                    "SELECT COALESCE(project_id, '') AS pid, SUM(COALESCE(total_amount,0)) FROM sales_invoices GROUP BY pid"
                )
                for pid, total in cur.fetchall():
                    if not pid:
                        continue
                    pid = str(pid)
                    entry = proyectos.setdefault(pid, {"project_id": pid, "proyecto": pid, "presupuesto": 0.0, "compras": 0.0, "ventas": 0.0, "margen": 0.0, "avance": None, "riesgo": None})
                    entry["ventas"] = float(total or 0)
            # Avance (último %)
            if _table_exists(conn, "daily_reports"):
                cur = conn.execute(
                    "SELECT project_id, MAX(fecha), AVG(avance_pct) FROM daily_reports GROUP BY project_id"
                )
                for pid, _f, avg in cur.fetchall():
                    if not pid:
                        continue
                    pid = str(pid)
                    entry = proyectos.setdefault(pid, {"project_id": pid, "proyecto": pid, "presupuesto": 0.0, "compras": 0.0, "ventas": 0.0, "margen": 0.0, "avance": None, "riesgo": None})
                    entry["avance"] = round(float(avg or 0), 2)
            # Riesgo (score max)
            if _table_exists(conn, "risk_predictions"):
                cur = conn.execute(
                    "SELECT project_id, MAX(score) FROM risk_predictions GROUP BY project_id"
                )
                for pid, score in cur.fetchall():
                    if not pid:
                        continue
                    pid = str(pid)
                    entry = proyectos.setdefault(pid, {"project_id": pid, "proyecto": pid, "presupuesto": 0.0, "compras": 0.0, "ventas": 0.0, "margen": 0.0, "avance": None, "riesgo": None})
                    entry["riesgo"] = round(float(score or 0), 2)

            # Margen
            for pid, e in proyectos.items():
                e["margen"] = round(float(e.get("ventas", 0) - e.get("compras", 0)), 2)
                items.append(e)

            return jsonify({"items": items, "meta": {"total": len(items)}})
    except Exception as e:
        logger.error("Error en /api/proyectos/kpis: %s", e)
        return jsonify({"items": [], "meta": {"total": 0}})


@app.route("/api/control_financiero/resumen")
def api_control_financiero_resumen():
    """Resumen financiero por proyecto.

    Calcula:
      - presupuesto: desde tablas de presupuestos (si existen)
      - comprometido: suma de OC aprobadas/cerradas (si hay columna status) o todas
      - disponible_conservador = presupuesto - comprometido
    Si no hay datos retorna lista vacía.
    """
    try:
        items: list[dict] = []
        with db_conn(DB_PATH) as conn:
            cur = conn.cursor()

            # Presupuestos
            budgets: dict[str, float] = {}
            try:
                if _table_exists(conn, "proyectos") and _table_exists(
                    conn, "v_presupuesto_totales"
                ):
                    cur.execute(
                        "SELECT pr.nombre AS project_name, "
                        "COALESCE(v.total_presupuesto,0) AS budget "
                        "FROM proyectos pr "
                        "LEFT JOIN presupuestos pb ON pb.id = ("  # noqa: E501
                        " SELECT MAX(id) FROM presupuestos WHERE proyecto_id = pr.id) "
                        "LEFT JOIN v_presupuesto_totales v ON v.presupuesto_id = pb.id"
                    )
                    for pname, b in cur.fetchall():
                        if pname:
                            budgets[_norm_name(pname)] = float(b or 0)
            except Exception:
                budgets = {}

            # Comprometido (OC)
            committed: dict[str, float] = {}
            try:
                if _table_exists(conn, "purchase_orders_unified"):
                    cur.execute("PRAGMA table_info(purchase_orders_unified)")
                    cols = {r[1] for r in cur.fetchall()}
                    if "status" in cols:
                        cur.execute(
                            "SELECT COALESCE(zoho_project_name,'') AS pn, "
                            "SUM(COALESCE(total_amount,0)) "
                            "FROM purchase_orders_unified "
                            "WHERE status IN ('approved','closed') GROUP BY pn"
                        )
                    else:
                        cur.execute(
                            "SELECT COALESCE(zoho_project_name,'') AS pn, "
                            "SUM(COALESCE(total_amount,0)) "
                            "FROM purchase_orders_unified GROUP BY pn"
                        )
                    for pn, total in cur.fetchall():
                        key = _norm_name(pn or "")
                        if key:
                            committed[key] = float(total or 0)
            except Exception:
                committed = {}

            # Construir items (union de claves)
            for key in sorted(set(budgets) | set(committed)):
                presupuesto = budgets.get(key, 0.0)
                compro = committed.get(key, 0.0)
                items.append(
                    {
                        "project_name": key,
                        "presupuesto": presupuesto,
                        "comprometido": compro,
                        "disponible_conservador": round(presupuesto - compro, 2),
                    }
                )

        return jsonify({"items": items, "meta": {"total": len(items)}})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/control_financiero/resumen: %s", e)
        return jsonify({"items": [], "meta": {"total": 0}}), 500


@app.route("/api/proyectos/<project_key>/resumen")
def api_proyecto_resumen(project_key: str):
    try:
        with db_conn(DB_PATH) as conn:
            resumen = {"project_key": project_key}
            # Resolver por id o nombre; aplicar aliases si existen
            alias_map, _display = _get_alias_maps(conn)
            key_norm = _norm_name(project_key)
            key_canon = alias_map.get(key_norm, key_norm)

            # Helper: condiciones para consultas por id o nombre
            def _where_id_or_name(col_id: str, col_name: str) -> tuple[str, list]:
                # Intentar match exacto por id, si falla usar nombre canónico
                return (
                    f"({col_id} = OR {col_name} = ?)",
                    [project_key, project_key],
                )

            def _where_name_canon(col_name: str) -> tuple[str, list]:
                return (
                    f"LOWER(TRIM({col_name})) = ?",
                    [key_canon],
                )
            # Nombre y presupuesto
            if _table_exists(conn, "projects"):
                # Primero por id; si no, por nombre canónico
                cur = conn.execute(
                    "SELECT name, budget_total FROM projects WHERE COALESCE(zoho_project_id, id) = ?",
                    (project_key,),
                )
                row = cur.fetchone()
                if not row:
                    cur = conn.execute(
                        "SELECT name, budget_total FROM projects WHERE LOWER(TRIM(name)) = ?",
                        (key_canon,),
                    )
                    row = cur.fetchone()
                if row:
                    resumen["proyecto"] = row[0]
                    resumen["presupuesto"] = float(row[1] or 0)
            # Compras
            if _table_exists(conn, "purchase_orders_unified"):
                # Intentar por id o por nombre (canónico)
                cols = _table_columns(conn, "purchase_orders_unified")
                if "zoho_project_id" in cols and "zoho_project_name" in cols:
                    where1, params1 = _where_id_or_name("COALESCE(zoho_project_id,'')", "COALESCE(zoho_project_name,'')")
                    cur = conn.execute(
                        f"SELECT SUM(COALESCE(total_amount,0)) FROM purchase_orders_unified WHERE {where1}",
                        params1,
                    )
                    total = (cur.fetchone() or [0])[0]
                    if not total:
                        where2, params2 = _where_name_canon("LOWER(TRIM(COALESCE(zoho_project_name,'')))")
                        cur = conn.execute(
                            f"SELECT SUM(COALESCE(total_amount,0)) FROM purchase_orders_unified WHERE {where2}",
                            params2,
                        )
                        total = (cur.fetchone() or [0])[0]
                else:
                    where2, params2 = _where_name_canon("LOWER(TRIM(COALESCE(zoho_project_name,'')))")
                    cur = conn.execute(
                        f"SELECT SUM(COALESCE(total_amount,0)) FROM purchase_orders_unified WHERE {where2}",
                        params2,
                    )
                    total = (cur.fetchone() or [0])[0]
                resumen["compras"] = float(total or 0)
            # Ventas
            if _table_exists(conn, "sales_invoices"):
                where1, params1 = _where_id_or_name("COALESCE(project_id,'')", "COALESCE(project_name,'')") if "project_name" in _table_columns(conn, "sales_invoices") else _where_id_or_name("COALESCE(project_id,'')", "COALESCE(project_id,'')")
                cur = conn.execute(
                    f"SELECT SUM(COALESCE(total_amount,0)) FROM sales_invoices WHERE {where1}",
                    params1,
                )
                total = (cur.fetchone() or [0])[0]
                if not total and "project_name" in _table_columns(conn, "sales_invoices"):
                    where2, params2 = _where_name_canon("LOWER(TRIM(COALESCE(project_name,'')))")
                    cur = conn.execute(
                        f"SELECT SUM(COALESCE(total_amount,0)) FROM sales_invoices WHERE {where2}",
                        params2,
                    )
                    total = (cur.fetchone() or [0])[0]
                resumen["ventas"] = float(total or 0)
            # Avance
            if _table_exists(conn, "daily_reports"):
                where1, params1 = _where_id_or_name("project_id", "project_name") if "project_name" in _table_columns(conn, "daily_reports") else ("project_id = ?", [project_key])
                cur = conn.execute(
                    f"SELECT AVG(avance_pct) FROM daily_reports WHERE {where1}",
                    params1,
                )
                val = cur.fetchone()[0]
                resumen["avance"] = round(float(val or 0), 2)
            # Riesgo
            if _table_exists(conn, "risk_predictions"):
                where1, params1 = _where_id_or_name("project_id", "project_name") if "project_name" in _table_columns(conn, "risk_predictions") else ("project_id = ?", [project_key])
                cur = conn.execute(
                    f"SELECT MAX(score) FROM risk_predictions WHERE {where1}",
                    params1,
                )
                val = cur.fetchone()[0]
                resumen["riesgo"] = round(float(val or 0), 2)
            # Margen
            resumen["margen"] = round(float(resumen.get("ventas", 0) - resumen.get("compras", 0)), 2)
            return jsonify(resumen)
    except Exception as e:
        logger.error("Error en /api/proyectos/<id>/resumen: %s", e)
        return jsonify({"error": "server_error"}), 500
def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return cur.fetchone() is not None


def _table_columns(conn: sqlite3.Connection, name: str) -> set[str]:
    cols: set[str] = set()
    try:
        cur = conn.execute(f"PRAGMA table_info({name})")
        for row in cur.fetchall():
            cols.add(row[1])  # name
    except sqlite3.Error:
        pass
    return cols


def _first_existing_col(cols: set[str], options: list[str]) -> str | None:
    """Return the first column name that exists in cols from options."""
    for c in options:
        if c in cols:
            return c
    return None


def _get_alias_maps(conn: sqlite3.Connection) -> tuple[dict[str, str], dict[str, str]]:
    """Build tolerant alias maps for project names.

    Returns (alias_map, display_map):
    - alias_map: maps normalized aliases -> canonical normalized name
    - display_map: maps canonical normalized name -> pretty display

    Sources: projects (name), projects_analytic_map (zoho_project_name),
    purchase_orders_unified (zoho_project_name) when available.
    """
    alias_map: dict[str, str] = {}
    display_map: dict[str, str] = {}
    try:
        # From projects table
        if _table_exists(conn, "projects"):
            cur = conn.execute("SELECT id, name FROM projects")
            for _pid, name in cur.fetchall():
                if not name:
                    continue
                canon = _norm_name(name)
                display_map.setdefault(canon, str(name))
                # Map both with and without numeric prefix (e.g., "2313 - Foo")
                alias_map[canon] = canon
                stripped = _norm_name(_strip_code_prefix(str(name)))
                alias_map.setdefault(stripped, canon)
        # From analytic map
        if _table_exists(conn, "projects_analytic_map"):
            cur = conn.execute("SELECT zoho_project_id, zoho_project_name FROM projects_analytic_map")
            for _pid, pname in cur.fetchall():
                if not pname:
                    continue
                canon = _norm_name(pname)
                display_map.setdefault(canon, str(pname))
                alias_map.setdefault(canon, canon)
                stripped = _norm_name(_strip_code_prefix(str(pname)))
                alias_map.setdefault(stripped, canon)
        # From purchase_orders_unified as a last source for names seen in OC
        if _table_exists(conn, "purchase_orders_unified"):
            cols = _table_columns(conn, "purchase_orders_unified")
            if "zoho_project_name" in cols:
                cur = conn.execute(
                    "SELECT DISTINCT COALESCE(zoho_project_name,'') FROM purchase_orders_unified WHERE TRIM(COALESCE(zoho_project_name,'')) <> ''"
                )
                for (pname,) in cur.fetchall():
                    canon = _norm_name(pname)
                    if not canon:
                        continue
                    display_map.setdefault(canon, str(pname))
                    alias_map.setdefault(canon, canon)
                    stripped = _norm_name(_strip_code_prefix(str(pname)))
                    alias_map.setdefault(stripped, canon)
    except Exception:
        # Best-effort: ensure identity mapping for safety
        pass
    return alias_map, display_map


def _resolve_project_ids(conn: sqlite3.Connection, project_key: str) -> list[int]:
    """Resolve likely project IDs from a human key using projects table.

    Tries by exact numeric id, or by matching normalized name (with/without code prefix).
    Returns a list of candidate IDs (may be empty).
    """
    ids: set[int] = set()
    try:
        # If project_key looks like an integer, include it
        try:
            ids.add(int(str(project_key).strip()))
        except Exception:
            pass
        if _table_exists(conn, "projects"):
            k1 = _norm_key(project_key)
            k2 = _norm_key(_strip_code_prefix(project_key))
            cur = conn.execute(
                "SELECT id FROM projects WHERE LOWER(TRIM(name)) IN (?,?)",
                (k1, k2),
            )
            for (pid,) in cur.fetchall():
                try:
                    ids.add(int(pid))
                except Exception:
                    continue
    except Exception:
        return list(ids)
    return list(ids)


# ----------------------------------------------------------------------------
# Contratos: overrides locales (cuando no existe una fuente canónica)
# ----------------------------------------------------------------------------

def _ensure_contract_overrides(conn: sqlite3.Connection) -> None:
    """Create local overrides table to persist contracted sales per project.

    Schema fields:
    - project_key: raw key used by API (could be name with code prefix)
    - project_key_norm: normalized key for matching (lower/trim, strips accents)
    - project_name_display: optional pretty display
    - contract_net: net amount (without IVA)
    - iva_rate: default 0.19
    - contract_gross: gross amount (with IVA)
    - currency: default CLP
    - source: free text (e.g., "manual", "oficio EP6")
    - note: optional
    - updated_at: timestamp
    Unique on project_key_norm to simplify upserts.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_contract_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_key TEXT NOT NULL,
            project_key_norm TEXT NOT NULL UNIQUE,
            project_name_display TEXT,
            contract_net REAL NOT NULL,
            iva_rate REAL DEFAULT 0.19,
            contract_gross REAL,
            currency TEXT DEFAULT 'CLP',
            source TEXT,
            note TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        """
    )


def _get_contract_override(
    conn: sqlite3.Connection, project_key: str
) -> dict | None:
    """Fetch override by tolerant project key.

    Tries: norm(key) and norm(strip_code_prefix(key)).
    """
    _ensure_contract_overrides(conn)
    k1 = _norm_key(project_key)
    k2 = _norm_key(_strip_code_prefix(project_key))
    cur = conn.execute(
        "SELECT project_key, project_name_display, contract_net, iva_rate, contract_gross, currency, source, note "
        "FROM project_contract_overrides WHERE project_key_norm IN (?,?)",
        (k1, k2),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {

        "project_key": row[0],
        "project_name_display": row[1],
        "contract_net": float(row[2] or 0),
        "iva_rate": float(row[3] if row[3] is not None else 0.19),
        "contract_gross": float(row[4] or 0),
        "currency": row[5] or "CLP",
        "source": row[6],
        "note": row[7],
    }


def _upsert_contract_override(
    conn: sqlite3.Connection,
    project_key: str,
    project_name_display: str | None,
    contract_net: float | None,
    contract_gross: float | None,
    iva_rate: float | None,
    currency: str | None,
    source: str | None,
    note: str | None,
) -> dict:
    _ensure_contract_overrides(conn)
    norm = _norm_key(project_key)
    iva = 0.19 if iva_rate is None else float(iva_rate)
    # Calculate missing net/gross if possible
    net = float(contract_net) if contract_net is not None else None
    gross = float(contract_gross) if contract_gross is not None else None
    if net is None and gross is not None:
        net = round(gross / (1.0 + iva), 2)
    if gross is None and net is not None:
        gross = round(net * (1.0 + iva), 2)
    if net is None:
        raise ValueError("contract_net_or_contract_gross_required")

    conn.execute(
        (
            "INSERT INTO project_contract_overrides(project_key, project_key_norm, project_name_display, contract_net, iva_rate, contract_gross, currency, source, note, updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,datetime('now')) "
            "ON CONFLICT(project_key_norm) DO UPDATE SET "
            " project_key=excluded.project_key, "
            " project_name_display=excluded.project_name_display, "
            " contract_net=excluded.contract_net, "
            " iva_rate=excluded.iva_rate, "
            " contract_gross=excluded.contract_gross, "
            " currency=excluded.currency, "
            " source=excluded.source, "
            " note=excluded.note, "
            " updated_at=datetime('now')"
        ),
        (
            project_key,
            norm,
            project_name_display,
            float(net),
            float(iva),
            float(gross if gross is not None else 0.0),
            currency or "CLP",
            source,
            note,
        ),
    )
    conn.commit()
    return _get_contract_override(conn, project_key) or {}


# ----------------------------------------------------------------------------
# Proyecto 360: Endpoints mínimos (summary, purchases, budget, finance, time, docs, chats, IA)
# Basado en playbook de ideas/proyectos. Usa vistas canónicas si existen.
# ----------------------------------------------------------------------------

def _norm_key(key: str) -> str:
    try:
        return _norm_name(key)
    except Exception:
        # Fallback básico
        return (key or "").strip().lower()


def _strip_code_prefix(name: str) -> str:
    try:
        import re as _re
        return _re.sub(r"^\s*\d+\s*[-:–]\s*", "", name or "").strip()
    except Exception:
        return (name or "").strip()


# ----------------------------------------------------------------------------
# EP (Estados de Pago) y Obras Adicionales
# ----------------------------------------------------------------------------

def _ensure_payment_states(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_payment_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_key_norm TEXT NOT NULL,
            project_key TEXT,
            ep_number TEXT,
            date TEXT,
            net_amount REAL NOT NULL,
            iva_rate REAL DEFAULT 0.19,
            gross_amount REAL,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pps_project ON project_payment_states(project_key_norm)"
    )


def _ensure_additional_works(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_additional_works (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_key_norm TEXT NOT NULL,
            project_key TEXT,
            name TEXT,
            status TEXT,
            net_amount REAL NOT NULL,
            iva_rate REAL DEFAULT 0.19,
            gross_amount REAL,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_paw_project ON project_additional_works(project_key_norm)"
    )


def _project_where_clause(col_project_name: str, project_key: str) -> tuple[str, list]:
    """Return a WHERE clause to match by normalized project name, tolerant to ID prefixes.

    Example: _project_where_clause("COALESCE(zoho_project_name,'')", "2313 - TEP San Eugenio")
    -> ("LOWER(TRIM(COALESCE(zoho_project_name,''))) IN (?,?)", ["2313 - tep san eugenio", "tep san eugenio"])  # normalized keys
    """
    k1 = _norm_key(project_key)
    k2 = _norm_key(_strip_code_prefix(project_key))
    if k1 == k2:
        return (f"LOWER(TRIM({col_project_name})) = ?", [k1])
    return (f"LOWER(TRIM({col_project_name})) IN (?,?)", [k1, k2])


# --- EP schema minimal ensure (for server-side import by project key) ---
def _ensure_ep_min_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS ep_headers (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            contract_id INTEGER,
            ep_number TEXT,
            period_start TEXT,
            period_end TEXT,
            submitted_at TEXT,
            approved_at TEXT,
            status TEXT,
            retention_pct REAL,
            notes TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ep_project
            ON ep_headers(project_id);

        CREATE TABLE IF NOT EXISTS ep_lines (
            id INTEGER PRIMARY KEY,
            ep_id INTEGER NOT NULL,
            sov_item_id INTEGER,
            item_code TEXT,
            description TEXT,
            unit TEXT,
            qty_period REAL,
            unit_price REAL,
            amount_period REAL,
            qty_cum REAL,
            amount_cum REAL,
            chapter TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_ep_lines_ep
            ON ep_lines(ep_id);

        CREATE TABLE IF NOT EXISTS ep_deductions (
            id INTEGER PRIMARY KEY,
            ep_id INTEGER NOT NULL,
            type TEXT,
            description TEXT,
            amount REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ep_ded_ep
            ON ep_deductions(ep_id);
        """
    )
    conn.commit()


@app.route("/api/projects/<project_key>/summary")
def api_project_summary(project_key: str):
    """KPIs 360 del proyecto. Calcula en forma robusta usando vistas si existen.

    Devuelve: sales_contracted, budget_cost, committed, invoiced_ap, paid,
    ar_invoiced, ar_collected, margins, progress_pct, flags y próximos hitos.
    """
    try:
        with db_conn(DB_PATH) as conn:
            resumen: dict[str, object] = {
                "project_id": project_key,
                "project_name": project_key,
            }

            # Nombre y presupuesto de costo (PC)
            budget_cost = 0.0
            # projects.budget_total
            if _table_exists(conn, "projects"):
                cur = conn.execute(
                    "SELECT name, COALESCE(budget_total,0) FROM projects WHERE LOWER(TRIM(name)) = ?",
                    (_norm_key(project_key),),
                )
                row = cur.fetchone()
                if row:
                    resumen["project_name"] = row[0]
                    budget_cost = float(row[1] or 0)
            # v_presupuesto_totales como alternativa
            if not budget_cost and _table_exists(conn, "v_presupuesto_totales"):
                where, params = _project_where_clause("COALESCE(project_name,'')", project_key)
                cur = conn.execute(
                    f"SELECT COALESCE(total_presupuesto,0) FROM v_presupuesto_totales WHERE {where}",
                    params,
                )
                val = cur.fetchone()
                if val:
                    budget_cost = float(val[0] or 0)

            # Comprometido (OC)
            committed = 0.0
            if _table_exists(conn, "purchase_orders_unified"):
                cols = _table_columns(conn, "purchase_orders_unified")
                pname_col = "COALESCE(zoho_project_name,'')" if "zoho_project_name" in cols else "COALESCE(project_name,'')"
                where, params = _project_where_clause(pname_col, project_key)
                # Suma por estados aprobados/cerrados si produce valor, si no, incluye todas las OC
                committed_status = 0.0
                if "status" in cols:
                    try:
                        cur = conn.execute(
                            f"SELECT SUM(COALESCE(total_amount,0)) FROM purchase_orders_unified WHERE {where} AND LOWER(COALESCE(status,'')) IN ('approved','closed')",
                            params,
                        )
                        committed_status = float((cur.fetchone() or [0])[0] or 0)
                    except sqlite3.Error:
                        committed_status = 0.0
                try:
                    cur = conn.execute(
                        f"SELECT SUM(COALESCE(total_amount,0)) FROM purchase_orders_unified WHERE {where}",
                        params,
                    )
                    committed_all = float((cur.fetchone() or [0])[0] or 0)
                except sqlite3.Error:
                    committed_all = 0.0
                committed = committed_status if committed_status > 0 else committed_all

            # AP (facturas compra)
            invoiced_ap = 0.0
            if _table_exists(conn, "v_facturas_compra"):
                # Intentar según columnas disponibles de la vista
                cols_ap = _table_columns(conn, "v_facturas_compra")
                amount_col = "monto_total" if "monto_total" in cols_ap else ("amount" if "amount" in cols_ap else None)
                pname_col = None
                for c in ("project_name", "proyecto", "zoho_project_name"):
                    if c in cols_ap:
                        pname_col = c
                        break
                if amount_col and pname_col:
                    try:
                        where, params = _project_where_clause(f"COALESCE({pname_col},'')", project_key)
                        cur = conn.execute(
                            f"SELECT SUM(COALESCE({amount_col},0)) FROM v_facturas_compra WHERE {where}",
                            params,
                        )
                        invoiced_ap = float((cur.fetchone() or [0])[0] or 0)
                    except sqlite3.Error:
                        invoiced_ap = 0.0

            # Pagos (egresos) conciliados
            paid = 0.0
            if _table_exists(conn, "v_cartola_bancaria"):
                cols_cb = _table_columns(conn, "v_cartola_bancaria")
                amount_col = "monto" if "monto" in cols_cb else ("paid_amount" if "paid_amount" in cols_cb else None)
                pname_col = None
                for c in ("project_name", "proyecto"):
                    if c in cols_cb:
                        pname_col = c
                        break
                if amount_col and pname_col:
                    try:
                        where, params = _project_where_clause(f"COALESCE({pname_col},'')", project_key)
                        cur = conn.execute(
                            f"SELECT SUM(COALESCE({amount_col},0)) FROM v_cartola_bancaria WHERE {where}",
                            params,
                        )
                        paid = float((cur.fetchone() or [0])[0] or 0)
                    except sqlite3.Error:
                        paid = 0.0

            # Ventas contratadas (techo)
            sales_contracted = 0.0
            sales_contracted_net = None
            sales_contracted_gross = None
            sales_iva_rate = 0.19
            if _table_exists(conn, "v_sales_contracted_project"):
                where, params = _project_where_clause("COALESCE(project_name,'')", project_key)
                cur = conn.execute(
                    (
                        "SELECT SUM(COALESCE(sales_contracted,0)) "
                        "FROM v_sales_contracted_project WHERE "
                        f"{where}"
                    ),
                    params,
                )
                sales_contracted = float((cur.fetchone() or [0])[0] or 0)
                sales_contracted_net = sales_contracted
            # Fallback: intentar columnas de contrato en projects
            if sales_contracted == 0 and _table_exists(conn, "projects"):
                cols_pr = _table_columns(conn, "projects")
                c = _first_existing_col(
                    cols_pr,
                    [
                        "contract_total",
                        "contract_value",
                        "monto_contrato",
                        "precio_contrato",
                        "sales_total",
                        "ventas_contratadas",
                    ],
                )
                name_col = "name" if "name" in cols_pr else (
                    "project_name" if "project_name" in cols_pr else None
                )
                if c and name_col:
                    where, params = _project_where_clause(
                        f"COALESCE({name_col},'')", project_key
                    )
                    cur = conn.execute(
                        f"SELECT COALESCE({c},0) FROM projects WHERE {where}",
                        params,
                    )
                    sales_contracted = float((cur.fetchone() or [0])[0] or 0)
                    sales_contracted_net = sales_contracted

            # Fallback final: overrides locales (DB or manual file)
            if sales_contracted == 0:
                try:
                    ov = _get_contract_override(conn, project_key)
                except Exception:
                    ov = None
                if ov:
                    sales_contracted_net = float(ov.get("contract_net") or 0)
                    sales_iva_rate = float(ov.get("iva_rate") or 0.19)
                    gross = ov.get("contract_gross")
                    if gross is None and sales_contracted_net is not None:
                        sales_contracted_gross = round(
                            float(sales_contracted_net) * (1.0 + sales_iva_rate), 2
                        )
                    else:
                        sales_contracted_gross = float(gross or 0)
                    sales_contracted = float(sales_contracted_net or 0)
                else:
                    # Manual file-based lookup by tolerant key match
                    try:
                        k1 = _norm_key(project_key)
                        k2 = _norm_key(_strip_code_prefix(project_key))
                        mc = None
                        for mk, mv in MANUAL_CONTRACTS.items():
                            if _norm_key(str(mk)) in (k1, k2):
                                mc = mv
                                break
                        if mc:
                            net = mc.get("contract_net")
                            gross = mc.get("contract_gross")
                            iva = mc.get("iva_rate", 0.19)
                            if net is None and gross is not None:
                                net = round(float(gross) / (1.0 + float(iva)), 2)
                            if gross is None and net is not None:
                                gross = round(float(net) * (1.0 + float(iva)), 2)
                            if net is not None:
                                sales_contracted = float(net)
                                sales_contracted_net = float(net)
                                sales_contracted_gross = float(gross or 0)
                                sales_iva_rate = float(iva)
                    except Exception:
                        pass

            # AR facturado y cobrado (si existen vistas)
            ar_invoiced = 0.0
            ar_collected = 0.0
            # Prefer AR by project_id from EP schema if available
            try:
                pids = _resolve_project_ids(conn, project_key)
            except Exception:
                pids = []
            if pids and _table_exists(conn, "ar_invoices"):
                try:
                    q = (
                        "SELECT SUM(COALESCE(amount_total,0)) "
                        "FROM ar_invoices WHERE status IN ('issued','paid') "
                        "AND project_id IN ("
                        + ",".join(["?"] * len(pids))
                        + ")"
                    )
                    cur = conn.execute(q, pids)
                    ar_invoiced = float((cur.fetchone() or [0])[0] or 0)
                except sqlite3.Error:
                    pass
            if (
                pids
                and _table_exists(conn, "ar_collections")
                and _table_exists(conn, "ar_invoices")
            ):
                try:
                    q = (
                        "SELECT SUM(COALESCE(c.amount,0)) FROM ar_collections c "
                        "JOIN ar_invoices a ON a.id = c.invoice_id "
                        "WHERE a.project_id IN ("
                        + ",".join(["?"] * len(pids))
                        + ")"
                    )
                    cur = conn.execute(q, pids)
                    ar_collected = float((cur.fetchone() or [0])[0] or 0)
                except sqlite3.Error:
                    pass
            # Fallback to name-based aggregate views if present
            if (
                ar_invoiced == 0.0
                and _table_exists(conn, "v_ar_invoiced_project")
            ):
                where, params = _project_where_clause(
                    "COALESCE(project_name,'')", project_key
                )
                cur = conn.execute(
                    (
                        "SELECT SUM(COALESCE(ar_invoiced,0)) "
                        f"FROM v_ar_invoiced_project WHERE {where}"
                    ),
                    params,
                )
                ar_invoiced = float((cur.fetchone() or [0])[0] or 0)
            if (
                ar_collected == 0.0
                and _table_exists(conn, "v_ar_collected_project")
            ):
                where, params = _project_where_clause(
                    "COALESCE(project_name,'')", project_key
                )
                cur = conn.execute(
                    (
                        "SELECT SUM(COALESCE(ar_collected,0)) "
                        f"FROM v_ar_collected_project WHERE {where}"
                    ),
                    params,
                )
                ar_collected = float((cur.fetchone() or [0])[0] or 0)

            # Totales EP (estados de pago) y Obras adicionales locales
            ep_total_net = 0.0
            ep_total_gross = 0.0
            # Prefer EP approved totals from EP schema if available
            if (
                pids
                and _table_exists(conn, "ep_headers")
                and _table_exists(conn, "ep_lines")
            ):
                try:
                    q = (
                        "SELECT COALESCE(SUM(l.amount_period),0) AS amt "
                        "FROM ep_lines l JOIN ep_headers h ON h.id = l.ep_id "
                        "WHERE h.status IN ('approved','invoiced','paid') "
                        "AND h.project_id IN ("
                        + ",".join(["?"] * len(pids))
                        + ")"
                    )
                    cur = conn.execute(q, pids)
                    ep_total_net = float((cur.fetchone() or [0])[0] or 0)
                    # Include deductions
                    qd = (
                        "SELECT COALESCE(SUM(d.amount),0) FROM ep_deductions d "
                        "JOIN ep_headers h ON h.id = d.ep_id "
                        "WHERE h.status IN ('approved','invoiced','paid') "
                        "AND h.project_id IN ("
                        + ",".join(["?"] * len(pids))
                        + ")"
                    )
                    cur = conn.execute(qd, pids)
                    ded = float((cur.fetchone() or [0])[0] or 0)
                    ep_total_net = max(ep_total_net - ded, 0.0)
                    # assume 19% VAT as default gross
                    ep_total_gross = round(ep_total_net * 1.19, 2)
                except sqlite3.Error:
                    pass
            extras_total_net = 0.0
            extras_total_gross = 0.0
            try:
                _ensure_payment_states(conn)
                _ensure_additional_works(conn)
                k1 = _norm_key(project_key)
                k2 = _norm_key(_strip_code_prefix(project_key))
                sql_ep = (
                    "SELECT "
                    "SUM(COALESCE(net_amount,0)) AS sum_net, "
                    "SUM(COALESCE(gross_amount, "
                    "COALESCE(net_amount,0) + "
                    "COALESCE(net_amount,0)*"
                    "COALESCE(iva_rate,0))) AS "
                    "sum_gross FROM project_payment_states "
                    "WHERE project_key_norm IN (?,?)"
                )
                cur = conn.execute(sql_ep, (k1, k2))
                r = cur.fetchone()
                if r and (ep_total_net == 0.0 and ep_total_gross == 0.0):
                    ep_total_net = float(r[0] or 0)
                    ep_total_gross = float(r[1] or 0)
                sql_ex = (
                    "SELECT "
                    "SUM(COALESCE(net_amount,0)) AS sum_net, "
                    "SUM(COALESCE(gross_amount, "
                    "COALESCE(net_amount,0) + "
                    "COALESCE(net_amount,0)*"
                    "COALESCE(iva_rate,0))) AS "
                    "sum_gross FROM project_additional_works "
                    "WHERE project_key_norm IN (?,?)"
                )
                cur = conn.execute(sql_ex, (k1, k2))
                r2 = cur.fetchone()
                if r2:
                    extras_total_net = float(r2[0] or 0)
                    extras_total_gross = float(r2[1] or 0)
            except Exception:
                pass

            # Contrato + extras para % facturado
            contract_net = (
                float(sales_contracted_net)
                if sales_contracted_net is not None
                else float(sales_contracted or 0)
            )
            contract_gross = (
                float(sales_contracted_gross)
                if sales_contracted_gross is not None
                else (
                    round(contract_net * (1.0 + sales_iva_rate), 2)
                    if contract_net
                    else 0.0
                )
            )
            contract_plus_extras_net = round(
                contract_net + extras_total_net, 2
            )
            billed_pct = round(
                (ep_total_net / contract_plus_extras_net) * 100.0, 2
            ) if contract_plus_extras_net > 0 else 0.0

            # Avance
            progress_pct = 0.0
            if _table_exists(conn, "daily_reports"):
                cols = _table_columns(conn, "daily_reports")
                if "project_name" in cols:
                    where, params = _project_where_clause(
                        "COALESCE(project_name,'')", project_key
                    )
                    cur = conn.execute(
                        (
                            "SELECT AVG(COALESCE(avance_pct,0)) "
                            f"FROM daily_reports WHERE {where}"
                        ),
                        params,
                    )
                    progress_pct = float((cur.fetchone() or [0])[0] or 0)

            # Margenes
            resumen.update(
                {
                    # Maintain legacy key as NET value for consistency with PC (net)
                    "sales_contracted": sales_contracted,
                    # Extended fields
                    "sales_contracted_net": sales_contracted_net
                    if sales_contracted_net is not None
                    else sales_contracted,
                    "sales_contracted_gross": sales_contracted_gross,
                    "sales_iva_rate": round(sales_iva_rate, 4),
                    "budget_cost": round(budget_cost, 2),
                    "committed": round(committed, 2),
                    "invoiced_ap": round(invoiced_ap, 2),
                    "paid": round(paid, 2),
                    "ar_invoiced": round(ar_invoiced, 2),
                    "ar_collected": round(ar_collected, 2),
                    # Contrato y EP/Extras
                    "contract_net": round(contract_net, 2),
                    "contract_gross": round(contract_gross, 2),
                    "extras_net": round(extras_total_net, 2),
                    "extras_gross": round(extras_total_gross, 2),
                    "contract_plus_extras_net": contract_plus_extras_net,
                    "ep_total_net": round(ep_total_net, 2),
                    "ep_total_gross": round(ep_total_gross, 2),
                    "billed_pct": billed_pct,
                    "margin_expected": round(
                        sales_contracted - budget_cost, 2
                    ),
                    "margin_committed": round(sales_contracted - committed, 2),
                    "margin_real": round(sales_contracted - invoiced_ap, 2),
                    "progress_pct": round(progress_pct, 2),
                }
            )

            # Flags simples
            flags: list[str] = []
            if committed > 0 and budget_cost > 0 and committed > budget_cost:
                flags.append("exceeds_budget")
            if invoiced_ap > committed > 0:
                flags.append("invoice_over_po")
            if paid > invoiced_ap > 0:
                flags.append("overpaid")
            resumen["flags"] = flags

            # Próximos hitos (si hay vistas)
            next_milestones: list[dict] = []
            if _table_exists(conn, "v_project_schedule"):
                where, params = _project_where_clause("COALESCE(project_name,'')", project_key)
                cur = conn.execute(
                    f"SELECT title, date FROM v_project_schedule WHERE {where} AND date >= date('now') ORDER BY date ASC LIMIT 5",
                    params,
                )
                for t, d in cur.fetchall():
                    next_milestones.append({"title": t, "date": d})
            resumen["next_milestones"] = next_milestones

            return jsonify(resumen)
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/summary: %s", e)
        return jsonify({"error": "server_error"}), 500


@app.route("/api/projects/<project_key>/payments", methods=["GET", "POST"])
def api_project_payments(project_key: str):
    """Listar y crear Estados de Pago del proyecto (persistidos localmente)."""
    try:
        with db_conn(DB_PATH) as conn:
            _ensure_payment_states(conn)
            k1 = _norm_key(project_key)
            k2 = _norm_key(_strip_code_prefix(project_key))
            if request.method == "GET":
                sql = (
                    "SELECT id, ep_number, date, net_amount, iva_rate, "
                    "COALESCE(gross_amount, "
                    "net_amount + net_amount*COALESCE(iva_rate,0)), note "
                    "FROM project_payment_states "
                    "WHERE project_key_norm IN (?,?) "
                    "ORDER BY date ASC, id ASC"
                )
                cur = conn.execute(sql, (k1, k2))
                items = []
                total_net = 0.0
                total_gross = 0.0
                for r in cur.fetchall():
                    net = float(r[3] or 0)
                    gross = float(r[5] or 0)
                    total_net += net
                    total_gross += gross
                    items.append(
                        {
                            "id": r[0],
                            "ep_number": r[1],
                            "date": r[2],
                            "net_amount": net,
                            "iva_rate": float(r[4] or 0),
                            "gross_amount": gross,
                            "note": r[6],
                        }
                    )
                return jsonify(
                    {
                        "items": items,
                        "totals": {
                            "net": round(total_net, 2),
                            "gross": round(total_gross, 2),
                        },
                    }
                )
            # POST
            data = request.get_json(silent=True) or {}
            net = data.get("net_amount")
            gross = data.get("gross_amount")
            iva = data.get("iva_rate", 0.19)
            if net is None and gross is None:
                return jsonify({"error": "missing:net_or_gross"}), 400
            if net is None and gross is not None:
                net = round(float(gross) / (1.0 + float(iva)), 2)
            if gross is None and net is not None:
                gross = round(float(net) * (1.0 + float(iva)), 2)
            insert_sql = (
                "INSERT INTO project_payment_states("
                "project_key_norm, project_key, ep_number, date, "
                "net_amount, iva_rate, gross_amount, note) "
                "VALUES(?,?,?,?,?,?,?,?)"
            )
            conn.execute(
                insert_sql,
                (
                    k1,
                    project_key,
                    data.get("ep_number"),
                    data.get("date"),
                    float(net or 0),
                    float(iva or 0),
                    float(gross or 0),
                    data.get("note"),
                ),
            )
            conn.commit()
            return jsonify({"ok": True}), 201
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/payments: %s", e)
        return jsonify({"items": [], "totals": {"net": 0, "gross": 0}}), 500


@app.route("/api/projects/<project_key>/extras", methods=["GET", "POST"])
def api_project_extras(project_key: str):
    """Listar y crear Obras Adicionales del proyecto (persistencia local)."""
    try:
        with db_conn(DB_PATH) as conn:
            _ensure_additional_works(conn)
            k1 = _norm_key(project_key)
            k2 = _norm_key(_strip_code_prefix(project_key))
            if request.method == "GET":
                sql = (
                    "SELECT id, name, status, net_amount, iva_rate, "
                    "COALESCE(gross_amount, "
                    "net_amount + net_amount*COALESCE(iva_rate,0)), note "
                    "FROM project_additional_works "
                    "WHERE project_key_norm IN (?,?) "
                    "ORDER BY id ASC"
                )
                cur = conn.execute(sql, (k1, k2))
                items = []
                total_net = 0.0
                total_gross = 0.0
                for r in cur.fetchall():
                    net = float(r[3] or 0)
                    gross = float(r[5] or 0)
                    total_net += net
                    total_gross += gross
                    items.append(
                        {
                            "id": r[0],
                            "name": r[1],
                            "status": r[2],
                            "net_amount": net,
                            "iva_rate": float(r[4] or 0),
                            "gross_amount": gross,
                            "note": r[6],
                        }
                    )
                return jsonify(
                    {
                        "items": items,
                        "totals": {
                            "net": round(total_net, 2),
                            "gross": round(total_gross, 2),
                        },
                    }
                )
            # POST
            data = request.get_json(silent=True) or {}
            net = data.get("net_amount")
            gross = data.get("gross_amount")
            iva = data.get("iva_rate", 0.19)
            if net is None and gross is None:
                return jsonify({"error": "missing:net_or_gross"}), 400
            if net is None and gross is not None:
                net = round(float(gross) / (1.0 + float(iva)), 2)
            if gross is None and net is not None:
                gross = round(float(net) * (1.0 + float(iva)), 2)
            insert_sql = (
                "INSERT INTO project_additional_works("
                "project_key_norm, project_key, name, status, "
                "net_amount, iva_rate, gross_amount, note) "
                "VALUES(?,?,?,?,?,?,?,?)"
            )
            conn.execute(
                insert_sql,
                (
                    k1,
                    project_key,
                    data.get("name"),
                    data.get("status"),
                    float(net or 0),
                    float(iva or 0),
                    float(gross or 0),
                    data.get("note"),
                ),
            )
            conn.commit()
            return jsonify({"ok": True}), 201
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/extras: %s", e)
        return jsonify({"items": [], "totals": {"net": 0, "gross": 0}}), 500


@app.route("/api/projects/<project_key>/contract", methods=["GET", "POST"])
def api_project_contract_override(project_key: str):
    """Get or set a local contract override for a project.

    POST body (JSON):
    - project_name_display (optional)
    - contract_net (optional)
    - contract_gross (optional)
    - iva_rate (optional, default 0.19)
    - currency (optional, default CLP)
    - source, note (optional)
    One of contract_net or contract_gross is required.
    """
    try:
        with db_conn(DB_PATH) as conn:
            if request.method == "GET":
                ov = _get_contract_override(conn, project_key)
                return jsonify(ov or {})
            payload = request.get_json(silent=True) or {}
            ov = _upsert_contract_override(
                conn,
                project_key=project_key,
                project_name_display=payload.get("project_name_display"),
                contract_net=payload.get("contract_net"),
                contract_gross=payload.get("contract_gross"),
                iva_rate=payload.get("iva_rate"),
                currency=payload.get("currency"),
                source=payload.get("source"),
                note=payload.get("note"),
            )
            return jsonify(ov), 201
    except ValueError as ve:  # missing net/gross
        return jsonify({"error": str(ve)}), 400
    except Exception as e:  # noqa: BLE001
        logger.error("Error en contract override: %s", e)
        return jsonify({"error": "server_error"}), 500


@app.route("/api/projects/<project_key>/purchases")
def api_project_purchases(project_key: str):
    """Listado de OC del proyecto con paginación básica."""
    try:
        with db_conn(DB_PATH) as conn:
            if not _table_exists(conn, "purchase_orders_unified"):
                return jsonify({"items": [], "meta": {"total": 0, "page": 1, "page_size": 50, "pages": 0}})
            args = request.args
            page = max(1, int(args.get("page", 1)))
            page_size = max(1, min(200, int(args.get("page_size", 50))))
            offset = (page - 1) * page_size
            cols = _table_columns(conn, "purchase_orders_unified")
            pname_col = "COALESCE(zoho_project_name,'')" if "zoho_project_name" in cols else "COALESCE(project_name,'')"
            where, params = _project_where_clause(pname_col, project_key)

            status_filter_sql = ""
            if "status" in cols:
                try:
                    approved_cond = (
                        " AND LOWER(COALESCE(status,'')) IN ("
                        "'approved','closed'"
                        ")"
                    )
                    sum_sql = (
                        "SELECT SUM(COALESCE(total_amount,0)) "
                        "FROM purchase_orders_unified "
                        f"WHERE {where}" + approved_cond
                    )
                    cur = conn.execute(sum_sql, params)
                    val = float((cur.fetchone() or [0])[0] or 0)
                    if val > 0:
                        status_filter_sql = approved_cond
                except sqlite3.Error:
                    pass

            count_sql = (
                "SELECT COUNT(1) FROM purchase_orders_unified "
                f"WHERE {where}{status_filter_sql}"
            )
            data_sql = (
                "SELECT po_number, po_date, total_amount, currency, status, "
                "COALESCE(zoho_vendor_name, vendor_rut, '') AS vendor_name "
                "FROM purchase_orders_unified WHERE "
                + where
                + status_filter_sql
                + " ORDER BY po_date DESC LIMIT OFFSET ?"
            )
            cur = conn.execute(count_sql, params)
            total = cur.fetchone()[0]
            cur = conn.execute(data_sql, [*params, page_size, offset])
            rows = []
            for r in cur.fetchall():
                rows.append(
                    {
                        "po_number": r[0],
                        "po_date": r[1],
                        "total_amount": float(r[2] or 0),
                        "currency": r[3],
                        "status": r[4],
                        "vendor_name": r[5],
                    }
                )
            return jsonify(
                {
                    "items": rows,
                    "meta": {
                        "total": total,
                        "page": page,
                        "page_size": page_size,
                        "pages": (total + page_size - 1) // page_size,
                    },
                }
            )
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/purchases: %s", e)
        return jsonify({"items": [], "meta": {"total": 0, "page": 1, "page_size": 50, "pages": 0}}), 500


@app.route("/api/projects/<project_key>/budget")
def api_project_budget(project_key: str):
    """Presupuesto por proyecto (totales y capítulos si existen vistas)."""
    try:
        with db_conn(DB_PATH) as conn:
            result = {"chapters": [], "totals": {"pc_total": 0.0, "committed": 0.0, "available_conservative": 0.0}}
            pc_total = 0.0
            committed = 0.0

            if _table_exists(conn, "v_presupuesto_totales"):
                where, params = _project_where_clause("COALESCE(project_name,'')", project_key)
                cur = conn.execute(
                    f"SELECT COALESCE(total_presupuesto,0) FROM v_presupuesto_totales WHERE {where}",
                    params,
                )
                row = cur.fetchone()
                if row:
                    pc_total = float(row[0] or 0)

            if _table_exists(conn, "v_po_committed_project"):
                where, params = _project_where_clause("COALESCE(project_name,'')", project_key)
                cur = conn.execute(
                    f"SELECT COALESCE(committed,0) FROM v_po_committed_project WHERE {where}",
                    params,
                )
                row = cur.fetchone()
                if row:
                    committed = float(row[0] or 0)

            result["totals"]["pc_total"] = round(pc_total, 2)
            result["totals"]["committed"] = round(committed, 2)
            result["totals"]["available_conservative"] = round(pc_total - committed, 2)
            return jsonify(result)
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/budget: %s", e)
        return jsonify({"chapters": [], "totals": {"pc_total": 0, "committed": 0, "available_conservative": 0}}), 500


@app.route("/api/projects/<project_key>/finance")
def api_project_finance(project_key: str):
    """Finanzas: AP, pagos, AR y cobranzas + buckets de cashflow y EP/AR mensuales.

    Adds (optionally when views exist):
    - ep_approved: [{month, amount_net}]
    - ar_expected: [{month, amount}]
    - ar_actual:   [{month, amount}]
    """
    try:
        with db_conn(DB_PATH) as conn:
            args = request.args
            from_month = args.get("from")
            to_month = args.get("to")
            where, params = _project_where_clause("COALESCE(project_name,'')", project_key)
            out = {
                "ap_invoices": [],
                "payments": [],
                "ar_invoices": [],
                "collections": [],
                "cashflow": {"expected": [], "actual": [], "variance": []},
                # Optional series; only present if views exist
                "ep_approved": [],
                "ar_expected": [],
                "ar_actual": [],
            }

            if _table_exists(conn, "v_facturas_compra"):
                cur = conn.execute(
                    f"SELECT invoice_id, vendor, amount, date FROM v_facturas_compra WHERE {where} ORDER BY date DESC LIMIT 100",
                    params,
                )
                out["ap_invoices"] = [
                    {"invoice_id": r[0], "vendor": r[1], "amount": float(r[2] or 0), "date": r[3]} for r in cur.fetchall()
                ]
            if _table_exists(conn, "v_cartola_bancaria"):
                cur = conn.execute(
                    f"SELECT payment_id, paid_amount, paid_date FROM v_cartola_bancaria WHERE {where} ORDER BY paid_date DESC LIMIT 100",
                    params,
                )
                out["payments"] = [
                    {"payment_id": r[0], "amount": float(r[1] or 0), "date": r[2]} for r in cur.fetchall()
                ]
            if _table_exists(conn, "v_ar_invoices"):
                cur = conn.execute(
                    f"SELECT invoice_id, customer, amount, date FROM v_ar_invoices WHERE {where} ORDER BY date DESC LIMIT 100",
                    params,
                )
                out["ar_invoices"] = [
                    {"invoice_id": r[0], "customer": r[1], "amount": float(r[2] or 0), "date": r[3]} for r in cur.fetchall()
                ]
            if _table_exists(conn, "v_cobranzas"):
                cur = conn.execute(
                    f"SELECT receipt_id, amount, date FROM v_cobranzas WHERE {where} ORDER BY date DESC LIMIT 100",
                    params,
                )
                out["collections"] = [
                    {"receipt_id": r[0], "amount": float(r[1] or 0), "date": r[2]} for r in cur.fetchall()
                ]

            # Cashflow buckets (expected/actual/variance)
            # Aplicar filtro de rango si se entrega (YYYY-MM)
            def _month_between(col: str) -> str:
                conds = []
                if from_month:
                    conds.append(f"{col} >= ?")
                if to_month:
                    conds.append(f"{col} <= ?")
                return (" AND ".join(conds)) if conds else ""

            extra_params: list = []
            if from_month:
                extra_params.append(from_month + "-01")
            if to_month:
                extra_params.append(to_month + "-01")

            if _table_exists(conn, "v_cashflow_expected_project"):
                range_sql = _month_between("bucket_month")
                sql = f"SELECT bucket_month, expected_outflow FROM v_cashflow_expected_project WHERE {where}"
                if range_sql:
                    sql += " AND " + range_sql
                cur = conn.execute(sql, [*params, *extra_params])
                out["cashflow"]["expected"] = [
                    {"month": r[0], "amount": float(r[1] or 0)} for r in cur.fetchall()
                ]
            if _table_exists(conn, "v_cashflow_actual_project"):
                range_sql = _month_between("bucket_month")
                sql = f"SELECT bucket_month, actual_outflow FROM v_cashflow_actual_project WHERE {where}"
                if range_sql:
                    sql += " AND " + range_sql
                cur = conn.execute(sql, [*params, *extra_params])
                out["cashflow"]["actual"] = [
                    {"month": r[0], "amount": float(r[1] or 0)} for r in cur.fetchall()
                ]
            if _table_exists(conn, "v_cashflow_variance_project"):
                range_sql = _month_between("bucket_month")
                sql = f"SELECT bucket_month, expected_outflow, actual_outflow, variance FROM v_cashflow_variance_project WHERE {where}"
                if range_sql:
                    sql += " AND " + range_sql
                cur = conn.execute(sql, [*params, *extra_params])
                out["cashflow"]["variance"] = [
                    {"month": r[0], "expected": float(r[1] or 0), "actual": float(r[2] or 0), "variance": float(r[3] or 0)}
                    for r in cur.fetchall()
                ]

            # EP/AR monthly (from EP module views if present)
            # Filter by project by tolerant name; these views aggregate by project_id
            # so we also try by resolved project ids when feasible.
            try:
                pids = _resolve_project_ids(conn, project_key)
            except Exception:
                pids = []

            def _month_range_cond(col: str) -> tuple[str, list]:
                conds = []
                vals: list = []
                if from_month:
                    conds.append(f"{col} >= ?")
                    vals.append(from_month + "-01")
                if to_month:
                    conds.append(f"{col} <= ?")
                    vals.append(to_month + "-01")
                return (" AND ".join(conds), vals)

            if pids and _table_exists(conn, "v_ep_approved_project"):
                rng_sql, rng_vals = _month_range_cond("bucket_month")
                ph = ",".join(["?"] * len(pids))
                sql = (
                    "SELECT bucket_month, SUM(ep_amount_net) FROM v_ep_approved_project "
                    f"WHERE project_id IN ({ph})"
                )
                if rng_sql:
                    sql += " AND " + rng_sql
                sql += " GROUP BY bucket_month ORDER BY bucket_month"
                cur = conn.execute(sql, [*pids, *rng_vals])
                out["ep_approved"] = [
                    {"month": r[0], "amount_net": float(r[1] or 0)}
                    for r in cur.fetchall()
                ]

            if pids and _table_exists(conn, "v_ar_expected_project"):
                rng_sql, rng_vals = _month_range_cond("bucket_month")
                ph = ",".join(["?"] * len(pids))
                sql = (
                    "SELECT bucket_month, SUM(expected_inflow) FROM v_ar_expected_project "
                    f"WHERE project_id IN ({ph})"
                )
                if rng_sql:
                    sql += " AND " + rng_sql
                sql += " GROUP BY bucket_month ORDER BY bucket_month"
                cur = conn.execute(sql, [*pids, *rng_vals])
                out["ar_expected"] = [
                    {"month": r[0], "amount": float(r[1] or 0)}
                    for r in cur.fetchall()
                ]

            if pids and _table_exists(conn, "v_ar_actual_project"):
                rng_sql, rng_vals = _month_range_cond("bucket_month")
                ph = ",".join(["?"] * len(pids))
                sql = (
                    "SELECT bucket_month, SUM(actual_inflow) FROM v_ar_actual_project "
                    f"WHERE project_id IN ({ph})"
                )
                if rng_sql:
                    sql += " AND " + rng_sql
                sql += " GROUP BY bucket_month ORDER BY bucket_month"
                cur = conn.execute(sql, [*pids, *rng_vals])
                out["ar_actual"] = [
                    {"month": r[0], "amount": float(r[1] or 0)}
                    for r in cur.fetchall()
                ]

            return jsonify(out)
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/finance: %s", e)
        return jsonify({"ap_invoices": [], "payments": [], "ar_invoices": [], "collections": [], "cashflow": {"expected": [], "actual": [], "variance": []}}), 500


@app.route("/api/projects/<project_key>/time")
def api_project_time(project_key: str):
    try:
        with db_conn(DB_PATH) as conn:
            out = {"milestones": [], "progress_pct": 0}
            if _table_exists(conn, "v_project_schedule"):
                where, params = _project_where_clause("COALESCE(project_name,'')", project_key)
                cur = conn.execute(
                    f"SELECT title, date FROM v_project_schedule WHERE {where} ORDER BY date ASC LIMIT 50",
                    params,
                )
                out["milestones"] = [{"title": r[0], "date": r[1]} for r in cur.fetchall()]
            # progress de daily_reports si existe
            if _table_exists(conn, "daily_reports"):
                cols = _table_columns(conn, "daily_reports")
                if "project_name" in cols:
                    where, params = _project_where_clause("COALESCE(project_name,'')", project_key)
                    cur = conn.execute(
                        f"SELECT AVG(COALESCE(avance_pct,0)) FROM daily_reports WHERE {where}",
                        params,
                    )
                    out["progress_pct"] = round(float((cur.fetchone() or [0])[0] or 0), 2)
            return jsonify(out)
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/time: %s", e)
        return jsonify({"milestones": [], "progress_pct": 0}), 500


@app.route("/api/projects/<project_key>/docs")
def api_project_docs(project_key: str):
    try:
        with db_conn(DB_PATH) as conn:
            files = []
            if _table_exists(conn, "project_drive_files"):
                where, params = _project_where_clause("COALESCE(project_name,'')", project_key)
                cur = conn.execute(
                    f"SELECT file_id, title, mime, url, modified_time FROM project_drive_files WHERE {where} ORDER BY modified_time DESC LIMIT 100",
                    params,
                )
                files = [
                    {"id": r[0], "title": r[1], "mime": r[2], "url": r[3], "modified_time": r[4]} for r in cur.fetchall()
                ]
            return jsonify({"files": files})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/docs: %s", e)
        return jsonify({"files": []}), 500


@app.route("/api/projects/<project_key>/ep")
def api_project_ep_list(project_key: str):
    """Lista de Estados de Pago (EP) del proyecto identificado por clave flexible.

    Resuelve IDs de proyecto desde nombre o ID y lista encabezados con totales,
    reutilizando el mismo contrato de la ruta de ep_api.
    """
    try:
        with db_conn(DB_PATH) as conn:
            # Resolver posibles IDs
            pids = _resolve_project_ids(conn, project_key)
            if not pids:
                return jsonify({"items": []})
            ph = ",".join(["?"] * len(pids))
            rows = conn.execute(
                (
                    "SELECT h.*, "
                    "       (SELECT COALESCE(SUM(l.amount_period),0) FROM ep_lines l WHERE l.ep_id = h.id) AS amount_period, "
                    "       (SELECT COALESCE(SUM(d.amount),0) FROM ep_deductions d WHERE d.ep_id = h.id) AS deductions "
                    "  FROM ep_headers h "
                    f" WHERE h.project_id IN ({ph}) "
                    " ORDER BY COALESCE(h.approved_at, h.submitted_at) DESC"
                ),
                pids,
            ).fetchall()
            return jsonify({"items": [dict(r) for r in rows]})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/ep: %s", e)
        return jsonify({"items": []}), 500


@app.route("/api/projects/<project_key>/ep/import", methods=["POST"])
def api_project_ep_import(project_key: str):
    """Importar un EP usando una clave de proyecto tolerante.

    Body JSON esperado:
      {
        "ep_header": { ep_number?, period_start?, period_end?, retention_pct?, notes?, contract_id},
        "ep_lines": [ { item_code?, description?, unit?, qty_period?, unit_price?, amount_period?, qty_cum?, amount_cum?, chapter}, ... ],
        "ep_deductions": [ { type, description?, amount }, ... ]
      }
    """
    try:
        with db_conn(DB_PATH) as conn:
            payload = request.get_json(silent=True) or {}
            header = payload.get("ep_header") or {}
            lines = payload.get("ep_lines") or []
            deductions = payload.get("ep_deductions") or []
            if not isinstance(lines, list) or len(lines) == 0:
                return jsonify({"error": "missing:ep_lines"}), 422

            pids = _resolve_project_ids(conn, project_key)
            if not pids:
                return jsonify({"error": "project_not_found", "project_key": project_key}), 422
            project_id = int(pids[0])

            _ensure_ep_min_schema(conn)
            cur = conn.cursor()
            cur.execute(
                (
                    "INSERT INTO ep_headers("
                    "project_id, contract_id, ep_number, period_start, period_end, submitted_at, status, retention_pct, notes"
                    ") VALUES(?,?,?,?,?, date('now'), 'submitted', ?, ?)"
                ),
                (
                    project_id,
                    header.get("contract_id"),
                    header.get("ep_number"),
                    header.get("period_start"),
                    header.get("period_end"),
                    header.get("retention_pct"),
                    header.get("notes"),
                ),
            )
            ep_id = cur.lastrowid

            # Validación contra contrato/SOV si existe
            sov = {}
            prev = {}
            if header.get("contract_id") is not None:
                try:
                    c_id = header.get("contract_id")
                    # Capacidades por item
                    sov = {
                        r[0]: float(r[1] or 0)
                        for r in conn.execute(
                            "SELECT item_code, COALESCE(line_total,0) FROM client_sov_items WHERE contract_id=?",
                            (c_id,),
                        ).fetchall()
                    }
                    # Acumulado previo aprobado por item
                    prev = {
                        r[0]: float(r[1] or 0)
                        for r in conn.execute(
                            (
                                "SELECT l.item_code, COALESCE(SUM(l.amount_period),0) AS amount_cum "
                                "FROM ep_lines l JOIN ep_headers h ON h.id=l.ep_id "
                                "WHERE h.contract_id=AND h.status IN('approved','invoiced','paid') "
                                "GROUP BY l.item_code"
                            ),
                            (c_id,),
                        ).fetchall()
                    }
                except Exception:
                    sov, prev = {}, {}

            for ln in lines:
                amt = ln.get("amount_period")
                if (
                    amt is None
                    and ln.get("qty_period") is not None
                    and ln.get("unit_price") is not None
                ):
                    try:
                        amt = float(ln["qty_period"]) * float(ln["unit_price"])
                    except Exception:
                        amt = None

                code = ln.get("item_code")
                if code and code in sov:
                    cap = float(sov.get(code) or 0)
                    prev_amt = float(prev.get(code, 0))
                    if (prev_amt + float(amt or 0)) > (cap + 1e-6):
                        return (
                            jsonify({
                                "error": "ep_exceeds_contract_item",
                                "detail": f"Item {code} excede SOV",
                                "item_code": code,
                                "cap": cap,
                                "prev": prev_amt,
                                "attempt": float(amt or 0),
                            }),
                            422,
                        )

                cur.execute(
                    (
                        "INSERT INTO ep_lines("
                        "ep_id, sov_item_id, item_code, description, unit, "
                        "qty_period, unit_price, amount_period, qty_cum, amount_cum, chapter) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?)"
                    ),
                    (
                        ep_id,
                        ln.get("sov_item_id"),
                        code,
                        ln.get("description"),
                        ln.get("unit"),
                        ln.get("qty_period"),
                        ln.get("unit_price"),
                        amt,
                        ln.get("qty_cum"),
                        ln.get("amount_cum"),
                        ln.get("chapter"),
                    ),
                )

            for d in deductions:
                cur.execute(
                    (
                        "INSERT INTO ep_deductions(ep_id, type, description, amount) "
                        "VALUES(?,?,?,?)"
                    ),
                    (
                        ep_id,
                        d.get("type"),
                        d.get("description"),
                        d.get("amount"),
                    ),
                )

            conn.commit()
            return jsonify({"ok": True, "ep_id": ep_id})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/ep/import: %s", e)
        return jsonify({"error": "server_error"}), 500


@app.route("/api/projects/<project_key>/chats")
def api_project_chats(project_key: str):
    try:
        with db_conn(DB_PATH) as conn:
            threads = []
            if _table_exists(conn, "whatsapp_threads"):
                where, params = _project_where_clause("COALESCE(project_name,'')", project_key)
                cur = conn.execute(
                    f"SELECT id, counterpart, last_message, updated_at FROM whatsapp_threads WHERE {where} ORDER BY updated_at DESC LIMIT 100",
                    params,
                )
                threads = [
                    {"id": r[0], "counterpart": r[1], "last_message": r[2], "updated_at": r[3]} for r in cur.fetchall()
                ]
            return jsonify({"threads": threads})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/chats: %s", e)
        return jsonify({"threads": []}), 500


@app.route("/api/projects/<project_key>/reconcile/ap_po")
def api_project_reconcile_ap_po(project_key: str):
    """Sugiere conciliación entre Facturas de Compra (AP) y Órdenes de Compra (PO) por proyecto.

    Estrategia:
    - Filtrar AP y PO por nombre de proyecto tolerante (con y sin prefijo numérico)
    - Intentar match exacto por monto (o monto/1.19 por IVA) y ventana de fecha (+/- 7 días)
    - Devolver mejores 50 enlaces sugeridos con score simple
    """
    try:
        with db_conn(DB_PATH) as conn:
            cols_ap = _table_columns(conn, "v_facturas_compra") if _table_exists(conn, "v_facturas_compra") else set()
            cols_po = _table_columns(conn, "purchase_orders_unified") if _table_exists(conn, "purchase_orders_unified") else set()
            if not cols_ap or not cols_po:
                return jsonify({"items": [], "meta": {"total": 0}})

            # Column discovery
            ap_amount = _first_existing_col(cols_ap, ["monto_total", "amount", "monto"])
            ap_date = _first_existing_col(cols_ap, ["fecha", "date"])
            ap_vendor = _first_existing_col(cols_ap, ["proveedor_rut", "proveedor", "vendor"])
            ap_doc = _first_existing_col(cols_ap, ["documento_numero", "document_number", "doc"])
            ap_pname = _first_existing_col(cols_ap, ["project_name", "proyecto", "zoho_project_name"]) or ""

            po_amount = _first_existing_col(cols_po, ["total_amount", "monto_total", "amount"])
            po_date = _first_existing_col(cols_po, ["po_date", "fecha", "date"])
            po_vendor = _first_existing_col(cols_po, ["vendor_rut", "zoho_vendor_name"])  # prefer rut
            po_doc = _first_existing_col(cols_po, ["po_number", "zoho_po_id"]) or "po_number"
            po_pname = _first_existing_col(cols_po, ["zoho_project_name", "project_name"]) or ""

            if not (ap_amount and ap_date and po_amount and po_date and po_pname and ap_pname):
                return jsonify({"items": [], "meta": {"total": 0}})

            # WHERE por proyecto (tolerante)
            where_ap, params_ap = _project_where_clause(f"COALESCE({ap_pname},'')", project_key)
            where_po, params_po = _project_where_clause(f"COALESCE({po_pname},'')", project_key)

            # Traer AP y PO del proyecto
            ap_sql = (
                f"SELECT {ap_doc} AS doc, {ap_vendor} AS vendor, {ap_amount} AS amount, {ap_date} AS fecha "
                f"FROM v_facturas_compra WHERE {where_ap}"
            )
            po_sql = (
                f"SELECT {po_doc} AS po, {po_vendor} AS vendor, {po_amount} AS amount, {po_date} AS fecha "
                f"FROM purchase_orders_unified WHERE {where_po}"
            )
            cur = conn.execute(ap_sql, params_ap)
            ap_rows = [{"doc": r[0], "vendor": r[1], "amount": float(r[2] or 0), "fecha": r[3]} for r in cur.fetchall()]
            cur = conn.execute(po_sql, params_po)
            po_rows = [{"po": r[0], "vendor": r[1], "amount": float(r[2] or 0), "fecha": r[3]} for r in cur.fetchall()]

            # Matching heurístico
            suggestions = []
            def _parse_date(s: str | None):
                try:
                    from datetime import datetime as _dt
                    return _dt.fromisoformat(str(s)[:10]).date() if s else None
                except Exception:
                    return None

            for ap in ap_rows:
                ap_amt = abs(ap["amount"] or 0)
                ap_amt_net = round(ap_amt / 1.19, 2) if ap_amt else 0
                ap_date = _parse_date(ap["fecha"])  # type: ignore
                for po in po_rows:
                    score = 0
                    po_amt = abs(po["amount"] or 0)
                    if po_amt == ap_amt or po_amt == ap_amt_net:
                        score += 70
                    elif ap_amt and abs(po_amt - ap_amt) / ap_amt <= 0.01:
                        score += 50
                    # vendor match (RUT preferido)
                    if ap.get("vendor") and po.get("vendor") and str(ap["vendor"]).strip() == str(po["vendor"]).strip():
                        score += 20
                    # fecha window
                    po_date = _parse_date(po["fecha"])  # type: ignore
                    if ap_date and po_date:
                        delta = abs((po_date - ap_date).days)
                        if delta == 0:
                            score += 10
                        elif delta <= 7:
                            score += 5
                    if score >= 50:
                        suggestions.append(
                            {
                                "ap_doc": ap.get("doc"),
                                "po_number": po.get("po"),
                                "vendor_ap": ap.get("vendor"),
                                "vendor_po": po.get("vendor"),
                                "amount_ap": ap_amt,
                                "amount_po": po_amt,
                                "date_ap": ap.get("fecha"),
                                "date_po": po.get("fecha"),
                                "score": score,
                            }
                        )

            suggestions.sort(key=lambda x: x["score"], reverse=True)
            top = suggestions[:50]
            return jsonify({"items": top, "meta": {"total": len(top), "project": project_key}})
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/reconcile/ap_po: %s", e)
        return jsonify({"items": [], "meta": {"total": 0}}), 500


@app.route("/api/projects/<project_key>/ai/summary", methods=["POST"])
def api_project_ai_summary(project_key: str):
    try:
        # Stub inicial: devolver placeholder hasta integrar motor IA
        payload = request.get_json(silent=True) or {}
        tone = (payload.get("tone") or "neutral").lower()
        return jsonify(
            {
                "summary_text": f"Resumen IA ({tone}) para proyecto '{project_key}' aún no implementado.",
                "bullets": [
                    "Ventas, PC, OC, AP, Pagado consolidados",
                    "Cashflow esperado vs actual",
                    "Riesgos y próximos hitos",
                ],
                "risks": [],
            }
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/ai/summary: %s", e)
        return jsonify({"summary_text": "error", "bullets": [], "risks": []}), 500


@app.route("/api/projects/<project_key>/ai/qna", methods=["POST"])
def api_project_ai_qna(project_key: str):
    try:
        payload = request.get_json(silent=True) or {}
        question = (payload.get("question") or "").strip()
        if not question:
            return jsonify({"error": "missing_field:question"}), 422
        # Stub de respuesta
        return jsonify(
            {
                "answer": f"Q&A aún no implementado. Pregunta: '{question}'. Proyecto: '{project_key}'.",
                "citations": [],
            }
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/projects/<id>/ai/qna: %s", e)
        return jsonify({"answer": "error", "citations": []}), 500


@app.route("/api/purchase_orders", methods=["GET", "POST"])
def api_purchase_orders():
    try:
        with db_conn(DB_PATH) as conn:
            if not _table_exists(conn, "purchase_orders_unified"):
                if request.method == "GET":
                    return jsonify(
                        {
                            "items": [],
                            "meta": {
                                "total": 0,
                                "page": 1,
                                "page_size": 50,
                                "pages": 0,
                            },
                        }
                    )
                return jsonify({"error": "table_not_found"}), 400

            cols = _table_columns(conn, "purchase_orders_unified")

            if request.method == "GET":
                args = request.args
                page = max(1, int(args.get("page", 1)))
                page_size = max(1, min(200, int(args.get("page_size", 50))))
                offset = (page - 1) * page_size

                # Build select list dynamically
                select_parts = []
                if "id" in cols:
                    select_parts.append("id")
                else:
                    select_parts.append("rowid AS id")
                for c in [
                    "po_number",
                    "po_date",
                    "total_amount",
                    "currency",
                    "status",
                    "zoho_project_id",
                    "zoho_project_name",
                    "zoho_vendor_name",
                    "vendor_rut",
                ]:
                    if c in cols:
                        select_parts.append(c)
                select_sql = ", ".join(select_parts)

                where = ["1=1"]
                params: list = []

                # Filters
                if (v := args.get("vendor_rut")) and "vendor_rut" in cols:
                    where.append("vendor_rut = ?")
                    params.append(v)
                if (v := args.get("project")) and "zoho_project_name" in cols:
                    where.append("zoho_project_name LIKE ?")
                    params.append(f"%{v}%")
                if (v := args.get("date_from")) and "po_date" in cols:
                    where.append("po_date >= ?")
                    params.append(v)
                if (v := args.get("date_to")) and "po_date" in cols:
                    where.append("po_date <= ?")
                    params.append(v)
                if (v := args.get("search")):
                    like = f"%{v}%"
                    or_parts = []
                    if "po_number" in cols:
                        or_parts.append("po_number LIKE ?")
                        params.append(like)
                    if "zoho_vendor_name" in cols:
                        or_parts.append("zoho_vendor_name LIKE ?")
                        params.append(like)
                    if or_parts:
                        where.append("(" + " OR ".join(or_parts) + ")")

                allowed_order = ["po_date", "total_amount", "po_number", "id"]
                order_by = args.get("order_by", "po_date")
                order_dir = (
                    "ASC"
                    if args.get("order_dir", "DESC").upper() == "ASC"
                    else "DESC"
                )
                if order_by not in allowed_order:
                    order_by = "po_date" if "po_date" in cols else "id"

                where_sql = " AND ".join(where)
                data_sql = (
                    f"SELECT {select_sql} FROM purchase_orders_unified "
                    f"WHERE {where_sql} ORDER BY {order_by} {order_dir} "
                    "LIMIT OFFSET ?"
                )
                count_sql = (
                    "SELECT COUNT(1) FROM purchase_orders_unified WHERE "
                    f"{where_sql}"
                )

                cur = conn.execute(count_sql, params)
                total = cur.fetchone()[0]
                cur = conn.execute(data_sql, [*params, page_size, offset])
                rows = [dict(r) for r in cur.fetchall()]
                return jsonify(
                    {
                        "items": rows,
                        "meta": {
                            "total": total,
                            "page": page,
                            "page_size": page_size,
                            "pages": (total + page_size - 1) // page_size,
                        },
                    }
                )

            # POST (create)
            data = request.get_json(silent=True) or {}
            # Requisitos mínimos: RUT, fecha, total; número puede autogenerarse.
            required = ["vendor_rut", "po_date", "total_amount"]
            for k in required:
                if not data.get(k):
                    return jsonify({"error": f"missing_field:{k}"}), 400

            # Normalizar RUT
            if data.get("vendor_rut"):
                data["vendor_rut"] = _rut_normalize(
                    str(data.get("vendor_rut"))
                )

            # Asignar número si no viene provisto
            if not data.get("po_number"):
                try:
                    data["po_number"] = _po_next_number(conn)
                    data.setdefault("source_platform", "ofitec_api")
                except Exception:
                    # Fallback por tiempo
                    data["po_number"] = "PO-" + datetime.now().strftime(
                        "%Y%m%d%H%M%S"
                    )
                    data.setdefault("source_platform", "ofitec_api")

            # Duplicate check (if columns exist) using zoho_po_id when provided
            dup_where = []
            dup_params: list = []
            if data.get("zoho_po_id") and "zoho_po_id" in cols:
                dup_where.append("zoho_po_id = ?")
                dup_params.append(data["zoho_po_id"])
            else:
                for (k, col) in [
                    ("vendor_rut", "vendor_rut"),
                    ("po_number", "po_number"),
                    ("po_date", "po_date"),
                    ("total_amount", "total_amount"),
                ]:
                    if col in cols:
                        dup_where.append(f"{col} = ?")
                        dup_params.append(data[k])
            if dup_where:
                cur = conn.execute(
                    "SELECT COUNT(1) FROM purchase_orders_unified WHERE "
                    + " AND ".join(dup_where),
                    dup_params,
                )
                if cur.fetchone()[0] > 0:
                    return jsonify({"error": "duplicate_po"}), 409

            # Build insert dynamically respecting available columns
            insert_cols = []
            insert_vals = []
            insert_params = []

            def add(col: str, value):
                insert_cols.append(col)
                insert_vals.append("?")
                insert_params.append(value)

            for (k, col) in [
                ("vendor_rut", "vendor_rut"),
                ("po_number", "po_number"),
                ("po_date", "po_date"),
                ("total_amount", "total_amount"),
                ("zoho_vendor_name", "zoho_vendor_name"),
                ("zoho_project_name", "zoho_project_name"),
                ("zoho_po_id", "zoho_po_id"),
                ("zoho_project_id", "zoho_project_id"),
            ]:
                if col in cols and data.get(k) is not None:
                    add(col, data.get(k))

            # Defaults per Ley BD (si existen columnas)
            now_iso = datetime.now().isoformat()
            if "currency" in cols:
                add("currency", data.get("currency") or "CLP")
            if "status" in cols:
                add("status", data.get("status") or "draft")
            if "source_platform" in cols:
                add(
                    "source_platform",
                    data.get("source_platform") or "ofitec.ai",
                )
            if "created_at" in cols:
                add("created_at", now_iso)
            if "migration_id" in cols:
                add(
                    "migration_id",
                    data.get("migration_id") or f"ofitec_ai_manual_{now_iso}",
                )

            sql = (
                "INSERT INTO purchase_orders_unified ("
                + ", ".join(insert_cols)
                + ") VALUES ("
                + ", ".join(insert_vals)
                + ")"
            )
            cur = conn.execute(sql, insert_params)
            conn.commit()

            new_id = cur.lastrowid
            # Crear línea de cashflow planned (opcional)
            try:
                if _table_exists(conn, "cashflow_planned"):
                    amount = float(data.get("total_amount", 0) or 0)
                    conn.execute(
                        (
                            "INSERT INTO cashflow_planned (project_id, category, fecha, monto, moneda, status, source_ref) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)"
                        ),
                        (
                            data.get("zoho_project_id"),
                            "purchase",
                            data.get("po_date"),
                            amount,
                            data.get("currency") or "CLP",
                            "planned",
                            f"PO:{data.get('po_number')}",
                        ),
                    )
                    conn.commit()
            except Exception:
                pass
            # Fetch created row
            id_selector = "id" if "id" in cols else "rowid"
            cur = conn.execute(
                f"SELECT * FROM purchase_orders_unified WHERE {id_selector} = ?",
                (new_id,),
            )
            row = cur.fetchone()
            return jsonify(dict(row)), 201
    except Exception as e:  # noqa: BLE001
        logger.error("Error en /api/purchase_orders: %s", e)
        return jsonify({"error": "server_error"}), 500


@app.route("/api/purchase_orders/<int:item_id>")
def api_purchase_order_detail(item_id: int):
    try:
        with db_conn(DB_PATH) as conn:
            if not _table_exists(conn, "purchase_orders_unified"):
                return jsonify({"error": "table_not_found"}), 400
            cols = _table_columns(conn, "purchase_orders_unified")
            id_selector = "id" if "id" in cols else "rowid"
            cur = conn.execute(
                f"SELECT * FROM purchase_orders_unified WHERE {id_selector} = ?",
                (item_id,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "not_found"}), 404
            return jsonify(dict(row))
    except Exception as e:  # noqa: BLE001
        logger.error("Error en detalle de purchase_order: %s", e)
        return jsonify({"error": "server_error"}), 500


# ---------------------------------------------------------------------------
# AR Rules / Matching progress quick dashboards (serve badges & simple HTML)
# ---------------------------------------------------------------------------

@app.route("/dash/ar-rules/badges/<path:filename>")
def ar_rules_badge_file(filename: str):  # noqa: D401
    """Sirve archivos dentro de la carpeta 'badges' (SVG / JSON / CSV)."""
    try:
        if not BADGES_DIR.exists():  # pragma: no cover - defensive
            return jsonify({"error": "badges_dir_not_found"}), 404
        # Seguridad básica: impedir path traversal
        if ".." in filename or filename.startswith("/"):
            return jsonify({"error": "invalid_path"}), 400
        full = BADGES_DIR / filename
        if not full.exists():
            return jsonify({"error": "not_found"}), 404
        # Usar send_from_directory para delegar mime-type
        return send_from_directory(str(BADGES_DIR), filename)
    except Exception as e:  # noqa: BLE001
        logger.error("Error sirviendo badge %s: %s", filename, e)
        return jsonify({"error": "serve_failed"}), 500


@app.route("/dash/ar-rules")
def ar_rules_static_dashboard():
    """Retorna el HTML estático generado por el workflow (`ar_rules_dashboard.html`)."""
    try:
        html_path = BADGES_DIR / "ar_rules_dashboard.html"
        if not html_path.exists():
            return jsonify({"error": "dashboard_not_generated"}), 404
        return html_path.read_text(encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        logger.error("Error leyendo dashboard estatico: %s", e)
        return jsonify({"error": "dashboard_read_failed"}), 500


@app.route("/dash/ar-rules/live")
def ar_rules_live_dashboard():
    """Genera una vista ligera en vivo listando badges presentes y links a JSON/CSV.

    No depende del HTML pre-generado y refleja el estado actual del directorio.
    """
    try:
        if not BADGES_DIR.exists():
            return jsonify({"error": "badges_dir_not_found"}), 404
        badge_names = [
            "ar_rules_coverage.svg",
            "ar_rules_coverage_only.svg",
            "ar_rules_trend.svg",
            "ar_rules_trend_wma.svg",
            "ar_rules_volatility.svg",
            "ar_rules_thresholds.svg",
            "ar_rules_sparkline.svg",
            "ar_rules_streak.svg",
        ]
        existing_badges = [b for b in badge_names if (BADGES_DIR / b).exists()]
        data_files = [
            "ar_rules_stats.json",
            "prev_ar_rules_stats.json",
            "ar_rules_weekly.json",
            "ar_rules_volatility.json",
            "ar_rules_history.csv",
            "drop_meta.json",
            "cov_drop_meta.json",
        ]
        existing_data = [f for f in data_files if (BADGES_DIR / f).exists()]
        def img_tag(name: str) -> str:
            return f"<div class='badge'><img src='/dash/ar-rules/badges/{name}' alt='{name}' loading='lazy'/><div class='cap'>{name}</div></div>"
        badges_html = "".join(img_tag(n) for n in existing_badges) or "<p>(No hay badges aún)</p>"
        links_html = "".join(
            f"<li><a href='/dash/ar-rules/badges/{n}' target='_blank' rel='noopener'>{n}</a></li>" for n in existing_data
        ) or "<li>(Sin archivos de datos)</li>"
        html = f"""
<!DOCTYPE html>
<html lang='es'>
  <head>
    <meta charset='utf-8'/>
    <title>AR Rules Progress</title>
    <style>
      body {{ font-family: system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; margin: 18px; background:#fafafa; }}
      h1 {{ margin-top:0; }}
      .grid {{ display:flex; flex-wrap:wrap; gap:12px; }}
      .badge {{ border:1px solid #ddd; background:#fff; padding:6px 8px; border-radius:6px; box-shadow:0 1px 2px rgba(0,0,0,0.08); text-align:center; }}
      .badge img {{ display:block; max-width:100%; height:auto; }}
      .cap {{ font-size:11px; margin-top:4px; color:#555; word-break:break-all; }}
      ul {{ line-height:1.5; }}
      footer {{ margin-top:32px; font-size:12px; color:#777; }}
      .note {{ background:#eef6ff; padding:8px 12px; border:1px solid #b5d6ff; border-radius:4px; margin-bottom:16px; }}
    </style>
  </head>
  <body>
    <h1>AR Rules - Progreso & Métricas</h1>
    <div class='note'>Vista dinámica generada al vuelo. Para la versión estática del workflow usa <code>/dash/ar-rules</code>.</div>
    <h2>Badges</h2>
    <div class='grid'>{badges_html}</div>
    <h2>Archivos de Datos</h2>
    <ul>{links_html}</ul>
    <footer>Actualizado en tiempo real al recargar. Directorio: {BADGES_DIR}</footer>
  </body>
</html>
        """
        return Response(html, mimetype="text/html")
    except Exception as e:  # noqa: BLE001
        logger.error("Error generando dashboard live: %s", e)
        return jsonify({"error": "live_dashboard_failed"}), 500


if __name__ == "__main__":
    # Run development server only when executed directly (Docker CMD)
    # Ensures the container stays up and listens on the official port.
    app.run(host="0.0.0.0", port=PORT, debug=False)
