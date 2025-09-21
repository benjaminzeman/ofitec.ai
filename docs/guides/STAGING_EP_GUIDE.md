# Guía de Módulo: Staging Import EP

## 1. Propósito

Permitir carga masiva controlada de avances EP desde planillas heterogéneas con validación previa a la promoción.

## 2. Flujo

1. Crear staging: POST `/api/ep/import/staging` `{ rows: [...] }`.
2. Validar: POST `/api/ep/import/staging/{sid}/validate` → agrega cálculos y violaciones.
3. Corregir filas problemáticas (planilla o SOV/contrato).
4. Promover: POST `/api/ep/import/staging/{sid}/promote` → crea EP `submitted`.
5. Aprobar y facturar flujo normal.

## 3. Inferencia de Columnas

Heurística intenta mapear encabezados variados (ej: "ITEM", "CODIGO", "MONTO"). Incluir nombres claros reduce errores.

## 4. Violaciones Detectadas

| Código | Significado | Acción |
|--------|-------------|-------|
| ep_exceeds_contract_item | Suma línea + aprobados > SOV cap | Ajustar monto / ampliar SOV |
| invalid_payload | Estructura insuficiente | Revisar campos requeridos |
| violations_present | Promote bloqueado | Corregir y revalidar |

## 5. Recomendaciones

- Normalizar encabezados en plantillas maestras internas.
- Versionar planillas para auditoría.
- Validar antes de mediodía para tener margen de corrección.

## 6. Checklist

1. Planilla limpia sin fórmulas volátiles.
2. Crear staging.
3. Validar y revisar violaciones.
4. Corregir / revalidar hasta limpio.
5. Promover.
6. Continuar flujo EP estándar.

## 7. Roadmap Sugerido

- Reporte HTML de validación descargable.
- Reglas configurables (blacklist columnas, mandatory fields dinámicos).
- Auto-sugerencia de mapeo con ML ligero.

## 8. Troubleshooting

| Síntoma | Causa | Acción |
|---------|-------|-------|
| Columns faltantes | Encabezados ambiguos | Renombrar y reintentar |
| Promote rechaza | violations_present | Revalidar tras ajuste |
| Monto duplicado | Filas repetidas en planilla | Depurar orígenes |

## Fin de la Guía
