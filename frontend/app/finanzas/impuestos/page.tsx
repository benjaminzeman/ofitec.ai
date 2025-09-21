'use client';

import { useEffect, useState } from 'react';
import DataTable from '@/components/ui/DataTable';
import ConciliarButton from '@/components/ConciliarButton';
import { fetchReconcileLinks, formatCurrency, formatDate } from '@/lib/api';

export default function ImpuestosPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [linksByKey, setLinksByKey] = useState<
    Record<
      string,
      {
        loading: boolean;
        items: Array<{ id: number; amount: number; type: string; ref: string; fecha: string }>;
        error?: string;
      }
    >
  >({});

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api';
        const resp = await fetch(`${base}/finanzas/impuestos`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const payload = await resp.json();
        setItems(payload.items || []);
      } catch (e: any) {
        setError(e?.message || 'Error');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Impuestos</h1>
        <p className="text-slate-500 dark:text-slate-400">Fuente: v_impuestos</p>
      </div>
      <DataTable
        columns={
          [
            {
              key: 'expand',
              label: '',
              width: '40px',
              render: (_: any, row: any) => (
                <button
                  className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                  title="Ver enlaces de conciliación"
                  onClick={(e) => {
                    e.stopPropagation();
                    const key = `${row.periodo}|${row.tipo}`;
                    const newKey = expandedKey === key ? null : key;
                    setExpandedKey(newKey);
                    if (newKey && !linksByKey[newKey]) {
                      setLinksByKey((prev) => ({
                        ...prev,
                        [newKey]: { loading: true, items: [] },
                      }));
                      fetchReconcileLinks({
                        tax_period: String(row.periodo),
                        tax_tipo: String(row.tipo),
                      } as any)
                        .then((res) =>
                          setLinksByKey((prev) => ({
                            ...prev,
                            [newKey]: { loading: false, items: res.items || [] },
                          })),
                        )
                        .catch((err) =>
                          setLinksByKey((prev) => ({
                            ...prev,
                            [newKey]: {
                              loading: false,
                              items: [],
                              error: err?.message || 'Error cargando enlaces',
                            },
                          })),
                        );
                    }
                  }}
                >
                  {expandedKey === `${row.periodo}|${row.tipo}` ? '▾' : '▸'}
                </button>
              ),
            },
            { key: 'periodo', label: 'Periodo' },
            { key: 'tipo', label: 'Tipo' },
            {
              key: 'monto_debito',
              label: 'Débito',
              render: (v: number) => formatCurrency(Number(v || 0)),
            },
            {
              key: 'monto_credito',
              label: 'Crédito',
              render: (v: number) => formatCurrency(Number(v || 0)),
            },
            { key: 'neto', label: 'Neto', render: (v: number) => formatCurrency(Number(v || 0)) },
            { key: 'estado', label: 'Estado' },
            { key: 'fecha_presentacion', label: 'Fecha Presentación' },
            {
              key: 'acciones',
              label: 'Acciones',
              render: (_: any, row: any) => (
                <ConciliarButton
                  sourceType="tax"
                  getSource={() => ({
                    id: row.id ?? undefined,
                    amount: Number(row.neto ?? row.monto_total ?? row.monto ?? 0),
                    date: row.fecha_presentacion || row.periodo || undefined,
                    ref: `${row.tipo || 'IMP'}-${row.periodo || ''}`,
                  })}
                />
              ),
            },
          ] as any
        }
        data={items}
        loading={loading}
        emptyMessage="Sin impuestos"
        isRowExpanded={(row: any) => expandedKey === `${row.periodo}|${row.tipo}`}
        renderExpandedRow={(row: any) => {
          const key = `${row.periodo}|${row.tipo}`;
          const entry = linksByKey[key];
          if (!entry) return <div className="text-slate-500">Cargando…</div>;
          if (entry.loading) return <div className="text-slate-500">Cargando…</div>;
          if (entry.error) return <div className="text-red-600">{entry.error}</div>;
          if (!entry.items?.length)
            return (
              <div className="text-slate-500">Sin enlaces de conciliación para este impuesto.</div>
            );
          return (
            <div className="space-y-2">
              <div className="text-xs text-slate-500">
                Enlaces de conciliación ({entry.items.length})
              </div>
              <ul className="space-y-1">
                {entry.items.map((it, i) => (
                  <li key={i} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs ${it.type === 'bank' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200' : it.type === 'sales' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200' : it.type === 'purchase' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-200' : it.type === 'expense' ? 'bg-slate-100 text-slate-700 dark:bg-slate-900/40 dark:text-slate-200' : 'bg-slate-100 text-slate-700 dark:bg-slate-900/40 dark:text-slate-200'}`}
                      >
                        {it.type}
                      </span>
                      <span className="text-slate-700 dark:text-slate-200">{it.ref || 's/n'}</span>
                      <span className="text-slate-500">· {formatDate(it.fecha)}</span>
                    </div>
                    <div className="font-medium">{formatCurrency(it.amount || 0)}</div>
                  </li>
                ))}
              </ul>
            </div>
          );
        }}
      />
    </div>
  );
}
