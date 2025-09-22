'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';

type ScHeader = {
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
};

type ScLine = {
  id?: number;
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
  type: 'retention' | 'advance_amortization' | 'penalty' | 'other';
  description?: string;
  amount: number;
};

export default function ScEPEditPage(..._args: any[]) {
  const routeParams = useParams() as { project?: string; epId?: string };
  const projectKey = decodeURIComponent(routeParams.project || '');
  const epId = Number(routeParams.epId); // keep epId (used in JSX) but ensure any additional params would be prefixed if unused
  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api',
    [],
  );
  const [header, setHeader] = useState<ScHeader | null>(null);
  const [lines, setLines] = useState<ScLine[]>([]);
  const [deductions, setDeductions] = useState<ScDeduction[]>([]);
  const [summary, setSummary] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const r = await fetch(`${apiBase}/sc/ep/${epId}`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        setHeader(data?.header || null);
        setLines(data?.lines || []);
        setDeductions(data?.deductions || []);
      } catch (e: any) {
        setError(e?.message || 'Error cargando EP');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [apiBase, epId]);

  async function refreshSummary() {
    try {
      const r = await fetch(`${apiBase}/sc/ep/${epId}/summary`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setSummary(await r.json());
    } catch (e: any) {
      setNotice(e?.message || 'No se pudo cargar resumen');
    }
  }

  useEffect(() => {
    if (header) refreshSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [header]);

  function updateLine(idx: number, patch: Partial<ScLine>) {
    setLines((prev) => {
      const clone = [...prev];
      const l = { ...clone[idx], ...patch };
      // calcular amount si procede
      const qty = l.qty_period;
      const up = l.unit_price;
      if (
        (l.amount_period == null || patch.qty_period != null || patch.unit_price != null) &&
        isFinite(Number(qty)) &&
        isFinite(Number(up))
      ) {
        l.amount_period = Number(qty) * Number(up);
      }
      clone[idx] = l;
      return clone;
    });
  }

  function addEmptyLine() {
    setLines((prev) => [
      ...prev,
      { description: '', qty_period: undefined, unit_price: undefined, amount_period: undefined },
    ]);
  }

  function removeLine(idx: number) {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  }

  function addDeduction() {
    setDeductions((prev) => [...prev, { type: 'other', description: '', amount: 0 }]);
  }

  function updateDeduction(idx: number, patch: Partial<ScDeduction>) {
    setDeductions((prev) => {
      const clone = [...prev];
      clone[idx] = { ...clone[idx], ...patch };
      return clone;
    });
  }

  function removeDeduction(idx: number) {
    setDeductions((prev) => prev.filter((_, i) => i !== idx));
  }

  async function saveAll() {
    setSaving(true);
    setNotice(null);
    try {
      // guardar header
      if (header) {
        const r1 = await fetch(`${apiBase}/sc/ep/${epId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ep_number: header.ep_number,
            period_start: header.period_start,
            period_end: header.period_end,
            status: header.status,
            retention_pct: header.retention_pct,
            notes: header.notes,
          }),
        });
        if (!r1.ok) throw new Error(await r1.text());
      }
      // guardar líneas
      {
        const payload = { lines: lines.map(({ id, ...rest }) => rest) };
        const r2 = await fetch(`${apiBase}/sc/ep/${epId}/lines/bulk`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!r2.ok) throw new Error(await r2.text());
      }
      // guardar deducciones
      {
        const payload = {
          deductions: deductions.map(({ id, ...rest }) => ({
            ...rest,
            amount: Number(rest.amount || 0),
          })),
        };
        const r3 = await fetch(`${apiBase}/sc/ep/${epId}/deductions/bulk`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!r3.ok) throw new Error(await r3.text());
      }
      await refreshSummary();
      setNotice('Cambios guardados');
    } catch (e: any) {
      setNotice(e?.message || 'No se pudo guardar');
    } finally {
      setSaving(false);
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
        <Link href={`/proyectos/${encodeURIComponent(projectKey)}/sc-ep`} className="text-lime-700">
          EP Subcontratistas
        </Link>
        <span> / </span>
        <span className="text-slate-700">Editar EP #{epId}</span>
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

      {header && (
        <div className="space-y-6">
          {/* Header editable */}
          <div className="border rounded-xl p-4">
            <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">EP N°</label>
                <input
                  value={header.ep_number || ''}
                  onChange={(e) => setHeader({ ...header, ep_number: e.target.value })}
                  className="w-full border rounded px-2 py-1"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Estado</label>
                <select
                  value={header.status || 'submitted'}
                  onChange={(e) => setHeader({ ...header, status: e.target.value })}
                  className="w-full border rounded px-2 py-1"
                >
                  {['draft', 'submitted', 'approved', 'rejected', 'invoiced', 'paid'].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Retención (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={header.retention_pct ?? 0}
                  onChange={(e) => setHeader({ ...header, retention_pct: Number(e.target.value) })}
                  className="w-full border rounded px-2 py-1"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Periodo Inicio</label>
                <input
                  type="date"
                  value={header.period_start || ''}
                  onChange={(e) => setHeader({ ...header, period_start: e.target.value })}
                  className="w-full border rounded px-2 py-1"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Periodo Fin</label>
                <input
                  type="date"
                  value={header.period_end || ''}
                  onChange={(e) => setHeader({ ...header, period_end: e.target.value })}
                  className="w-full border rounded px-2 py-1"
                />
              </div>
              <div className="md:col-span-6">
                <label className="block text-xs text-slate-500 mb-1">Notas</label>
                <input
                  value={header.notes || ''}
                  onChange={(e) => setHeader({ ...header, notes: e.target.value })}
                  className="w-full border rounded px-2 py-1"
                />
              </div>
            </div>
          </div>

          {/* Líneas */}
          <div className="border rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-medium">Líneas</h2>
              <button
                onClick={addEmptyLine}
                className="px-2 py-1 text-xs rounded bg-slate-100 border hover:bg-slate-200"
              >
                Agregar línea
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-slate-500">
                  <tr>
                    <th className="py-2 px-3">Item</th>
                    <th className="py-2 px-3">Descripción</th>
                    <th className="py-2 px-3">Unidad</th>
                    <th className="py-2 px-3 text-right">Cant</th>
                    <th className="py-2 px-3 text-right">P. Unitario</th>
                    <th className="py-2 px-3 text-right">Subtotal</th>
                    <th className="py-2 px-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {lines.map((ln, _idx) => (
                    <tr key={_idx}>
                      <td className="py-2 px-3">
                        <input
                          value={ln.item_code || ''}
                          onChange={(e) => updateLine(_idx, { item_code: e.target.value })}
                          className="w-full border rounded px-2 py-1"
                        />
                      </td>
                      <td className="py-2 px-3">
                        <input
                          value={ln.description || ''}
                          onChange={(e) => updateLine(_idx, { description: e.target.value })}
                          className="w-full border rounded px-2 py-1"
                        />
                      </td>
                      <td className="py-2 px-3">
                        <input
                          value={ln.unit || ''}
                          onChange={(e) => updateLine(_idx, { unit: e.target.value })}
                          className="w-full border rounded px-2 py-1"
                        />
                      </td>
                      <td className="py-2 px-3 text-right">
                        <input
                          type="number"
                          step="0.01"
                          value={ln.qty_period ?? ''}
                          onChange={(e) =>
                            updateLine(_idx, {
                              qty_period:
                                e.target.value === '' ? undefined : Number(e.target.value),
                            })
                          }
                          className="w-28 border rounded px-2 py-1 text-right"
                        />
                      </td>
                      <td className="py-2 px-3 text-right">
                        <input
                          type="number"
                          step="0.01"
                          value={ln.unit_price ?? ''}
                          onChange={(e) =>
                            updateLine(_idx, {
                              unit_price:
                                e.target.value === '' ? undefined : Number(e.target.value),
                            })
                          }
                          className="w-28 border rounded px-2 py-1 text-right"
                        />
                      </td>
                      <td className="py-2 px-3 text-right">{fmt(ln.amount_period)}</td>
                      <td className="py-2 px-3 text-right">
                        <button
                          onClick={() => removeLine(_idx)}
                          className="px-2 py-1 text-xs rounded bg-rose-50 text-rose-600 border border-rose-200 hover:bg-rose-100"
                        >
                          Quitar
                        </button>
                      </td>
                    </tr>
                  ))}
                  {lines.length === 0 && (
                    <tr>
                      <td className="py-3 px-3 text-slate-500" colSpan={7}>
                        Sin líneas
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Deducciones */}
          <div className="border rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-medium">Deducciones</h2>
              <button
                onClick={addDeduction}
                className="px-2 py-1 text-xs rounded bg-slate-100 border hover:bg-slate-200"
              >
                Agregar deducción
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-slate-500">
                  <tr>
                    <th className="py-2 px-3">Tipo</th>
                    <th className="py-2 px-3">Descripción</th>
                    <th className="py-2 px-3 text-right">Monto</th>
                    <th className="py-2 px-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {deductions.map((d, _idx) => (
                    <tr key={_idx}>
                      <td className="py-2 px-3">
                        <select
                          value={d.type}
                          onChange={(e) => updateDeduction(_idx, { type: e.target.value as any })}
                          className="w-full border rounded px-2 py-1"
                        >
                          {['retention', 'advance_amortization', 'penalty', 'other'].map((t) => (
                            <option key={t} value={t}>
                              {t}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-2 px-3">
                        <input
                          value={d.description || ''}
                          onChange={(e) => updateDeduction(_idx, { description: e.target.value })}
                          className="w-full border rounded px-2 py-1"
                        />
                      </td>
                      <td className="py-2 px-3 text-right">
                        <input
                          type="number"
                          step="0.01"
                          value={d.amount ?? 0}
                          onChange={(e) =>
                            updateDeduction(_idx, { amount: Number(e.target.value || 0) })
                          }
                          className="w-32 border rounded px-2 py-1 text-right"
                        />
                      </td>
                      <td className="py-2 px-3 text-right">
                        <button
                          onClick={() => removeDeduction(_idx)}
                          className="px-2 py-1 text-xs rounded bg-rose-50 text-rose-600 border border-rose-200 hover:bg-rose-100"
                        >
                          Quitar
                        </button>
                      </td>
                    </tr>
                  ))}
                  {deductions.length === 0 && (
                    <tr>
                      <td className="py-3 px-3 text-slate-500" colSpan={4}>
                        Sin deducciones
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Resumen */}
          <div className="border rounded-xl p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-medium">Resumen</h2>
              <button
                onClick={refreshSummary}
                className="px-2 py-1 text-xs rounded bg-slate-100 border hover:bg-slate-200"
              >
                Actualizar
              </button>
            </div>
            {summary ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
                <div className="p-3 rounded border bg-white">
                  <div className="text-xs text-slate-500">Subtotal Líneas</div>
                  <div className="text-lg font-semibold">{fmt(summary.lines_subtotal)}</div>
                </div>
                <div className="p-3 rounded border bg-white">
                  <div className="text-xs text-slate-500">Deducciones</div>
                  <div className="text-lg font-semibold">{fmt(summary.deductions_total)}</div>
                </div>
                <div className="p-3 rounded border bg-white">
                  <div className="text-xs text-slate-500">Neto</div>
                  <div className="text-lg font-semibold">{fmt(summary.amount_net)}</div>
                </div>
              </div>
            ) : (
              <div className="text-slate-500 mt-2">Sin datos de resumen.</div>
            )}
          </div>

          {/* Guardar */}
          <div className="flex justify-end">
            <button
              onClick={saveAll}
              disabled={saving}
              className="px-4 py-2 rounded bg-lime-600 text-white hover:bg-lime-700 disabled:opacity-50"
            >
              {saving ? 'Guardando…' : 'Guardar cambios'}
            </button>
          </div>
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
