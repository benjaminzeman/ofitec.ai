# Guía de Uso del Portal Ofitec

Esta guía orienta a usuarios operativos y financieros sobre cómo aprovechar los módulos implementados: Matching AP↔PO, Estado de Pago (EP), Retenciones, Cobranzas (AR) e Importaciones Staging.

---
## 1. Panorama General

El portal consolida procesos de control financiero del ciclo Compra → Recepción → Factura de Proveedor → Estado de Pago Cliente → Facturación & Cobranza.

| Dominio | Objetivo | Entidades Clave |
|---------|----------|-----------------|
| Matching AP↔PO | Vincular facturas de cuentas por pagar a Órdenes de Compra y sus líneas respetando tolerancias | purchase_orders_unified, v_po_line_balances_pg, ap_po_links |
| Estado de Pago (EP) | Gestionar avance contractual y facturación al cliente | client_contracts, client_sov_items, ep_headers, ep_lines, ep_deductions |
| Retenciones | Registrar y liberar montos retenidos contractualmente | ep_retention_ledger |
| Cobranzas (AR) | Emitir y registrar cobros de facturas cliente | ar_invoices, ar_collections |
| Import Staging EP | Subir planillas de avance y validar contra contrato | ep_import_staging |

---
## 2. Matching AP↔PO

### 2.1 Flujo Básico

1. Obtener sugerencias: POST `/api/ap-match/suggestions` con `{ vendor_rut, amount, date }`.
2. Previsualizar aplicación de líneas: POST `/api/ap-match/preview` con `links` (lista de líneas PO con montos propuestos).
3. Confirmar (persiste): POST `/api/ap-match/confirm` (genera ap_po_links y evento).
4. Feedback (aceptar / rechazar): POST `/api/ap-match/feedback` con `{ invoice_id, accepted, reason }`.

### 2.2 Tolerancias

- Se resuelven por precedencia: vendor > project > global (tabla `ap_match_config`).
- Campos: `amount_tol_pct`, `qty_tol_pct`, `recv_required`.
- La preview marca violaciones: `links_exceed_po_total`, `amount_exceeds_remaining`, `qty_exceeds_remaining`, `invoice_over_receipt`.

### 2.3 Buenas Prácticas

- Enviar `vendor_rut` + `amount` para mejorar scoring de sugerencias.
- Revisar razones (`reasons[]`) para trazabilidad (e.g. `coverage_pct`, `amount_delta_pct`).
- Usar feedback cuando se hace override manual para mejorar analítica futura.

---
## 3. Estado de Pago (EP)

### 3.1 Conceptos

- Contrato (`client_contracts`) define: cliente, retención %, términos de pago.
- SOV (Schedule of Values) lista ítems y tope económico (control de sobre-ejecución).
- EP Header (`ep_headers`): periodo + estado (draft → approved → invoiced → paid).
- EP Lines (`ep_lines`): avance monetario por ítem (valida contra SOV acumulado aprobado, no incluye borradores anteriores).
- Deducciones (`ep_deductions`): retención explícita, penalizaciones, amortizaciones, otros.

### 3.2 Flujo Manual Minimal

1. Crear contrato: POST `/api/contracts`.
2. Cargar SOV: POST `/api/contracts/{id}/sov/import`.
3. Crear EP: POST `/api/ep` (hereda `retention_pct` si no se envía).
4. Subir líneas: POST `/api/ep/{ep_id}/lines/bulk`.
5. (Opcional) Deducciones: POST `/api/ep/{ep_id}/deductions/bulk`.
6. Resumen / validación: GET `/api/ep/{ep_id}/summary`.
7. Aprobar: POST `/api/ep/{ep_id}/approve`.
8. Generar factura cliente: POST `/api/ep/{ep_id}/generate-invoice`.
9. Ver retención: GET `/api/ep/{ep_id}/retention`.

### 3.3 Importación Masiva (Staging)

1. Crear staging: POST `/api/ep/import/staging` con `rows` crudos de planilla.
2. Validar: POST `/api/ep/import/staging/{sid}/validate` → calcula montos y violaciones.
3. Corregir violaciones (si `ep_exceeds_contract_item` presente) ajustando planilla o SOV.
4. Promover: POST `/api/ep/import/staging/{sid}/promote` (si no hay violaciones severas) → crea EP en estado `submitted`.
5. Continuar flujo estándar (aprobar → facturar).

### 3.4 Estados del EP

| Estado | Descripción | Transiciones |
|--------|-------------|--------------|
| draft | Borrador editable | draft → submitted / approved |
| submitted | Cargado vía import / flujo semi controlado | submitted → approved |
| approved | Validado para facturación | approved → invoiced |
| invoiced | Factura emitida | invoiced → paid |
| paid | Cerrado financiero | - |

### 3.5 Retenciones

- Automática: si no hay deducción tipo `retention` se calcula `lines_subtotal * retention_pct` al facturar y se registra en `ep_retention_ledger`.
- Explícita: una deducción `retention` desplaza el cálculo automático.
- Liberación total: POST `/api/ep/{ep_id}/retention/release`.
- Liberación parcial: POST `/api/ep/{ep_id}/retention/release-partial` con `{ amount }`.
- Métricas: `retention_held`, `retention_released`, `retention_outstanding` (en summary y ledger).

### 3.6 Salvaguardas EP / AR

| Caso | Error | Condición |
|------|-------|-----------|
| Factura duplicada | `duplicate_invoice` | Ya existe invoice activa para EP |
| Monto neto cero | `zero_amount_invoice` | Net = 0 tras deducciones |
| Límite SOV excedido | `ep_exceeds_contract_item` | Suma aprobada + periodo > cap Ítem |

---

## 4. Cobranzas (AR)

- Factura se genera con due_date = `invoice_date + payment_terms_days` (contrato o 30 default).
- Registrar cobranza: POST `/api/ar/invoices/{id}/collect` (valida `over_collected`).
- KPIs agregados en vistas: `v_ar_expected_project`, `v_ar_actual_project` para flujos proyectados vs cobrados.

---

## 5. Dashboards & Métricas

- Proyectos: montos orden de compra, avance aprobado (EP), facturación esperada y cobranzas reales.
- Finanzas: consolidado de pipeline (approved, pending_invoice, expected_inflow, actual_collections, retenciones pendientes).

---

## 6. Errores Comunes (422) Resumen

| Código | Contexto | Acción Recomendada |
|--------|----------|-------------------|
| invalid_payload | Falta/forma inválida de campos | Revisar cuerpo JSON |
| ep_exceeds_contract_item | Límite SOV superado | Ajustar línea o ampliar SOV |
| duplicate_invoice | Reintento facturación | Consultar invoice existente |
| zero_amount_invoice | Net = 0 | Revisar líneas/deducciones |
| over_collected | Cobranza excede total | Ajustar monto cobrado |
| amount_exceeds_remaining | Línea PO excede saldo | Revisar link propuesto |
| qty_exceeds_remaining | Cantidad excede saldo | Ajustar cantidad |
| invoice_over_receipt | Falta recepción 3-way | Registrar recepción o reducir qty |
| violations_present | Staging con violaciones | Corregir antes de promover |

---

## 7. Buenas Prácticas Operativas

- Mantener SOV actualizado antes de cargar EP masivos.
- Usar staging para cargas > 10 líneas (validación automática ahorra reprocesos).
- Revisar `summary` antes de aprobar EP para validar net y retención.
- Liberar retención parcial sólo cuando exista evidencia documental (policy interna).
- Proveer feedback en matching para mejorar heurísticas futuras.

---

## 8. Checklist Rápido (EP)

1. Contrato y SOV creados.
2. EP creado (o promovido desde staging).
3. Líneas cargadas y sin violaciones.
4. Deducciones (retención explícita si aplica).
5. Summary validado (net y retención correctos).
6. Aprobar.
7. Generar factura.
8. Monitorear cobranza y retención (release parcial / total según avance contractual).

---

## 9. Siguientes Evoluciones (Roadmap Sugerido)

- Auditoría de eventos (ap_match_events) vía endpoint de lectura.
- Versionado de SOV / comparativo de variaciones.
- Aging de retenciones por bucket de días.
- UI wizard multi-paso para EP (crear → líneas → deducciones → resumen → aprobar → facturar).
- Ajuste parametrizable de IVA y monedas.

---

## 10. Soporte & Debug

- Consultar logs de violaciones vía respuesta JSON (`violations` array).
- Revisar tabla `ep_retention_ledger` para discrepancias de retención.
- Validar configuraciones de tolerancia: GET `/api/ap-match/config`.
- Confirmar existencia de vistas requeridas (ej. `v_po_line_balances_pg`) si faltan violaciones esperadas.

---

## Fin de la Guía
