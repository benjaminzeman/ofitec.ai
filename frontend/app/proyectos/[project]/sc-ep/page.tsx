'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

type ScHeader = {
  id: number;
  project_id: number;
  subcontract_id?: number;
  ep_number?: string;
  period_start?: string;
  period_end?: string;
  submitted_at?: string;
  approved_at?: string;
  status?: string;
  retention_pct?: number;
  notes?: string;
};

type ScLine = {
  id?: number;
  ep_id?: number;
  item_code?: string;
  description?: string;
  unit?: string;
  qty_period?: number;
  unit_price?: number;
  amount_period?: number;
  qty_cum?: number;
  amount_cum?: number;
  chapter?: string;
};

type ScDeduction = {
  id?: number;
  ep_id?: number;
  type: 'retention' | 'advance_amortization' | 'penalty' | 'other';
  description?: string;
  amount: number;
};

export default function ProjectScEPListPage({ params }: { params: { project: string } }) {
  const projectKey = decodeURIComponent(params.project);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [retentionPct, setRetentionPct] = useState<number>(0.05);
  const [periodStart, setPeriodStart] = useState<string>('');
  const [periodEnd, setPeriodEnd] = useState<string>('');
  const [epNumber, setEpNumber] = useState<string>('');

  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api',
    [],
  );

  async function refresh() {
    try {
      setLoading(true);
      setError(null);
      // Obtener project_id desde backend 360 si disponible
      const projResp = await fetch(`${apiBase}/projects/${encodeURIComponent(projectKey)}`);
      let project_id: number | null = null;
      if (projResp.ok) {
        const pd = await projResp.json().catch(() => ({}));
        project_id = pd?.project?.id ?? pd?.id ?? null;
      }
      const url = project_id
        ? `${apiBase}/sc/ep?project_id=${encodeURIComponent(String(project_id))}`
        : `${apiBase}/sc/ep`;
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setItems(data?.items || []);
    } catch (e: any) {
      setError(e?.message || 'Error cargando SC EPs');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectKey]);

  async function createEP() {
    setNotice(null);
    setCreating(true);
    try {
      // Igual que arriba, descubrimos project_id
      const projResp = await fetch(`${apiBase}/projects/${encodeURIComponent(projectKey)}`);
      let project_id: number | null = null;
      if (projResp.ok) {
        const pd = await projResp.json().catch(() => ({}));
        project_id = pd?.project?.id ?? pd?.id ?? null;
      }
      if (!project_id) throw new Error('No se pudo resolver project_id');
      const r = await fetch(`${apiBase}/sc/ep`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id,
          ep_number: epNumber || undefined,
          period_start: periodStart || undefined,
          period_end: periodEnd || undefined,
          retention_pct: retentionPct ?? undefined,
          notes: undefined,
        }),
      });
      const text = await r.text();
      if (!r.ok) throw new Error(text || `HTTP ${r.status}`);
      const payload = JSON.parse(text);
      const epId = payload?.ep_id;
      if (epId) {
        window.location.href = `/proyectos/${encodeURIComponent(projectKey)}/sc-ep/${epId}`;
      } else {
        await refresh();
        setNotice('EP creado');
      }
    } catch (e: any) {
      setNotice(e?.message || 'No se pudo crear SC EP');
    } finally {
      setCreating(false);
    }
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
        <span className="text-slate-700">EP Subcontratistas</span>
      </div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          EP Subcontratistas
        </h1>
        <Link href={`/proyectos/${encodeURIComponent(projectKey)}`} className="text-lime-700">
          Volver a 360
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Retención (%)</label>
          <input
            type="number"
            step="0.01"
            value={retentionPct}
            onChange={(e) => setRetentionPct(Number(e.target.value))}
            className="w-full border rounded px-2 py-1"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Periodo Inicio</label>
          <input
            type="date"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
            className="w-full border rounded px-2 py-1"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Periodo Fin</label>
          <input
            type="date"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
            className="w-full border rounded px-2 py-1"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">EP N° (opcional)</label>
          <input
            value={epNumber}
            onChange={(e) => setEpNumber(e.target.value)}
            className="w-full border rounded px-2 py-1"
          />
        </div>
      </div>
      <div>
        <button
          onClick={createEP}
          disabled={creating}
          className="px-3 py-2 rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          {creating ? 'Creando…' : 'Nuevo EP Subcontrato'}
        </button>
      </div>

      {loading && <div className="text-slate-500">Cargando…</div>}
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
                <th className="py-2 px-3 text-right">Subtotal Líneas</th>
                <th className="py-2 px-3 text-right">Deducciones</th>
                <th className="py-2 px-3 text-right">Neto Estimado</th>
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
                  <td className="py-2 px-3 text-right">{fmt(it.lines_subtotal)}</td>
                  <td className="py-2 px-3 text-right">{fmt(it.deductions_total)}</td>
                  <td className="py-2 px-3 text-right">{fmt(it.amount_net_estimate)}</td>
                  <td className="py-2 px-3">
                    <div className="flex gap-2">
                      <Link
                        href={`/proyectos/${encodeURIComponent(projectKey)}/sc-ep/${it.id}`}
                        className="px-2 py-1 text-xs rounded bg-slate-100 border hover:bg-slate-200"
                      >
                        Editar
                      </Link>
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

function fmt(v: any) {
  const n = Number(v || 0);
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
  }).format(n);
}
