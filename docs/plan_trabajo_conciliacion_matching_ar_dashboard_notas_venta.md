# Plan de Trabajo Ofitec – Conciliación, Matching AP/AR, Dashboard CEO y Notas de Venta

Fecha: 2025-09-20
Estado Base: Implementaciones core operativas (AP Matching, AR Mapping, vistas financieras, logging estructurado y métricas técnicas). Faltan capas de auditoría, correlativos, feedback de calidad y optimizaciones avanzadas.

---
## 1. Resumen Ejecutivo

Se dispone de la infraestructura principal: matching AP con tolerancias jerárquicas, heurísticas AR→Proyecto, vistas canónicas financieras, endpoint CEO básico y motor de conciliación fuzzy. Para consolidar “gobernanza + inteligencia iterativa” faltan: (a) auditoría formal y maker–checker, (b) métricas de calidad (precision/recall, acceptance), (c) correlativo y auditoría de Notas de Venta, (d) importadores y enriquecimientos que alimenten dashboards, (e) optimizaciones avanzadas (split/merge, aprendizaje adaptativo).

---
 
## 2. Gap Matrix (Síntesis)

| Área | Componente | Estado | Comentario |
|------|------------|--------|------------|
| Conciliación | Motor fuzzy (amount/vendor/date) | Implementado | `backend/reconcile_engine.py` |
| Conciliación | Feedback / training events | Faltante | No tabla de eventos ni endpoint de aceptación |
| Conciliación | Alias learning continuo | Parcial | Uso de `recon_aliases` pero sin alta automática |
| Conciliación | Métricas precisión@k / recall | Faltante | Solo métricas técnicas (latencias, drop) |
| Conciliación | Maker–checker + hash chain | Faltante | No estados approval ni firmas |
| Conciliación | Split/Merge multi-documento | Faltante | No subset-sum aplicado en conciliación |
| AP Matching | Tablas + endpoints core | Implementado | `_ensure_tables` y endpoints v2 |
| AP Matching | 3-way profundo | Parcial | Usa vistas si existen; fallback superficial |
| AP Matching | Pesos dinámicos aplicados | Parcial | Pesos leídos pero no usados en scoring principal |
| AP Matching | Learning adaptativo | Faltante | No ajuste de pesos por eventos |
| AP Matching | Métricas calidad | Faltante | No counters precision/coverage |
| AR Mapping | Heurísticas multi-fuente + auto_assign | Implementado | `api_ar_map.py` |
| AR Mapping | Importador Chipax AR | Faltante | Script no hallado (`tools/import_chipax_ar.py`) |
| AR Mapping | Métricas coverage / acceptance | Faltante | No endpoint resumen |
| Dashboard | Script builder + endpoint | Parcial | Divergencias de campos, faltan diagnostics completos |
| Notas de Venta | Tabla básica + emisión factura | Implementado | En `ep_api._ensure_schema` |
| Notas de Venta | Correlativo anual + aprobación + auditoría | Faltante | Falta sales_note_audit / note_number secuencial |
| Notas de Venta | pdf_hash / integridad | Faltante | No campo ni cálculo |
| Notas de Venta | Estados completos (draft→approved→issued) | Parcial | Falta paso approved y transición formal |
| Gobierno | Maker–checker global | Faltante | Ningún flujo con aprobación dual |
| Gobierno | KPIs negocio (acceptance, coverage) | Faltante | Necesario para iteración de ML |

---
 
## 3. Roadmap Propuesto

### Sprint 1 (Quick Wins)

1. Notas de Venta: correlativo anual (`note_number`), sales_note_audit, endpoint de aprobación.
2. CEO Overview: alinear campos con builder + agregar diagnostics mínimos.
3. Importador AR Chipax: script `tools/import_chipax_ar.py` (idempotente).
4. Endpoint métricas matching inicial: `/api/metrics/matching_summary` (AP y AR) con counts y aceptación.
5. Centralizar utilidades RUT (`backend/utils/chile.py`).

### Sprint 2 (Refinamiento)

1. AP Matching: aplicar pesos configurables al cálculo de `confidence`.
2. Conciliación: endpoint feedback (accept/reject) + tabla recon_match_events.
3. AR Mapping: alias auto-learning al confirmar reglas / auto_assign.
4. Exponer métricas p@1, p@5 provisionales (AP y AR) según eventos.
5. Normalizar/estandarizar payload CEO (working_cap placeholders).

### Sprint 3 (Governance & Data Quality)

1. Maker–checker inicial para sales_notes y ap-match confirm.
2. pdf_hash + emitted_at + approved_* (IP, UA, user) en sales_notes.
3. Dashboard: working_cap + backlog mínimo (sumas aging + PO totals).
4. Recon: registrar timestamps y usuario en aprobaciones / feedback.

### Sprint 4 (Inteligencia Avanzada)

1. Split/Merge conciliación (subset-sum multi-candidato) y AP matching combinatorio mejorado.
2. Re-entrenamiento adaptativo de pesos (batch diario) usando eventos aceptados.
3. Métricas Prometheus de calidad (acceptance_rate, auto_assign_precision, mapping_coverage).
4. Panel /api/metrics detallado (series históricas si snapshot diario).

### Sprint 5 (Auditoría Criptográfica & 3-Way Profundo)

1. Hash chain en sales_note_audit y ap_match_events.
2. Maker–checker extendido a conciliación.
3. 3-Way deep (receipts vs PO vs invoice) con vistas expandidas.
4. Precision/Recall históricos + export CSV para análisis.

---
 
## 4. Detalle Técnico – Sprint 1

### 4.1 Notas de Venta

- ALTER TABLE sales_notes: add emitted_at TEXT, approved_at TEXT, approved_by TEXT, approved_ip TEXT, approved_ua TEXT, pdf_hash TEXT.
- Crear tabla sales_note_audit(id PK, sales_note_id, action, actor, ip, user_agent, payload_json, created_at DEFAULT CURRENT_TIMESTAMP, hash_prev, hash_curr).
- Secuencia anual: SELECT MAX(CAST(substr(note_number,1,3) AS INT)) WHERE substr(note_number,5,4)= (AÑO ACTUAL); genera `f"{seq:03d}-{YEAR}"`.
- Endpoint POST /api/sales-notes/{id}/approve: valida draft, asigna correlativo y registra audit.

### 4.2 CEO Overview

- Unificar campos con builder: incluir diagnostics (has_sales_invoices, has_budgets, po_total) y placeholders working_cap/backlog.
- Tests de contrato ligero: snapshot clave de JSON.

### 4.3 Importador AR

- Script: lee CSV Chipax → inserta/actualiza sales_invoices (UPSERT por invoice_number+customer_rut+issue_date). Limpia montos y normaliza RUT.
- Opcional: generar vistas llamando a `create_finance_views.py` tras carga.

### 4.4 Métricas Matching Iniciales

- Tabla match_metrics_snapshots (date, ap_events_total, ap_events_accepted, ar_map_events, auto_assign_success, created_at).
- Endpoint GET /api/metrics/matching_summary recalcula on-demand si snapshot < 15 min.

### 4.5 Utilidades RUT

- Extraer `_rut_normalize` a `backend/utils/chile.py` + agregar `rut_is_valid` (reutilizable para futuras validaciones).

---
 
## 5. Consideraciones de Diseño

- Idempotencia: scripts de migración defensivos (IF EXISTS / PRAGMA checks) para no romper BD existentes.
- Backfill: al crear auditoría de sales_notes, insertar fila inicial tipo seed (action='snapshot').
- Performance: subset-sum avanzado diferir hasta Sprint 4 para evitar over-engineering temprano.
- Observabilidad: agregar contadores Prometheus desde Sprint 2 (prefijo ofitec_matching_*).

---
 
## 6. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|-----------|
| Falta de datos AR reales limita dashboard | Métricas vacías | Importador AR temprano (Sprint 1) |
| Migraciones CRUD en producción SQLite | Posible lock prolongado | ALTERs pequeños + vacuum opcional off-peak |
| Crecimiento ap_match_events | Bloat | Índices + snapshot métricas agregadas |
| Subset-sum costoso | Latencia API | Precomputar greedy y ofrecer botón "optimizar" (Sprint 4) |
| Hash chain inconsistente por errores | Auditoría inválida | Validación integridad en test + fallback disable if corrupt |

---
 
## 7. KPIs a Introducir

- Sprint 2: ap_match_p_at_1, ar_map_auto_assign_success_rate
- Sprint 3: sales_notes_approval_lag (tiempo draft→approved)
- Sprint 4: reconciliation_p_at_1, reconciliation_avg_suggestions
- Sprint 5: maker_checker_violations_detected, hash_chain_valid (gauge)

---
 
## 8. Estimación (Alta Nivel)

| Sprint | Duración Estimada | Riesgo Global |
|--------|-------------------|---------------|
| 1 | 1-1.5 semanas | Bajo |
| 2 | 1-2 semanas | Medio |
| 3 | 2 semanas | Medio |
| 4 | 2-3 semanas | Alto |
| 5 | 2-3 semanas | Alto |

---
 
## 9. Next Immediate Actions (al aprobar este plan)

1. Implementar migraciones sales_notes (nuevas columnas) + tabla audit.
2. Endpoint approve + correlativo + test básico.
3. Ajustar /api/ceo/overview para incluir diagnostics alineados.
4. Esqueleto importador AR + docs de uso.
5. Endpoint /api/metrics/matching_summary (conteos simples).

---
 
## 10. Aprobación

Marcar este documento como "baseline" (commit) y crear issues por Sprint:

- Label: sprint-1, area:ventas, area:matching, area:conciliacion, area:notas-venta.

---
 
## 11. Apéndice: Referencias de Código Actual

- AP Matching: `backend/api_ap_match.py`
- AR Mapping: `backend/api_ar_map.py`
- AR Invoices List: `backend/api_sales_invoices.py`
- Vistas Finanzas: `tools/create_finance_views.py`
- CEO Overview: `backend/server.py` (`api_ceo_overview`)
- Notas de Venta: `backend/ep_api.py` (sales_notes)
- Conciliación fuzzy: `backend/reconcile_engine.py`

---
Fin del documento.
