# Guía de Módulo: Matching AP↔PO

## 1. Propósito

Acelerar y controlar la asociación de facturas de proveedores (AP) a Órdenes de Compra (PO) y sus líneas, respetando tolerancias configurables y dejando trazabilidad de decisiones.

## 2. Entidades / Tablas Clave

| Tabla / Vista | Rol |
|---------------|-----|
| purchase_orders_unified | Cabeceras y líneas consolidadas de OC |
| v_po_line_balances_pg | Saldos dinámicos (qty y monto restante) por línea |
| ap_po_links | Relación factura ↔ línea OC con monto aplicado |
| ap_match_config | Config de tolerancias (global / project / vendor) |
| ap_match_feedback | Feedback de usuario (aceptado / override / rechazado) |

## 3. Flujo Operativo

1. Sugerir: POST `/api/ap-match/suggestions` → ranking de candidatos.
2. Previsualizar: POST `/api/ap-match/preview` con `{ invoice_id?, vendor_rut, amount, links[] }`.
3. Confirmar: POST `/api/ap-match/confirm` → persiste en `ap_po_links`.
4. Feedback: POST `/api/ap-match/feedback` (`accepted`, `reason`).

## 4. Resolución de Tolerancias

Precedencia: vendor > project > global.

Campos:

- `amount_tol_pct`: % de diferencia admisible de monto acumulado vs factura.
- `qty_tol_pct`: % exceso de cantidad permitido vs cantidad PO.
- `recv_required`: fuerza validación de recepciones (3-way match).

## 5. Validaciones en Preview

| Código | Situación | Acción |
|--------|-----------|--------|
| links_exceed_po_total | Sumatoria supera el total PO | Reducir monto aplicado |
| amount_exceeds_remaining | Monto línea > saldo | Ajustar monto |
| qty_exceeds_remaining | Cantidad > saldo | Ajustar qty |
| invoice_over_receipt | recv_required y recepción insuficiente | Registrar recepción o bajar qty |

## 6. Scoring (Sugerencias)

Heurística (ejemplos de factores):

- Cobertura de monto (`coverage_pct`).
- Delta relativo de monto (`amount_delta_pct`).
- Coincidencia de vendor.
- Antigüedad (prioriza líneas más antiguas cuando similar score).

## 7. Feedback

Motiva aprendizaje/manual analytics.

Campos típicos `reason`: `partial_delivery`, `force_override`, `price_variation_explained`.

## 8. Métricas Recomendada (Futuro)

- % Facturas auto-sugeridas sin override.
- Tiempo promedio desde recepción a match definitivo.
- Ranking vendors con mayor tasa de overrides.

## 9. Checklist Rápido

1. Verificar config tolerancias.
2. Ejecutar sugerencias.
3. Ajustar manual si violaciones leves justificadas.
4. Confirmar.
5. Registrar feedback si override.

## 10. Roadmap Sugerido

- Endpoint de auditoría de eventos de matching.
- Ajuste dinámico de tolerancias por histórico.
- Detección de outliers (precio unitario vs histórico).

## 11. Troubleshooting

| Síntoma | Posible Causa | Paso |
|---------|---------------|------|
| Preview siempre viola recepciones | Falta vista recepciones real | Revisar `recv_required` o poblar recepciones |
| No aparecen sugerencias | Filtros demasiado estrictos | Revisar tolerancias globales |
| Feedback 404 | Endpoint no cargado | Validar blueprint `api_ap_match` en servidor |

## Fin de la Guía
