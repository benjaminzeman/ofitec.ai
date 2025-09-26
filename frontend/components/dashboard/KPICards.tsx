'use client';

import { useDashboardData } from '@/hooks/useDashboardData';
import { MetricaIcono, EstadoBadge } from '@/lib/icons';

export function KPICards() {
  const { kpis, loading, error } = useDashboardData();

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm animate-pulse"
          >
            <div className="p-6">
              <div className="h-4 bg-slate-100 dark:bg-slate-700 rounded mb-2"></div>
              <div className="h-8 bg-slate-100 dark:bg-slate-700 rounded mb-4"></div>
              <div className="h-4 bg-slate-100 dark:bg-slate-700 rounded w-1/2"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error || !kpis) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
          <div className="p-6">
            <p className="text-red-500">Error: {error || 'No data available'}</p>
          </div>
        </div>
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('es-CL').format(num);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
      {/* Total Orders */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-500 dark:text-slate-400 text-sm mb-1">Órdenes Totales</p>
              <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
                {formatNumber(kpis.total_orders)}
              </p>
            </div>
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center">
              <MetricaIcono tipo="ordenes" value="" size="lg" />
            </div>
          </div>
          <div className="mt-4 flex items-center">
            <MetricaIcono 
              tipo="ordenes" 
              value={`${kpis.growth_rate > 0 ? '+' : ''}${kpis.growth_rate.toFixed(1)}%`}
              trend={kpis.growth_rate >= 0 ? "up" : "down"}
              size="sm"
            />
            <span className="text-slate-500 dark:text-slate-400 text-sm ml-2">vs mes anterior</span>
          </div>
        </div>
      </div>

      {/* Total Providers */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-500 dark:text-slate-400 text-sm mb-1">Proveedores</p>
              <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
                {formatNumber(kpis.total_providers)}
              </p>
            </div>
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center">
              <MetricaIcono tipo="proveedores" value="" size="lg" />
            </div>
          </div>
          <div className="mt-4 flex items-center">
            <EstadoBadge estado="vigente" showLabel={false} size="xs" />
            <span className="text-sm text-lime-500 ml-2">{formatNumber(kpis.active_providers)}</span>
            <span className="text-slate-500 dark:text-slate-400 text-sm ml-2">
              activos este mes
            </span>
          </div>
        </div>
      </div>

      {/* Total Projects */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-500 dark:text-slate-400 text-sm mb-1">Proyectos</p>
              <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
                {formatNumber(kpis.total_projects)}
              </p>
            </div>
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center">
              <MetricaIcono tipo="proyectos" value="" size="lg" />
            </div>
          </div>
          <div className="mt-4 flex items-center">
            <EstadoBadge estado="pendiente" showLabel={false} size="xs" />
            <span className="text-sm text-lime-500 ml-2">{Math.round(kpis.total_projects * 0.3)}</span>
            <span className="text-slate-500 dark:text-slate-400 text-sm ml-2">en progreso</span>
          </div>
        </div>
      </div>

      {/* Total Amount */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-500 dark:text-slate-400 text-sm mb-1">Facturación</p>
              <p className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
                {formatCurrency(kpis.total_amount)}
              </p>
            </div>
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center">
              <MetricaIcono tipo="revenue" value="" size="lg" />
            </div>
          </div>
          <div className="mt-4 flex items-center">
            <MetricaIcono tipo="revenue" value="+8%" trend="up" size="sm" />
            <span className="text-slate-500 dark:text-slate-400 text-sm ml-2">vs objetivo</span>
          </div>
        </div>
      </div>
    </div>
  );
}
