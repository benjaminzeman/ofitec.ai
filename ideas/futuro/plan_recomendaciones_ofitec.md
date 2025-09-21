# Plan de Recomendaciones Ofitec.ai (basado en ZIP)

**Fecha:** 2025-09-17  
**Ámbito:** Monorepo Next.js 14 (frontend) + Flask (backend) + docker-compose + microservicio `services/conciliacion_bancaria` + SQLite local.

---

## 1) Resumen ejecutivo
El desarrollo es **funcional y útil** para una constructora. La innovación proviene de la integración vertical (obra/finanzas/conciliación/IA). Para pasar a un producto listo para producción y elevar el “wow” del dashboard, se recomiendan mejoras en **DB**, **API**, **observabilidad**, **conciliación híbrida** y **UX consistente DeFi**.

---

## 2) Hallazgos del ZIP (clave para priorizar)
- **DB:** SQLite en `data/chipax_data.db` (ok dev). No hay Postgres ni migraciones (Alembic).  
- **Backend Flask:** endpoints y server básicos; falta OpenAPI y tests.  
- **Frontend Next.js:** estructura limpia; no se ve design system centralizado ni SWR/React Query.  
- **Docker:** compose frontend+backend; faltan healthchecks y servicios de observabilidad.  
- **Microservicio conciliación:** existe base en `services/conciliacion_bancaria` (falta explicabilidad/score).  
- **CI/CD:** no hay workflows activos.  
- **Seguridad:** CORS y secrets por revisar; rate-limiting no implementado.

---

## 3) Recomendaciones priorizadas

### 3.1 Corto plazo (0–4 semanas)
1. **DB a Postgres** (mantén SQLite para dev):  
   - `docker-compose.override.yml` con `postgres` y volumen.  
   - Var `DATABASE_URL=postgresql+psycopg2://...`.  
   - Script de **seeds** (proyectos demo, movimientos bancarios de muestra).
2. **Healthchecks + /api/health**:  
   - Backend: `GET /api/health -> {"status":"ok"}`.  
   - Compose: `healthcheck` para frontend y backend.
3. **CI/CD GitHub Actions** (lint + tests + build):  
   - Backend: `pytest`, `flake8`.  
   - Frontend: `npm ci`, `lint`, `build`.
4. **Seguridad básica**:  
   - **CORS** por entorno (dev/prod).  
   - **Flask-Limiter** en endpoints sensibles.  
   - `.env.example` consolidado (sin secretos reales).

### 3.2 Mediano plazo (1–3 meses)
5. **API versionada y con contrato**:  
   - ` /api/v1/...` + documentación (Swagger/OpenAPI con Pydantic/Flask-OpenAPI).  
   - Normalizar respuestas (DTOs) y errores.
6. **Conciliación híbrida v2**:  
   - Reglas determinísticas (monto/fecha/glosa normalizada) + **fuzzy** (`rapidfuzz`).  
   - **Explicabilidad**: `{matched_by: rule|fuzzy, score, detalles}`.  
   - **Feedback** del usuario para aprendizaje (whitelist/blacklist y ajuste de pesos).
7. **Observabilidad**:  
   - Prometheus + Grafana en compose override.  
   - Métricas clave: `% conciliado`, `match_rate`, `aging_no_conciliado`, latencias API, errores por endpoint.
8. **UX/Design System**:  
   - Carpeta `/frontend/design/` con **tokens** (colores, tipografías, spacing) y componentes base (KpiCard, Trend, Table).  
   - **SWR/React Query** para cache/revalidación.

### 3.3 Largo plazo (3–6 meses)
9. **IA & búsqueda semántica**:  
   - Servicio `ai_bridge` independiente (si no existe aún).  
   - `pgvector` para glosas/documentos y ranking de similitud.  
   - Modelos de riesgo/plazo con features de avances/HH.
10. **Seguridad/Compliance**:  
   - Gestión de secretos (env en prod), auditoría de conciliación, logs JSON.

---

## 4) Dashboard CEO/Operativo (en línea con lo existente)
- **CEO (5–6 KPIs):** avance ponderado, margen proyectado %, cash 30/60/90, riesgos críticos, top desviaciones.  
- **Operativo:** productividad HH, avance diario/semanal, incidencias SLA, OC vs consumo, % conciliado del mes.  
- **Accionabilidad:** drill‑down desde cada card; estados vacíos y skeletons.

---

## 5) Tareas concretas (2 semanas)
**Semana 1**  
- `docker-compose.override.yml` con Postgres + healthchecks.  
- Endpoint `GET /api/health`.  
- `.env.example` consolidado.  
- CI/CD mínimo activo.

**Semana 2**  
- Pipeline conciliación v2 (reglas + fuzzy + explicabilidad).  
- 3 KPIs en frontend con SWR (mock o DB): `% conciliado mes`, `match_rate`, `aging`.  
- 8–12 tests (backend+frontend).

---

## 6) Cambios en repo (propuestos)
- `infra/docker-compose.override.yml` → Postgres, Prometheus, Grafana.  
- `backend/app/health.py` → blueprint health.  
- `backend/app/reconciliation/` → `rules.py`, `fuzzy.py`, `service.py`, `schemas.py`.  
- `backend/app/observability/metrics.py` → export Prometheus (si aplicas).  
- `frontend/design/` → tokens, components base.  
- `frontend/app/ceo/page.tsx` y `frontend/app/operativo/page.tsx` → vistas claras.

---

## 7) Riesgos y mitigaciones
- **Riesgo**: complejidad al migrar DB → **Mitigación**: script de ETL + entorno paralelo (SQLite en dev).  
- **Riesgo**: latencia en fuzzy/ML → **Mitigación**: pre‑normalización de glosas y cache resultados recientes.  
- **Riesgo**: inconsistencias UX → **Mitigación**: Design System y componentes reutilizables.

---

## 8) Métricas de éxito (técnicas)
- **% conciliado mensual** y **match_rate** > 90% en 2º mes.  
- **TTFR** (tiempo en ver primer dashboard) < 2 min tras login.  
- **Errores 5xx** < 0.5% por semana.  
- **Coverage tests** ≥ 50% en 6 semanas.

---

## 9) Anexos (variables de entorno recomendadas)
- `NEXT_PUBLIC_API_BASE`, `FLASK_ENV`, `SECRET_KEY`, `CORS_ALLOW_ORIGIN`, `DATABASE_URL`, `LOG_LEVEL`.  
- Integraciones: `WHATSAPP_*`, `CHIPAX_*`.  
- Producción: dominios permitidos en CORS, secretos vía variables del entorno.

