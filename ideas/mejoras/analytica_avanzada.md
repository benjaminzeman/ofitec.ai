# ANALÍTICA AVANZADA — ETL Financiero, Marts, Contratos y Linaje de Datos

> Documento técnico para Copilot — Integrar analítica financiera avanzada en Ofitec.ai (Next.js + Flask + PostgreSQL/DuckDB). Basado en entregas 9–14. Sustituye dependencias Odoo; todo sobre **DB propia** y APIs.

---

## 1) Objetivos
- Construir **ETL financiero** que procese NV, AR/AP, aging y conciliación bancaria.
- Crear **marts** analíticos en PostgreSQL/DuckDB para KPIs: cashflow proyectado, WIP (work in progress), aging histórico, lead times.
- Establecer **contratos de datos** versionados (schemas, validaciones, tests).
- Añadir **linaje y catálogo** (OpenLineage/Marquez) para trazabilidad.
- Automatizar **dashboards pack** (Metabase/Next.js) para CEO y Finanzas.

---

## 2) Arquitectura
```
ETL (Python/Flask jobs) → Staging (Postgres schema staging_*)
   → Transform (dbt-like SQL) → Marts (schema mart_*)
   → Exposición API (/api/v1/analytics/...)
   → Dashboards (Next.js + Metabase opcional)

+ DuckDB (in-process, consultas OLAP rápidas)
+ OpenLineage (tracking jobs, datasets)
```

---

## 3) Modelo de datos analíticos

### 3.1 Tablas Staging (ejemplo)
- `staging_nv` — notas de venta normalizadas.
- `staging_ar` / `staging_ap` — facturas AR/AP con pagos.
- `staging_bank` — movimientos conciliados.

### 3.2 Marts
- `mart_cashflow_forecast`
  - columnas: fecha, proyecto, saldo inicial, ingresos esperados, egresos esperados, saldo proyectado.
- `mart_wip`
  - columnas: proyecto, avance físico, avance financiero, costos incurridos, margen estimado.
- `mart_aging_hist`
  - columnas: cliente, mes, bucket_0_30, bucket_31_60, bucket_61_90, bucket_90p.
- `mart_leadtime`
  - columnas: tipo, promedio_días, p95_días.

---

## 4) ETL (Flask jobs / scripts)
- Jobs programados con Celery/cron.
- Pasos: extract (queries NV/AR/AP/bancos), transform (SQL en schema staging), load (insert en marts).
- Cada job emite evento OpenLineage → Marquez.

### Ejemplo (pseudo-Python)
```python
# backend/app/jobs/etl_cashflow.py
from app.db import session
from datetime import date

def run(period: str):
    # 1. extraer NV y facturas abiertas
    # 2. cruzar con pagos esperados
    # 3. calcular saldo proyectado
    # 4. insertar en mart_cashflow_forecast
    pass
```

---

## 5) Contratos de datos
- Esquema `contracts/` con YAML/JSON que defina columnas esperadas, tipos, restricciones.
- Tests automáticos (pytest):
  - columnas presentes,
  - tipos correctos,
  - valores no nulos en campos clave.
- Al fallar → alerta Slack/Email.

Ejemplo contrato (YAML):
```yaml
name: mart_cashflow_forecast
columns:
  - name: fecha
    type: date
    nullable: false
  - name: saldo_proyectado
    type: numeric
    nullable: false
```

---

## 6) Linaje y catálogo
- Usar **OpenLineage** con **Marquez**:
  - Cada job ETL reporta inputs/outputs.
  - Guardar en `metadata/` + UI Marquez.
- Beneficio: trazabilidad de cada KPI hasta fuente (NV/AR/AP).

---

## 7) Dashboards pack

### 7.1 CEO
- Cards: cashflow proyectado, aging global, avance WIP.
- Serie temporal: saldo proyectado semanal.

### 7.2 Finanzas
- Aging histórico por cliente.
- Lead time de cobro/pago.
- Conciliación: % conciliado vs total.

### 7.3 Operativo
- Proyectos: avance físico vs financiero.
- Costos incurridos vs presupuesto.

**Next.js UI**: páginas `/analytics/cashflow`, `/analytics/wip`, `/analytics/aging`, `/analytics/leadtime`.

**Metabase (opcional)**: usar provisioning YAML para crear dashboards automáticamente.

---

## 8) Seguridad y SLOs
- API `/api/v1/analytics/...` protegida (roles: CEO, Finanzas, PM).
- SLOs de BI: latencia < 5s por consulta, disponibilidad 99%.
- Tests E2E para validar carga dashboards.

---

## 9) Checklist de aceptación
- [ ] ETL jobs corren y llenan marts.
- [ ] Data contracts definidos y validados en CI.
- [ ] Linaje visible en Marquez.
- [ ] Dashboards CEO/Finanzas/Operativo cargan sin error.
- [ ] Latencia consultas < 5s.

---

## 10) Prompts Copilot sugeridos
- "Crea migraciones Alembic para marts mart_cashflow_forecast, mart_wip, mart_aging_hist, mart_leadtime."
- "Implementa job Flask/Celery que calcule mart_cashflow_forecast y reporte a OpenLineage."
- "Genera contratos YAML en contracts/ y tests pytest que los validen contra DB."
- "Construye página Next.js `/analytics/cashflow` con gráfico de saldo proyectado y cards de KPIs."

