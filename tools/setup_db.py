#!/usr/bin/env python3
"""
Orquestador de setup de la BD canónica del ofitec.ai.

Acciones:
- Aplica schema SQL (tablas base + vistas básicas en schema.sql)
- Crea/actualiza vistas canónicas de Finanzas
- Verifica presencia de tablas y vistas requeridas
- (Opcional) Ejecuta quality_report para diagnóstico de datos

Uso:
  python tools/setup_db.py [--db ofitec.ai/data/chipax_data.db] [--with-quality-report]

Opcional: puedes definir DB_PATH para cambiar el destino.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    _here = Path(__file__).resolve().parent
    sys.path.append(str(_here))
from common_db import default_db_path


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=default_db_path(prefer_root=False))
    ap.add_argument("--with-quality-report", action="store_true", help="Run quality_report after setup")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    py = sys.executable or "python"
    db = os.path.abspath(args.db)

    # 1) apply schema
    rc = run([py, str(here / "apply_schema.py"), "--db", db, "--schema", str(here / "schema.sql")])
    if rc != 0:
        return rc

    # 2) create finance views
    rc = run([py, str(here / "create_finance_views.py"), "--db", db])
    if rc != 0:
        return rc

    # 3) verify
    rc = run([py, str(here / "verify_schema.py"), "--db", db])
    if rc != 0:
        return rc

    # 4) optional quality report
    if args.with_quality_report:
        rc = run([py, str(here / "quality_report.py"), "--db", db])
        if rc != 0:
            return rc

    print("Setup OK for:", db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
