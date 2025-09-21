'use client';

import { useEffect, useMemo, useState } from 'react';
import DataTable from '@/components/ui/DataTable';
import ConciliarButton from '@/components/ConciliarButton';

interface BalanceRow {
  banco: string;
  cuenta: string;
  moneda: string;
  saldo_actual?: number;
  saldo_calc?: number;
  movimientos_30d?: number;
}

export default function TesoreriaPage() {
  const [data, setData] = useState<BalanceRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const columns = useMemo(
    () => [
      { key: 'banco', label: 'Banco', sortable: true },
      { key: 'cuenta', label: 'Cuenta', sortable: true },
      { key: 'moneda', label: 'Moneda', sortable: true },
      {
        key: 'saldo_actual',
        label: 'Saldo',
        sortable: true,
        render: (v: number, row: any) =>
          new Intl.NumberFormat('es-CL', {
            style: 'currency',
            currency: row.moneda || 'CLP',
            minimumFractionDigits: 0,
          }).format(Number(v ?? row.saldo_calc ?? 0)),
      },
      { key: 'movimientos_30d', label: 'Mov. 30d' },
      {
        key: 'acciones',
        label: 'Acciones',
        render: (_: any, row: any) => (
          <ConciliarButton
            sourceType="bank"
            getSource={() => ({
              ref: `${row.banco || 'BANCO'}-${row.cuenta || ''}`,
              currency: row.moneda || 'CLP',
            })}
          />
        ),
      },
    ],
    [],
  );

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const resp = await fetch(
          process.env.NEXT_PUBLIC_API_BASE
            ? `${process.env.NEXT_PUBLIC_API_BASE}/tesoreria/saldos`
            : 'http://localhost:5555/api/tesoreria/saldos',
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const payload = await resp.json();
        setData(payload.items || []);
      } catch (e: any) {
        setError(e?.message || 'Error cargando saldos');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
          Saldos de Tesorería
        </h1>
        <p className="text-slate-500 dark:text-slate-400">Consolidado por cuenta bancaria</p>
      </div>
      <DataTable columns={columns as any} data={data} loading={loading} emptyMessage="Sin saldos" />
    </div>
  );
}
