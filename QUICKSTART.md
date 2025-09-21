# QUICKSTART

Guía express para levantar el stack, generar un Estado de Pago, emitir una Nota de Venta y luego una Factura con cobranza parcial.

## 1. Levantar entorno

Opción Docker (recomendado):

```bash
docker compose up --build -d
```

Opción local (solo backend):

```bash
python -m pip install -r backend/requirements.txt
python backend/server.py
```

El backend expone por defecto: `http://localhost:5555`.
Frontend (si se levanta) en: `http://localhost:3001`.

## 2. Crear contrato y SOV

```bash
curl -s -X POST http://localhost:5555/api/contracts \
  -H 'Content-Type: application/json' \
  -d '{"project_id":101,"customer_id":101,"code":"CT-1","retention_pct":0.05}'

curl -s -X POST http://localhost:5555/api/contracts/1/sov/import \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"item_code":"IT-1","qty":10,"unit_price":1000}]}'
```

## 3. Crear EP y líneas

```bash
# Crear header EP
curl -s -X POST http://localhost:5555/api/ep \
  -H 'Content-Type: application/json' \
  -d '{"project_id":101,"contract_id":1,"ep_number":"EP-1"}'

# Agregar líneas (avances del periodo)
curl -s -X POST http://localhost:5555/api/ep/1/lines/bulk \
  -H 'Content-Type: application/json' \
  -d '{"lines":[{"item_code":"IT-1","qty_period":2,"unit_price":1000,"amount_period":2000}]}'

# Aprobar EP
curl -s -X POST http://localhost:5555/api/ep/1/approve
```

## 4. Generar Nota de Venta (opcional) y Factura

```bash
# Generar Nota de Venta
curl -s -X POST http://localhost:5555/api/ep/1/generate-sales-note | jq

# Emitir factura desde la Nota de Venta
SALES_NOTE_ID=1
curl -s -X POST http://localhost:5555/api/sales-notes/$SALES_NOTE_ID/issue-invoice | jq
```

Alternativa directa (sin nota de venta):

```bash
curl -s -X POST http://localhost:5555/api/ep/1/generate-invoice | jq
```

## 5. Registrar cobranza parcial

```bash
# (Suponiendo invoice_id=1)
curl -s -X POST http://localhost:5555/api/ar/invoices/1/collect \
  -H 'Content-Type: application/json' \
  -d '{"amount":500,"method":"bank_transfer"}' | jq
```

## 6. Retención: liberar total o parcial

```bash
# Liberación parcial de 30
curl -s -X POST http://localhost:5555/api/ep/1/retention/release \
  -H 'Content-Type: application/json' \
  -d '{"mode":"partial","amount":30}' | jq

# Liberación total del saldo
curl -s -X POST http://localhost:5555/api/ep/1/retention/release \
  -H 'Content-Type: application/json' \
  -d '{"mode":"full"}' | jq
```

## 7. AP ↔ PO Matching (mínimo)

```bash
curl -s -X GET http://localhost:5555/api/ap-match/suggestions?project_id=101 | jq
```

## 8. Ver overviews financieros

```bash
curl -s -X GET 'http://localhost:5555/api/projects/overview?project_id=101' | jq
curl -s -X GET 'http://localhost:5555/api/finance/overview?project_id=101' | jq
```

## 9. Errores comunes

| Código | Causa | Acción |
|--------|-------|--------|
| `ep_exceeds_contract_item` | Avance supera qty SOV | Revisar qty acumulada |
| `sales_note_exists` | Ya hay nota activa para EP | Cancelar o usar existente |
| `over_collected` | Cobranza > saldo factura | Ajustar monto |
| `retention_over_release` | Monto > retención pendiente | Disminuir parcial |

Más códigos: ver `API_ERROR_CODES.md`.

## 10. Ejecutar tests

```bash
python -m pytest -q
```

## 11. Siguientes pasos

- Integrar autenticación / permisos.
- Añadir validaciones de fecha (period_start/end).
- Mejorar ranking de matching AP con feedback histórico.

---
Fin Quickstart
