# OFITEC — **Landings por Módulo** (Proyectos y Finanzas)
> Qué debe ver el usuario al entrar a **Proyectos** y a **Finanzas**. Diseño **Dashboard & KPI** primero (no listados), con acciones de alto impacto y contratos de datos. Alineado a *docs_oficiales* (Ley de Puertos 3001/5555, DB Canónica por vistas `v_*`, Estrategia Visual sin emojis) y a lo ya definido en *Control Financiero 360*, *Conciliación* y *CEO Dashboard*.

---

## 0) Principios
- **Signal over noise**: mostrar métricas que cambian decisiones, no contadores de actividad.
- **Panorama → Diagnóstico → Acción** en 10–20 s.
- **Explicabilidad**: cada KPI con “¿Por qué?” (fórmula + vista origen).
- **Role-aware**: aterrizajes distintos por módulo/rol, pero patrones comunes (chips, mini‑sparklines, CTA único por tarjeta).
- **Ley de Puertos**: UI 3001 consume API 5555; nada directo a la DB desde el frontend.

---

## 1) Módulo **Proyectos** — Landing: *Dashboard & KPI*
**Ruta por defecto**: `/proyectos/overview`  
**Subsecciones**: `Overview` (este dashboard) • `Lista` (tabla completa) • `Control Financiero` (detalle por proyecto) • `Subcontratos` • `Planning`.

### 1.1 KPIs de Portafolio (arriba)
- **Proyectos activos** `N`
- **PC Total** (Presupuesto de Costos) y **Comprometido (PO)** con **Disponible = PC − PO**  
- **Ejecución**: `GRN / AP facturado / AP pagado` (mini‑barra apilada)  
- **Salud**: % **En presupuesto** / **> Presupuesto** / **Sin presupuesto**  
- **Riesgo portafolio** (0–100) con top‑3 razones.

### 1.2 Diagnóstico (gráficos compactos)
- **Embudo de costos** PC → PO → GRN → AP → Pagado (apilado)  
- **Distribución de riesgo** por proyecto (heatmap o barras: `PO/PC`, `gasto vs avance`, `3‑way`)
- **WIP ventas (EP)**: EP aprobados sin facturar, EP en revisión.

### 1.3 Excepciones & Acciones (lista priorizada)
Items con **CTA** directo, ordenados por impacto:  
- *“8 proyectos sin presupuesto cargado”* → Importar presupuesto  
- *“3 OC superan el presupuesto”* → Revisar/ajustar  
- *“5 facturas > recepción (3‑way)”* → Abrir panel 3‑way  
- *“6 EP aprobados sin FV”* → Generar factura de venta  
- *“N facturas AP vencen en 7 días”* → Programar pagos/flujo de caja

### 1.4 Datos (vistas `v_*`)
- `v_project_financial_kpis` (ya propuesto) → PC, PO, GRN, AP, Pagado, EP, avance.  
- `v_3way_status_po_line_ext(_pg)` → violaciones 3‑way por proyecto.  
- `v_ep_resumen` → EP por estado (aprobado/pendiente/facturado).  
- `v_portfolio_health` **(nueva)**: resume on_budget/over_budget/without_pc.

### 1.5 Endpoint 5555
`GET /api/projects/overview`  →  
```json
{
  "portfolio": {"activos":25, "pc_total": 5750111455, "po": 5040424868, "disponible": 709686587, "ejecucion": {"grn":..., "ap":..., "pagado":...}},
  "salud": {"on_budget":12, "over_budget":5, "without_pc":8, "tres_way":17, "riesgo": {"score":67, "reasons":[...] }},
  "wip": {"ep_aprobados_sin_fv":6, "ep_en_revision":3},
  "acciones": [ {"title":"Importar presupuesto…","cta":"/presupuestos/importar"}, ... ]
}
```

### 1.6 UI (wireframe)
Fila 1: PC vs PO (barra) • Ejecución (mini‑barra) • Salud (donut) • Riesgo (chip)  
Fila 2: Embudo costos • WIP EP • Heatmap Riesgo  
Fila 3: Excepciones & Acciones (lista)

### 1.7 `Lista` (subsección)
Tabla completa con búsqueda/segmentación, **no** como landing. Mantener columnas: `Proyecto`, `PC`, `PO`, `GRN`, `AP`, `Pagado`, `Avance`, `Riesgo`, `Acciones`.

---

## 2) Módulo **Finanzas** — Landing: *Dashboard & KPI*
**Ruta por defecto**: `/finanzas/overview`  
**Subsecciones**: `Overview` • `Flujo de Caja` (calendario 13 semanas) • `Cuentas Bancarias` • `Conciliación` • `AR (Ventas)` • `AP (Compras)` • `Impuestos/Nómina` • `Reportes`.

### 2.1 KPIs (arriba)
- **Caja hoy** (suma cuentas) + **proyección 13 semanas** (d7/d30/d60/d90) con brechas vs mínimo operativo.  
- **Ingresos mes/YTD vs plan** y **Margen bruto %** vs plan.  
- **AR aging** (1‑30 / 31‑60 / >60) y **AP por vencer** (7/14/30).
- **Conciliación**: % conciliado (AR/AP/banco) y *auto‑match coverage* (cuánto hace solo el sistema).

### 2.2 Diagnóstico & Acciones
- **Calendario de caja** (mini-sparkline semanal) con CTA “Abrir 13 semanas”.  
- **Top deudores** y **Top pagos próximos** (chips con CTA a cobro/orden de pago).  
- **Excepciones**: pagos sin respaldo, facturas sin OC/GRN, movimientos sin clasificar.

### 2.3 Datos (vistas `v_*`)
- `v_company_cash_forecast_90d` / `v_cash_forecast_13w`  
- `v_company_revenue_vs_plan`, `v_company_gross_margin_vs_plan`  
- `v_ar_aging_by_project`, `v_ap_schedule`  
- `v_kpi_conciliacion` **(nueva)**: % conciliado y auto‑match por fuente.

### 2.4 Endpoint 5555
`GET /api/finance/overview` → payload análogo al del CEO, pero con mayor detalle operativo y CTAs a conciliación, pagos y cobranzas.

### 2.5 UI (wireframe)
Fila 1: Caja & forecast • Ingresos/Margen vs plan • AR/AP (barras)  
Fila 2: Calendario de caja • Top deudores/pagos • Conciliación (% + auto‑match)  
Fila 3: Excepciones & Acciones.

---

## 3) Navegación y rutas
- **Proyectos** → `Overview` por defecto. La tabla grande pasa a `Lista`.  
- **Finanzas** → `Overview` por defecto. Las páginas actuales (Cartola, Conciliación, AR/AP) quedan como subpestañas.  
- **CEO Dashboard** permanece como home global (`/dashboard`) y enlaza a estos dos landings.

---

## 4) Cambios en *docs_oficiales*
**ESTRATEGIA_CREACION_PAGINAS.md**  
- Definir patrón de **Landing = Dashboard & KPI** para cada módulo.  
- Estructura: KPIs arriba, diagnóstico medio, **Excepciones & Acciones** abajo.  

**MAPEO_BASE_DATOS_PAGINAS.md**  
- Mapear nuevas rutas: `/proyectos/overview`, `/proyectos/lista`, `/finanzas/overview`, `/finanzas/flujo`, etc.  

**DB_CANONICA_Y_VISTAS.md**  
- Añadir `v_portfolio_health` y `v_kpi_conciliacion` + especificar campos de `v_company_*` usados aquí.  

**ESTRATEGIA_VISUAL.md**  
- Confirmar uso de **chips**, **mini‑sparklines** y **tooltips “¿Por qué?”**. Prohibición de emojis vigente.

---

## 5) Contratos de datos (resumen)
### `/api/projects/overview`
```json
{
  "portfolio": {"activos":N, "pc_total":0, "po":0, "disponible":0, "ejecucion": {"grn":0, "ap":0, "pagado":0}},
  "salud": {"on_budget":0, "over_budget":0, "without_pc":0, "tres_way":0, "riesgo": {"score":0, "reasons":[]}},
  "wip": {"ep_aprobados_sin_fv":0, "ep_en_revision":0},
  "acciones": [{"title":"…","cta":"/…"}]
}
```

### `/api/finance/overview`
```json
{
  "cash": {"today":0, "d7":0, "d30":0, "d60":0, "d90":0, "shortfall_7":0, "shortfall_30":0},
  "revenue": {"month": {"real":0, "plan":0, "delta_pct":0}, "ytd": {"real":0, "plan":0, "delta_pct":0}},
  "margin": {"month_pct":0, "plan_pct":0, "delta_pp":0},
  "ar": {"d1_30":0, "d31_60":0, "d60_plus":0, "top_clientes":[]},
  "ap": {"d7":0, "d14":0, "d30":0, "top_proveedores":[]},
  "conciliacion": {"porc_conciliado":0, "auto_match":0},
  "acciones": [{"title":"…","cta":"/…"}]
}
```

---

## 6) Aceptación (QA)
1) Las rutas `/proyectos/overview` y `/finanzas/overview` existen y cargan **sin datos vacíos** (usar seeds mínimos).  
2) Cada tarjeta tiene **CTA** a una acción concreta.  
3) Los KPIs muestran **fuente/vista** al hacer hover en “¿Por qué?”.  
4) No hay emojis; contraste AA; navegación por teclado.  
5) La **Lista** completa está accesible pero **no** es la landing.

---

## 7) Plan de implementación (Copilot)
1) Crear vistas faltantes: `v_portfolio_health`, `v_kpi_conciliacion` y, si no están, `v_project_financial_kpis`, `v_company_*`.  
2) Implementar endpoints `/api/projects/overview` y `/api/finance/overview` (cache simple).  
3) Construir UI de `Overview` para ambos módulos (tarjetas + mini‑sparklines + lista de acciones).  
4) Mover tabla actual a `/proyectos/lista` y ligar los CTA.  
5) Actualizar *docs_oficiales* (sección 4).  
6) QA según sección 6 + seeds para demo.

---

### Cierre
Tus módulos abrirán con **Dashboard & KPI** que orientan la operación y priorizan acciones; la tabla queda como una vista secundaria. El diseño es consistente con el **CEO Dashboard** y refuerza la arquitectura canónica de Ofitec.

