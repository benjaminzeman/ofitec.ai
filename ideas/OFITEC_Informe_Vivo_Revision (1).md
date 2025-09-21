# OFITEC — **Informe Vivo de Revisión de Código**  
**Última actualización:** 2025-09-14 20:22:30  
**Autor:** Asistente (revisión automática + guía para Copilot)  
**Ámbito:** Repo *ofitec.ai* (frontend Next.js, backend Flask, SQLite + vistas canónicas, tools ETL)

> Este documento se irá **actualizando** con hallazgos, verificaciones, sugerencias y tareas concretas para que **Copilot** continúe el desarrollo **sin romper** las reglas oficiales (Ley de Puertos, Ley de Base de Datos, DB Canónica, Estrategia Visual).

---

## 0) Resumen Ejecutivo (estado actual)
- **Frontend (Next.js)** configurado en **puerto 3001** (OK Ley de Puertos).  
- **Cliente API** con *fallback* a `http://localhost:5555/api` (OK).  
- **Backend (Flask)** en **:5555** con rutas clave detectadas:  
  - `/api/projects`, `/api/projects_v2`  
  - `/api/control_financiero/resumen`  
  - `/api/conciliacion/sugerencias`, `/api/conciliacion/confirmar`  
  - `/api/status`
- **DB**: uso de **chipax_data.db** y tablas/vistas canónicas (ej. `purchase_orders_unified`, `v_presupuesto_totales`, `v_facturas_compra`, `v_cartola_bancaria`).  
- **Tools/ETL** presentes: `apply_ofitec_schema_sqlite.py`, `create_finance_views.py`, `import_ofitec_budget.py`, `verify_schema.py`, `add_indexes.py`, utilidades de conciliación y RUT.

**Conclusión breve:** La **arquitectura cumple** los principios base. Falta **cablear UI** para el endpoint de **control financiero** y **endurecer reglas** de negocio (no facturar > OC, no pagar > facturado), con flags/semaforización visibles.

---

## 1) Verificaciones realizadas
- ✅ **Puertos**: 3001 (front) y 5555 (API) detectados.
- ✅ **API Base** en front: `API_BASE_URL` vía env o *fallback* `http://localhost:5555/api`.
- ✅ **Endpoints** backend encontrados: `/api/projects_v2`, `/api/control_financiero/resumen`, conciliación, status.
- ✅ **Tools** para esquema/vistas/ETL: presentes y consistentes.
- ⚠️ **UI de Control Financiero** no consume todavía `/api/control_financiero/resumen` (no hallado en front).
- ⚠️ **Reglas duras** (Factura ≤ OC; Pago ≤ Factura) deben aplicarse **server-side** y reflejarse en UI (semaforización y bloqueos).

---

## 2) Tareas Prioritarias (para Copilot)
### P0 — Bloqueos/Reglas críticas
1. **Factura ≤ OC**  
   - Implementar validación en el backend al registrar/conciliar facturas **por línea** y por **OC total**.  
   - Responder **422** con detalle y guardar **flag** (`invoice_over_po`) para UI.
2. **Pago ≤ Factura**  
   - En confirmación de conciliación: validar **saldo de factura** antes de aplicar pago.  
   - **422** si excede. Flag `overpaid` para UI.
3. **OC ≤ Presupuesto (PC)**  
   - Al aprobar OC: comprobar que **OC_acum + OC_nueva ≤ PC** (por proyecto o por partida si aplica).  
   - Si excede, exigir **aprobación** con motivo y rol (flag `exceeds_budget`).

### P1 — UI de Control Financiero
4. **Página /proyectos/:id/control**  
   - Consumir `/api/control_financiero/resumen`.  
   - **KPICards**: PC, Comprometido (OC), (en etapa 2: Facturado, Pagado), Disponibles (Conservador/Real).  
   - **Barras**: Waterfall (PC → OC → Facturado → Pagado).  
   - **Semáforos**: `exceeds_budget`, `invoice_over_po`, `overpaid`.  
   - **Drill-down**: Partida → OC → Facturas → Pagos.
5. **Lista /proyectos**  
   - Añadir columnas `%OC/PC`, `%Facturado/PC`, `%Pagado/Facturado` con chips (✔/⏳/⚠).

### P2 — Robustez & Gobernanza
6. **Aliases de proyectos**  
   - Tabla `project_aliases` + endpoint `/api/aliases/project` (upsert) para emparejar nombres (OC vs Presupuesto).  
   - Normalizar nombres (lower, sin tildes) en joins.
7. **Preflight y observabilidad**  
   - Script `tools/preflight.sh` que valide **puertos**, `/api/status`, **existencia de vistas**, y latencia < 500ms.  
   - Logging de cálculos de control (INFO) y violaciones (WARN/ERROR).

---

## 3) Instrucciones concretas (paso a paso)

### 3.1 Backend (Flask, :5555)
- **Agregar validaciones** (si no existen) en las rutas de factura/pago:  
  - *Factura ≤ OC*: agrupar por `po_number` y/o `order_line_id`.  
  - *Pago ≤ Factura*: verificar saldo factura en conciliación.  
  - Responder 422 con payload:  
    ```json
    {
      "error": "invoice_over_po",
      "po_number": "PO-123",
      "allowed_remaining": 1000000,
      "attempted": 1200000
    }
    ```
- **Exponer control financiero** (si aún no trae todo):  
  - `budget_cost` desde `v_presupuesto_totales` (PC real si existe; **fallback** 1.25× solo si no hay PC).  
  - `committed` desde `purchase_orders_unified` filtrando estados `approved/closed`.  
  - *(Etapa 2)* `invoiced` desde `v_facturas_compra` y `paid` desde `v_cartola_bancaria`.  
  - Derivados: `available_conservative = PC - OC`, `available_real = PC - AP`.

**Pseudocódigo de respuesta** `/api/projects/control`:
```python
return {
  "projects": [ {
    "project_name": name,
    "budget_cost": pc_total,
    "committed": committed,
    "invoiced": invoiced,
    "paid": paid,
    "available_conservative": pc_total - committed,
    "available_real": pc_total - invoiced,
    "flags": flags_for(name)
  } for name in project_names ],
  "meta": {"schema_version":"1.1","sources":[
    "v_presupuesto_totales","purchase_orders_unified","v_facturas_compra","v_cartola_bancaria"
  ]}
}
```

### 3.2 Frontend (Next.js, :3001)
- **Cliente**: `frontend/lib/api.ts` → agregar `getControlFinanciero()` que consuma `/api/control_financiero/resumen` o `/api/projects/control`.  
- **Página**: `frontend/app/proyectos/[id]/control/page.tsx`  
  - **KPICards** (PC, OC, AP, Paid, DispC, DispR), **ProgressBars** (apiladas) y **Badges** por flags.  
  - Tabla árbol Capítulo/Partida (si el backend expone detalle).
- **Diseño**: seguir **Estrategia Visual** (Inter, lime #84CC16, radius 12, **sin sombras**, bordes 1px, fondos planos).

### 3.3 DB/ETL
- Ejecutar/confirmar **vistas** de presupuesto y finanzas.  
- Si no existe, crear `project_aliases` + vista de nombres normalizados.  
- Mantener **idempotencia** e **integridad** (Ley BD): RUT válido, índices anti-duplicados, staging/auditoría si procede.

---

## 4) Comandos de verificación

```bash
# Backend en pie y DB conectada
curl -s http://localhost:5555/api/status | jq

# Resumen de control financiero
curl -s http://localhost:5555/api/control_financiero/resumen | jq

# Proyectos (meta incluida)
curl -s 'http://localhost:5555/api/projects_v2?with_meta=1' | jq

# Alias de proyectos
curl -s -X POST http://localhost:5555/api/aliases/project   -H 'Content-Type: application/json'   -d '{"from":"Proyecto X Excel","to":"Proyecto X ERP"}' | jq
```

---

## 5) Riesgos y mitigación
- **Mismatch de nombres** (OC vs Presupuesto): usar `project_aliases` + normalización; opcional: asistente de similitud.  
- **Datos crudos en producción**: prohibido por Ley BD → exponer **vistas canónicas** y consumirlas desde API.  
- **Latencias**: si `/api/projects/control` > 500ms, considerar **vistas materializadas** o caché temporal (5-10 min).

---

## 6) Roadmap sugerido
1. **(Hoy)** Validaciones duras + UI de Control (PC/OC/DispC).  
2. **(Próxima iteración)** Integrar `invoiced` y `paid` (vistas canónicas) + semáforos completos.  
3. **(Luego)** Panel de excepciones (Factura sin OC, Pago sin Factura), retenciones/garantías, avances físicos (devengado).

---

## 7) Changelog (historial de esta revisión)
- 2025-09-14 20:22:30 — Creación del informe vivo, verificados puertos/endpoints/tools; definidos P0/P1/P2 y pasos de implementación.

---

## 8) Anexos útiles
- **Colección Postman** (si no la tienes a mano): `ofitec_postman_collection.json` (GET control, GET ledger, POST alias).  
- **SQL extras SQLite** (aliases + vistas auxiliares): `ofitec_sqlite_extras.sql`.

---

## Actualización 2025-09-14 20:31:10

### Hallazgos adicionales (automáticos)

- **Front consume /api/control_financiero/resumen en UI**: No (no se detectó referencia en el front)
- **Validaciones duras en backend (flags invoice_over_po/overpaid/exceeds_budget)**: Se encontraron referencias
- **Tests backend/ frontend**: Python tests: True • TS tests: True
- **OpenAPI/Swagger**: No
- **Migraciones (Alembic/others)**: No
- **CI (GitHub Actions)**: Sí
- **Pre-commit hooks**: No
- **Linters/formatters**: ESLint: False • Prettier: False • Flake8/Black: False
- **.env / .env.sample**: .env: False • .env.sample: False
- **Docker/Compose**: Dockerfile: True • Compose: True
- **backend/server.py tamaño (líneas)**: 2332

### Faltantes y mejoras prioritarias

- Cablear **UI** para consumir `/api/control_financiero/resumen` (tabla, KPIs, semáforos).
- Publicar **OpenAPI** (YAML/JSON) para los endpoints: descubrimiento y contrato fuerte.
- Incorporar **migraciones** (Alembic o similar) para DB y vistas canónicas.
- Añadir **pre-commit** con black/flake8/isort + eslint/prettier.
- Publicar **.env.sample** sin secretos y documentar variables.

### Sugerencias creativas (prácticas de vanguardia)

- **Versionado de presupuestos**: mantener histórico por versión (aprobación, fecha, autor) y comparar versiones (diff por capítulo/partida).
- **Escenarios y forecasting**: simular escenarios (±% costos, atrasos) y proyectar *Disponible Real* con *Earned Value* (CPI/SPI).
- **Análisis de proveedores**: KPIs de performance (lead time, desvío de precio, % backorder, compliance de documentos).
- **Anomalía y fraude light**: heurísticas para detectar facturas fuera de rango, pagos duplicados, IC de precio por insumo.
- **Multimoneda e índices**: capa de conversión (FX/UF) para consolidar PC/OC/AP/Pagos en moneda base del proyecto.
- **Materialized views / cache**: refresco programado para `/api/projects/control` si supera 500ms con datos grandes.
- **Workflows maker-checker**: aprobación en dos pasos para exceder PC o modificar OC críticas (bitácora robusta).
- **Data lineage**: trazabilidad desde **Pago → Factura → OC → Partida → Capítulo → Presupuesto → Proyecto** (UI con breadcrumbs).
- **Plantillas de importación auto-aprendibles**: persistir decisiones de mapping por cliente/proveedor para acelerar próximos imports.
- **OpenAPI + SDK**: generar cliente TypeScript/Python directamente desde OpenAPI para minimizar errores de integración.

### Plan por sprints (2 semanas)

**Sprint 1 (P0-P1)**
- Validaciones server-side (Factura≤OC, Pago≤Factura) + flags y códigos 422.
- UI de Control: KPIs (PC, OC, DispC) + semáforos y drill-down básico.
- OpenAPI inicial + pre-commit + CI con linters y tests mínimos.

**Sprint 2 (P1-P2)**
- Integrar Facturado y Pagado (vistas canónicas) con UI y panel de excepciones.
- Aliases de proyectos (tabla + endpoint) + normalización.
- Docker/Compose + script preflight (puertos, health, vistas, latencias).
