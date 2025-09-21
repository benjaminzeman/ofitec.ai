'use client';

import { useEffect, useState } from 'react';
import { KPICards } from '@/components/dashboard/KPICards';
import { ChartsGrid } from '@/components/dashboard/ChartsGrid';
import KpiCard from '@/components/ui/KpiCard';
import ActionsList from '@/components/ui/ActionsList';
import Link from 'next/link';
import { fetchCeoOverview, CeoOverview } from '@/lib/api';

export default function DashboardPage() {
  const [ceo, setCeo] = useState<CeoOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const d = await fetchCeoOverview();
        setCeo(d);
      } catch (e: any) {
        console.warn('CEO overview fallback', e);
        setError('No se pudo cargar el resumen ejecutivo. Mostrando panel estándar.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const peso = (n: number) =>
    new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
    }).format(n || 0);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            Dashboard Principal
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Resumen ejecutivo de la actividad comercial y operacional
          </p>
          {error && <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">{error}</p>}
        </div>
        <div className="flex gap-2">
          <Link
            href="/finanzas/overview"
            className="px-3 py-2 bg-lime-500 text-white rounded-xl text-sm hover:bg-lime-600"
          >
            Ver Resumen Finanzas
          </Link>
          <Link
            href="/proyectos/overview"
            className="px-3 py-2 bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-xl text-sm border border-slate-200 dark:border-slate-600 hover:bg-slate-200 dark:hover:bg-slate-600"
          >
            Ver Resumen Proyectos
          </Link>
        </div>
      </div>

      {/* CEO Overview (when available) */}
      {ceo ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard title="Caja Hoy" value={peso(ceo.cash.today)} icon={'💵'} accent="lime" />
          <KpiCard
            title="Facturación Mes"
            value={peso(ceo.revenue.month)}
            icon={'🧾'}
            accent="blue"
          />
          <KpiCard title="Proyectos" value={ceo.projects.total} icon={'🏗️'} accent="amber" />
          <KpiCard title="Riesgo Alto" value={ceo.risk.high} icon={'⚠️'} accent="red" />
        </div>
      ) : (
        <KPICards />
      )}

      {/* Charts */}
      <ChartsGrid />

      {/* Quick Actions */}
      <div className="mt-6">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
          <div className="p-6">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
              Acciones Rápidas
            </h3>
            {ceo ? (
              <ActionsList items={ceo.acciones || []} />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Link
                  href="/finanzas/ordenes-compra"
                  className="text-center bg-lime-500 hover:bg-lime-600 text-white px-4 py-2 rounded-xl font-medium transition-colors"
                >
                  Nueva Orden de Compra
                </Link>
                <Link
                  href="/proveedores"
                  className="text-center bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-900 dark:text-slate-100 px-4 py-2 rounded-xl font-medium transition-colors border border-slate-200 dark:border-slate-600"
                >
                  Consultar Proveedor
                </Link>
                <Link
                  href="/finanzas/reportes-proyectos"
                  className="text-center bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-900 dark:text-slate-100 px-4 py-2 rounded-xl font-medium transition-colors border border-slate-200 dark:border-slate-600"
                >
                  Ver Reportes
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
