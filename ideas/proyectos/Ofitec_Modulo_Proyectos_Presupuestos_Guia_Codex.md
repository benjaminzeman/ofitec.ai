
# Guía Técnica – Ofitec: Módulo de Proyectos y Presupuestos (versión con presupuesto de ejemplo)

Este documento amplía la especificación para **Codex** tomando como base el archivo de Excel entregado: `Presupuesto Ejemplo.xlsx`.
Se incluye un mapeo de hojas, detección de encabezados, fórmulas, y recomendaciones de cómo persistir e interconectar la información en Ofitec.

---

## 1) Inventario de Hojas (mapeo rápido)
### Hoja: **Presupuesto**
- Filas: 103 | Columnas: 30
- Fórmulas (escaneadas): 99
- Encabezados detectados (muestra): ITEM, DESCRIPCION, UNIDAD, CANTIDAD, PRECIO UNITARIO $, PRECIO TOTAL $, PRECIO UNITARIO UF, PRECIO TOTAL UF
- Ejemplos de fórmulas:
  - `=_xlfn.XLOOKUP(A4,Partidas!A:A,Partidas!G:G)`
  - `=+D4*E4`
  - `=+E4/39300`
  - `=+G4*D4`
  - `=_xlfn.XLOOKUP(A6,Partidas!A:A,Partidas!G:G)`
### Hoja: **Partidas**
- Filas: 166 | Columnas: 34
- Fórmulas (escaneadas): 501
- Encabezados detectados (muestra): ITEM, DESCRIPCION, UNI, Cantidad, Permanencia, Subtotal, PU, TOTAL
- Ejemplos de fórmulas:
  - `=_xlfn.XLOOKUP(A3,Presupuesto!A:A,Presupuesto!B:B)`
  - `=_xlfn.XLOOKUP(A4,Presupuesto!A:A,Presupuesto!B:B)`
  - `=_xlfn.XLOOKUP(A4,Presupuesto!A:A,Presupuesto!C:C)`
  - `=_xlfn.XLOOKUP(A4,Presupuesto!A:A,Presupuesto!D:D)`
  - `=+H4/D4`
### Hoja: **Recursos**
- Filas: 29 | Columnas: 11
- Fórmulas (escaneadas): 78
- Encabezados detectados (muestra): RecursoID, Iniciales, Grupo, Tipo, Descripcion, Unidad, CostoUnitario, Costo Maq x Dia, TOTAL HH, Cant de Dias, TOTAL $
- Ejemplos de fórmulas:
  - `=SUMIF(Partidas!A:A,A2,Partidas!F:F)`
  - `=+I2*G2`
  - `=SUMIF(Partidas!A:A,A3,Partidas!F:F)`
  - `=+I3*G3`
  - `=SUMIF(Partidas!A:A,A4,Partidas!F:F)`
### Hoja: **Costo_Indirecto**
- Filas: 63 | Columnas: 12
- Fórmulas (escaneadas): 90
- Encabezados detectados (muestra): ITEM, DESCRIPCIÓN, UD, CANTIDAD, PERMANENCIA, P. UNITARIO, TOTAL
- Ejemplos de fórmulas:
  - `=+F3*E3*D3`
  - `=+F4*E4*D4`
  - `=+F5*E5*D5`
  - `=1200000*1.35`
  - `=+F6*E6*D6`

> Nota: Los conteos de fórmulas son de una muestra acotada (máx. 300 filas × 30 columnas por hoja) para acelerar el análisis.

---

## 2) Referencias Cruzadas entre Hojas (encontradas en fórmulas)
- **Presupuesto → Costo_Indirecto**: 1 referencias (muestra)

**Implicancia para Codex**: donde existan referencias `HojaA!Celda` se deben modelar **JOINs** o **VISTAS** que reproduzcan estos vínculos.  
Toda lógica de cálculo actualmente resuelta con fórmulas debe migrarse a **consultas SQL** o **procedimientos** en el backend, manteniendo el resultado visible en UI.

---

## 3) Esquema de Datos Propuesto (normalizado)

## Recomendaciones de Modelado (Ofitec → Base de Datos)
- Cada **Hoja Excel** debe mapearse a una **tabla** o **vista materializada** en Ofitec.
- Úsese una **clave primaria** (ej. `id` autoincremental) y una **clave de negocio** cuando exista (ej. `codigo_partida`, `codigo_capitulo`).
- Estándar de **nombres de campos**: snake_case en backend (p. ej., `codigo_partida`, `unidad`, `cantidad`, `precio_unitario`, `costo_total`).
- Estándar de **tipos** sugeridos:
  - Códigos/IDs: `VARCHAR(64)`
  - Descripciones: `TEXT`
  - Unidades: `VARCHAR(16)`
  - Cantidades/HH/Horas: `DECIMAL(18,4)`
  - Precios/Costos: `DECIMAL(18,4)`
  - Moneda (CLP/UF): `VARCHAR(8)` + tabla `fx_uf` para conversión diaria
- **Relaciones** esperadas:
  - `capitulos (1) ── (N) partidas`
  - `partidas (1) ── (N) apu_insumos` (materiales, mano de obra, maquinaria, subcontratos)
  - `proyectos (1) ── (1) presupuesto` (versión vigente)
  - `partidas (1) ── (N) avances` y `partidas (1) ── (N) imputaciones_financieras`


### Tablas mínimas
- `proyectos`: id, codigo, nombre, cliente_id, comuna, region, fecha_inicio_plan, fecha_termino_plan, fecha_termino_real, estado, tipo, responsable_id.
- `presupuestos`: id, proyecto_id, version, estado, moneda, factor_uf, observaciones, created_at.
- `capitulos`: id, presupuesto_id, codigo_capitulo, nombre, orden.
- `partidas`: id, capitulo_id, codigo_partida, descripcion, unidad, cantidad, precio_unitario, costo_directo, costo_indirecto, utilidad, total, rendimiento_meta_json.
- `apu_insumos`: id, partida_id, tipo_insumo (material|mano_obra|maquinaria|subcontrato), codigo_insumo, descripcion, unidad, cantidad, precio_unitario, subtotal.
- `avances`: id, partida_id, fecha, cantidad_avance, porcentaje, observaciones.
- `imputaciones_financieras`: id, partida_id, tipo_doc (oc|factura|egreso|estado_pago), numero_doc, fecha, monto, moneda, proveedor_id, enlace_doc.
- `fx_uf`: fecha, valor_uf.
- `retenciones`: id, proyecto_id, tipo, porcentaje, fecha_inicio, fecha_fin, monto_retenido, monto_liberado.
- `garantias`: id, proyecto_id, tipo (fiel_cumplimiento|anticipo|correcta_ejecucion), numero, emisor, monto, fecha_inicio, fecha_vencimiento, estado.

---

## 4) Lógica de Cálculo a Migrar desde Excel
1. **Totales de Partida**: `total_partida = cantidad * precio_unitario` (si precio incluye solo costo directo) o suma de `apu_insumos` + indirectos + utilidad.
2. **Totales por Capítulo**: `sum(total_partida)` agrupado por `capitulo_id` y `presupuesto_id`.
3. **Costo Directo / Indirecto / Utilidad**: parametrizar en tabla `presupuestos` o `parametros_empresa`.
4. **Avance Físico**: `avance_% = sum(avances.cantidad_avance)/partidas.cantidad` con top en 100%.
5. **Avance Financiero**: `monto_ejecutado = sum(imputaciones_financieras.monto)` y su % respecto a `sum(total_partida)`.
6. **Curva S**: generar serie temporal de acumulados por mes (físico y financiero).
7. **CLP/UF**: si moneda es UF, convertir al día de la operación vía `fx_uf` y mostrar ambas.

> Cualquier fórmula detectada en Excel que combine celdas de varias hojas debe traducirse a **vistas** o **materializaciones** con campos calculados y pruebas unitarias.

---

## 5) Importador desde Excel (ETL ligero)
- Detección automática de **encabezados** por hoja (primera fila con ≥30% strings).
- Mapeo configurable: **columna Excel → campo tabla** (guardar JSON de mapeo por hoja).
- Validaciones:
  - Campos requeridos (ej. `codigo_partida`, `unidad`, `cantidad`, `precio_unitario`).
  - Tipos y coerción numérica (coma/punto decimal).
  - Duplicados en `codigo_partida` y `codigo_capitulo`.
- Estrategia de **idempotencia**: hash por fila (concat de campos clave) para evitar doble carga.
- **Reporte de importación**: filas insertadas, actualizadas, rechazadas (con motivo).

---

## 6) UI/UX – Pantallas Clave
- **Presupuesto (grid)**: capítulos y partidas en árbol, edición en línea, subtotales por capítulo, totales globales, moneda, filtros.
- **APU**: editor por partida con pestañas por tipo de insumo; recalcula totales en tiempo real.
- **Proyecto**: dashboard con KPIs (avance físico/financiero, margen, desviaciones), cronograma y Curva S.
- **Comparativo**: Presupuesto vs Avance vs Estado de Pago (tabla y gráficos).
- **ETL**: asistente de importación con previsualización, reglas y log de resultados.

---

## 7) Seguridad y Versionamiento
- Cambios en partidas y APU generan **nueva versión** del presupuesto con diff visible.
- Permisos por rol (Administrador, Jefe de Obra, Finanzas, Lectura).
- Bitácora de auditoría: quién cambió qué y cuándo (por proyecto/presupuesto).

---

## 8) Integración con otros módulos
- **Site Management**: `avances` y consumos desde terreno imputan a `partidas`.
- **Finanzas**: OC/Facturas/Egresos → `imputaciones_financieras`.
- **Conciliación bancaria**: enlazar movimientos con facturas/egresos del proyecto.
- **Documentos**: anexos (planos, contratos, especificaciones) enlazados a proyecto/partida.

---

## 9) Tareas para Codex (checklist)
- [ ] Crear tablas sugeridas y migraciones.
- [ ] Implementar importador Excel con mapeo por hoja detectada en el archivo.
- [ ] Escribir vistas/consultas para totales por partida, capítulo y presupuesto.
- [ ] Implementar cálculo de Avance Físico y Financiero + Curva S.
- [ ] Construir dashboards (proyecto y comparativo) y editor APU.
- [ ] Implementar versionamiento y auditoría.
- [ ] Conectar con módulos Site Management y Finanzas.
- [ ] Pruebas unitarias de cálculos (paridad con Excel cargado).

---

## 10) Anexos
- Archivo analizado: `Presupuesto Ejemplo.xlsx`
- Hojas detectadas: Presupuesto, Partidas, Recursos, Costo_Indirecto
