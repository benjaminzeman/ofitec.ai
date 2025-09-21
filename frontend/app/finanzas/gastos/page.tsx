'use client';

import { useEffect, useState, useMemo } from 'react';
import DataTable from '@/components/ui/DataTable';
import ConciliarButton from '@/components/ConciliarButton';
import { fetchReconcileLinks, formatCurrency, formatDate } from '@/lib/api';

export default function GastosPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [linksById, setLinksById] = useState<
    Record<
      string,
      {
        loading: boolean;
        items: Array<{ id: number; amount: number; type: string; ref: string; fecha: string }>;
        error?: string;
      }
    >
  >({});
  // Drawer handled by ConciliarButton

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const base =
          typeof window !== 'undefined'
            ? '/api'
            : process.env.NEXT_PUBLIC_API_BASE ||
              `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5555'}/api`;
        const resp = await fetch(`${base}/finanzas/gastos`);
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
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Gastos</h1>
        <p className="text-slate-500 dark:text-slate-400">Fuente: v_gastos</p>
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
                    const key = String(row.gasto_id);
                    const newKey = expandedId === key ? null : key;
                    setExpandedId(newKey);
                    if (newKey && !linksById[newKey]) {
                      setLinksById((prev) => ({ ...prev, [newKey]: { loading: true, items: [] } }));
                      fetchReconcileLinks({ expense_id: Number(row.gasto_id) })
                        .then((res) =>
                          setLinksById((prev) => ({
                            ...prev,
                            [newKey]: { loading: false, items: res.items || [] },
                          })),
                        )
                        .catch((err) =>
                          setLinksById((prev) => ({
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
                  {expandedId === String(row.gasto_id) ? '▾' : '▸'}
                </button>
              ),
            },
            { key: 'fecha', label: 'Fecha' },
            { key: 'categoria', label: 'Categoría' },
            { key: 'descripcion', label: 'Descripción' },
            { key: 'monto', label: 'Monto', render: (v: number) => formatCurrency(Number(v || 0)) },
            { key: 'moneda', label: 'Moneda' },
            { key: 'proveedor_rut', label: 'Proveedor RUT' },
            { key: 'proyecto', label: 'Proyecto' },
            {
              key: 'acciones',
              label: 'Acciones',
              render: (_: any, row: any) => (
                <ConciliarButton
                  sourceType="expense"
                  getSource={() => ({
                    amount: Number(row.monto || 0),
                    date: row.fecha,
                    ref: String(row.gasto_id || row.descripcion || ''),
                    currency: row.moneda,
                  })}
                />
              ),
            },
          ] as any
        }
        data={items}
        loading={loading}
        emptyMessage="Sin gastos"
        isRowExpanded={(row: any) => expandedId === String(row.gasto_id)}
        renderExpandedRow={(row: any) => {
          const key = String(row.gasto_id);
          const entry = linksById[key];
          if (!entry) return <div className="text-slate-500">Cargando…</div>;
          if (entry.loading) return <div className="text-slate-500">Cargando…</div>;
          if (entry.error) return <div className="text-red-600">{entry.error}</div>;
          if (!entry.items?.length)
            return (
              <div className="text-slate-500">Sin enlaces de conciliación para este gasto.</div>
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
                        className={`px-2 py-0.5 rounded-full text-xs ${it.type === 'bank' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200' : it.type === 'sales' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200' : it.type === 'purchase' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-200' : 'bg-slate-100 text-slate-700 dark:bg-slate-900/40 dark:text-slate-200'}`}
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
