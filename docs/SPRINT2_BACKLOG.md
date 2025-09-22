# Sprint 2 Backlog (Propuesto)

Objetivo macro: Capturar feedback explícito y señales de calidad para alimentar métricas (p@k / precisión-recall) y preparar terreno para pesos adaptativos y aprendizaje incremental (AR alias + matching).

Duración sugerida: 1-2 semanas (ajustar según capacidad real). Priorizar vertical "captura de feedback" antes de métricas derivadas.

## 1. Feedback Events (Core)

### 1.1 AR Mapping Feedback

- Endpoint: `POST /api/ar/feedback`
- Payload mínimo: `{ invoice_id, action: 'accept'|'reject', reason?: str }`
- Persistencia: tabla `ar_feedback_events` (`id, created_at, invoice_id, action, reason, source`)
- Validaciones: invoice existente, acción válida, idempotencia opcional (último evento vivo).
- Extensión futura: score previo, proyecto sugerido vs confirmado.

### 1.2 AP Matching Feedback

- Endpoint: `POST /api/ap-match/feedback`
- Payload: `{ event_id, action: 'accept'|'reject', reason?: str }`
- Tabla: `ap_match_feedback` (`id, created_at, event_id, action, reason, source`).
- Link con `ap_match_events` para obtener propuesta original.
- Considerar índice `event_id` + `created_at` para consultas recientes.

### 1.3 Reconciliation Feedback (Opcional en S2 si hay tiempo)

- Endpoint: `POST /api/conciliacion/feedback`
- Usa el ID de la sugerencia / confirmación (o hash de movimiento + documento) para marcar `correcta|incorrecta|missing_link`.
- Tabla: `recon_feedback_events`.

## 2. Métricas Derivadas (p@k y Calidad)

Dependen de flujo de feedback mínimo (al menos algunos eventos accept/reject).

### 2.1 KPIs Iniciales

- `matching_ap_precision_recent`: aceptados / (aceptados + rechazados) últimos N (configurable, default 200).
- `matching_ap_feedback_volume_24h`: conteo feedback AP 24h.
- `matching_ar_precision_recent`: igual para AR.
- Exportación en `/api/matching/metrics/prom` (nuevos gauges) + JSON extendido.

### 2.2 p@k (Top-K) (Preparación)

- Guardar orden original de candidatos (si ya se persiste `candidates_json`, reutilizar).
- Definir función util `precision_at_k(confirms, k)`.
- p@1 y p@3 inicial (si volumen de feedback ≥ threshold mínimo, e.g., 30).

## 3. Adaptive Weights (Scaffolding)

No recalibrar automáticamente aún; sólo preparar estructura.

### 3.1 Tabla de Versionado

- `matching_weight_versions` (`id, created_at, context, weights_json, notes, active`)
- Permite activar/desactivar versiones manualmente.

### 3.2 Endpoint Admin

- `POST /api/matching/weights/activate` `{ version_id }` → marca activo.
- `GET /api/matching/weights/active` → devuelve set actual.
- Validar unicidad de activo.

### 3.3 Cálculo Experimental (Offline)

- Script `tools/recompute_matching_weights.py` que lee feedback + eventos y sugiere ajuste simple (placeholder: aumenta peso de feature con mejor correlación binaria con accept/reject).

## 4. AR Alias Auto-Learning (Incremental)

### 4.1 Captura de Alias

- Al recibir feedback positivo (accept) donde `customer_name` no tiene regla, registrar par candidato en staging `ar_rule_candidates`.

### 4.2 Promoción Temprana

- Script / endpoint `POST /api/ar/promote_candidates` con criterios: frecuencia ≥ M (configurable), ratio aceptación ≥ X%.
- Reutilizar lógica de `promote_ar_rules.py` si posible (refactor a función común interna).

## 5. Governance & Auditoría

### 5.1 Hash Chain Opcional (Scope S2 ?)

- Evaluar reutilización del modelo de `sales_note_audit` para encadenar feedback críticos (matching / AR) produciendo `feedback_audit`.
- Campos: `id, created_at, entity, entity_id, action, prev_hash, hash`.
- Pospuesta si complejiza el ciclo.

### 5.2 Metadata de Origen

- Añadir columna `source` (`manual|api|import|system`) a tablas de feedback para distinguir señales humanas de automáticas.

## 6. Documentación & Tests

- README: nueva subsección Feedback & Calidad.
- Docs: `docs/FEEDBACK_METRICS.md` (si escala).
- Tests unitarios: creación feedback, métricas p@k (calculo sobre fixtures), toggling de versiones de pesos.
- Smoke test: enviar 3 accept / 2 reject y verificar gauges precision recientes.

## 7. Migraciones / DDL

Checklist DDL incremental (SQLite):

```sql
CREATE TABLE IF NOT EXISTS ar_feedback_events (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT (datetime('now')),
  invoice_id INTEGER NOT NULL,
  action TEXT NOT NULL,
  reason TEXT,
  source TEXT
);
CREATE INDEX IF NOT EXISTS idx_ar_feedback_invoice ON ar_feedback_events(invoice_id);

CREATE TABLE IF NOT EXISTS ap_match_feedback (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT (datetime('now')),
  event_id INTEGER NOT NULL,
  action TEXT NOT NULL,
  reason TEXT,
  source TEXT
);
CREATE INDEX IF NOT EXISTS idx_ap_match_feedback_event ON ap_match_feedback(event_id);

-- Opcional conciliación
CREATE TABLE IF NOT EXISTS recon_feedback_events (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT (datetime('now')),
  reconciliation_id INTEGER,
  action TEXT NOT NULL,
  reason TEXT,
  source TEXT
);
CREATE INDEX IF NOT EXISTS idx_recon_feedback_recon ON recon_feedback_events(reconciliation_id);

CREATE TABLE IF NOT EXISTS matching_weight_versions (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT (datetime('now')),
  context TEXT,
  weights_json TEXT NOT NULL,
  notes TEXT,
  active INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_weight_versions_active ON matching_weight_versions(active);

CREATE TABLE IF NOT EXISTS ar_rule_candidates (
  id INTEGER PRIMARY KEY,
  created_at TEXT DEFAULT (datetime('now')),
  customer_name TEXT NOT NULL,
  project_id INTEGER NOT NULL,
  hits INTEGER DEFAULT 1,
  last_seen_at TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_ar_rule_candidates_name_proj ON ar_rule_candidates(customer_name, project_id);
```

## 8. Acceptance Criteria

- [ ] Endpoints feedback AP y AR aceptan payload válido y persisten fila.
- [ ] Métricas de precisión recientes aparecen en `/api/matching/metrics/prom` tras feedback.
- [ ] Tabla `matching_weight_versions` permite activar una versión (exactamente 1 activa) y `GET /active` refleja cambio.
- [ ] Script de recompute genera un JSON de pesos sugeridos (even si es heurístico placeholder).
- [ ] Alias sin regla generan candidates y promoción crea reglas reales (dry run + real).

## 9. Riesgos / Mitigación

| Riesgo | Mitigación |
|--------|-----------|
| Bajo volumen de feedback invalida p@k | Gate: no exponer p@k si n < threshold. |
| Crecimiento excesivo de tablas feedback | Índices y limpieza futura (retención configurable). |
| Sesgo por feedback parcial (solo errores reportados) | Incluir acciones 'accept' y 'reject' desde UI. |
| Activación accidental de pesos experimentales | Endpoint admin exige confirmación (token o flag). |
| Promoción de alias ruidosos | Umbral de hits + ratio aceptación, modo dry run. |

## 10. Fuera de Alcance (S2)

- Serie histórica completa de precisión (queda para S3 con snapshotting)
- Auto-reentrenamiento nocturno sin supervisión
- Integración SII avanzada (salvo soporte actual)
- Maker-Checker extendido más allá de feedback crítico

---

Preparado para iterar: priorizar secciones 1 y 2; restantes pueden solaparse en paralelo si hay tiempo.
