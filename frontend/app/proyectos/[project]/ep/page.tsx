'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import * as XLSX from 'xlsx';

type EPHeader = {
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

export default function ProjectEPListPage({ params }: { params: { project: string } }) {
  const projectKey = decodeURIComponent(params.project);
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

  function parseLines(raw: string): any[] {
    // Simple parser: each line "item_code,description,qty,unit_price,amount" (amount optional if qty*price)
    return raw
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => {
        const parts = l.split(',').map((p) => p.trim());
        const [item_code, description, qty, unit_price, amount] = parts;
        const qtyN = qty ? Number(qty) : undefined;
        const upN = unit_price ? Number(unit_price) : undefined;
        const amtN = amount ? Number(amount) : qtyN != null && upN != null ? qtyN * upN : undefined;
        return {
          item_code: item_code || undefined,
          description: description || undefined,
          qty_period: qtyN,
          unit_price: upN,
          amount_period: amtN,
        };
      });
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

      {/* Import Wizard */}
      <ImportWizard projectKey={projectKey} onImported={refresh} setNotice={setNotice} />
    </div>
  );
}

function ImportWizard({
  projectKey,
  onImported,
  setNotice,
}: {
  projectKey: string;
  onImported: () => void;
  setNotice: (s: string | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [epNumber, setEpNumber] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [linesRaw, setLinesRaw] = useState('');
  const [deductionsRaw, setDeductionsRaw] = useState('');
  const [loading, setLoading] = useState(false);
  const [excelRows, setExcelRows] = useState<any[] | null>(null);
  const [excelCols, setExcelCols] = useState<string[]>([]);
  const [mapping, setMapping] = useState<{ [k: string]: string }>({
    item_code: 'item_code',
    description: 'description',
    qty_period: 'qty',
    unit_price: 'unit_price',
    amount_period: 'amount',
  });

  const apiBase = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api',
    [],
  );

  async function submit() {
    setNotice(null);
    setLoading(true);
    try {
      const ep_lines = excelRows ? rowsFromExcel() : parseLinesLocal(linesRaw);
      const body = {
        project_key: projectKey,
        ep_header: {
          ep_number: epNumber || undefined,
          period_start: periodStart || undefined,
          period_end: periodEnd || undefined,
        },
        ep_lines,
        ep_deductions: parseDeductionsLocal(deductionsRaw),
      };
      const r = await fetch(`${apiBase}/projects/${encodeURIComponent(projectKey)}/ep/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const txt = await r.text();
      if (!r.ok) throw new Error(txt || `HTTP ${r.status}`);
      setNotice('EP importado correctamente');
      setOpen(false);
      onImported();
    } catch (e: any) {
      setNotice(e?.message || 'No se pudo importar EP');
    } finally {
      setLoading(false);
    }
  }

  function parseLinesLocal(raw: string) {
    return raw
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => {
        const [item_code, description, qty, unit_price, amount] = l.split(',').map((s) => s.trim());
        const qtyN = qty ? Number(qty) : undefined;
        const upN = unit_price ? Number(unit_price) : undefined;
        const amtN = amount ? Number(amount) : qtyN != null && upN != null ? qtyN * upN : undefined;
        return { item_code, description, qty_period: qtyN, unit_price: upN, amount_period: amtN };
      });
  }

  function parseDeductionsLocal(raw: string) {
    // line format: type,description,amount
    return raw
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => {
        const [type, description, amount] = l.split(',').map((s) => s.trim());
        return { type, description, amount: amount ? Number(amount) : undefined };
      });
  }

  function readExcel(file: File) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const data = new Uint8Array(e.target?.result as ArrayBuffer);
      const workbook = XLSX.read(data, { type: 'array' });
      const wsname = workbook.SheetNames[0];
      const ws = workbook.Sheets[wsname];
      const json = XLSX.utils.sheet_to_json(ws, { defval: '' }) as any[];
      setExcelRows(json);
      const cols = Object.keys(json[0] || {});
      setExcelCols(cols);
      const lc = cols.map((c) => c.toLowerCase().trim());
      const find = (alts: string[]) => {
        for (const a of alts) {
          const i = lc.indexOf(a);
          if (i >= 0) return cols[i];
        }
        return cols[0] || '';
      };
      setMapping({
        item_code: find(['item_code', 'codigo', 'código', 'item', 'cod']),
        description: find(['description', 'descripcion', 'descripción', 'detalle']),
        qty_period: find(['qty', 'cantidad', 'qty_period', 'cant']),
        unit_price: find(['unit_price', 'precio', 'precio_unitario', 'pu']),
        amount_period: find(['amount', 'monto', 'total', 'amount_period']),
      });
    };
    reader.readAsArrayBuffer(file);
  }

  function rowsFromExcel(): any[] {
    if (!excelRows) return [];
    return excelRows.map((r) => {
      const item_code = r[mapping.item_code];
      const description = r[mapping.description];
      const qty = Number(r[mapping.qty_period]);
      const up = Number(r[mapping.unit_price]);
      const amountVal = r[mapping.amount_period];
      const amount =
        amountVal !== undefined && amountVal !== ''
          ? Number(amountVal)
          : isFinite(qty) && isFinite(up)
            ? qty * up
            : undefined;
      return {
        item_code,
        description,
        qty_period: isFinite(qty) ? qty : undefined,
        unit_price: isFinite(up) ? up : undefined,
        amount_period: amount,
      };
    });
  }

  return (
    <div className="border rounded-xl p-4">
      <div className="flex items-center justify-between">
        <h2 className="font-medium">Importar EP</h2>
        <button onClick={() => setOpen((o) => !o)} className="text-sm text-lime-700">
          {open ? 'Cerrar' : 'Abrir'}
        </button>
      </div>
      {open && (
        <div className="mt-4 space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-slate-500 mb-1">EP N°</label>
              <input
                value={epNumber}
                onChange={(e) => setEpNumber(e.target.value)}
                className="w-full border rounded px-2 py-1"
                placeholder="ej: 5"
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
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">
              Líneas (item_code, description, qty, unit_price, amount)
            </label>
            <textarea
              value={linesRaw}
              onChange={(e) => setLinesRaw(e.target.value)}
              className="w-full border rounded px-2 py-2 h-32"
              placeholder="SOV-10, Hormigón 25MPa, 10, 50000"
            ></textarea>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">
              Deducciones (type, description, amount)
            </label>
            <textarea
              value={deductionsRaw}
              onChange={(e) => setDeductionsRaw(e.target.value)}
              className="w-full border rounded px-2 py-2 h-24"
              placeholder="retencion, Retención Garantía 5%, 150000"
            ></textarea>
          </div>
          <div className="flex gap-2 items-center flex-wrap">
            <div className="flex items-center gap-2">
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) readExcel(f);
                }}
              />
              {excelRows && (
                <span className="text-xs text-slate-500">{excelRows.length} filas de Excel</span>
              )}
            </div>
            <button
              disabled={loading}
              onClick={submit}
              className="px-3 py-1 rounded bg-lime-700 text-white hover:bg-lime-800 disabled:opacity-50"
            >
              {loading ? 'Importando…' : 'Importar EP'}
            </button>
            <button
              disabled={loading}
              onClick={() => {
                setLinesRaw('');
                setDeductionsRaw('');
                setEpNumber('');
                setPeriodStart('');
                setPeriodEnd('');
              }}
              className="px-3 py-1 rounded border"
            >
              Limpiar
            </button>
          </div>
          {excelRows && (
            <div className="mt-4 space-y-3">
              <div className="text-sm text-slate-600">Mapear columnas:</div>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                {(
                  ['item_code', 'description', 'qty_period', 'unit_price', 'amount_period'] as const
                ).map((k) => (
                  <div key={k}>
                    <label className="block text-xs text-slate-500 mb-1">{k}</label>
                    <select
                      value={mapping[k]}
                      onChange={(e) => setMapping((prev) => ({ ...prev, [k]: e.target.value }))}
                      className="w-full border rounded px-2 py-1"
                    >
                      {excelCols.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Previsualización</label>
                <div className="text-xs max-h-40 overflow-auto border rounded">
                  <table className="w-full">
                    <thead>
                      <tr>
                        <th className="px-2 py-1 text-left">item_code</th>
                        <th className="px-2 py-1 text-left">description</th>
                        <th className="px-2 py-1 text-right">qty</th>
                        <th className="px-2 py-1 text-right">unit_price</th>
                        <th className="px-2 py-1 text-right">amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rowsFromExcel()
                        .slice(0, 10)
                        .map((r, i) => (
                          <tr key={i}>
                            <td className="px-2 py-1">{r.item_code}</td>
                            <td className="px-2 py-1">{r.description}</td>
                            <td className="px-2 py-1 text-right">{r.qty_period}</td>
                            <td className="px-2 py-1 text-right">{r.unit_price}</td>
                            <td className="px-2 py-1 text-right">{r.amount_period}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
