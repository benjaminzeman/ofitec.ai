#!/usr/bin/env python3
"""
Importa presupuestos de proyectos desde XLSX/CSV usando plantillas de ideas/ofitec_import_templates.json

Características
- Carga flexible de XLSX/CSV (utiliza io_utils.load_rows)
- Normaliza encabezados y realiza matching difuso simple (difflib)
- Usa las plantillas JSON para pre-mapear columnas; si hay ambigüedad y no se
  pasa --assume-yes, solicita confirmación interactiva
- Inserta datos en tablas SQLite (proyectos, presupuestos, capitulos, partidas)

Uso típico:
  python tools/import_ofitec_budget.py \
    --xlsx data/raw/presupuestos/Proyecto_X.xlsx \
    --project "Proyecto X" \
    [--sheet Presupuesto] [--assume-yes]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from difflib import SequenceMatcher
import sys

if __package__ in (None, ""):
    here = Path(__file__).resolve().parent
    sys.path.append(str(here))

from common_db import default_db_path
from io_utils import load_rows
from etl_common import norm_text, norm_colname, parse_number


def ensure_schema(conn: sqlite3.Connection) -> None:
    # Dependemos de apply_ofitec_schema_sqlite.py
    pass


def ensure_project(conn: sqlite3.Connection, name: str) -> int:
    cur = conn.execute("SELECT id FROM proyectos WHERE LOWER(nombre)=LOWER(?)", (name,))
    row = cur.fetchone()
    if row:
        return int(row[0])
    conn.execute("INSERT INTO proyectos(nombre) VALUES (?)", (name,))
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def create_presupuesto(conn: sqlite3.Connection, proyecto_id: int) -> int:
    conn.execute("INSERT INTO presupuestos(proyecto_id, estado) VALUES (?, 'vigente')", (proyecto_id,))
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def load_templates(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def best_match(header: str, candidates: list[str]) -> tuple[str | None, float]:
    h = norm_colname(header)
    best, score = None, 0.0
    for c in candidates:
        s = SequenceMatcher(None, h, norm_colname(c)).ratio()
        if s > score:
            best, score = c, s
    return best, score


def resolve_mapping(headers: list[str], template_map: dict[str, str], suggestions: dict[str, list[dict]], assume_yes: bool) -> dict[str, str]:
    mapping: dict[str, str] = {}
    # Pre-map exacts
    for target, src in (template_map or {}).items():
        # Confirm presence or best match
        if src in headers:
            mapping[target] = src
        else:
            best, score = best_match(src, headers)
            if best and score >= 0.6:
                mapping[target] = best
    # Fill missing using suggestions candidates
    for target in ["codigo_partida", "descripcion", "unidad", "cantidad", "precio_unitario", "total"]:
        if target in mapping:
            continue
        cand_headers = [x.get("excel_col_name", "") for x in (suggestions or {}).get(target, [])]
        # Expand with all headers as fallback
        if not cand_headers:
            cand_headers = headers
        best, score = best_match(target, cand_headers)
        if best and score >= 0.5:
            # best is a candidate header name; map to the actual header present (if needed)
            if best in headers:
                mapping[target] = best
            else:
                act, s2 = best_match(best, headers)
                if act and s2 >= 0.5:
                    mapping[target] = act
    # Interactive confirm if still missing
    missing = [t for t in ["codigo_partida","descripcion","unidad","cantidad","precio_unitario","total"] if t not in mapping]
    if missing and not assume_yes:
        print("Campos sin mapear:", missing)
        print("Encabezados disponibles:", headers)
        for t in missing:
            sel = input(f"Seleccione encabezado para '{t}' (o deje vacío para omitir): ")
            if sel and sel in headers:
                mapping[t] = sel
    return mapping


def insert_partidas(conn: sqlite3.Connection, presupuesto_id: int, rows: list[dict], mapping: dict[str, str]) -> int:
    n = 0
    for r in rows:
        cp = norm_text(r.get(mapping.get("codigo_partida", "")))
        desc = norm_text(r.get(mapping.get("descripcion", "")))
        unidad = norm_text(r.get(mapping.get("unidad", "")))
        cant = parse_number(r.get(mapping.get("cantidad", "")))
        pu = parse_number(r.get(mapping.get("precio_unitario", "")))
        total = r.get(mapping.get("total", ""))
        total_val = parse_number(total) if total not in (None, "") else round(cant * pu, 2)
        conn.execute(
            "INSERT INTO partidas(capitulo_id, codigo_partida, descripcion, unidad, cantidad, precio_unitario, total) VALUES (NULL,?,?,?,?,?,?)",
            (cp or None, cp, desc, unidad, cant, pu, total_val),
        )
        n += 1
    conn.commit()
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--project", required=True, help="Nombre del proyecto para asociar el presupuesto")
    ap.add_argument("--sheet", default=None, help="Nombre de hoja (opcional). Si no, usa la plantilla 'Presupuesto'")
    ap.add_argument("--assume-yes", action="store_true")
    ap.add_argument("--templates", default=str(Path(__file__).resolve().parents[1] / "ideas" / "ofitec_import_templates.json"))
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    args = ap.parse_args()

    # Load data
    rows = load_rows(args.xlsx, sheet=args.sheet)
    if not rows:
        print("Sin filas para importar.")
        return 1
    headers = list(rows[0].keys())

    # Load template
    templates = load_templates(Path(args.templates))
    tpl = None
    for t in templates.get("templates", []):
        if (args.sheet and t.get("excel_sheet") == args.sheet) or (not args.sheet and t.get("excel_sheet") == "Presupuesto"):
            tpl = t
            break
    if not tpl:
        print("No se encontró plantilla adecuada.")
        return 2

    mapping = resolve_mapping(headers, tpl.get("column_map", {}), tpl.get("suggestions", {}), args.assume_yes)
    print("Mapping aplicado:", mapping)

    conn = sqlite3.connect(args.db)
    try:
        proyecto_id = ensure_project(conn, args.project)
        presupuesto_id = create_presupuesto(conn, proyecto_id)
        inserted = insert_partidas(conn, presupuesto_id, rows, mapping)
        print(f"Importadas {inserted} partidas al presupuesto {presupuesto_id} del proyecto '{args.project}'")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

