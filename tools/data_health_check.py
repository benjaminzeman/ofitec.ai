#!/usr/bin/env python3
"""
Health Check integral para la base SQLite principal.

Objetivos:
 1. Confirmar existencia de tablas y vistas núcleo.
 2. Métricas rápidas: filas, tamaño aproximado en disco, fecha mínima/máxima.
 3. Detección de índices faltantes (heurístico) en columnas que parecen
     ser claves de búsqueda.
 4. Heurística de fragmentación: páginas freelist vs páginas totales.
 5. Recomendaciones: ejecutar VACUUM / ANALYZE según umbrales.
 6. Validación de integridad: PRAGMA integrity_check.

Uso:
  python tools/data_health_check.py --db data/chipax_data.db --json

Salida:
  - Por defecto: reporte humano.
  - Con --json: objeto JSON serializado.

Limitaciones:
  - No modifica la BD.
  - No fuerza ANALYZE (solo recomienda).

"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
from pathlib import Path
import sys
if __package__ in (None, ''):
    sys.path.append(str(Path(__file__).resolve().parent))
from common_db import default_db_path

CORE_TABLES = [
    'projects', 'vendors_unified', 'customers', 'purchase_orders_unified',
    'purchase_lines_unified', 'ap_invoices', 'bank_movements', 'expenses',
    'sales_invoices'
]
CORE_VIEWS = [
    'v_facturas_compra', 'v_facturas_venta', 'v_cartola_bancaria',
]
# Columnas candidatas a index si no existe índice (heurístico simple)
CANDIDATE_INDEX_COLUMNS = {
    'purchase_orders_unified': ['po_date', 'vendor_rut', 'zoho_project_id'],
    'purchase_lines_unified': ['po_id'],
    'ap_invoices': ['invoice_date', 'vendor_rut'],
    'bank_movements': ['fecha', 'external_id'],
    'expenses': ['fecha', 'proveedor_rut'],
    'sales_invoices': ['invoice_date', 'customer_rut'],
}


def collect_schema(conn: sqlite3.Connection):
    cur = conn.execute(
        "SELECT name, type FROM sqlite_master "
        "WHERE type IN ('table','view','index')"
    )
    rows = cur.fetchall()
    tables = {n for (n, t) in rows if t == 'table'}
    views = {n for (n, t) in rows if t == 'view'}
    indexes = {n for (n, t) in rows if t == 'index'}
    return tables, views, indexes


def table_row_count(conn, table: str) -> int:
    try:
        cur = conn.execute(f"SELECT COUNT(1) FROM {table}")
        return cur.fetchone()[0] or 0
    except sqlite3.Error:
        return -1


def table_min_max_dates(
    conn, table: str, date_cols=(
        'fecha', 'invoice_date', 'po_date'
    )
):
    # Devuelve primer col fecha encontrada con min/max
    for col in date_cols:
        try:
            cur = conn.execute(f"SELECT MIN({col}), MAX({col}) FROM {table}")
            r = cur.fetchone()
            if r and (r[0] or r[1]):
                return col, r[0], r[1]
        except sqlite3.Error:
            continue
    return None, None, None


def existing_index_ddl(conn) -> dict:
    ddls = {}
    cur = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index'"
    )
    for name, sql in cur.fetchall():
        ddls[name] = sql or ''
    return ddls


def index_exists_for(conn, table: str, column: str) -> bool:
    cur = conn.execute("PRAGMA index_list(%s)" % table)
    idx_rows = cur.fetchall()
    for row in idx_rows:
        idx_name = row[1]
        cur2 = conn.execute("PRAGMA index_info(%s)" % idx_name)
        cols = [r[2] for r in cur2.fetchall()]
        if cols == [column] or column in cols:
            return True
    return False


def freelist_ratio(conn) -> tuple[int, int, float]:
    page_count = conn.execute("PRAGMA page_count").fetchone()[0]
    freelist_count = conn.execute("PRAGMA freelist_count").fetchone()[0]
    ratio = (freelist_count / page_count) if page_count else 0.0
    return page_count, freelist_count, ratio


def integrity_check(conn) -> str:
    try:
        res = conn.execute("PRAGMA integrity_check").fetchone()[0]
        return res
    except sqlite3.Error as e:
        return f"ERROR: {e}"


def analyze_last_run(conn) -> int | None:
    try:
        cur = conn.execute("SELECT MAX(timestamp) FROM sqlite_stat1")
        r = cur.fetchone()[0]
        return r
    except sqlite3.Error:
        return None


def suggest_actions(data) -> list[str]:
    suggestions = []
    # Fragmentación
    if data['freelist']['ratio'] > 0.2 and data['row_counts_total'] > 5000:
        suggestions.append(
            'Ejecutar VACUUM (alto porcentaje de páginas libres)'
        )
    # ANALYZE
    if data['analyze_last_run'] is None:
        suggestions.append('Ejecutar ANALYZE (no hay estadísticas)')
    # Índices
    for rec in data['tables']:
        for miss in rec.get('missing_indexes', []):
            suggestions.append(f"Crear índice sugerido: {miss}")
    if not suggestions:
        suggestions.append('Sin acciones críticas. OK')
    return suggestions


def build_report(db_path: str):
    size_bytes = Path(db_path).stat().st_size if os.path.exists(db_path) else 0
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables, views, _ = collect_schema(conn)

        table_reports = []
        total_rows = 0
        for t in sorted(t for t in tables if not t.startswith('sqlite_')):
            rc = table_row_count(conn, t)
            total_rows += rc if rc > 0 else 0
            date_col, dmin, dmax = table_min_max_dates(conn, t)
            missing = []
            if t in CANDIDATE_INDEX_COLUMNS:
                for col in CANDIDATE_INDEX_COLUMNS[t]:
                    if not index_exists_for(conn, t, col):
                        missing.append(f"{t}({col})")
            table_reports.append({
                'table': t,
                'rows': rc,
                'date_col': date_col,
                'date_min': dmin,
                'date_max': dmax,
                'missing_indexes': missing,
            })

        page_count, freelist_count, ratio = freelist_ratio(conn)
        integrity = integrity_check(conn)
        analyze_ts = analyze_last_run(conn)

        report = {
            'db_path': db_path,
            'db_size_bytes': size_bytes,
            'row_counts_total': total_rows,
            'tables': table_reports,
            'views_present': sorted(list(views)),
            'core_tables_missing': [t for t in CORE_TABLES if t not in tables],
            'core_views_missing': [v for v in CORE_VIEWS if v not in views],
            'freelist': {
                'page_count': page_count,
                'freelist_count': freelist_count,
                'ratio': round(ratio, 4),
            },
            'integrity_check': integrity,
            'analyze_last_run': analyze_ts,
        }
        report['suggestions'] = suggest_actions(report)
        return report
    finally:
        conn.close()


def render_human(report):
    out = []
    out.append(
        f"DB: {report['db_path']} ({report['db_size_bytes']/1024:.1f} KiB)"
    )
    out.append(f"Total filas estimadas: {report['row_counts_total']}")
    out.append("")
    if report['core_tables_missing'] or report['core_views_missing']:
        out.append("[FALTANTES]")
        for t in report['core_tables_missing']:
            out.append(f" - Tabla faltante: {t}")
        for v in report['core_views_missing']:
            out.append(f" - Vista faltante: {v}")
        out.append("")
    out.append("[TABLAS]")
    for tr in report['tables']:
        line = f" - {tr['table']}: {tr['rows']} filas"
        if tr['date_col']:
            line += (
                f" | {tr['date_col']} [{tr['date_min']} .. {tr['date_max']}]"
            )
        if tr['missing_indexes']:
            line += f" | idx sugeridos: {', '.join(tr['missing_indexes'])}"
        out.append(line)
    out.append("")
    fr = report['freelist']
    out.append(
        f"[FRAGMENTACION] pages={fr['page_count']} "
        f"freelist={fr['freelist_count']} ratio={fr['ratio']}"
    )
    out.append(f"[INTEGRIDAD] {report['integrity_check']}")
    out.append(f"[ANALYZE] timestamp={report['analyze_last_run']}")
    out.append("")
    out.append("[SUGERENCIAS]")
    for s in report['suggestions']:
        out.append(f" - {s}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description='Health check DB SQLite')
    ap.add_argument('--db', default=default_db_path())
    ap.add_argument('--json', action='store_true', help='Salida JSON')
    args = ap.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print('DB not found:', db_path)
        return 2

    report = build_report(db_path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_human(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
