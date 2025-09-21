# OFITEC — Addenda **Postgres** + **UI Chips/Badges**
> Este addenda se crea para evitar el límite de tamaño del archivo anterior. Contiene: (1) **SQL Postgres** de vistas que faltaban y (2) **componentes React** para chips/badges de estado, listos para pegar.

---

## 1) SQL — Postgres (vistas finales)
> Supone tablas/vistas canónicas: `purchase_orders_unified`, `purchase_order_lines` (qty, unit_price, po_line_id, po_id), `invoice_lines` (po_line_id, qty, unit_price, invoice_id), y la vista **`v_po_line_received_accum`** (de la sección 11 Postgres). Ajusta nombres si difieren en tu repo.

### 1.1 Rollups de OC por cantidades y montos
```sql
DROP VIEW IF EXISTS v_po_rollups_pg;
CREATE VIEW v_po_rollups_pg AS
WITH pol AS (
  SELECT po_id,
         SUM(qty)                                        AS total_ordered_qty,
         SUM(qty * unit_price)::numeric(18,2)            AS po_total
  FROM purchase_order_lines
  GROUP BY po_id
), rec AS (
  SELECT pol.po_id,
         SUM(COALESCE(r.qty_received_accum,0))           AS total_received_qty
  FROM purchase_order_lines pol
  LEFT JOIN v_po_line_received_accum r ON r.po_line_id = pol.po_line_id
  GROUP BY pol.po_id
), bil_q AS (
  SELECT pol.po_id,
         SUM(il.qty)                                     AS total_billed_qty
  FROM purchase_order_lines pol
  JOIN invoice_lines il ON il.po_line_id = pol.po_line_id
  GROUP BY pol.po_id
), bil_amt AS (
  SELECT pol.po_id,
         SUM(il.qty * il.unit_price)::numeric(18,2)      AS total_billed
  FROM purchase_order_lines pol
  JOIN invoice_lines il ON il.po_line_id = pol.po_line_id
  GROUP BY pol.po_id
)
SELECT po.po_id,
       po.vendor_id,
       p.total_ordered_qty,
       COALESCE(r.total_received_qty,0) AS total_received_qty,
       COALESCE(bq.total_billed_qty,0)  AS total_billed_qty,
       p.po_total,
       COALESCE(ba.total_billed,0)      AS total_billed
FROM purchase_orders_unified po
LEFT JOIN pol p  ON p.po_id  = po.po_id
LEFT JOIN rec r  ON r.po_id  = po.po_id
LEFT JOIN bil_q bq ON bq.po_id = po.po_id
LEFT JOIN bil_amt ba ON ba.po_id = po.po_id;
```

### 1.2 Estados paralelos de OC (enhanced)
```sql
DROP VIEW IF EXISTS v_po_status_enhanced_pg;
CREATE VIEW v_po_status_enhanced_pg AS
SELECT
  u.*,  -- campos canónicos de purchase_orders_unified
  r.total_ordered_qty,
  r.total_received_qty,
  r.total_billed_qty,
  r.po_total,
  r.total_billed,
  /* estados paralelos */
  CASE WHEN r.total_billed       >= r.po_total           THEN 'billed'   ELSE 'unbilled' END AS billed_status,
  CASE WHEN r.total_received_qty >= r.total_ordered_qty  THEN 'received' ELSE CASE WHEN COALESCE(r.total_received_qty,0) = 0 THEN 'none' ELSE 'partial' END END AS received_status,
  /* substatus compuesto (no contractual) */
  CASE
    WHEN u.cancelled_at IS NOT NULL THEN 'cancelled'
    WHEN r.total_billed >= r.po_total AND r.total_received_qty >= r.total_ordered_qty THEN 'closed'
    WHEN COALESCE(r.total_billed,0) = 0 AND COALESCE(r.total_received_qty,0) = 0 THEN 'open'
    ELSE 'in_progress'
  END AS order_status
FROM purchase_orders_unified u
LEFT JOIN v_po_rollups_pg r USING (po_id);
```

### 1.3 Flags de conciliación AP (3‑way)
```sql
DROP VIEW IF EXISTS v_ap_reconciliation_flags_pg;
CREATE VIEW v_ap_reconciliation_flags_pg AS
SELECT
  il.invoice_id,
  il.po_line_id,
  /* reglas duras */
  CASE WHEN il.qty > COALESCE(rec.qty_received_accum,0) THEN 1 ELSE 0 END AS invoice_over_receipt,
  CASE WHEN (il.qty * il.unit_price) > (pol.qty * pol.unit_price) THEN 1 ELSE 0 END AS invoice_over_po,
  /* resumen */
  CASE WHEN (il.qty > COALESCE(rec.qty_received_accum,0)) OR ((il.qty*il.unit_price) > (pol.qty*pol.unit_price)) THEN 1 ELSE 0 END AS is_bill_reconciliation_violated
FROM invoice_lines il
JOIN purchase_order_lines pol ON pol.po_line_id = il.po_line_id
LEFT JOIN v_po_line_received_accum rec ON rec.po_line_id = il.po_line_id;
```

---

## 2) UI — Chips y Badges (Next.js + Tailwind)
> Estilo Ofitec: Inter, bordes 1px, `rounded-full`, sin sombras. Componentes ligeros y reutilizables.

### 2.1 `StatusChips.tsx` — OC (order/received/billed)
```tsx
'use client';
import React from 'react';

const pill = 'px-2 py-0.5 text-xs rounded-full border';

export default function StatusChips({ order, received, billed }:{ order:string; received:string; billed:string }){
  const map = (v:string)=>({
    open:'border-neutral-300', in_progress:'border-amber-400', closed:'border-emerald-500', cancelled:'border-rose-500'
  } as any)[v] || 'border-neutral-300';
  const map2 = (v:string)=>({ none:'border-neutral-300', partial:'border-amber-400', received:'border-emerald-500' } as any)[v] || 'border-neutral-300';
  const map3 = (v:string)=>({ unbilled:'border-amber-400', billed:'border-emerald-500' } as any)[v] || 'border-neutral-300';
  return (
    <div className="flex items-center gap-2">
      <span className={`${pill} ${map(order)}`}>{order}</span>
      <span className={`${pill} ${map2(received)}`}>received: {received}</span>
      <span className={`${pill} ${map3(billed)}`}>billed: {billed}</span>
    </div>
  );
}
```

### 2.2 `InvoiceReconBadge.tsx` — Factura AP (conciliación 3‑way)
```tsx
'use client';
import React from 'react';

export default function InvoiceReconBadge({ overPO, overReceipt }:{ overPO:boolean; overReceipt:boolean }){
  let label = 'OK 3-way';
  let cls = 'border-emerald-500';
  if (overPO && overReceipt) { label = 'Factura > PO y > Recepción'; cls = 'border-rose-600'; }
  else if (overPO) { label = 'Factura > PO'; cls = 'border-rose-600'; }
  else if (overReceipt) { label = 'Factura > Recepción'; cls = 'border-rose-600'; }
  return <span className={`px-2 py-0.5 text-xs rounded-full border ${cls}`}>{label}</span>;
}
```

### 2.3 `PurchaseOrderList.tsx` — lista de OC con chips
```tsx
'use client';
import React, { useEffect, useState } from 'react';
import StatusChips from './StatusChips';

export default function PurchaseOrderList({ projectId }:{ projectId:number }){
  const [items,setItems] = useState<any[]>([]);
  useEffect(()=>{(async()=>{
    const r = await fetch(`/api/projects/${projectId}/purchases?page=1&page_size=50&txn=true`);
    const j = await r.json(); setItems(j.items||[]);
  })();},[projectId]);

  return (
    <div className="rounded-2xl border">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-neutral-500">
            <th className="p-2">PO</th><th className="p-2">Proveedor</th><th className="p-2">Total</th><th className="p-2">Estados</th>
          </tr>
        </thead>
        <tbody>
          {items.map((x:any)=> (
            <tr key={x.po_id} className="border-t">
              <td className="p-2">{x.po_id}</td>
              <td className="p-2">{x.vendor_name}</td>
              <td className="p-2">{Number(x.total_amount).toLocaleString()}</td>
              <td className="p-2">
                <StatusChips order={x.order_status} received={x.received_status} billed={x.billed_status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### 2.4 `SupplierInvoiceRow.tsx` — fila con badge 3‑way
```tsx
'use client';
import React from 'react';
import InvoiceReconBadge from './InvoiceReconBadge';

export default function SupplierInvoiceRow({ inv }:{ inv:any }){
  return (
    <tr className="border-t">
      <td className="p-2">#{inv.invoice_id}</td>
      <td className="p-2">{inv.po_id}</td>
      <td className="p-2">{inv.project}</td>
      <td className="p-2">{Number(inv.amount_total).toLocaleString()}</td>
      <td className="p-2">{inv.status}</td>
      <td className="p-2">{inv.paid_date || inv.due_date}</td>
      <td className="p-2">
        <InvoiceReconBadge overPO={!!inv.flags?.invoice_over_po} overReceipt={!!inv.flags?.invoice_over_receipt} />
      </td>
    </tr>
  );
}
```

---

## 3) Notas de implementación (rápidas)
- Backend `/api/projects/:id/purchases` debe **enriquecer** cada PO con `order_status`, `received_status`, `billed_status` desde `v_po_status_enhanced_pg`.
- Endpoint de **facturas AP** debe adjuntar `flags` desde `v_ap_reconciliation_flags_pg` por línea y un agregado por factura.
- Mantener **`page_context`** en listas (como Zoho) para paginación fluida.
- Testing: casos límite — OC sin líneas, recepción parcial, factura mayor, devolución negativa, moneda con distinta precisión.

