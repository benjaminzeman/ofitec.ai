# Guía de Contribución

Esta guía establece el flujo de trabajo, criterios de calidad y convenciones para contribuir al repositorio.

## Tabla de Contenido

- [Filosofía](#filosofía)
- [Branching](#branching)
- [Commits](#commits)
- [Pull Requests](#pull-requests)
- [Revisión de Código](#revisión-de-código)
- [Tests & Cobertura](#tests--cobertura)
- [Observabilidad (Matching & Conciliación)](#observabilidad-matching--conciliación)
- [Métricas Avanzadas AP Matching](#métricas-avanzadas-ap-matching)
- [Alertas & Dashboards](#alertas--dashboards)
- [Variables de Entorno Clave](#variables-de-entorno-clave)
- [Base de Datos & Migraciones](#base-de-datos--migraciones)
- [Checklist Rápida de PR](#checklist-rápida-de-pr)
- [Estilo Frontend](#estilo-frontend)
- [Estilo Backend](#estilo-backend)
- [Performance & Stress](#performance--stress)
- [Flujos Especiales](#flujos-especiales)
- [Futuras Mejores Prácticas (Roadmap)](#futuras-mejores-prácticas-roadmap)

## Filosofía

Iterar rápido, instrumentar temprano y documentar cada métrica que exponga decisiones o riesgos.

Principios:

- Cambios pequeños y observables > refactors gigantes silenciosos.
- Métrica sin interpretación/documentación = deuda.
- Tests cubren invariantes del dominio (montos, estados, tolerancias) y no sólo "happy paths".
- La rama `master` siempre debe poder desplegarse.

## Branching

Flujo simplificado de una sola rama estable: `master`.

Opcional (cuando se agrande el equipo) se pueden usar ramas efímeras `feat/...`, `fix/...` que se eliminan tras merge. Mientras el equipo sea pequeño, commits directos a `master` están permitidos siempre que:

- Tests pasan localmente.
- No se rompen scripts críticos.
- Se actualiza documentación si cambia comportamiento.

## Commits

Formato recomendado (similar a Conventional Commits):

```text
<tipo>(<área>): <resumen conciso>
```

Tipos sugeridos: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore`, `build`, `ci`.

Ejemplos:

- `feat(ap-matching): agrega p99 y stddev de confianza`
- `docs(observability): guía mini endpoint metrics`

Reglas:

- Idioma consistente (actualmente ES para docs, código puede mezclar ES/EN si ya existe).
- Un commit = una intención.
- Evitar commits "wip" (prefiere squash local antes de push si es ruido).

## Pull Requests

Mientras se contribuya directo a `master`, un PR es opcional. Usa PR cuando:

- Cambio afecta múltiples módulos (AP Matching + EP + Frontend).
- Necesitas feedback de diseño.
- Introduces dependencia externa.

Contenido mínimo del PR:

- Resumen del problema + solución.
- Riesgos y mitigaciones (si aplica).
- Notas de métricas nuevas (si expone gauges, histogramas, ratios, etc.).

## Revisión de Código

Criterios de revisión:

- Claridad: nombres expresivos, early returns, mínima anidación innecesaria.
- Invariantes defendidos por tests (si agregas regla de negocio, agrega test que la rompa y luego arregla).
- Observabilidad: ¿existe métrica / log suficiente para diagnosticar un fallo futuro?
- Rendimiento: evitar N+1 en queries y loops innecesarios en ventanas grandes.

## Tests & Cobertura

Ejecutar siempre:

```bash
python -m pytest -q
```

Cobertura mínima sugerida backend: 70% líneas (enforced en CI si se activa input). Añade tests para:

- Cálculo de percentiles / ratios nuevos.
- Transformaciones críticas de montos (rounding, tolerancias).
- Migraciones de esquema.

Marcadores disponibles: `perf`, `stress`.

## Observabilidad (Matching & Conciliación)

- Endpoints Prometheus dedicados: `/api/matching/metrics/prom`, `/api/conciliacion/metrics/prom` (si se habilitan sus flags).
- Formato mini: `/api/matching/metrics/mini` para lecturas ligeras.
- Evitar agregar métricas no documentadas en `docs/guides/MATCHING_GUIDE.md`.

## Métricas Avanzadas AP Matching

Gating por variable `MATCHING_AP_ADVANCED`.

Incluye:

- `confidence_sum`
- Percentiles exactos: `confidence_p50_raw`, `confidence_p95_raw`, `confidence_p99_raw`
- Buckets aproximados: `confidence_p95_bucket`, `confidence_p99_bucket`
- Distribución por buckets: `confidence_bucket_{edge}`
- `confidence_high_ratio` (proporción >= 0.90)
- `confidence_stddev`

Requerimientos al agregar nuevas:

1. Test (presencia + valor no negativo / rango esperado).
2. Documentación (guía + README si afecta onboarding).
3. Panel Grafana (si aporta señal duradera).
4. Regla de alerta (si puede degradarse silenciosamente).

## Alertas & Dashboards

Ubicaciones:

- Dashboards: `docs/observability/grafana_matching_ap_dashboard.json`
- Reglas: `docs/observability/prometheus_rules_matching.yml`

Al agregar una métrica potencialmente SLO-crítica, crear:

- Panel
- Regla (warning / critical si aplica)
- Sección de interpretación

## Variables de Entorno Clave

Matching / AP:

- `MATCHING_AP_ADVANCED` (activa métricas avanzadas)

Conciliación:

- `RECON_PROM_CLIENT`, `RECON_LATENCY_WINDOW_SIZE`, `RECON_LATENCY_SLO_P95`, etc. (ver README sección correspondiente)

Backend generales:

- `DB_PATH`, `PORT`, `CORS_ORIGINS`

## Base de Datos & Migraciones

Scripts relevantes:

- `tools/migrate_ap_match_schema.py`
- `tools/create_finance_views.py`

Política:

- Backup antes de migrar (`scripts/backup_local.ps1`).
- Migrations deben ser idempotentes o defensivas (chequear existencia de tabla/columna antes de crear).

## Checklist Rápida de PR

Antes de solicitar revisión:

- [ ] Tests pasan (`pytest -q`)
- [ ] Cobertura no baja significativamente
- [ ] Docs actualizadas (README / guía específica)
- [ ] Nuevas variables de entorno documentadas
- [ ] Dashboard/alerta agregada (si métrica nueva SLO-ish)
- [ ] Sin prints debug accidentales
- [ ] Commit message claro

## Estilo Frontend

- Formato: `npm run format`
- Lint: `npm run lint`
- Evitar lógica de negocio compleja en componentes; mover a helpers.

## Estilo Backend

- Funciones pequeñas, responsables de una cosa.
- Evitar efectos colaterales ocultos (retornar datos en vez de mutar globales).
- Manejar errores con mensajes accionables (no "Exception" genérico).

## Performance & Stress

Marcadores `perf` / `stress` permiten aislar tests en CI. Si introduces un cambio con riesgo de latencia:

1. Añade medición temporal local.
2. Compara p95 antes/después.
3. Documenta si cambian presupuestos.

## Flujos Especiales

- Promoción de reglas AR: `scripts/promote_ar_rules.ps1` (usar `-DryRun` para validar conteo mínimo).
- Smokes EP / AR ya listados en README.

## Futuras Mejores Prácticas (Roadmap)

- Introducir `RECORDING RULES` para suavizar queries de dashboards.
- Badge de métricas agregadas (ratio alto, stddev) a partir de resultados recientes.
- Automatizar publicación de paneles.

---

Sigue este documento vivo: si algo cambia y no está aquí, se considera deuda técnica documental.
