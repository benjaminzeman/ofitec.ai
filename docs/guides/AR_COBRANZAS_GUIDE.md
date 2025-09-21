# Guía de Módulo: Cobranzas (AR)

## 1. Propósito

Gestionar facturas cliente emitidas desde EP y su ciclo de cobranza, con visibilidad de flujos esperados vs reales.

## 2. Entidades Clave

| Entidad | Rol |
|---------|-----|
| ar_invoices | Facturas generadas (referencia a ep_id) |
| ar_collections | Pagos / cobranzas parciales o totales |
| ep_retention_ledger | Fuente para saldos retenidos pendientes |
| v_ar_expected_project | Proyección de influjos (por proyecto) |
| v_ar_actual_project | Cobranzas materializadas |

## 3. Flujo

1. EP aprobado genera invoice: POST `/api/ep/{id}/generate-invoice`.
2. Registrar cobranza parcial: POST `/api/ar/invoices/{inv_id}/collect`.
3. Repetir hasta saldo 0.
4. (Opcional) Liberar retenciones luego de milestones.

## 4. Cálculo de Saldos

Saldo = `invoice_total - sum(collections)`.
Bloqueo: Si `amount > saldo` → `over_collected`.

## 5. KPIs Clave

- DSO (futuro): días promedio de cobranza.
- % Cobranza acumulada vs Expected.
- Retención pendiente total.

## 6. Validaciones

| Código | Contexto | Acción |
|--------|----------|-------|
| duplicate_invoice | Segundo intento generación | Usar invoice existente |
| over_collected | Cobro excede saldo | Ajustar monto al saldo |

## 7. Checklist

1. EP aprobado.
2. Invoice generado.
3. Cobranza(s) registradas.
4. Saldo 0 alcanzado.
5. Retención liberada (si corresponde).

## 8. Roadmap Sugerido

- Aging (0-30 / 31-60 / 61-90 / 90+).
- Alertas de facturas por vencer.
- Integración con gateway de pagos.

## 9. Troubleshooting

| Síntoma | Posible Causa | Acción |
|---------|---------------|-------|
| No aparece invoice | EP no aprobado aún | Aprobar EP primero |
| over_collected | Monto > saldo | Recalcular saldo pendiente |
| Retención sin liberar | Falta endpoint release | Ejecutar release parcial / total |

## Fin de la Guía
