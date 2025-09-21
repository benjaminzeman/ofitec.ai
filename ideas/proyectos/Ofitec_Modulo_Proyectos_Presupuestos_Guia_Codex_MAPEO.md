# Ofitec – Módulo Proyectos & Presupuestos

## Anexo A: Mapeo explícito de hojas/columnas del archivo de ejemplo

> **IMPORTANTE**: Este archivo Excel es **solo un ejemplo**. Codex debe programar un importador **tolerante a formatos**: los nombres de hojas/columnas pueden variar.

### Hoja: **Presupuesto** (encabezado en fila 1)

Columnas detectadas (primeras 24):

- 01. `ITEM`
- 02. `DESCRIPCION`
- 03. `UNIDAD`
- 04. `CANTIDAD`
- 05. `PRECIO UNITARIO $`
- 06. `PRECIO TOTAL $`
- 07. `PRECIO UNITARIO UF`
- 08. `PRECIO TOTAL UF`
- 09. `col_9`
- 10. `col_10`
- 11. `col_11`
- 12. `col_12`
- 13. `col_13`
- 14. `col_14`
- 15. `col_15`
- 16. `col_16`
- 17. `col_17`
- 18. `col_18`
- 19. `col_19`
- 20. `col_20`
- 21. `col_21`
- 22. `col_22`
- 23. `col_23`
- 24. `col_24`

### Hoja: **Partidas** (encabezado en fila 1)

Columnas detectadas (primeras 24):

- 01. `ITEM`
- 02. `DESCRIPCION`
- 03. `UNI`
- 04. `Cantidad`
- 05. `Permanencia`
- 06. `Subtotal`
- 07. `PU`
- 08. `TOTAL`
- 09. `col_9`
- 10. `col_10`
- 11. `col_11`
- 12. `col_12`
- 13. `col_13`
- 14. `col_14`
- 15. `col_15`
- 16. `col_16`
- 17. `col_17`
- 18. `col_18`
- 19. `col_19`
- 20. `col_20`
- 21. `col_21`
- 22. `col_22`
- 23. `col_23`
- 24. `col_24`

### Hoja: **Recursos** (encabezado en fila 1)

Columnas detectadas (primeras 24):

- 01. `RecursoID`
- 02. `Iniciales`
- 03. `Grupo`
- 04. `Tipo`
- 05. `Descripcion`
- 06. `Unidad`
- 07. `CostoUnitario`
- 08. `Costo Maq x Dia`
- 09. `TOTAL HH`
- 10. `Cant de Dias`
- 11. `TOTAL $`

### Hoja: **Costo_Indirecto** (encabezado en fila 1)

Columnas detectadas (primeras 24):

- 01. `ITEM`
- 02. `DESCRIPCIÓN`
- 03. `UD`
- 04. `CANTIDAD`
- 05. `PERMANENCIA`
- 06. `P. UNITARIO`
- 07. `TOTAL`
- 08. `col_8`
- 09. `col_9`
- 10. `col_10`
- 11. `col_11`
- 12. `col_12`

---

## Anexo B: Reglas de ETL **robusto** (esquema flexible)

1. **Descubrimiento de esquema**:

   - Detectar automáticamente la fila de encabezados (heurística sobre primeras 10 filas: mayor densidad de texto, baja razón numéricos).

   - Normalizar nombres (trim, colapsar espacios, quitar tildes, pasar a snake_case).

   - Intentar *matching difuso* de columnas con el esquema objetivo (ej.: `codigo partida`, `cod_partida`, `Ítem` → `codigo_partida`).

2. **Asistente interactivo** cuando haya ambigüedad:

   - Si la confianza del matching < umbral (p.ej. 0.7), **preguntar al usuario**: “¿Qué columna corresponde a `codigo_partida`?”

   - Permitir guardar el mapeo como **plantilla** por cliente/tipo de presupuesto para reusarlo.

3. **Tipos y validaciones**:

   - Coerción de números con punto o coma decimal; fechas en varios formatos.

   - Reglas mínimas: `codigo_capitulo` y `codigo_partida` no vacíos; `cantidad` y `precio_unitario` numéricos.

   - Duplicados: advertir si `codigo_partida` se repite dentro del mismo capítulo.

4. **Persistencia**:

   - Cargar `capitulos`, `partidas`, `apu_insumos` según la hoja de origen.

   - Mantener **idempotencia** con hash por fila clave (evitar duplicar cargas).

5. **Trazabilidad**:

   - Guardar log de importación (filas insertadas/actualizadas/rechazadas y motivo).

   - Conservar copia del archivo original asociado al presupuesto/versión.

6. **Pruebas**:

   - Validar totales por capítulo vs. Excel.

   - Verificar que las fórmulas multilámina se reproduzcan en vistas/materializaciones.

---

## Anexo C: Sugerencia de mapeo al esquema Ofitec (ejemplo)

> Ajustar a las columnas reales de cada hoja usando matching difuso + confirmación del usuario.

### Capítulos

- `codigo_capitulo`  ⇐ columnas que contengan `capítulo`, `capitulo`, `chapter`, `cod cap`.

- `nombre`           ⇐ columnas con `nombre`, `descripción capítulo`.

- `orden`            ⇐ si existe una columna de orden/posición.

### Partidas

- `codigo_partida`   ⇐ `ítem`, `item`, `código`, `codigo`, `partida`.

- `descripcion`      ⇐ `descripción`, `descripcion`, `detalle`.

- `unidad`           ⇐ `u`, `unidad`, `unit`.

- `cantidad`         ⇐ `cant`, `cantidad`, `qty`.

- `precio_unitario`  ⇐ `p.u.`, `precio unitario`, `unit price`.

- `total`            ⇐ `parcial`, `total`, o recalculado (`cantidad * precio_unitario`).

### APU (insumos)

- `tipo_insumo`      ⇐ inferido por hoja o por columna (material/mano_obra/maquinaria/subcontrato).

- `codigo_insumo`    ⇐ `código`, `codigo`, `ref`.

- `descripcion`      ⇐ `descripción`, `detalle`.

- `unidad`           ⇐ `unidad`.

- `cantidad`         ⇐ `cantidad`.

- `precio_unitario`  ⇐ `precio unitario`.

- `subtotal`         ⇐ `subtotal` o recalculado.
