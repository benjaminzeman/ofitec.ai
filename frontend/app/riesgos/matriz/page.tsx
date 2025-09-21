'use client';

import { useEffect, useState } from 'react';
import DataTable from '@/components/ui/DataTable';

export default function RiesgosMatrizPage() {
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
          Matriz de Riesgos
        </h1>
        <p className="text-slate-500 dark:text-slate-400">Fuente: risk_matrix / risk_predictions</p>
      </div>
      <DataTable
        columns={
          [
            { key: 'project_id', label: 'Proyecto' },
            { key: 'riesgo', label: 'Riesgo' },
            { key: 'probabilidad', label: 'Prob.' },
            { key: 'impacto', label: 'Impacto' },
            { key: 'nivel', label: 'Nivel' },
            { key: 'estado', label: 'Estado' },
            { key: 'owner', label: 'Owner' },
          ] as any
        }
        data={items}
        loading={loading}
        emptyMessage="Sin riesgos"
      />
    </div>
  );
}
