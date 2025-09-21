# Guía de Módulo: Retenciones

## 1. Propósito

Controlar el ciclo de vida de montos retenidos contractualmente: registro automático o explícito y liberaciones parciales / totales auditables.

## 2. Origen de la Retención

- Automática: porcentaje `retention_pct` del contrato aplicado al subtotal de líneas del EP en el momento de facturar (si no existe deducción explícita `retention`).
- Explícita: deducción tipo `retention` en `ep_deductions` define el monto retenido.

## 3. Ledger

`ep_retention_ledger` registra filas con:

| Campo | Descripción |
|-------|-------------|
| id | Identificador |
| ep_id | EP origen |
| event | `hold` / `release_full` / `release_partial` |
| amount | Monto del evento (positivo) |
| hold_row_id | Referencia fila original en caso de split parcial |
| created_at | Timestamp |

## 4. Liberaciones

- Total: POST `/api/ep/{ep_id}/retention/release` → consume todo el outstanding.
- Parcial: POST `/api/ep/{ep_id}/retention/release-partial` `{ amount }` → algoritmo FIFO ajusta o divide filas hold.

## 5. Resumen

GET `/api/ep/{ep_id}/retention` devuelve:

| Campo | Significado |
|-------|-------------|
| held_total | Suma de entradas `hold` |
| released_total | Suma de liberaciones acumuladas |
| outstanding | Diferencia pendiente |

## 6. Validaciones

| Código | Situación | Acción |
|--------|----------|--------|
| amount_exceeds_outstanding | Parcial > saldo | Reducir monto solicitado |
| invalid_state | EP sin retención registrada | Verificar invoice previa |

## 7. Estrategia Parcial (FIFO)

1. Ordenar filas hold por `id` asc.
2. Consumir montos hasta cubrir `amount` solicitado.
3. Si una fila es mayor al remanente:
   - Dividir: reducir fila original y crear nueva fila `release_partial` con porción liberada.

## 8. Checklist

1. Factura generada (retención registrada).
2. Confirmar outstanding > 0.
3. Decidir parcial vs total.
4. Ejecutar endpoint.
5. Revisar ledger y summary.

## 9. Roadmap Sugerido

- Aging de retenciones (días desde hold).
- Reglas de liberación condicionadas a milestones.
- Reporte consolidado por cliente / proyecto.

## 10. Troubleshooting

| Síntoma | Causa probable | Acción |
|---------|----------------|-------|
| Retención no aparece | No se generó invoice aún | Generar factura EP |
| Parcial no descuenta | Valor excede outstanding | Recalcular saldo antes |
| Outstanding negativo | Error histórico | Auditar ledger manualmente |

## Fin de la Guía
