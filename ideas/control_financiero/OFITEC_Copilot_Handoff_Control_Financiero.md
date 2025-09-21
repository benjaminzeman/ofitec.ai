# OFITEC — Handoff para Copilot
## Control Financiero de Proyectos (alineado a docs_oficiales)
**Fecha:** 2025-09-14 • **Ámbito:** Integrar `ideas/control_financiero` con el proyecto vigente (SQLite + API 5555 + Front 3001)

> Este handoff resume el **estado real** del proyecto tras Codex, y define tareas **claras** para mantener coherencia con docs_oficiales (Ley BD, Puertos, DB Canónica, Estrategia Visual).
> Debe permitirte continuar sin romper nada y con validaciones fuertes.

---

## 1) Estado actual (según última entrega de Codex)
- **Esquema Presupuestos** (SQLite) aplicado: `proyectos`, `presupuestos`, `capitulos`, `partidas` + vistas `v_capitulos_totales`, `v_presupuesto_totales`.
- **Importador tolerante a formatos**: `tools/import_ofitec_budget.py` (XLSX/CSV) con matching difuso y modo interactivo; utiliza `ideas/ofitec_import_templates.json`.
- **API**:
  - `/api/projects_v2?with_meta=1` usa **presupuesto real** desde `v_presupuesto_totales`; **fallback 1.25×** solo si **no** hay presupuesto.
  - **Nuevo** `/api/control_financiero/resumen`: `presupuesto`, `comprometido`(OC), `disponible_conservador = presupuesto − comprometido`.
- **Frontend**:
  - `frontend/lib/api.ts` preserva `orders` y `providers` (arregla “0 órdenes • 0 proveedores”).
  - Página **/proyectos** muestra Presupuesto/Gastado/Disponible con presupuesto real si existe.

---

## 2) Reglas y convenciones (no romper)
- **Ley de Puertos**: Front en **:3001**, API en **:5555** (JSON only).
- **Ley de BD**: no usar datasets crudos en producción; usar **vistas/tablas canónicas**; validaciones anti-duplicados y RUT.
- **DB Canónica**: si agregas vistas/tablas, documenta en `DB_CANONICA_Y_VISTAS.md`.
- **Estrategia Visual**: Inter, lime #84CC16, radius 12px, **sin sombras**, componentes KPICard/Progress/Badge/Table.

---

## 3) Tareas inmediatas (Copilot)
### 3.1 Aliasing de proyectos (evitar mismatch nombres)
- Crear tabla **`project_aliases`** (ver SQL en `ofitec_sqlite_extras.sql`).
- Agregar endpoint **POST** `/api/aliases/project` con body `{from, to}`.
- Resolver en API: al computar agregados por proyecto, intentar match por:
  1) igualdad normalizada (lower + sin tildes), luego
  2) alias explícito (tabla), y opcionalmente
  3) similitud (si se implementa un asistente adicional).

### 3.2 Vista de compromiso (OC) y presupuesto (PC)
- Si **ya existe** `v_presupuesto_totales`, conservarla.
- Añadir vista **`v_po_committed`**: suma de OC **aprobadas/cerradas** por proyecto.
- (Opcional) Vista **`v_control_financiero_resumen`** que combine PC y OC para el **Disponible Conservador**.

### 3.3 API de Control
- Endpoint **GET** `/api/projects/control` (o mantener `/api/control_financiero/resumen` si ya está) que exponga:
  - `budget_cost`, `committed`, `available_conservative` y flags base: `exceeds_budget`.
- Mantener el **fallback 1.25×** solo cuando **no** exista presupuesto, en el **backend** (no en SQL).

### 3.4 UI (3001)
- En **/proyectos** y/o nueva **/proyectos/:id/control**:
  - KPICards: **PC**, **OC**, **Disponible Conservador**; (dejar placeholders para AP/Pagado).
  - Barras (Waterfall) PC → OC; semáforo (✔/⚠) si `OC > PC`.

---

## 4) Validaciones duras (deben bloquear o exigir aprobación)
- **OC ≤ PC** (por proyecto y, cuando sea posible, por capítulo/partida).
- **Factura ≤ OC** (fase 2 al integrar facturas).
- **Pago ≤ Factura** (fase 2 al integrar cartola).

---

## 5) SQL listo (SQLite) — ver `ofitec_sqlite_extras.sql`
Incluye:
- `project_aliases`
- `v_project_names_norm` (normaliza nombres sin tildes y en minúsculas; ideal para JOIN por nombre)
- `v_po_committed` (suma OC aprobadas/cerradas)
- `v_control_financiero_resumen` (PC, OC, DisponibleC) *sin fallback* (el fallback vive en API)

> **Nota:** Si alguna tabla/vista nombrada no existe en tu base, adapta los nombres en el SQL o aplica la lógica en API.

---

## 6) Contratos API (referencia rápida)
### GET `/api/projects/control`
**Resp:** 
```json
{
  "projects": [
    {
      "project_name": "Proyecto X",
      "budget_cost": 1000000,
      "committed": 820000,
      "available_conservative": 180000,
      "flags": []
    }
  ],
  "meta": {"schema_version":"1.1","sources":["v_presupuesto_totales","v_po_committed"]}
}
```

### POST `/api/aliases/project`
**Req:** `{"from":"Proyecto X Excel","to":"Proyecto X ERP"}` → Upsert

---

## 7) Checklist de entrega
- [ ] Ejecutar `ofitec_sqlite_extras.sql` (o versionar migración).
- [ ] Exponer/ajustar endpoints (`/api/projects/control`, `/api/aliases/project`).
- [ ] Conectar UI 3001 (KPICards + barras PC/OC).
- [ ] Documentar en `DB_CANONICA_Y_VISTAS.md` y `README.md`.
- [ ] Tests: 3 proyectos (uno con presupuesto, uno sin → fallback, uno excedido OC).

---

## 8) Riesgos y mitigaciones
- **Nombres diferentes entre fuentes** → usar `project_aliases` y normalización; revisar que el JOIN por nombres normalizados esté encapsulado en una vista o en la capa API.
- **Esquemas divergentes** (nombres de tablas/vistas) → mantener una **capa de compatibilidad** en la API (queries condicionales por existencia de columna/tabla).
- **Datos crudos** en producción → prohibido por Ley BD; si se requiere, montar **vistas canónicas** primero.

---

## 9) Próxima etapa (cuando haya fuentes de AP/Pagos)
- Añadir vistas `v_cost_invoiced` (facturas) y `v_cost_paid` (banco conciliado), con flags `invoice_over_po` y `overpaid`.
- UI: dual bars por capítulo/partida (AP/PC y Pagado/AP), panel de excepciones (Factura sin OC, Pago sin Factura).
