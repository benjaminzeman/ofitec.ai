
#!/usr/bin/env python3
"""Import Chipax CSV data into the canonical SQLite database."""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_RAW_DIR = DATA_DIR / "raw" / "chipax"
DEFAULT_DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "chipax_data.db"))
SOURCE_PLATFORM = "CHIPAX"

if __package__ in (None, ""):
    sys.path.append(str(TOOLS_DIR))

from etl_common import parse_number


@dataclass(frozen=True)
class ImportConfig:
    db_path: str
    raw_dir: Path


@dataclass
class Metrics:
    ap_inserted: int = 0
    ap_updated: int = 0
    ar_inserted: int = 0
    ar_updated: int = 0
    expenses_inserted: int = 0
    expenses_updated: int = 0
    bank_inserted: int = 0
    bank_updated: int = 0
    reconciliations: int = 0
    links: int = 0

    def as_dict(self) -> Dict[str, int]:
        data = self.__dict__.copy()
        data["ap_upserts"] = self.ap_inserted + self.ap_updated
        data["ar_upserts"] = self.ar_inserted + self.ar_updated
        data["expenses_upserts"] = self.expenses_inserted + self.expenses_updated
        data["bank_upserts"] = self.bank_inserted + self.bank_updated
        return data


# Connection helpers -----------------------------------------------------


def _connect(cfg: ImportConfig) -> sqlite3.Connection:
    con = sqlite3.connect(cfg.db_path)
    con.row_factory = sqlite3.Row
    return con


def _iter_csv(cfg: ImportConfig, pattern: str) -> Iterable[Path]:
    if not cfg.raw_dir.exists():
        return []
    return sorted(cfg.raw_dir.glob(pattern))


def _parse_amount(value: object) -> float:
    return round(parse_number(value), 2)


def _strip(value: Optional[str]) -> str:
    return value.strip() if value else ""


def _safe_currency(value: Optional[str]) -> str:
    val = _strip(value).upper()
    return val or "CLP"




def _ensure_unique_index(conn: sqlite3.Connection, name: str, table: str, columns: tuple[str, ...]) -> None:
    group_cols = ", ".join(f'"{col}"' for col in columns)
    duplicates = conn.execute(
        f'SELECT MIN(id) as keep_id, GROUP_CONCAT(id) as ids FROM "{table}"'
        f' GROUP BY {group_cols} HAVING COUNT(*) > 1'
    ).fetchall()
    for keep_id, ids in duplicates:
        if not ids:
            continue
        id_list = [int(val) for val in ids.split(',') if val]
        to_delete = [row_id for row_id in id_list if row_id != keep_id]
        if to_delete:
            placeholders = ','.join('?' for _ in to_delete)
            conn.execute(f'DELETE FROM "{table}" WHERE id IN ({placeholders})', to_delete)
    info = conn.execute(f"PRAGMA index_info('{name}')").fetchall()
    existing = tuple(row[2] for row in info)
    desired = tuple(columns)
    if existing and existing != desired:
        conn.execute(f'DROP INDEX IF EXISTS "{name}"')
    quoted_cols = ", ".join(f'"{col}"' for col in columns)
    conn.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS "{name}" ON "{table}" ({quoted_cols})')


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}')








def import_ap(cfg: ImportConfig, metrics: Metrics) -> None:
    with _connect(cfg) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS ap_invoices (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              vendor_rut TEXT,
              vendor_name TEXT,
              invoice_number TEXT,
              invoice_date TEXT,
              due_date TEXT,
              currency TEXT DEFAULT 'CLP',
              net_amount REAL,
              tax_amount REAL,
              exempt_amount REAL,
              total_amount REAL,
              source_platform TEXT,
              source_id TEXT,
              project_name TEXT,
              status TEXT,
              created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        _ensure_columns(con, 'ap_invoices', {
            'due_date': 'TEXT',
            'currency': "TEXT DEFAULT 'CLP'",
            'net_amount': 'REAL',
            'tax_amount': 'REAL',
            'exempt_amount': 'REAL',
            'total_amount': 'REAL',
            'source_platform': 'TEXT',
            'source_id': 'TEXT',
            'project_name': 'TEXT',
            'status': 'TEXT',
        })
        _ensure_unique_index(con, 'ux_ap_unique', 'ap_invoices', ('vendor_rut', 'invoice_number', 'invoice_date', 'source_platform'))

    files = _iter_csv(cfg, "*_Facturas compra_conciliacion.csv")
    if not files:
        return

    with _connect(cfg) as con:
        cur = con.cursor()
        for path in files:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    vendor_rut = _strip(row.get("RUT") or row.get("Rut"))
                    invoice_number = _strip(row.get("Folio") or row.get("Serie"))
                    invoice_date = _strip(
                        row.get("Fecha Emision")
                        or row.get("Fecha Emisión")
                        or row.get("Fecha Emisión (DTE)")
                    )
                    if not invoice_number or not invoice_date:
                        continue

                    vendor_name = _strip(
                        row.get("Razon Social")
                        or row.get("Razón Social")
                        or row.get("Proveedor")
                    )
                    due_date = _strip(row.get("Fecha Vencimiento") or row.get("Vencimiento"))
                    currency = _safe_currency(row.get("Moneda"))
                    net_amount = _parse_amount(row.get("Monto Neto (CLP)") or row.get("Monto Neto"))
                    tax_amount = _parse_amount(row.get("Monto IVA (CLP)") or row.get("IVA"))
                    exempt_amount = _parse_amount(row.get("Monto Exento (CLP)") or row.get("Exento"))
                    total_amount = _parse_amount(row.get("Monto Total (CLP)") or row.get("Monto Total"))
                    project_name = _strip(row.get("Proyecto")) or None
                    status = _strip(row.get("Estado") or row.get("Status") or "open").lower() or "open"
                    source_id = _strip(row.get("ID") or row.get("Id Documento")) or None

                    exists = cur.execute(
                        """
                        SELECT id FROM ap_invoices
                         WHERE vendor_rut=? AND invoice_number=? AND invoice_date=? AND source_platform=?
                        """,
                        (vendor_rut, invoice_number, invoice_date, SOURCE_PLATFORM),
                    ).fetchone()

                    cur.execute(
                        """
                        INSERT INTO ap_invoices (
                            vendor_rut, vendor_name, invoice_number, invoice_date,
                            due_date, currency, net_amount, tax_amount, exempt_amount,
                            total_amount, source_platform, source_id, project_name, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(vendor_rut, invoice_number, invoice_date, source_platform)
                        DO UPDATE SET
                            vendor_name=excluded.vendor_name,
                            due_date=excluded.due_date,
                            currency=excluded.currency,
                            net_amount=excluded.net_amount,
                            tax_amount=excluded.tax_amount,
                            exempt_amount=excluded.exempt_amount,
                            total_amount=excluded.total_amount,
                            source_id=COALESCE(excluded.source_id, ap_invoices.source_id),
                            project_name=COALESCE(excluded.project_name, ap_invoices.project_name),
                            status=excluded.status
                        """,
                        (
                            vendor_rut,
                            vendor_name,
                            invoice_number,
                            invoice_date,
                            due_date,
                            currency,
                            net_amount,
                            tax_amount,
                            exempt_amount,
                            total_amount,
                            SOURCE_PLATFORM,
                            source_id,
                            project_name,
                            status,
                        ),
                    )
                    if exists:
                        metrics.ap_updated += 1
                    else:
                        metrics.ap_inserted += 1
        con.commit()


def import_ar(cfg: ImportConfig, metrics: Metrics) -> None:
    with _connect(cfg) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS sales_invoices (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              customer_rut TEXT,
              customer_name TEXT,
              invoice_number TEXT,
              invoice_date TEXT,
              due_date TEXT,
              currency TEXT,
              net_amount REAL,
              tax_amount REAL,
              exempt_amount REAL,
              total_amount REAL,
              status TEXT,
              project_id INTEGER,
              source_platform TEXT,
              source_id TEXT,
              created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        _ensure_columns(con, 'sales_invoices', {
            'due_date': 'TEXT',
            'currency': 'TEXT',
            'net_amount': 'REAL',
            'tax_amount': 'REAL',
            'exempt_amount': 'REAL',
            'total_amount': 'REAL',
            'status': 'TEXT',
            'project_id': 'INTEGER',
            'source_platform': 'TEXT',
            'source_id': 'TEXT',
        })
        _ensure_unique_index(con, 'ux_sales_unique', 'sales_invoices', ('customer_rut', 'invoice_number', 'invoice_date', 'source_platform'))

    files = _iter_csv(cfg, "*_Facturas venta_conciliacion.csv")
    if not files:
        return

    with _connect(cfg) as con:
        cur = con.cursor()
        for path in files:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    rut = _strip(row.get("RUT") or row.get("Rut"))
                    invoice_number = _strip(row.get("Folio") or row.get("Serie"))
                    invoice_date = _strip(
                        row.get("Fecha Emision")
                        or row.get("Fecha Emisión")
                        or row.get("Fecha Emisión (DTE)")
                    )
                    if not invoice_number or not invoice_date:
                        continue

                    customer_name = _strip(
                        row.get("Razon Social")
                        or row.get("Razón Social")
                        or row.get("Cliente")
                    )
                    due_date = _strip(row.get("Fecha Vencimiento") or row.get("Vencimiento"))
                    currency = _safe_currency(row.get("Moneda"))
                    net_amount = _parse_amount(row.get("Monto Neto (CLP)") or row.get("Monto Neto"))
                    tax_amount = _parse_amount(row.get("Monto IVA (CLP)") or row.get("IVA"))
                    exempt_amount = _parse_amount(row.get("Monto Exento (CLP)") or row.get("Exento"))
                    total_amount = _parse_amount(row.get("Monto Total (CLP)") or row.get("Monto Total"))
                    status = _strip(row.get("Estado") or row.get("Status") or "open").lower() or "open"
                    source_id = _strip(row.get("ID") or row.get("Id Documento")) or None

                    exists = cur.execute(
                        """
                        SELECT id FROM sales_invoices
                         WHERE customer_rut=? AND invoice_number=? AND invoice_date=? AND source_platform=?
                        """,
                        (rut, invoice_number, invoice_date, SOURCE_PLATFORM),
                    ).fetchone()

                    cur.execute(
                        """
                        INSERT INTO sales_invoices (
                            customer_rut, customer_name, invoice_number, invoice_date,
                            due_date, currency, net_amount, tax_amount, exempt_amount,
                            total_amount, status, project_id, source_platform, source_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(customer_rut, invoice_number, invoice_date, source_platform)
                        DO UPDATE SET
                            customer_name=excluded.customer_name,
                            due_date=excluded.due_date,
                            currency=excluded.currency,
                            net_amount=excluded.net_amount,
                            tax_amount=excluded.tax_amount,
                            exempt_amount=excluded.exempt_amount,
                            total_amount=excluded.total_amount,
                            status=excluded.status,
                            source_id=COALESCE(excluded.source_id, sales_invoices.source_id)
                        """,
                        (
                            rut,
                            customer_name,
                            invoice_number,
                            invoice_date,
                            due_date,
                            currency,
                            net_amount,
                            tax_amount,
                            exempt_amount,
                            total_amount,
                            status,
                            None,
                            SOURCE_PLATFORM,
                            source_id,
                        ),
                    )
                    if exists:
                        metrics.ar_updated += 1
                    else:
                        metrics.ar_inserted += 1
        con.commit()


def _bank_external_id(fecha: str, cuenta: str, moneda: str, monto: float, glosa: str) -> str:
    raw = "|".join([
        fecha or "",
        cuenta or "",
        moneda or "",
        f"{monto:.2f}",
        glosa.lower().strip(),
    ])
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"{SOURCE_PLATFORM.lower()}:{digest}"


def import_bank(cfg: ImportConfig, metrics: Metrics) -> None:
    with _connect(cfg) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS bank_movements (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              fecha TEXT,
              bank_name TEXT,
              account_number TEXT,
              glosa TEXT,
              monto REAL,
              moneda TEXT,
              tipo TEXT,
              saldo REAL,
              referencia TEXT,
              fuente TEXT,
              external_id TEXT
            );
            """
        )
        _ensure_columns(con, 'bank_movements', {
            'fuente': 'TEXT',
            'external_id': 'TEXT'
        })
        _ensure_unique_index(con, 'ux_bank_external', 'bank_movements', ('external_id',))

    files = _iter_csv(cfg, "*banco de chile*conciliacion.csv")
    if not files:
        # Fallback to generic cartola pattern
        files = _iter_csv(cfg, "*Cartola*.csv")
    if not files:
        return

    with _connect(cfg) as con:
        cur = con.cursor()
        for path in files:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    fecha = _strip(row.get("Fecha") or row.get("fecha"))
                    glosa = _strip(
                        row.get("Glosa")
                        or row.get("Descripcion")
                        or row.get("Descripción")
                    )
                    # Handle Chipax format: Cargo (debit) and Abono (credit)
                    cargo = _parse_amount(row.get("Cargo") or 0)
                    abono = _parse_amount(row.get("Abono") or 0)
                    monto = abono - cargo  # Net amount (positive for credit, negative for debit)
                    if monto == 0:
                        # Fallback to generic Monto column
                        monto = _parse_amount(row.get("Monto") or row.get("monto"))
                    moneda = _safe_currency(row.get("Moneda"))
                    banco = _strip(row.get("Banco") or row.get("bank"))
                    # Handle different account number column names
                    cuenta = _strip(row.get("Cuenta") or row.get("account") or row.get("Número Cuenta"))
                    referencia = _strip(row.get("Referencia") or row.get("referencia"))
                    saldo = _parse_amount(row.get("Saldo") or row.get("saldo"))
                    tipo = _strip(row.get("Tipo") or row.get("tipo") or ("credito" if monto >= 0 else "debito")).lower()
                    external_id = _strip(row.get("ID") or row.get("id") or row.get("External ID") or row.get("Id"))
                    if not external_id:
                        external_id = _bank_external_id(fecha, cuenta, moneda, monto, glosa)

                    exists = cur.execute(
                        "SELECT id FROM bank_movements WHERE external_id=?",
                        (external_id,),
                    ).fetchone()

                    cur.execute(
                        """
                        INSERT INTO bank_movements (
                            fecha, bank_name, account_number, glosa, monto,
                            moneda, tipo, saldo, referencia, fuente, external_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(external_id)
                        DO UPDATE SET
                            fecha=excluded.fecha,
                            bank_name=excluded.bank_name,
                            account_number=excluded.account_number,
                            glosa=excluded.glosa,
                            monto=excluded.monto,
                            moneda=excluded.moneda,
                            tipo=excluded.tipo,
                            saldo=excluded.saldo,
                            referencia=excluded.referencia,
                            fuente=excluded.fuente
                        """,
                        (
                            fecha,
                            banco,
                            cuenta,
                            glosa,
                            monto,
                            moneda,
                            tipo,
                            saldo,
                            referencia,
                            SOURCE_PLATFORM,
                            external_id,
                        ),
                    )
                    if exists:
                        metrics.bank_updated += 1
                    else:
                        metrics.bank_inserted += 1
        con.commit()


def import_expenses(cfg: ImportConfig, metrics: Metrics) -> None:
    with _connect(cfg) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS expenses (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              fecha TEXT,
              categoria TEXT,
              descripcion TEXT,
              monto REAL,
              moneda TEXT,
              proveedor_rut TEXT,
              proyecto TEXT,
              fuente TEXT,
              status TEXT,
              comprobante TEXT
            );
            """
        )
        _ensure_columns(con, 'expenses', {
            'fecha': 'TEXT',
            'categoria': 'TEXT',
            'descripcion': 'TEXT',
            'monto': 'REAL',
            'moneda': 'TEXT',
            'proveedor_rut': 'TEXT',
            'proyecto': 'TEXT',
            'fuente': 'TEXT',
            'status': 'TEXT',
            'comprobante': 'TEXT'
        })
        _ensure_unique_index(con, 'ux_expenses_chipax', 'expenses', ('fuente', 'comprobante', 'fecha', 'proveedor_rut', 'descripcion', 'monto'))

    files = _iter_csv(cfg, "*Gastos*.csv")
    if not files:
        return

    with _connect(cfg) as con:
        cur = con.cursor()
        for path in files:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    fecha = _strip(row.get("Fecha") or row.get("fecha"))
                    categoria = _strip(row.get("Categoria") or row.get("Categoría"))
                    descripcion = _strip(
                        row.get("Descripcion")
                        or row.get("Descripción")
                        or row.get("Glosa")
                        or row.get("Detalle")
                    )
                    monto = _parse_amount(
                        row.get("Monto")
                        or row.get("monto")
                        or row.get("Monto Conciliado")
                        or row.get("Monto Moneda Original")
                    )
                    moneda = _safe_currency(row.get("Moneda") or row.get("Moneda.1"))
                    proveedor_rut = _strip(
                        row.get("Proveedor_RUT")
                        or row.get("Rut Proveedor")
                        or row.get("RUT Proveedor")
                        or row.get("RUT")
                    )
                    proyecto = _strip(row.get("Proyecto")) or None
                    comprobante = _strip(
                        row.get("Comprobante")
                        or row.get("Documento")
                        or row.get("Numero Documento")
                        or row.get("Numero Comprobante")
                    )

                    exists = cur.execute(
                        """
                        SELECT id FROM expenses
                         WHERE fuente=? AND comprobante=? AND fecha=?
                           AND proveedor_rut=? AND descripcion=? AND monto=?
                        """,
                        (
                            SOURCE_PLATFORM,
                            comprobante,
                            fecha,
                            proveedor_rut,
                            descripcion,
                            monto,
                        ),
                    ).fetchone()

                    if exists:
                        cur.execute(
                            """
                            UPDATE expenses
                               SET categoria=?, descripcion=?, moneda=?, proveedor_rut=?,
                                   proyecto=?, status=?
                             WHERE id=?
                            """,
                            (
                                categoria,
                                descripcion,
                                moneda,
                                proveedor_rut,
                                proyecto,
                                "posted",
                                exists["id"],
                            ),
                        )
                        metrics.expenses_updated += 1
                    else:
                        cur.execute(
                            """
                            INSERT INTO expenses (
                                fecha, categoria, descripcion, monto, moneda,
                                proveedor_rut, proyecto, fuente, status, comprobante
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                fecha,
                                categoria,
                                descripcion,
                                monto,
                                moneda,
                                proveedor_rut,
                                proyecto,
                                SOURCE_PLATFORM,
                                "posted",
                                comprobante,
                            ),
                        )
                        metrics.expenses_inserted += 1
        con.commit()


# Public API -------------------------------------------------------------


def run(db_path: Optional[str] = None, raw_dir: Optional[str | Path] = None) -> Dict[str, int]:
    cfg = ImportConfig(
        db_path=str(db_path or DEFAULT_DB_PATH),
        raw_dir=Path(raw_dir or DEFAULT_RAW_DIR),
    )
    metrics = Metrics()
    import_ap(cfg, metrics)
    import_ar(cfg, metrics)
    import_expenses(cfg, metrics)
    import_bank(cfg, metrics)
    return metrics.as_dict()


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="Path to SQLite database")
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DIR),
        help="Directory containing Chipax CSV exports",
    )
    args = parser.parse_args(argv)

    metrics = run(db_path=args.db, raw_dir=args.raw_dir)
    print("Chipax import completed")
    for key in sorted(metrics):
        print(f"  {key}: {metrics[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
