'use client';

import { useEffect, useState } from 'react';
import DataTable from '@/components/ui/DataTable';
import ConciliarButton from '@/components/ConciliarButton';

export default function PreviredPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api';
        const resp = await fetch(`${base}/finanzas/previred`);
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
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Previred</h1>
        <p className="text-slate-500 dark:text-slate-400">Fuente: v_previred</p>
      </div>
      <DataTable
        columns={
          [
            { key: 'periodo', label: 'Periodo' },
            { key: 'rut_trabajador', label: 'RUT Trabajador' },
            { key: 'nombre_trabajador', label: 'Nombre' },
            { key: 'rut_empresa', label: 'RUT Empresa' },
            { key: 'monto_total', label: 'Monto' },
            { key: 'estado', label: 'Estado' },
            { key: 'fecha_pago', label: 'Fecha Pago' },
            {
              key: 'acciones',
              label: 'Acciones',
              render: (_: any, row: any) => (
                <ConciliarButton
                  sourceType="payroll"
                  getSource={() => ({
                    id: row.id ?? undefined,
                    amount: Number(row.monto_total ?? row.monto ?? 0),
                    date: row.fecha_pago || row.periodo || undefined,
                    ref: `${row.rut_trabajador || row.nombre_trabajador || 'PAY'}-${row.periodo || ''}`,
                  })}
                />
              ),
            },
          ] as any
        }
        data={items}
        loading={loading}
        emptyMessage="Sin registros"
      />
    </div>
  );
}
