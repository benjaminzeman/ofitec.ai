#!/usr/bin/env python
"""CLI para volcar datos RCV (ventas / compras) de un periodo.

Uso:
  python tools/rcv_dump.py --year 2025 --month 8 --tipo ventas
  python tools/rcv_dump.py -y 2025 -m 8 -t compras --limit 5 --json

Requiere variables de entorno:
  SII_RUT (formato ########-#)
  SII_AMBIENTE (cert|prod|...) opcional (default cert)

Flags:
  --tipo ventas|compras (default ventas)
  --json imprime JSON crudo normalizado
  --limit N limita número de filas mostradas (solo en tabla)
  --raw imprime payload bruto antes de normalización (debug)
  --fake fuerza SII_FAKE_MODE=1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Dict, Any

# Permite ejecutar fuera del paquete si se llama directamente
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from backend.sii_service import SiiClient  # type: ignore  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dump RCV period data")
    p.add_argument('-y', '--year', type=int, required=True)
    p.add_argument('-m', '--month', type=int, required=True)
    p.add_argument('-t', '--tipo', choices=['ventas', 'compras'], default='ventas')
    p.add_argument('--json', action='store_true', help='Imprime JSON normalizado')
    p.add_argument('--limit', type=int, default=0, help='Limita filas en modo tabla')
    p.add_argument('--raw', action='store_true', help='Muestra payload crudo (debug)')
    p.add_argument('--fake', action='store_true', help='Fuerza SII_FAKE_MODE=1')
    return p.parse_args()


def _format_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "(sin filas)"
    # Seleccionar columnas relevantes
    cols = ["periodo", "rut_emisor", "rut_receptor", "tipo_dte", "folio", "fecha_emision", "neto", "iva", "total", "estado_sii"]
    # Calcular anchos
    widths = {}
    for c in cols:
        widths[c] = max(len(c), max((len(str(r.get(c, ''))) for r in rows), default=0))
    header = ' | '.join(c.ljust(widths[c]) for c in cols)
    sep = '-+-'.join('-' * widths[c] for c in cols)
    lines = [header, sep]
    for r in rows:
        line = ' | '.join(str(r.get(c, '')).ljust(widths[c]) for c in cols)
        lines.append(line)
    return '\n'.join(lines)


def main() -> int:
    args = _parse_args()
    if args.fake:
        os.environ['SII_FAKE_MODE'] = '1'
    client = SiiClient()
    if args.raw:
        # Llamamos internamente al método privado solo para debug puntual
        periodo = f"{args.year:04d}-{args.month:02d}"
        raw = client._request_rcv(args.tipo, periodo)  # type: ignore
        print("# RAW:")
        try:
            print(json.dumps(raw, indent=2, ensure_ascii=False))
        except Exception:
            print(raw)
        print("\n# NORMALIZADO:")
    if args.tipo == 'ventas':
        rows = client.fetch_rcv_sales(args.year, args.month)
    else:
        rows = client.fetch_rcv_purchases(args.year, args.month)
    if args.limit > 0:
        rows = rows[: args.limit]
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        print(_format_table(rows))
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
