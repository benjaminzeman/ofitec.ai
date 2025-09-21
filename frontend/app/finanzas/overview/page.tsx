'use client';

import { useEffect, useState } from 'react';
import KpiCard from '@/components/ui/KpiCard';
import StackedBar from '@/components/ui/StackedBar';
import ActionsList from '@/components/ui/ActionsList';
import { fetchFinanceOverview, FinanceOverview } from '@/lib/api';

const peso = (n: number) =>
  new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
  }).format(n || 0);

export default function FinanceOverviewPage() {
  const [data, setData] = useState<FinanceOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const d = await fetchFinanceOverview();
        setData(d);
      } catch (e: any) {
        console.error(e);
        setError('No se pudo cargar el resumen financiero.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-8 w-48 bg-slate-200 dark:bg-slate-700 rounded" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="h-28 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <div className="bg-white dark:bg-slate-800 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 rounded-xl p-6">
          {error || 'Sin datos'}
        </div>
      </div>
    );
  }

  const { cash, revenue, ar, ap, conciliacion, acciones } = data;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Resumen Financiero
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Liquidez, cuentas por cobrar/pagar y conciliación
          </p>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard title="Caja Hoy" value={peso(cash.today)} icon={'💵'} accent="lime" />
        <KpiCard title="Cobros Mes" value={peso(revenue.month)} icon={'🧾'} accent="blue" />
        <KpiCard title="Cobros YTD" value={peso(revenue.ytd)} icon={'📈'} accent="amber" />
        <KpiCard
          title="Tasa Conciliación"
          value={`${Math.round((conciliacion?.tasa ?? 0) * 100)}%`}
          icon={'🔗'}
          accent="lime"
        />
      </div>

      {/* AR Aging */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Cuentas por Cobrar (CxC)
          </h3>
        </div>
        <StackedBar
          segments={[
            { label: '0-30', value: ar.aging.d0_30, color: '#65a30d' },
            { label: '31-60', value: ar.aging.d31_60, color: '#f59e0b' },
            { label: '61-90', value: ar.aging.d61_90, color: '#ef4444' },
            { label: '90+', value: ar.aging.d90p, color: '#7c3aed' },
          ]}
        />
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              Top Clientes
            </h4>
            <ul className="space-y-2">
              {ar.top_clientes.slice(0, 5).map((c, i) => (
                <li key={i} className="flex items-center justify-between text-sm">
                  <span className="text-slate-600 dark:text-slate-400">{c.name}</span>
                  <span className="font-medium text-slate-900 dark:text-slate-100">
                    {peso(c.amount)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Alertas</h4>
            <ul className="list-disc list-inside text-sm text-slate-600 dark:text-slate-400">
              <li>{peso(ar.aging.d61_90 + ar.aging.d90p)} vencidos &gt; 60 días</li>
            </ul>
          </div>
        </div>
      </div>

      {/* AP */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Cuentas por Pagar (CxP)
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <KpiCard title="Vence 7d" value={peso(ap.d7)} icon={'⏱️'} />
          <KpiCard title="Vence 14d" value={peso(ap.d14)} icon={'🗓️'} />
          <KpiCard title="Vence 30d" value={peso(ap.d30)} icon={'📅'} />
        </div>
        <div className="mt-4">
          <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            Top Proveedores
          </h4>
          <ul className="space-y-2">
            {ap.top_proveedores.slice(0, 5).map((p, i) => (
              <li key={i} className="flex items-center justify-between text-sm">
                <span className="text-slate-600 dark:text-slate-400">{p.name}</span>
                <span className="font-medium text-slate-900 dark:text-slate-100">
                  {peso(p.amount)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Acciones */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Acciones Sugeridas
        </h3>
        <ActionsList
          items={acciones.map((a, i) => ({
            id: a.id || i,
            title: a.title,
            description: a.description,
            priority: a.priority as any,
          }))}
        />
      </div>
    </div>
  );
}
