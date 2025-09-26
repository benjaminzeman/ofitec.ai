"""
OFITEC.AI - Validation Engine
Motor de validaciones financieras críticas para control de riesgos.

Implementa las reglas de negocio:
- Factura ≤ OC (por línea y total)
- Pago ≤ Factura (saldo disponible)
- OC ≤ Presupuesto (disponible por proyecto)
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationFlag:
    """Flag de validación con severidad y detalles."""
    flag_type: str
    severity: str  # "error", "warning", "info"
    message: str
    details: Dict[str, Any]
    project_name: Optional[str] = None
    entity_id: Optional[str] = None


@dataclass
class ValidationResult:
    """Resultado de validación."""
    is_valid: bool
    flags: List[ValidationFlag]
    allowed_amount: Optional[float] = None
    attempted_amount: Optional[float] = None
    validated_at: Optional[datetime] = None

    def __post_init__(self):
        """Establecer timestamp automáticamente."""
        if self.validated_at is None:
            self.validated_at = datetime.now()


class FinancialValidator:
    """Motor de validaciones financieras."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Crear conexión a la BD."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def validate_invoice_vs_po(self, po_number: str, invoice_amount: float,
                               po_line_id: Optional[str] = None) -> ValidationResult:
        """
        Validar que Factura ≤ OC (total o por línea).

        Args:
            po_number: Número de orden de compra
            invoice_amount: Monto de la factura
            po_line_id: ID de línea específica (opcional)

        Returns:
            ValidationResult con validación y flags
        """
        flags = []

        try:
            with self._get_connection() as conn:
                if po_line_id:
                    # Validación por línea específica
                    cur = conn.execute("""
                        SELECT
                            pol.po_number,
                            pol.line_total,
                            COALESCE(SUM(apl.amount), 0) as already_invoiced,
                            pol.line_total - COALESCE(SUM(apl.amount), 0) as remaining
                        FROM purchase_order_lines pol
                        LEFT JOIN ap_po_links apl ON apl.po_line_id = pol.id
                        WHERE pol.po_number = ? AND pol.id = ?
                        GROUP BY pol.po_number, pol.id, pol.line_total
                    """, (po_number, po_line_id))
                else:
                    # Validación por OC total - usar zoho_ordenes_final
                    cur = conn.execute("""
                        SELECT
                            zo."Purchase Order Number" as po_number,
                            zo."Total" as total_amount,
                            COALESCE(SUM(apl.amount), 0) as already_invoiced,
                            zo."Total" - COALESCE(SUM(apl.amount), 0) as remaining
                        FROM zoho_ordenes_final zo
                        LEFT JOIN ap_po_links apl ON apl.po_id = zo."Purchase Order Number"
                        WHERE zo."Purchase Order Number" = ?
                        GROUP BY zo."Purchase Order Number", zo."Total"
                    """, (po_number,))

                row = cur.fetchone()
                if not row:
                    flags.append(ValidationFlag(
                        flag_type="po_not_found",
                        severity="error",
                        message=f"Orden de compra {po_number} no encontrada",
                        details={"po_number": po_number}
                    ))
                    return ValidationResult(False, flags)

                total_amount = row["total_amount"] if "total_amount" in row.keys() else row["line_total"]
                already_invoiced = row["already_invoiced"]
                remaining = row["remaining"]

                if invoice_amount > remaining:
                    flags.append(ValidationFlag(
                        flag_type="invoice_over_po",
                        severity="error",
                        message=f"Factura excede disponible en OC {po_number}",
                        details={
                            "po_number": po_number,
                            "po_line_id": po_line_id,
                            "total_po": total_amount,
                            "already_invoiced": already_invoiced,
                            "remaining": remaining,
                            "attempted": invoice_amount,
                            "excess": invoice_amount - remaining
                        }
                    ))
                    return ValidationResult(False, flags, remaining, invoice_amount)

                # Advertencia si se consume más del 90%
                if invoice_amount > (remaining * 0.9):
                    flags.append(ValidationFlag(
                        flag_type="po_nearly_consumed",
                        severity="warning",
                        message=f"OC {po_number} cerca del límite (>90%)",
                        details={
                            "po_number": po_number,
                            "remaining_after": remaining - invoice_amount,
                            "consumption_pct": ((already_invoiced + invoice_amount) / total_amount) * 100
                        }
                    ))

                return ValidationResult(True, flags, remaining, invoice_amount)

        except Exception as e:
            logger.error(f"Error validating invoice vs PO: {e}")
            flags.append(ValidationFlag(
                flag_type="validation_error",
                severity="error",
                message=f"Error en validación: {str(e)}",
                details={"exception": str(e)}
            ))
            return ValidationResult(False, flags)

    def validate_payment_vs_invoice(self, invoice_id: int, payment_amount: float) -> ValidationResult:
        """
        Validar que Pago ≤ Saldo de Factura disponible.

        Args:
            invoice_id: ID de la factura
            payment_amount: Monto del pago

        Returns:
            ValidationResult con validación y flags
        """
        flags = []

        try:
            with self._get_connection() as conn:
                cur = conn.execute("""
                    SELECT
                        ai.id,
                        ai.total_amount,
                        ai.invoice_number,
                        ai.supplier_name,
                        COALESCE(SUM(cb.monto), 0) as already_paid,
                        ai.total_amount - COALESCE(SUM(cb.monto), 0) as remaining
                    FROM ap_invoices ai
                    LEFT JOIN v_cartola_bancaria cb ON cb.invoice_id = ai.id
                    WHERE ai.id = ?
                    GROUP BY ai.id, ai.total_amount, ai.invoice_number, ai.supplier_name
                """, (invoice_id,))

                row = cur.fetchone()
                if not row:
                    flags.append(ValidationFlag(
                        flag_type="invoice_not_found",
                        severity="error",
                        message=f"Factura ID {invoice_id} no encontrada",
                        details={"invoice_id": invoice_id}
                    ))
                    return ValidationResult(False, flags)

                total_amount = row["total_amount"]
                already_paid = row["already_paid"]
                remaining = row["remaining"]

                if payment_amount > remaining:
                    flags.append(ValidationFlag(
                        flag_type="overpaid",
                        severity="error",
                        message=f"Pago excede saldo de factura {row['invoice_number']}",
                        details={
                            "invoice_id": invoice_id,
                            "invoice_number": row["invoice_number"],
                            "supplier": row["supplier_name"],
                            "total_invoice": total_amount,
                            "already_paid": already_paid,
                            "remaining": remaining,
                            "attempted": payment_amount,
                            "excess": payment_amount - remaining
                        }
                    ))
                    return ValidationResult(False, flags, remaining, payment_amount)

                return ValidationResult(True, flags, remaining, payment_amount)

        except Exception as e:
            logger.error(f"Error validating payment vs invoice: {e}")
            flags.append(ValidationFlag(
                flag_type="validation_error",
                severity="error",
                message=f"Error en validación: {str(e)}",
                details={"exception": str(e)}
            ))
            return ValidationResult(False, flags)

    def validate_po_vs_budget(self, project_name: str, po_amount: float) -> ValidationResult:
        """
        Validar que OC ≤ Presupuesto disponible del proyecto.

        Args:
            project_name: Nombre del proyecto
            po_amount: Monto de la nueva OC

        Returns:
            ValidationResult con validación y flags
        """
        flags = []

        try:
            with self._get_connection() as conn:
                # Obtener presupuesto y comprometido actual
                cur = conn.execute("""
                    SELECT
                        p.name as project_name,
                        COALESCE(p.budget_total, vpt.total_presupuesto, 0) as budget_total,
                        COALESCE(SUM(po.total_amount), 0) as committed,
                        COALESCE(p.budget_total, vpt.total_presupuesto, 0) - COALESCE(SUM(po.total_amount), 0) as available
                    FROM projects p
                    LEFT JOIN v_presupuesto_totales vpt ON LOWER(TRIM(vpt.proyecto)) = LOWER(TRIM(p.name))
                    LEFT JOIN purchase_orders_unified po ON LOWER(TRIM(po.project_name)) = LOWER(TRIM(p.name))
                        AND po.status IN ('approved', 'closed')
                    WHERE LOWER(TRIM(p.name)) = LOWER(TRIM(?))
                    GROUP BY p.name, p.budget_total, vpt.total_presupuesto
                """, (project_name,))

                row = cur.fetchone()
                if not row or row["budget_total"] == 0:
                    # Proyecto sin presupuesto definido
                    flags.append(ValidationFlag(
                        flag_type="no_budget",
                        severity="warning",
                        message=f"Proyecto {project_name} sin presupuesto definido",
                        details={
                            "project_name": project_name,
                            "po_amount": po_amount,
                            "needs_budget": True
                        },
                        project_name=project_name
                    ))
                    return ValidationResult(True, flags)  # Permitir pero advertir

                budget_total = row["budget_total"]
                committed = row["committed"]
                available = row["available"]

                if po_amount > available:
                    flags.append(ValidationFlag(
                        flag_type="exceeds_budget",
                        severity="error" if po_amount > budget_total else "warning",
                        message=f"OC excede presupuesto disponible en {project_name}",
                        details={
                            "project_name": project_name,
                            "budget_total": budget_total,
                            "committed": committed,
                            "available": available,
                            "attempted": po_amount,
                            "excess": po_amount - available,
                            "requires_approval": True
                        },
                        project_name=project_name
                    ))
                    return ValidationResult(False, flags, available, po_amount)

                # Advertencia si consume más del 90% del disponible
                if po_amount > (available * 0.9):
                    flags.append(ValidationFlag(
                        flag_type="budget_nearly_consumed",
                        severity="warning",
                        message=f"Proyecto {project_name} cerca del límite presupuestal",
                        details={
                            "project_name": project_name,
                            "remaining_after": available - po_amount,
                            "budget_consumption_pct": ((committed + po_amount) / budget_total) * 100
                        },
                        project_name=project_name
                    ))

                return ValidationResult(True, flags, available, po_amount)

        except Exception as e:
            logger.error(f"Error validating PO vs budget: {e}")
            flags.append(ValidationFlag(
                flag_type="validation_error",
                severity="error",
                message=f"Error en validación: {str(e)}",
                details={"exception": str(e)}
            ))
            return ValidationResult(False, flags)

    def get_project_risk_flags(self, project_name: str) -> List[ValidationFlag]:
        """
        Obtener todos los flags de riesgo para un proyecto.

        Args:
            project_name: Nombre del proyecto

        Returns:
            Lista de ValidationFlag para el proyecto
        """
        flags = []

        try:
            with self._get_connection() as conn:
                # Buscar violaciones de 3-way match
                cur = conn.execute("""
                    SELECT COUNT(*) as violations
                    FROM v_facturas_compra fc
                    LEFT JOIN v_goods_receipt_summary grs ON grs.po_number = fc.po_number
                    WHERE LOWER(TRIM(fc.project_name)) = LOWER(TRIM(?))
                    AND (fc.total_amount > COALESCE(grs.total_received, 0)
                         OR grs.total_received IS NULL)
                """, (project_name,))

                violations = cur.fetchone()["violations"]
                if violations > 0:
                    flags.append(ValidationFlag(
                        flag_type="three_way_violations",
                        severity="warning",
                        message=f"{violations} violaciones de 3-way match en {project_name}",
                        details={
                            "project_name": project_name,
                            "violations_count": violations,
                            "requires_review": True
                        },
                        project_name=project_name
                    ))

                # Buscar facturas sin OC
                cur = conn.execute("""
                    SELECT COUNT(*) as orphan_invoices
                    FROM ap_invoices ai
                    LEFT JOIN ap_po_links apl ON apl.invoice_id = ai.id
                    WHERE LOWER(TRIM(ai.project_name)) = LOWER(TRIM(?))
                    AND apl.id IS NULL
                """, (project_name,))

                orphan_count = cur.fetchone()["orphan_invoices"]
                if orphan_count > 0:
                    flags.append(ValidationFlag(
                        flag_type="orphan_invoices",
                        severity="warning",
                        message=f"{orphan_count} facturas sin OC en {project_name}",
                        details={
                            "project_name": project_name,
                            "orphan_count": orphan_count,
                            "needs_matching": True
                        },
                        project_name=project_name
                    ))

                return flags

        except Exception as e:
            logger.error(f"Error getting project risk flags: {e}")
            return [ValidationFlag(
                flag_type="risk_analysis_error",
                severity="error",
                message=f"Error en análisis de riesgos: {str(e)}",
                details={"exception": str(e)},
                project_name=project_name
            )]


def create_validation_tables(db_path: str):
    """Crear tablas necesarias para el sistema de validaciones."""
    conn = sqlite3.connect(db_path)

    # Tabla para enlaces AP-PO (si no existe)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ap_po_links (
            id INTEGER PRIMARY KEY,
            invoice_id INTEGER NOT NULL,
            invoice_line_id INTEGER,
            po_id TEXT,
            po_line_id TEXT,
            amount REAL NOT NULL,
            qty REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            FOREIGN KEY(invoice_id) REFERENCES ap_invoices(id)
        )
    """)

    # Índices para performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ap_po_links_inv ON ap_po_links(invoice_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ap_po_links_po ON ap_po_links(po_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ap_po_links_po_line ON ap_po_links(po_line_id)")

    # Tabla para aliases de proyectos
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_aliases (
            id INTEGER PRIMARY KEY,
            original_name TEXT NOT NULL,
            canonical_name TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            UNIQUE(original_name, canonical_name)
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_aliases_orig ON project_aliases(original_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_aliases_canon ON project_aliases(canonical_name)")

    conn.commit()
    conn.close()

    logger.info("Validation tables created successfully")


# Helper functions para uso en APIs
def validate_and_return_response(validation_result: ValidationResult) -> Tuple[Dict, int]:
    """
    Convertir ValidationResult a respuesta HTTP.

    Returns:
        Tuple de (response_dict, status_code)
    """
    if validation_result.is_valid:
        return {
            "valid": True,
            "flags": [
                {
                    "type": flag.flag_type,
                    "severity": flag.severity,
                    "message": flag.message,
                    "details": flag.details
                }
                for flag in validation_result.flags
            ]
        }, 200
    else:
        error_flags = [flag for flag in validation_result.flags if flag.severity == "error"]
        primary_error = error_flags[0] if error_flags else validation_result.flags[0]

        return {
            "valid": False,
            "error": primary_error.flag_type,
            "message": primary_error.message,
            "details": primary_error.details,
            "allowed_remaining": validation_result.allowed_amount,
            "attempted": validation_result.attempted_amount,
            "flags": [
                {
                    "type": flag.flag_type,
                    "severity": flag.severity,
                    "message": flag.message,
                    "details": flag.details
                }
                for flag in validation_result.flags
            ]
        }, 422