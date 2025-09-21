'use client';

import { useEffect, useState } from 'react';
import DataTable from '@/components/ui/DataTable';

export default function SubcontratistasPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api';
        // Mostrar los últimos EP de subcontratos sin filtro
        const resp = await fetch(`${base}/sc/ep?limit=100`);
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
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Subcontratistas</h1>
      <p className="text-slate-600 dark:text-slate-400">EP recientes de subcontratistas</p>
      <DataTable
        columns={
          [
            { key: 'id', label: 'EP ID' },
            { key: 'project_id', label: 'Proyecto' },
            { key: 'ep_number', label: 'EP #' },
            {
              key: 'period',
              label: 'Periodo',
              render: (_: any, row: any) => `${row.period_start || '-'} → ${row.period_end || '-'}`,
            },
            { key: 'status', label: 'Estado' },
            {
              key: 'lines_subtotal',
              label: 'Subtotal',
              render: (v: number) =>
                new Intl.NumberFormat('es-CL', {
                  style: 'currency',
                  currency: 'CLP',
                  minimumFractionDigits: 0,
                }).format(Number(v || 0)),
            },
            {
              key: 'deductions_total',
              label: 'Deducciones',
              render: (v: number) =>
                new Intl.NumberFormat('es-CL', {
                  style: 'currency',
                  currency: 'CLP',
                  minimumFractionDigits: 0,
                }).format(Number(v || 0)),
            },
            {
              key: 'amount_net_estimate',
              label: 'Neto',
              render: (v: number) =>
                new Intl.NumberFormat('es-CL', {
                  style: 'currency',
                  currency: 'CLP',
                  minimumFractionDigits: 0,
                }).format(Number(v || 0)),
            },
          ] as any
        }
        data={items}
        loading={loading}
        emptyMessage="Sin EP de subcontratos"
      />
    </div>
  );
}
