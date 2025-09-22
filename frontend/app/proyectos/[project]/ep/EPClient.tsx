'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

export type EPHeader = {
  id: number;
  project_id: number;
  ep_number?: string;
  period_start?: string;
  period_end?: string;
  submitted_at?: string;
  approved_at?: string;
  status?: string;
  retention_pct?: number;
  notes?: string;
  amount_period?: number;
  deductions?: number;
};

interface Props {
  projectKey: string;
}

export default function EPClient({ projectKey }: Props) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<EPHeader[]>([]);
  const [notice, setNotice] = useState<string | null>(null);

  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api',
    [],
  );

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`${apiBase}/projects/${encodeURIComponent(projectKey)}/ep`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => setItems(data?.items || []))
      .catch((e) => setError(e?.message || 'Error cargando EP'))
      .finally(() => setLoading(false));
  }, [projectKey, apiBase]);

  async function refresh() {
    try {
      setLoading(true);
      const r = await fetch(`${apiBase}/projects/${encodeURIComponent(projectKey)}/ep`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setItems(data?.items || []);
    } catch (e: any) {
      setError(e?.message || 'Error');
    } finally {
      setLoading(false);
    }
  }

  async function approve(epId: number) {
    setNotice(null);
    const r = await fetch(`${apiBase}/ep/${epId}/approve`, { method: 'POST' });
    if (!r.ok) {
      const txt = await r.text().catch(() => '');
      setNotice(`No se pudo aprobar EP ${epId}: ${txt || r.status}`);
      return;
    }
    await refresh();
    setNotice(`EP ${epId} aprobado`);
  }

  async function generateInvoice(epId: number) {
    setNotice(null);
    const r = await fetch(`${apiBase}/ep/${epId}/generate-invoice`, { method: 'POST' });
    if (!r.ok) {
      const txt = await r.text().catch(() => '');
      setNotice(`No se pudo facturar EP ${epId}: ${txt || r.status}`);
      return;
    }
    await refresh();
    setNotice(`Factura generada para EP ${epId}`);
  }

  return (
    <div className="p-6 space-y-6">
      <div className="text-sm text-slate-500">
        <Link href="/proyectos" className="text-lime-700">
          Proyectos
        </Link>
        <span> / </span>
        <Link href={`/proyectos/${encodeURIComponent(projectKey)}`} className="text-lime-700">
          {projectKey}
        </Link>
        <span> / </span>
        <span className="text-slate-700">Estados de Pago (Cliente)</span>
      </div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Estados de Pago</h1>
        <Link href={`/proyectos/${encodeURIComponent(projectKey)}`} className="text-lime-700">
          Volver a 360
        </Link>
      </div>

      {loading && <div className="text-slate-500">Cargando...</div>}
      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 rounded-xl p-3">{error}</div>
      )}
      {notice && (
        <div className="bg-blue-50 text-blue-700 border border-blue-200 rounded-xl p-3">
          {notice}
        </div>
      )}

      {!loading && !error && (
        <div className="overflow-x-auto border rounded-xl">
          <table className="w-full text-sm">
            <thead className="text-left text-slate-500">
              <tr>
                <th className="py-2 px-3">EP</th>
                <th className="py-2 px-3">Periodo</th>
                <th className="py-2 px-3">Estado</th>
                <th className="py-2 px-3 text-right">Monto Neto</th>
                <th className="py-2 px-3 text-right">Deducciones</th>
                <th className="py-2 px-3">Aprobado</th>
                <th className="py-2 px-3">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((it) => (
                <tr key={it.id}>
                  <td className="py-2 px-3">{it.ep_number || it.id}</td>
                  <td className="py-2 px-3">
                    {(it.period_start || '-') + ' → ' + (it.period_end || '-')}
                  </td>
                  <td className="py-2 px-3">{it.status || '-'}</td>
                  <td className="py-2 px-3 text-right">
                    {new Intl.NumberFormat('es-CL', {
                      style: 'currency',
                      currency: 'CLP',
                      minimumFractionDigits: 0,
                    }).format(Number((it.amount_period || 0) - (it.deductions || 0)))}
                  </td>
                  <td className="py-2 px-3 text-right">
                    {new Intl.NumberFormat('es-CL', {
                      style: 'currency',
                      currency: 'CLP',
                      minimumFractionDigits: 0,
                    }).format(Number(it.deductions || 0))}
                  </td>
                  <td className="py-2 px-3">{it.approved_at || '-'}</td>
                  <td className="py-2 px-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => approve(it.id)}
                        className="px-2 py-1 text-xs rounded bg-emerald-600 text-white hover:bg-emerald-700"
                      >
                        Aprobar
                      </button>
                      <button
                        onClick={() => generateInvoice(it.id)}
                        className="px-2 py-1 text-xs rounded bg-indigo-600 text-white hover:bg-indigo-700"
                      >
                        Generar Factura
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td className="py-3 px-3 text-slate-500" colSpan={7}>
                    Sin EP registrados todavía.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
