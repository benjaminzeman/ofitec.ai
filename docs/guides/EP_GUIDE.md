# Guía de Módulo: Estado de Pago (EP)

## 1. Propósito

Gestionar avance contractual y facturación al cliente con control de topes (SOV) y retenciones.

## 2. Entidades Clave

| Entidad | Rol |
|---------|-----|
| client_contracts | Contrato base (cliente, retention_pct, payment_terms) |
| client_sov_items | Ítems y topes económicos (Schedule of Values) |
| ep_headers | Cabeceras EP (estado, fechas, referencia contrato) |
| ep_lines | Avance monetario del periodo por ítem |
| ep_deductions | Deducciones (retención explícita, penalizaciones, otros) |
| ep_retention_ledger | Registro histórico de retenciones y liberaciones |
| ar_invoices | Facturas generadas desde EP aprobado |
| ar_collections | Cobros registrados de facturas cliente |

## 3. Estados del EP

| Estado | Descripción | Transiciones |
|--------|-------------|--------------|
| draft | Borrador editable | approve |
| submitted | Creado vía staging promote | approve |
| approved | Validado para facturar | generate-invoice |
| invoiced | Factura emitida | paid (via collections) |
| paid | Factura cobrada | retention-release |

## 4. Flujo Manual

1. Crear contrato.
2. Importar SOV.
3. Crear EP (hereda retention_pct si no se envía).
4. Cargar líneas (bulk).
5. (Opcional) Deducciones.
6. Revisar summary.
7. Aprobar.
8. Generar factura.
9. Gestionar cobranzas y retenciones.

## 5. Staging (Carga Masiva)

1. POST `/api/ep/import/staging` → almacena filas crudas.
2. POST `/api/ep/import/staging/{id}/validate` → calcula montos + violaciones.
3. Corregir violaciones severas (`ep_exceeds_contract_item`).
4. Promote → crea EP en `submitted`.
5. Flujo normal (approve → invoice).

## 6. Retenciones

- Automática: si no hay deducción `retention`, se calcula monto = subtotal * retention_pct en invoice.
- Explícita: deducción `retention` reemplaza cálculo.
- Parcial release: `/retention/release-partial` (FIFO ledger con split ajustado).
- Total release: `/retention/release`.
- Métricas: held, released, outstanding.

## 7. Validaciones Clave

| Código | Contexto | Prevención |
|--------|----------|-----------|
| ep_exceeds_contract_item | Staging / lines bulk | Verificar acumulado vs SOV cap |
| zero_amount_invoice | generate-invoice | Revisar deducciones excesivas |
| duplicate_invoice | generate-invoice repeat | Idempotencia, usar la existente |
| over_collected | collections | Ajustar monto a saldo pendiente |
| amount_exceeds_outstanding | retention release-partial | Reducir monto solicitado |

## 8. Summary (Campos Relevantes)

| Campo | Descripción |
|-------|-------------|
| lines_subtotal | Suma de líneas del periodo |
| total_deductions | Suma deducciones (incluye retención explícita) |
| net_amount | Monto a facturar |
| retention_held | Retención registrada (explícita o calculada) |
| retention_released | Suma liberaciones ledger |
| retention_outstanding | Saldo retenido pendiente |

## 9. Checklist Rápido

1. Contrato + SOV listos.
2. EP cargado (manual o staging promovido).
3. Summary sin violaciones.
4. Aprobar.
5. Generar factura.
6. Registrar cobranzas.
7. Liberar retención cuando corresponda.

## 10. Roadmap Sugerido

- Aging de retención (buckets de días).
- Versionado histórico de SOV.
- Wizard UI multi-paso.
- Alertas de EP sin facturar > X días.

## 11. Troubleshooting

| Síntoma | Posible Causa | Acción |
|---------|---------------|--------|
| Retención cero inesperada | retention_pct no heredado | Revisar contrato / header EP |
| duplicate_invoice devuelto | Segundo intento generate-invoice | Obtener invoice existente |
| ep_exceeds_contract_item | Avance supera tope SOV | Ajustar líneas o SOV |
| over_collected | Cobro supera saldo | Reducir monto |
| retention release falla | Monto > outstanding | Recalcular saldo ledger |

## Fin de la Guía
