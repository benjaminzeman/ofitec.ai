# API Error Codes

Formato general de error:

```json
{
  "error": "codigo",
  "detail": "Mensaje humano corto",
  "extra": { "campo": "valor" }
}
```

## Generales

- `bad_request` : Payload inválido o faltan campos.
- `not_found` : Recurso inexistente.
- `conflict` : Estado incompatible con la operación.
- `internal_error` : Error inesperado no manejado.

## Contratos / SOV

- `contract_not_found` : ID de contrato no existe.
- `sov_duplicate_item` : Item repetido en import SOV.
- `sov_invalid_item` : Campos faltantes / inválidos.

## Estado de Pago (EP)

- `ep_not_found` : EP no existe.
- `ep_invalid_state` : Estado del EP no permite la acción.
- `ep_duplicate_number` : `ep_number` ya usado en ese contrato.
- `ep_line_missing` : Ítem en línea no existe en SOV.
- `ep_exceeds_contract_item` : Acumulado EP supera qty o valor SOV.
- `ep_no_lines` : Se requiere al menos una línea para aprobar / facturar.

## Retenciones

- `retention_not_found` : No existe registro de retención.
- `retention_already_released` : Ya fue totalmente liberada.
- `invalid_retention_amount` : Monto parcial <=0 o mayor al saldo.
- `retention_over_release` : Intento de liberar más que lo retenido.

## Notas de Venta (Sales Notes)

- `sales_note_exists` : Ya existe una nota de venta vigente para el EP.
- `sales_note_not_found` : ID no existe.
- `sales_note_cancelled` : La nota está cancelada (no puede facturarse).
- `sales_note_invoiced` : Ya convertida a factura.
- `sales_note_invalid_state` : Acción no permitida en estado actual.
- `zero_amount_sales_note` : Subtotal - deducciones <= 0.

## Facturación / Cuentas por Cobrar (AR)

- `invoice_not_found` : ID no existe.
- `duplicate_invoice` : Ya existe factura asociada a ese EP o nota.
- `invalid_invoice_state` : No se puede operar en estado actual.
- `over_collected` : Monto de cobranza excede saldo facturado.

## Matching AP

- `match_not_found` : Intento de feedback sobre match inexistente.
- `match_requires_invoice` : Falta `invoice_id` para feedback.

## Conciliación / Bancos (placeholder)

- `bank_tx_not_found` : Transacción bancaria no encontrada.
- `reconcile_conflict` : Operación contradice estado conciliado.

## Códigos futuros reservados

- `feature_not_enabled`
- `validation_error` (uso genérico validaciones batch)

## Buenas prácticas

1. `error` es estable y versionable; `detail` puede cambiar redacción.
2. Incluir `extra` con claves como `field`, `attempt`, `cap`, `prev`, etc.
3. Evitar devolver stacktrace al cliente.
4. Para listas masivas de errores, usar `errors: [ {...}, {...} ]` (extensión futura).

## Ejemplos

### EP excede SOV

```json
{
  "error": "ep_exceeds_contract_item",
  "detail": "Item IT-001 excede SOV",
  "item_code": "IT-001",
  "attempt": 1200.0,
  "prev": 1000.0,
  "cap": 1000.0
}
```

### Intento de sobre-liberar retención

```json
{
  "error": "retention_over_release",
  "detail": "Monto excede retención pendiente",
  "remaining": 70.0,
  "attempt": 80.0
}
```

### Nota de venta duplicada

```json
{
  "error": "sales_note_exists",
  "detail": "Ya existe nota emitida para el EP",
  "sales_note_id": 55
}
```
