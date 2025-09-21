'use client';

import { useEffect, useState } from 'react';
import DataTable from '@/components/ui/DataTable';

export default function RiesgosPrediccionesPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api';
      const resp = await fetch(`${base}/riesgos/resumen`);
      const payload = await resp.json();
      setItems(payload.items || []);
      setLoading(false);
    }
    load();
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
          Predicciones de Riesgo
        </h1>
        <p className="text-slate-500 dark:text-slate-400">Score más alto por proyecto</p>
      </div>
      <DataTable
        columns={
          [
            { key: 'project_id', label: 'Proyecto' },
            { key: 'riesgo', label: 'Categoría' },
            { key: 'nivel', label: 'Score' },
          ] as any
        }
        data={items}
        loading={loading}
        emptyMessage="Sin predicciones"
      />
    </div>
  );
}
