# OFITEC — Guía Operativa para Codex  
## Control Financiero de Proyectos (Presupuesto ↔ OC ↔ Facturas ↔ Pagos)  
**Versión:** 1.1 • **Fecha:** 2025-09-14 • **Autoridad:** docs_oficiales • **Cumplimiento:** OBLIGATORIO

> Este documento define, con alto nivel de detalle, cómo debe implementar Codex el control integral de costos de proyecto en Ofitec: desde el Presupuesto (capítulos/partidas), pasando por Órdenes de Compra (OC), Facturas y Pagos (conciliación bancaria).  
> Se alinea con las leyes y estándares oficiales (Base de Datos, Puertos, Mapeo de Datos y Estrategia Visual) ya vigentes en ofitec.ai. 【71†source】【68†source】【69†source】【70†source】【67†source】

---

## 0) Marco normativo (debes cumplirlo)

- **DB canónica y vistas**: usar contratos de datos y vistas canónicas definidos en `DB_CANONICA_Y_VISTAS.md`. Este documento es la **guía maestra** para estructura, relaciones, índices y gobernanza; su cumplimiento es **obligatorio**. 【71†source】  
- **Ley de Base de Datos**: estándares “NASA” (tolerancia cero a pérdida de datos, redundancia triple en validaciones, trazabilidad completa). Reglas inviolables como validación de RUT, anti-duplicados por índices y validaciones multicapa, y consultas autorizadas. 【68†source】  
- **Ley de Puertos**: **Frontend** exclusivo en **:3001** (Next.js) y **Backend API** en **:5555** (Flask/REST). **Separación estricta**: el backend no sirve HTML, el frontend no expone lógica de negocio. Páginas oficiales: `/proyectos`, `/proveedores`, `/finanzas`, `/ordenes`. 【69†source】  
- **Mapeo Datos ↔ Páginas**: seguir `MAPEO_BASE_DATOS_PAGINAS.md` para qué vistas/ tablas alimentan cada página (dashboard ejecutivo, finanzas avanzadas, conciliación inteligente, control de costos por proyecto). 【70†source】  
- **Estrategia Visual**: tokens y componentes base (Inter, lime `#84CC16`, radius 12px, **sin sombras**; KPICards, ProgressBar, Badge, Table) — usar estilos **planos** dark/light. 【67†source】

---

## 1) Conceptos y definiciones (contrato funcional)

> El control se basa en **6 magnitudes** por *Proyecto* y (opcionalmente) por *Capítulo/Partida*.

1. **Presupuesto de Venta (PV)**  
   Ingreso esperado (contrato con mandante). Fuente: tabla/vista de proyectos. **No confundir con costo.** 【70†source】

2. **Presupuesto de Costos (PC)**  
   Costo planificado para ejecutar la obra. Se obtiene desde **Presupuesto de capítulos/partidas** (vista canónica de totales).  
   - Base: `presupuestos / capitulos / partidas`  
   - Vista canónica: `v_presupuesto_totales` (suma de capítulos/partidas)  
   - Cuando exista presupuesto cargado para el proyecto, **PC = v_presupuesto_totales**; si no, se admite **fallback 1.25×** (temporal) solo mientras no exista presupuesto real.

3. **Comprometido (OC)**  
   Suma de **Órdenes de Compra aprobadas** del proyecto. **No debe superar PC** (regla/alerta/bloqueo).

4. **Facturado (AP)**  
   Suma de **facturas de proveedores** asociadas a OCs/partidas. **Nunca puede superar OC** (por línea, por OC y por proyecto).

5. **Pagado (BANK)**  
   Suma de **pagos conciliados** (cartola bancaria) aplicados a facturas. **Nunca puede superar AP**.  
   - Conciliación transversal disponible (motor y API) para vincular pagos ↔ facturas. 【70†source】

6. **Devengado (opcional)**  
   Valorización por avance físico, aunque no esté facturado (útil para cierres contables y gestión de obra).

**Disponibles**:
- **Disponible (Conservador)** = **PC − OC**  → ¿Cuánto puedo seguir comprometiendo?  
- **Disponible (Real)** = **PC − AP**        → ¿Cuánto me queda por facturar contra presupuesto?

---

## 2) Datos y modelo (alineado a lo oficial)

### 2.1 Tablas & fuentes (mínimas)
- **Proyectos**: maestro de proyectos con PV y metadatos. 【70†source】  
- **Presupuestos (detallado)**: `presupuestos / capitulos / partidas` + vista `v_presupuesto_totales` (**PC real**).  
- **Órdenes de compra** (unificadas): `purchase_orders_unified` con **RUT validado** y **anti-duplicados**; **fuente de verdad** para OC/Spent (histórico Zoho integrado). 【68†source】  
- **Proveedores unificados**: `vendors_unified` (normalización de nombres, RUT único). 【68†source】  
- **Facturas de compra**: vista canónica `v_facturas_compra` (proxy de órdenes/recepciones consolidadas). 【70†source】  
- **Cartola bancaria**: vista `v_cartola_bancaria` y servicio de **conciliación inteligente** (matching 1↔N / N↔1). 【70†source】

> **Prohibido** usar datasets “crudos” o no normalizados en producción; solo vistas/tablas canónicas autorizadas. 【68†source】

### 2.2 Integridad (obligatoria)
- **Validación de RUT** Chile para proveedores; nombres normalizados. 【68†source】  
- **Índices anti-duplicados**: (vendor_rut, po_number, po_date, total_amount) en órdenes; `rut_clean` único en proveedores. 【68†source】  
- **Transaccionalidad e idempotencia** en ETL (backup pre-importación, rollback si falla validación). 【68†source】

---

## 3) Vistas canónicas (cálculos listos para API/UI)

> Implementar en el motor preferido (SQLite/Postgres). Adaptar funciones (e.g., `LEAST`→`min`) según SGBD.

### 3.1 Totales de presupuesto
- `v_presupuesto_totales(project_id)`  
  - `total_presupuesto` = Σ(partidas.total) o Σ(partidas.cantidad × precio_unitario)

### 3.2 Comprometido, Facturado, Pagado
- `v_cost_committed(project_name)` → sumar OC aprobadas.  
- `v_cost_invoiced(project_name)`  → sumar monto facturado válido desde `v_facturas_compra`. 【70†source】  
- `v_cost_paid(project_name)`      → sumar pagos conciliados desde `v_cartola_bancaria`. 【70†source】

### 3.3 Disponibles y salud
- `v_available_conservative` = `v_presupuesto_totales.total_presupuesto − v_cost_committed.committed`  
- `v_available_real`         = `v_presupuesto_totales.total_presupuesto − v_cost_invoiced.invoiced`  
- `v_project_health_flags`   → reglas:  
  - `committed > total_presupuesto`  → **Sobrecompromiso** (⚠)  
  - `invoiced > committed`           → **Factura > OC** (⚠)  
  - `paid > invoiced`                → **Pago > Facturado** (⚠)

### 3.4 Compuesta
- `v_control_proyectos` (proyección para API): ver SQL en **Anexo C (SQLite)**.

---

## 4) Reglas de negocio (bloqueos, alertas, excepciones)

1. **OC vs Presupuesto (PC)**  
   - Al **aprobar OC**: validar `OC_acum + OC_nueva ≤ PC`.  
   - Si excede: requerir **aprobación** con motivo y rol autorizado; marcar alerta en `v_project_health_flags`.

2. **Factura vs OC**  
   - Al **registrar factura**: validar por **línea/partida** y por **OC total** que `Factura_acum ≤ OC`.  
   - Si **no existe OC** asociable: enviar a **Bandeja de Excepciones** (*“Factura sin OC”*).

3. **Pago vs Factura**  
   - Al **conciliar pago**: validar `Pago_acum ≤ Facturado_acum`.  
   - Disparar **alerta crítica** si alguien intenta pagar más de lo facturado.

4. **Nombre de proyecto (match)**  
   - Por defecto: case-insensitive y sin tildes.  
   - Adicional: **tabla `project_aliases`** para emparejar Excel/ERP/Zoho.  
   - Modo asistido: proponer matches por **similitud** y guardar el alias escogido.

5. **Monitoreo diario/semana**  
   - Métricas y alertas (duplicados, RUT inválidos, nulos, etc.), con umbrales y severidad definidos en la Ley de BD. 【68†source】

---

## 5) API (Puerto 5555) — contratos

> **Cumple Ley de Puertos**: Backend **solo JSON REST**, nada de HTML. 【69†source】

### 5.1 Endpoints nuevos

- `GET /api/projects/control`  
  **Query:** `?with_meta=1`  
  **Resp (ejemplo):**
  ```json
  {
    "projects": [
      {
        "project_name": "Parque Solar A",
        "budget_cost": 1250000000,
        "committed": 980000000,
        "invoiced": 740000000,
        "paid": 520000000,
        "available_conservative": 270000000,
        "available_real": 510000000,
        "flags": ["OK"]
      }
    ],
    "meta": {
      "schema_version": "1.1",
      "sources": ["v_presupuesto_totales","v_cost_committed","v_cost_invoiced","v_cost_paid"]
    }
  }
  ```

- `GET /api/projects/:id/ledger`  
  **Devuelve**: grilla jerárquica Capítulo → Partida → OC → Facturas → Pagos (IDs para trazabilidad).

- `POST /api/aliases/project`  
  **Body**: `{ "from": "Proyecto X Excel", "to": "Proyecto X ERP" }`  
  **Efecto**: crea/actualiza alias; fuerza recomputo de agregados.

### 5.2 Reglas de respuesta
- **Nunca** mezclar datos crudos ni endpoints no autorizados (ver “APIs prohibidas” en Ley BD). 【68†source】  
- Incluir **`flags[]`** derivados de `v_project_health_flags` (e.g., `"exceeds_budget"`, `"invoice_over_po"`, `"overpaid"`).

---

## 6) Frontend (Puerto 3001) — páginas y componentes

> **Cumple Ley de Puertos** (3001) y **Estrategia Visual** (tokens/componentes). 【69†source】【67†source】

### 6.1 `/proyectos` (lista)
- **KPICards** por proyecto: PC, OC, AP, Pagado, Disponible (Conservador/Real).  
- **Badges**: ✔ OK, ⏳ Atención, ⚠ Riesgo (colores semánticos). 【67†source】  
- **Tabla**: Totales y % (OC/PC, AP/PC, Pagado/AP); buscador, filtros (riesgo, proveedor).

### 6.2 `/proyectos/:id/control` (detalle)
- **Waterfall**: PC → OC → AP → Pagado (barras) + dos “Disponibles”.  
- **Árbol**: Capítulo → Partida con 2 barras por fila: (OC vs PC) y (AP vs PC).  
- **Panel “Excepciones”**: Facturas sin OC, pagos sin factura, duplicados sospechosos.  
- **Detalle OC**: por línea: Qty, PU, Total, Facturado_acum, **Saldo a facturar**, Pagado_acum, **Saldo a pagar**.

### 6.3 Estilo/UI
- **Tokens**: Inter, lime `#84CC16`, radius `12px`, **sin sombras**, bordes 1px, fondos planos; dark por defecto, light alternativo. 【67†source】  
- **Componentes**: `KPICard`, `ProgressBar`, `Badge`, `Table`, `Input`, `Button`. 【67†source】

---

## 7) ETL Presupuestos (robusto y tolerante a formatos)

- **Descubrimiento de encabezados** en primeras filas; **normalización** (tildes, espacios, snake_case).  
- **Matching difuso** de columnas con **modo interactivo** si confianza < umbral (guardar plantilla por cliente/proyecto).  
- **Idempotencia** (hash por fila clave) y **staging opcional** para auditoría.  
- **Validaciones**: campos requeridos, tipos y decimales (coma/punto), duplicados, sumas por capítulo.  
- **Reporte**: filas insertadas/actualizadas/rechazadas (motivo).  
- **Compatibilidad** con vistas canónicas (`v_presupuesto_totales`) al cierre de la importación.

---

## 8) Monitoreo, métricas y alertas

- **Integridad de datos**: registros sin proyecto <5%, sin proveedor 0%, montos 0% nulos/negativos.  
- **Calidad**: RUTs inválidos 0%, fechas futuras 0%.  
- **Duplicados**: exactos 0%, probables <0.1%, sospechosos <0.5%.  
- **Alertas**: crítica/inmediata (pérdida de BD, corrupción, intentos de borrado masivo), alta/media con SLA. 【68†source】

---

## 9) Seguridad, roles, auditoría

- **Roles**: Admin (aprueba presupuesto/OC), Compras (emite OC), Finanzas (facturas/pagos), Lectura.  
- **Bitácora** (quién/cómo/cuándo) para cambios en presupuesto, OC, facturas y pagos.  
- **Excepciones** requieren comentarios y **aprobación** (workflow minimal).

---

## 10) Rendimiento e índices

- Índices para agregaciones por `project_name`, `vendor_rut`, fechas.  
- Índices **únicos** anti-duplicados en órdenes y proveedores (ver Ley BD) — **obligatorio**. 【68†source】

---

## 11) Testing (unitario, integración, e2e)

- **Unitarios**: totales por capítulo/presupuesto = Excel de origen; derivadas (DisponibleC/DisponibleR).  
- **Integración**: match nombres (alias), flujo OC→Factura→Pago con reglas de tope.  
- **E2E**: escena con Factura sin OC, Pago sin Factura, y casos borde (retención, backorder).

---

## 12) Operativa / DevOps

- **Puertos oficiales**: 3001 (frontend), 5555 (API). **NO** levantar front alternos. 【69†source】  
- **Health checks**: `/api/health` (5555), `GET /proyectos` (3001). 【69†source】  
- **Backups** 3-2-1 (local, cloud, offsite) con verificación periódica. 【68†source】

---

## 13) Anexo C — SQL SQLite listo para aplicar

```sql
-- Presupuesto total por proyecto
DROP VIEW IF EXISTS v_presupuesto_totales;
CREATE VIEW v_presupuesto_totales AS
SELECT
  prj.project_name,
  SUM(p.total) AS total_presupuesto
FROM proyectos_presupuestos p
JOIN proyectos prj ON prj.id = p.project_id
GROUP BY prj.project_name;

-- Comprometido (OC aprobadas)
DROP VIEW IF EXISTS v_cost_committed;
CREATE VIEW v_cost_committed AS
SELECT
  oc.zoho_project_name AS project_name,
  SUM(oc.total_amount) AS committed
FROM purchase_orders_unified oc
WHERE oc.status IN ('approved','closed')
GROUP BY oc.zoho_project_name;

-- Facturado (vista canónica)
DROP VIEW IF EXISTS v_cost_invoiced;
CREATE VIEW v_cost_invoiced AS
SELECT
  f.project_name,
  SUM(f.total_amount) AS invoiced
FROM v_facturas_compra f
GROUP BY f.project_name;

-- Pagado (conciliado)
DROP VIEW IF EXISTS v_cost_paid;
CREATE VIEW v_cost_paid AS
SELECT
  c.project_name,
  SUM(c.paid_amount) AS paid
FROM v_cartola_bancaria c
GROUP BY c.project_name;

-- Disponibles y salud
DROP VIEW IF EXISTS v_available;
CREATE VIEW v_available AS
SELECT
  pc.project_name,
  pc.total_presupuesto,
  COALESCE(co.committed,0) AS committed,
  COALESCE(iv.invoiced,0) AS invoiced,
  COALESCE(pd.paid,0) AS paid,
  (pc.total_presupuesto - COALESCE(co.committed,0)) AS available_conservative,
  (pc.total_presupuesto - COALESCE(iv.invoiced,0))  AS available_real
FROM v_presupuesto_totales pc
LEFT JOIN v_cost_committed co ON co.project_name = pc.project_name
LEFT JOIN v_cost_invoiced iv ON iv.project_name = pc.project_name
LEFT JOIN v_cost_paid pd     ON pd.project_name = pc.project_name;

-- Flags de salud
DROP VIEW IF EXISTS v_project_health_flags;
CREATE VIEW v_project_health_flags AS
SELECT
  a.project_name,
  CASE WHEN committed > total_presupuesto THEN 'exceeds_budget' END AS flag1,
  CASE WHEN invoiced  > committed         THEN 'invoice_over_po' END AS flag2,
  CASE WHEN paid      > invoiced          THEN 'overpaid'        END AS flag3
FROM v_available a;
```

---

## 14) Anexo D — cURL rápidos & Postman

### cURL
```bash
# Control financiero (todos)
curl -s http://localhost:5555/api/projects/control?with_meta=1 | jq

# Ledger jerárquico por proyecto
curl -s http://localhost:5555/api/projects/PROYECTO_X/ledger | jq

# Crear alias de proyecto
curl -s -X POST http://localhost:5555/api/aliases/project   -H "Content-Type: application/json"   -d '{"from":"Proyecto X Excel","to":"Proyecto X ERP"}' | jq
```
