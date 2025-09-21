# OFITEC — Entregables Módulo **Proyecto** (OpenAPI + SQL + React)

**Propósito:** Implementar la vista 360º del Proyecto con contratos de API (OpenAPI), vistas SQL y componentes React base, todo **listo para Copilot** y alineado a tus reglas (Ley de Puertos 3001/5555, DB Canónica, Estrategia Visual).

> **Nota general:** Las consultas SQL están en **sabor SQLite** (TEXT para fechas y `strftime`). Para Postgres: usar `DATE/NUMERIC`, `make_interval` y `jsonb`.

---

## 1) OpenAPI (YAML) — Contratos `/api/projects/:id/*`

```yaml
openapi: 3.0.3
info:
  title: Ofitec — Proyecto 360
  version: 1.0.0
servers:
  - url: http://localhost:5555
    description: API local
paths:
  /api/projects/{id}/summary:
    get:
      summary: Resumen 360 del proyecto (KPIs + flags + milestones)
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: integer }
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProjectSummaryResp'
  /api/projects/{id}/purchases:
    get:
      summary: Compras/OC del proyecto
      parameters:
        - { name: id, in: path, required: true, schema: {type: integer} }
        - { name: page, in: query, schema: {type: integer, default: 1} }
        - { name: page_size, in: query, schema: {type: integer, default: 50} }
      responses:
        '200': { description: OK, content: { application/json: { schema: { $ref: '#/components/schemas/PurchasesResp' }}}}
  /api/projects/{id}/budget:
    get:
      summary: Presupuesto por capítulos/partidas con comprometido y disponible
      parameters: [ { name: id, in: path, required: true, schema: {type: integer} } ]
      responses:
        '200': { description: OK, content: { application/json: { schema: { $ref: '#/components/schemas/BudgetResp' }}}}
  /api/projects/{id}/finance:
    get:
      summary: Finanzas (AP/AR/Pagos/Cobranzas + cashflow expected/actual/variance)
      parameters:
        - { name: id, in: path, required: true, schema: {type: integer} }
        - { name: from, in: query, schema: {type: string, example: '2025-01'} }
        - { name: to, in: query, schema: {type: string, example: '2025-12'} }
      responses:
        '200': { description: OK, content: { application/json: { schema: { $ref: '#/components/schemas/FinanceResp' }}}}
  /api/projects/{id}/time:
    get:
      summary: Cronograma y milestones del proyecto
      parameters: [ { name: id, in: path, required: true, schema: {type: integer} } ]
      responses:
        '200': { description: OK, content: { application/json: { schema: { $ref: '#/components/schemas/TimeResp' }}}}
  /api/projects/{id}/docs:
    get:
      summary: Archivos de Google Drive asociados al proyecto
      parameters: [ { name: id, in: path, required: true, schema: {type: integer} } ]
      responses:
        '200': { description: OK, content: { application/json: { schema: { $ref: '#/components/schemas/DocsResp' }}}}
  /api/projects/{id}/chats:
    get:
      summary: Hilos de WhatsApp asociados (por proveedor/tema)
      parameters: [ { name: id, in: path, required: true, schema: {type: integer} } ]
      responses:
        '200': { description: OK, content: { application/json: { schema: { $ref: '#/components/schemas/ChatsResp' }}}}
  /api/projects/{id}/ai/summary:
    post:
      summary: Resumen IA del proyecto (semana actual)
      parameters: [ { name: id, in: path, required: true, schema: {type: integer} } ]
      requestBody:
        required: false
        content:
          application/json:
            schema: { type: object, properties: { tone: {type: string, enum: [neutral, exec, detail] }}}
      responses:
        '200': { description: OK, content: { application/json: { schema: { $ref: '#/components/schemas/AISummaryResp' }}}}
  /api/projects/{id}/ai/qna:
    post:
      summary: Q&A IA (RAG) acotado al proyecto
      parameters: [ { name: id, in: path, required: true, schema: {type: integer} } ]
      requestBody:
        required: true
        content:
          application/json:
            schema: { type: object, required: [question], properties: { question: {type: string} }}
      responses:
        '200': { description: OK, content: { application/json: { schema: { $ref: '#/components/schemas/AIQnaResp' }}}}
components:
  schemas:
    ProjectSummaryResp:
      type: object
      properties:
        project_id: { type: integer }
        project_name: { type: string }
        sales_contracted: { type: number }
        budget_cost: { type: number }
        committed: { type: number }
        invoiced_ap: { type: number }
        paid: { type: number }
        ar_invoiced: { type: number }
        ar_collected: { type: number }
        margin_expected: { type: number }
        margin_committed: { type: number }
        margin_real: { type: number }
        cashflow_net_month: { type: number }
        progress_pct: { type: number }
        flags: { type: array, items: { type: string } }
        next_milestones: { type: array, items: { type: object, properties: { title: {type: string}, date: {type: string, format: date} }}}
    PurchasesResp:
      type: object
      properties:
        items:
          type: array
          items:
            type: object
            properties:
              po_id: { type: string }
              vendor_name: { type: string }
              status: { type: string }
              total_amount: { type: number }
              committed_allocations:
                type: array
                items: { type: object, properties: { partida_id: {type: integer}, amount: {type: number} }}
        meta: { type: object, properties: { page: {type: integer}, page_size: {type: integer}, total: {type: integer} }}
    BudgetResp:
      type: object
      properties:
        chapters: { type: array, items: { $ref: '#/components/schemas/Chapter' }}
        totals: { type: object, properties: { pc_total: {type: number}, committed: {type: number}, available_conservative: {type: number} }}
    Chapter:
      type: object
      properties:
        chapter_id: { type: integer }
        chapter_name: { type: string }
        partidas:
          type: array
          items:
            type: object
            properties:
              partida_id: { type: integer }
              desc: { type: string }
              total_presupuesto: { type: number }
              comprometido: { type: number }
              disponible: { type: number }
              percent_oc_pc: { type: number }
              flags: { type: array, items: { type: string } }
    FinanceResp:
      type: object
      properties:
        ap_invoices: { type: array, items: { type: object, properties: { invoice_id: {type: string}, vendor: {type: string}, amount:{type:number}, date:{type:string} }}}
        payments: { type: array, items: { type: object, properties: { payment_id: {type: string}, amount:{type:number}, date:{type:string} }}}
        ar_invoices: { type: array, items: { type: object, properties: { invoice_id: {type: string}, customer: {type: string}, amount:{type:number}, date:{type:string} }}}
        collections: { type: array, items: { type: object, properties: { receipt_id: {type: string}, amount:{type:number}, date:{type:string} }}}
        cashflow:
          type: object
          properties:
            expected: { type: array, items: { $ref: '#/components/schemas/CashBucket' }}
            actual: { type: array, items: { $ref: '#/components/schemas/CashBucket' }}
            variance: { type: array, items: { $ref: '#/components/schemas/CashVariance' }}
    TimeResp:
      type: object
      properties:
        milestones: { type: array, items: { type: object, properties: { title:{type:string}, date:{type:string} }}}
        progress_pct: { type: number }
    DocsResp:
      type: object
      properties:
        files: { type: array, items: { type: object, properties: { id:{type:string}, title:{type:string}, mime:{type:string}, url:{type:string}, modified_time:{type:string} }}}
    ChatsResp:
      type: object
      properties:
        threads: { type: array, items: { type: object, properties: { id:{type:string}, counterpart:{type:string}, last_message:{type:string}, updated_at:{type:string} }}}
    AISummaryResp:
      type: object
      properties:
        summary_text: { type: string }
        bullets: { type: array, items: { type: string } }
        risks: { type: array, items: { type: string } }
    AIQnaResp:
      type: object
      properties:
        answer: { type: string }
        citations: { type: array, items: { type: object, properties: { type:{type:string}, ref:{type:string}, url:{type:string} }}}
    CashBucket:
      type: object
      properties: { month: {type: string}, amount: {type: number} }
    CashVariance:
      type: object
      properties: { month: {type: string}, expected: {type: number}, actual: {type: number}, variance: {type: number} }
```

---

## 2) SQL — Vistas base (SQLite flavor)

> Ajustar nombres si difieren. Las vistas asumen que ya existen: `v_presupuesto_totales`, `purchase_orders_unified`, `po_line_allocations`, `v_facturas_compra`, `v_cartola_bancaria`, `v_ventas_contratadas`, `v_cobranzas`, `purchase_order_lines`.

```sql
-- A) Comprometido por proyecto
DROP VIEW IF EXISTS v_po_committed_project;
CREATE VIEW v_po_committed_project AS
SELECT
  o.zoho_project_name AS project_name,
  SUM(COALESCE(o.total_amount,0)) AS committed
FROM purchase_orders_unified o
WHERE COALESCE(LOWER(o.status),'approved') IN ('approved','closed')
GROUP BY o.zoho_project_name;

-- B) Costos facturados (AP) por proyecto
DROP VIEW IF EXISTS v_cost_invoiced_project;
CREATE VIEW v_cost_invoiced_project AS
SELECT f.project_name, SUM(f.amount) AS invoiced
FROM v_facturas_compra f
GROUP BY f.project_name;

-- C) Costos pagados por proyecto
DROP VIEW IF EXISTS v_cost_paid_project;
CREATE VIEW v_cost_paid_project AS
SELECT b.project_name, SUM(b.paid_amount) AS paid
FROM v_cartola_bancaria b
GROUP BY b.project_name;

-- D) Ventas contratadas (techo de ingresos)
DROP VIEW IF EXISTS v_sales_contracted_project;
CREATE VIEW v_sales_contracted_project AS
SELECT v.project_name, SUM(v.amount) AS sales_contracted
FROM v_ventas_contratadas v
GROUP BY v.project_name;

-- E) AR (facturado a cliente) y cobranzas
DROP VIEW IF EXISTS v_ar_invoiced_project;
CREATE VIEW v_ar_invoiced_project AS
SELECT a.project_name, SUM(a.amount) AS ar_invoiced
FROM v_ar_invoices a
GROUP BY a.project_name;

DROP VIEW IF EXISTS v_ar_collected_project;
CREATE VIEW v_ar_collected_project AS
SELECT c.project_name, SUM(c.amount) AS ar_collected
FROM v_cobranzas c
GROUP BY c.project_name;

-- F) Cashflow esperado (outflows) desde líneas de OC (materiales)
DROP VIEW IF EXISTS v_po_line_invoice_schedule;
CREATE VIEW v_po_line_invoice_schedule AS
SELECT
  l.po_line_id,
  l.po_id,
  l.line_total AS amount,
  COALESCE(json_extract(l.delivery_plan, '$[0].invoice_date'), l.expected_delivery_date) AS est_invoice_date
FROM purchase_order_lines l;

DROP VIEW IF EXISTS v_po_line_payment_schedule;
CREATE VIEW v_po_line_payment_schedule AS
SELECT
  s.po_line_id,
  s.po_id,
  s.amount,
  DATE(s.est_invoice_date, '+' || COALESCE(v.payment_terms_days, 30) || ' day') AS est_payment_date
FROM v_po_line_invoice_schedule s
LEFT JOIN purchase_orders_unified o ON o.po_id = s.po_id
LEFT JOIN vendors_unified v ON v.id = o.vendor_id;

DROP VIEW IF EXISTS v_cashflow_expected_project;
CREATE VIEW v_cashflow_expected_project AS
SELECT
  o.zoho_project_name AS project_name,
  strftime('%Y-%m-01', p.est_payment_date) AS bucket_month,
  SUM(p.amount) AS expected_outflow
FROM v_po_line_payment_schedule p
JOIN purchase_orders_unified o ON o.po_id = p.po_id
GROUP BY project_name, bucket_month;

-- G) Cashflow actual (pagos conciliados) y variancia
DROP VIEW IF EXISTS v_cashflow_actual_project;
CREATE VIEW v_cashflow_actual_project AS
SELECT
  b.project_name,
  strftime('%Y-%m-01', b.paid_date) AS bucket_month,
  SUM(b.paid_amount) AS actual_outflow
FROM v_cartola_bancaria b
GROUP BY b.project_name, bucket_month;

DROP VIEW IF EXISTS v_cashflow_variance_project;
CREATE VIEW v_cashflow_variance_project AS
SELECT
  e.project_name,
  e.bucket_month,
  e.expected_outflow,
  COALESCE(a.actual_outflow,0) AS actual_outflow,
  (COALESCE(a.actual_outflow,0) - e.expected_outflow) AS variance
FROM v_cashflow_expected_project e
LEFT JOIN v_cashflow_actual_project a
  ON a.project_name = e.project_name AND a.bucket_month = e.bucket_month;

-- H) Resumen 360 por proyecto
DROP VIEW IF EXISTS v_project_summary;
CREATE VIEW v_project_summary AS
SELECT
  s.project_name,
  COALESCE(sales.sales_contracted,0) AS sales_contracted,
  COALESCE(pc.total_presupuesto,0) AS budget_cost,
  COALESCE(oc.committed,0) AS committed,
  COALESCE(ap.invoiced,0) AS invoiced_ap,
  COALESCE(paid.paid,0) AS paid,
  COALESCE(ar.ar_invoiced,0) AS ar_invoiced,
  COALESCE(col.ar_collected,0) AS ar_collected,
  (COALESCE(sales.sales_contracted,0) - COALESCE(pc.total_presupuesto,0)) AS margin_expected,
  (COALESCE(sales.sales_contracted,0) - COALESCE(oc.committed,0)) AS margin_committed,
  (COALESCE(sales.sales_contracted,0) - COALESCE(ap.invoiced,0)) AS margin_real
FROM (
  SELECT DISTINCT project_name FROM (
    SELECT project_name FROM v_po_committed_project
    UNION SELECT project_name FROM v_cost_invoiced_project
    UNION SELECT project_name FROM v_cost_paid_project
    UNION SELECT project_name FROM v_sales_contracted_project
    UNION SELECT project_name FROM v_ar_invoiced_project
    UNION SELECT project_name FROM v_ar_collected_project
  )
) s
LEFT JOIN v_sales_contracted_project sales ON sales.project_name = s.project_name
LEFT JOIN v_po_committed_project oc ON oc.project_name = s.project_name
LEFT JOIN v_cost_invoiced_project ap ON ap.project_name = s.project_name
LEFT JOIN v_cost_paid_project paid ON paid.project_name = s.project_name
LEFT JOIN v_ar_invoiced_project ar ON ar.project_name = s.project_name
LEFT JOIN v_ar_collected_project col ON col.project_name = s.project_name
LEFT JOIN v_presupuesto_totales pc ON pc.project_name = s.project_name;
```

---

## 3) React (Next.js, Tailwind, Recharts) — Componentes base

> Estilo: Inter, lime `#84CC16`, bordes 1px, **sin sombras**, radius `rounded-2xl`. Imports shadcn/ui y lucide-react están permitidos.

### 3.1 Cliente API (TypeScript)

```ts
// frontend/lib/projectsApi.ts
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5555/api';

export async function getProjectSummary(id: number) {
  const r = await fetch(`${API_BASE}/projects/${id}/summary`);
  if (!r.ok) throw new Error('summary failed');
  return r.json();
}
export async function getProjectBudget(id: number) {
  const r = await fetch(`${API_BASE}/projects/${id}/budget`);
  if (!r.ok) throw new Error('budget failed');
  return r.json();
}
export async function getProjectFinance(id: number, from?: string, to?: string) {
  const q = new URLSearchParams({ ...(from&&{from}), ...(to&&{to}) }).toString();
  const r = await fetch(`${API_BASE}/projects/${id}/finance${q?`?${q}`:''}`);
  if (!r.ok) throw new Error('finance failed');
  return r.json();
}
```

### 3.2 KPICard

```tsx
// frontend/components/KPICard.tsx
import React from 'react';

export default function KPICard({ label, value, suffix, hint }: {label:string; value:number|string; suffix?:string; hint?:string}) {
  return (
    <div className="rounded-2xl border border-neutral-200 p-4">
      <div className="text-sm text-neutral-500">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}{suffix?` ${suffix}`:''}</div>
      {hint && <div className="text-xs text-neutral-400 mt-1">{hint}</div>}
    </div>
  );
}
```

### 3.3 Waterfall (Recharts)

```tsx
// frontend/components/Waterfall.tsx
'use client';
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export default function Waterfall({ data }:{ data: {name:string; value:number}[] }) {
  return (
    <div className="rounded-2xl border border-neutral-200 p-4">
      <BarChart width={640} height={280} data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="value" />
      </BarChart>
    </div>
  );
}
```

### 3.4 Tabla Presupuesto (Capítulo→Partida)

```tsx
// frontend/components/BudgetTable.tsx
import React from 'react';

type Partida = { partida_id:number; desc:string; total_presupuesto:number; comprometido:number; disponible:number; percent_oc_pc:number; flags?:string[] };
type Chapter = { chapter_id:number; chapter_name:string; partidas: Partida[] };

export default function BudgetTable({ chapters }:{ chapters: Chapter[] }){
  return (
    <div className="rounded-2xl border border-neutral-200">
      {chapters.map(ch => (
        <div key={ch.chapter_id} className="border-b">
          <div className="px-4 py-2 font-medium bg-neutral-50">{ch.chapter_name}</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-neutral-500">
                <th className="p-2">Partida</th>
                <th className="p-2">Presupuesto</th>
                <th className="p-2">Comprometido</th>
                <th className="p-2">Disponible</th>
                <th className="p-2">%OC/PC</th>
              </tr>
            </thead>
            <tbody>
              {ch.partidas.map(p => (
                <tr key={p.partida_id} className="border-t">
                  <td className="p-2">{p.desc}</td>
                  <td className="p-2">{p.total_presupuesto.toLocaleString()}</td>
                  <td className="p-2">{p.comprometido.toLocaleString()}</td>
                  <td className="p-2">{p.disponible.toLocaleString()}</td>
                  <td className="p-2">{(p.percent_oc_pc||0).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
```

### 3.5 Página Proyecto [id]

```tsx
// frontend/app/proyectos/[id]/page.tsx
import KPICard from '@/components/KPICard';
import Waterfall from '@/components/Waterfall';
import BudgetTable from '@/components/BudgetTable';
import { getProjectSummary, getProjectBudget, getProjectFinance } from '@/lib/projectsApi';

export default async function ProjectPage({ params }:{ params:{ id:string } }){
  const id = Number(params.id);
  const [summary, budget, finance] = await Promise.all([
    getProjectSummary(id),
    getProjectBudget(id),
    getProjectFinance(id)
  ]);

  const wf = [
    { name: 'PC', value: summary.budget_cost },
    { name: 'OC', value: -summary.committed },
    { name: 'AP', value: -summary.invoiced_ap },
    { name: 'Pagado', value: -summary.paid },
  ];

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{summary.project_name}</h1>
        <div className="text-sm text-neutral-500">Progreso: {summary.progress_pct ?? 0}%</div>
      </header>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard label="Ventas" value={summary.sales_contracted?.toLocaleString()} />
        <KPICard label="PC" value={summary.budget_cost?.toLocaleString()} />
        <KPICard label="OC" value={summary.committed?.toLocaleString()} />
        <KPICard label="AP" value={summary.invoiced_ap?.toLocaleString()} />
        <KPICard label="Pagado" value={summary.paid?.toLocaleString()} />
        <KPICard label="Margen esperado" value={summary.margin_expected?.toLocaleString()} />
        <KPICard label="Margen comprometido" value={summary.margin_committed?.toLocaleString()} />
        <KPICard label="Margen real" value={summary.margin_real?.toLocaleString()} />
      </section>

      <Waterfall data={wf} />

      <section>
        <h2 className="text-lg font-medium mb-2">Presupuesto</h2>
        <BudgetTable chapters={budget.chapters || []} />
      </section>

      {/* TODO: Tabs para Compras / Finanzas / Tiempo / Docs / Chats / IA */}
    </div>
  );
}
```

---

## 4) Backend — notas de implementación

- Implementar los endpoints según el **OpenAPI** anterior, consumiendo **vistas canónicas**.
- Manejar reglas duras con **422** y payload explicativo.
- Agregar **cache** corto (5–10 min) en `/summary` si el costo de cómputo supera 500ms.
- Normalizar `project_name` y usar `project_aliases` si es necesario para joins.

---

## 5) QA rápido / Preflight

1. `curl -s http://localhost:5555/api/projects/42/summary | jq` (KPIs coherentes).
2. `curl -s 'http://localhost:5555/api/projects/42/finance?from=2025-01&to=2025-12' | jq` (buckets).
3. Navegar `/proyectos/42` y validar **KPIs/Waterfall/Tabla**.

---

## 6) Roadmap de cierre

- Añadir **tabs** completas (Compras, Finanzas, Tiempo, Docs, Chats, IA) con sus tablas/gráficos.
- Integrar **RAG** (DB + Drive) y acciones IA (crear borrador de OC, redactar mensajes).
- Consolidar **cashflow inflows** (AR) y panel de variancia con explicaciones.

