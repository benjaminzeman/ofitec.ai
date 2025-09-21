#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import os
from pathlib import Path
import sys

if __package__ in (None, ""):
    here = Path(__file__).resolve().parent
    sys.path.append(str(here))

from common_db import default_db_path


def main() -> int:
    db = os.environ.get("DB_PATH", default_db_path(prefer_root=False))
    conn = sqlite3.connect(db)
    try:
        stmts = [
            # purchase_orders_unified
            "CREATE INDEX IF NOT EXISTS ix_pou_vendor ON purchase_orders_unified(vendor_rut)",
            "CREATE INDEX IF NOT EXISTS ix_pou_project_name ON purchase_orders_unified(zoho_project_name)",
            "CREATE INDEX IF NOT EXISTS ix_pou_project_id ON purchase_orders_unified(zoho_project_id)",
            "CREATE INDEX IF NOT EXISTS ix_pou_po_date ON purchase_orders_unified(po_date)",
            "CREATE INDEX IF NOT EXISTS ix_pou_total_amount ON purchase_orders_unified(total_amount)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_pou_anti_dupe ON purchase_orders_unified(vendor_rut, po_number, po_date, total_amount)",
            # purchase_lines_unified
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_plu_po_lineid ON purchase_lines_unified(po_id, zoho_line_id)",
            # vendors
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_vendors_rut ON vendors_unified(rut_clean)",
            # bank
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_bank_external ON bank_movements(external_id)",
            "CREATE INDEX IF NOT EXISTS ix_bank_fecha ON bank_movements(fecha)",
        ]
        cur = conn.cursor()
        for s in stmts:
            try:
                cur.execute(s)
            except sqlite3.Error:
                # Skip if table not present yet
                pass
        conn.commit()
        print("Indexes ensured on:", db)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

