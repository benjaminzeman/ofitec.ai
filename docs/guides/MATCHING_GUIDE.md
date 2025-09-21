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
| invoice_over_receipt | recv_required y recepción insuficiente | Registrar recepción o bajar qty |

## 6. Scoring (Sugerencias)

Heurística (ejemplos de factores):

- Cobertura de monto (`coverage_pct`).
- Delta relativo de monto (`amount_delta_pct`).
- Coincidencia de vendor.
- Antigüedad (prioriza líneas más antiguas cuando similar score).


Campos típicos `reason`: `partial_delivery`, `force_override`, `price_variation_explained`.

## 7. Checklist Rápido

1. Verificar config tolerancias.
2. Ejecutar sugerencias.
3. Ajustar manual si violaciones leves justificadas.
4. Confirmar.

## 8. Troubleshooting Rápido

| Síntoma | Posible Causa | Paso |
|---------|---------------|------|
| Preview siempre viola recepciones | Falta vista recepciones real | Revisar `recv_required` o poblar recepciones |
| No aparecen sugerencias | Filtros demasiado estrictos | Revisar tolerancias globales / vendor |
| Feedback 404 | Blueprint no registrado | Verificar carga de `api_ap_match` |

## 9. Métricas Avanzadas de Confianza

Se exponen si `MATCHING_AP_ADVANCED` (default=on):

- `matching_ap_confidence_p50`, `matching_ap_confidence_p95`, `matching_ap_confidence_p99`
- `matching_ap_confidence_p95_bucket`, `matching_ap_confidence_p99_bucket`
- `matching_ap_confidence_sum` (exacta o aproximada)
- `matching_ap_confidence_bucket{range="..."}` distribución discreta
- `matching_ap_confidence_hist_bucket{le="..."}` cumulativa estilo histograma
- `matching_ap_confidence_high_ratio` proporción con `confidence >= 0.90`
- `matching_ap_confidence_stddev` desviación estándar poblacional

### Interpretación

- High Ratio: caída sostenida mientras p95 se mantiene = erosión de cola alta.
- Stddev: spike súbito = volatilidad; caída brusca junto a pérdida de percentiles altos = homogenización anómala.

### Alertas Sugeridas

```yaml
- alert: MatchingAPHighRatioLow
  expr: matching_ap_confidence_high_ratio < 0.40
  for: 10m
  labels:
    severity: warning
    service: matching-ap
  annotations:
    summary: "High confidence ratio bajo (<40%)"
    description: "Proporción de eventos >=0.9 cayó <40% por 10m. Posible degradación precisión."

- alert: MatchingAPStddevSpike
  expr: increase(matching_ap_confidence_stddev[15m]) > 0.10
  for: 5m
  labels:
    severity: info
    service: matching-ap
  annotations:
    summary: "Spike en stddev de confianza"
    description: "Desviación estándar subió >0.10 en 15m. Revisar entradas y últimos deploys."
```

## 10. Endpoint Mini

`GET /api/matching/metrics/mini` devuelve subset para dashboards de alta frecuencia (cada 15–30s) minimizando carga: p95, p99, high_ratio, stddev y acceptance + project_assign_rate.

## 11. Futuro (Ideas)

- Ajuste dinámico de tolerancias historicidad.
- Enriquecer features con estacionalidad de proveedor.
- Detección de outliers (precio unitario vs histórico).
