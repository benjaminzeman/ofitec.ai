'use client';

import { useEffect, useState } from 'react';
import DataTable from '@/components/ui/DataTable';

export default function ProyectosFinancieroPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api';
        const resp = await fetch(`${base}/proyectos/kpis`);
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
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
        Proyectos - Vista Financiera
      </h1>
      <p className="text-slate-600 dark:text-slate-400">
        KPIs por proyecto: Presupuesto, Compras, Ventas, Margen, Avance, Riesgo
      </p>
      <DataTable
        columns={
          [
            { key: 'project_id', label: 'ID' },
            { key: 'proyecto', label: 'Proyecto' },
            {
              key: 'presupuesto',
              label: 'Presupuesto',
              render: (v: number) =>
                new Intl.NumberFormat('es-CL', {
                  style: 'currency',
                  currency: 'CLP',
                  minimumFractionDigits: 0,
                }).format(Number(v || 0)),
            },
            {
              key: 'compras',
              label: 'Compras',
              render: (v: number) =>
                new Intl.NumberFormat('es-CL', {
                  style: 'currency',
                  currency: 'CLP',
                  minimumFractionDigits: 0,
                }).format(Number(v || 0)),
            },
            {
              key: 'ventas',
              label: 'Ventas',
              render: (v: number) =>
                new Intl.NumberFormat('es-CL', {
                  style: 'currency',
                  currency: 'CLP',
                  minimumFractionDigits: 0,
                }).format(Number(v || 0)),
            },
            {
              key: 'margen',
              label: 'Margen',
              render: (v: number) =>
                new Intl.NumberFormat('es-CL', {
                  style: 'currency',
                  currency: 'CLP',
                  minimumFractionDigits: 0,
                }).format(Number(v || 0)),
            },
            { key: 'avance', label: 'Avance (%)' },
            { key: 'riesgo', label: 'Riesgo (score)' },
          ] as any
        }
        data={items}
        loading={loading}
        emptyMessage="Sin proyectos"
      />
    </div>
  );
}
