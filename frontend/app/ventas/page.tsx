'use client';

import { useEffect, useState } from 'react';
import AssignProjectDrawer from '@/components/AssignProjectDrawer';
import { formatCurrency } from '@/lib/api';

type Row = {
  invoice_id: number;
  customer_rut: string;
  customer_name: string;
  invoice_number: string;
  issue_date: string;
  due_date?: string;
  currency?: string;
  total_amount: number;
  project_id?: number | null;
  paid_amount?: number | null;
};

export default function Ventas() {
  const [rows, setRows] = useState<Row[]>([]);
  const [sel, setSel] = useState<Row | null>(null);
  const [search, setSearch] = useState('');
  const [projectId, setProjectId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [loading, setLoading] = useState(false);
  const [aging, setAging] = useState<{
    d0_30: number;
    d31_60: number;
    d61_90: number;
    d90p: number;
  } | null>(null);

  async function fetchRows() {
    setLoading(true);
    try {
      const qs = new URLSearchParams({
        page: '1',
        page_size: '50',
        order_by: 'fecha',
        order_dir: 'DESC',
      });
      if (search) qs.set('search', search);
      if (projectId) qs.set('project_id', projectId);
      if (dateFrom) qs.set('date_from', dateFrom);
      if (dateTo) qs.set('date_to', dateTo);
      const url = `/api/sales_invoices?${qs.toString()}`;
      const r = await fetch(url).catch(() => null as any);
      if (r && r.ok) {
        const j = await r.json();
        const items = (j.items || []).map((x: any) => ({
          invoice_id: x.invoice_id ?? x.id ?? 0,
          customer_rut: x.customer_rut ?? x.cliente_rut ?? '',
          customer_name: x.customer_name ?? x.cliente_nombre ?? '',
          invoice_number: x.invoice_number ?? x.documento_numero ?? '',
          issue_date: x.issue_date ?? x.fecha ?? '',
          due_date: x.due_date,
          currency: x.currency ?? x.moneda,
          total_amount: Number(x.total_amount ?? x.monto_total ?? 0),
          project_id: x.project_id ?? null,
          paid_amount: Number(x.paid_amount ?? 0),
        })) as Row[];
        setRows(items);
      } else {
        // Fallback to canonical finanzas endpoint (v_facturas_venta)
        const r2 = await fetch('/api/finanzas/facturas_venta?page=1&page_size=50');
        const j2 = await r2.json();
        const items2 = (j2.items || []).map((x: any) => ({
          invoice_id: 0,
          customer_rut: x.cliente_rut ?? '',
          customer_name: x.cliente_nombre ?? '',
          invoice_number: x.documento_numero ?? '',
          issue_date: x.fecha ?? '',
          total_amount: Number(x.monto_total ?? 0),
          project_id: null,
          paid_amount: 0,
        })) as Row[];
        setRows(items2);
      }
    } catch (e) {
      console.error('Ventas load error', e);
    } finally {
      setLoading(false);
    }
  }

  async function fetchAging() {
    try {
      const res = await fetch('/api/ar_aging_by_project');
      if (!res.ok) return setAging(null);
      const data = await res.json();
      const items: Array<any> = data.items || [];
      const filtered = projectId
        ? items.filter((x) => String(x.project_id) === String(projectId))
        : items;
      const sum = filtered.reduce(
        (acc, x) => ({
          d0_30: acc.d0_30 + Number(x.d0_30 || 0),
          d31_60: acc.d31_60 + Number(x.d31_60 || 0),
          d61_90: acc.d61_90 + Number(x.d61_90 || 0),
          d90p: acc.d90p + Number(x.d90p || 0),
        }),
        { d0_30: 0, d31_60: 0, d61_90: 0, d90p: 0 },
      );
      setAging(sum);
    } catch (e) {
      setAging(null);
    }
  }

  useEffect(() => {
    fetchRows();
    fetchAging();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="p-4">
      <h1 className="text-xl font-semibold mb-3">Facturas de Venta</h1>
      <div className="mb-3 flex flex-wrap gap-2 items-end">
        <div className="flex flex-col">
          <label className="text-xs text-neutral-500">Buscar</label>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="cliente o folio"
            className="border rounded px-2 py-1"
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-neutral-500">Proyecto ID</label>
          <input
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            placeholder="2306"
            className="border rounded px-2 py-1 w-28"
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-neutral-500">Desde</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="border rounded px-2 py-1"
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-neutral-500">Hasta</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="border rounded px-2 py-1"
          />
        </div>
        <button
          onClick={() => {
            fetchRows();
            fetchAging();
          }}
          className="px-3 py-1.5 rounded bg-slate-900 text-white"
          disabled={loading}
        >
          {loading ? 'Cargando…' : 'Aplicar'}
        </button>
        {aging && (
          <div className="ml-auto flex gap-2 text-xs">
            <span className="px-2 py-1 rounded bg-emerald-50 text-emerald-700">
              0-30: {formatCurrency(aging.d0_30)}
            </span>
            <span className="px-2 py-1 rounded bg-amber-50 text-amber-700">
              31-60: {formatCurrency(aging.d31_60)}
            </span>
            <span className="px-2 py-1 rounded bg-orange-50 text-orange-700">
              61-90: {formatCurrency(aging.d61_90)}
            </span>
            <span className="px-2 py-1 rounded bg-rose-50 text-rose-700">
              90+: {formatCurrency(aging.d90p)}
            </span>
          </div>
        )}
      </div>
      <div className="rounded-2xl border overflow-auto bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-neutral-500">
              <th className="p-2">Folio</th>
              <th className="p-2">Cliente</th>
              <th className="p-2">Fecha</th>
              <th className="p-2">Total</th>
              <th className="p-2">Proyecto</th>
              <th className="p-2">Cobrado</th>
              <th className="p-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => {
              const outstanding = Number(x.total_amount || 0) - Number(x.paid_amount || 0);
              const overdue = !!x.due_date && outstanding > 0 && new Date(x.due_date) < new Date();
              return (
                <tr key={`${x.invoice_id}-${x.invoice_number}`} className="border-t">
                  <td className="p-2">{x.invoice_number}</td>
                  <td className="p-2">{x.customer_name}</td>
                  <td className="p-2">
                    <div className="flex items-center gap-2">
                      <span>{x.issue_date}</span>
                      {overdue && (
                        <span className="text-rose-700 bg-rose-100 text-[10px] px-1.5 py-0.5 rounded">
                          Vencida
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-2">{formatCurrency(Number(x.total_amount || 0))}</td>
                  <td className="p-2">
                    {x.project_id ? (
                      <span>{x.project_id}</span>
                    ) : (
                      <span className="text-amber-600">(sin proyecto)</span>
                    )}
                  </td>
                  <td className="p-2">{formatCurrency(Number(x.paid_amount || 0))}</td>
                  <td className="p-2">
                    {!x.project_id && (
                      <button className="border px-2 py-1 rounded" onClick={() => setSel(x)}>
                        Asignar proyecto
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {sel && (
        <AssignProjectDrawer
          invoice={sel}
          onClose={() => {
            setSel(null);
            // Refresh list after assignment
            fetchRows();
            fetchAging();
          }}
        />
      )}
    </div>
  );
}
