'use client';

import { useDashboardData } from '@/hooks/useDashboardData';

export function ChartsGrid() {
  const { ordersChart, topProviders, loading, error } = useDashboardData();

  if (loading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl animate-pulse">
          <div className="p-6">
            <div className="h-6 bg-slate-100 dark:bg-slate-700 rounded mb-4"></div>
            <div className="h-64 bg-slate-100 dark:bg-slate-700 rounded"></div>
          </div>
        </div>
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl animate-pulse">
          <div className="p-6">
            <div className="h-6 bg-slate-100 dark:bg-slate-700 rounded mb-4"></div>
            <div className="space-y-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-4 bg-slate-100 dark:bg-slate-700 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
          <div className="p-6">
            <p className="text-red-500">Error: {error}</p>
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

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Orders Chart */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Órdenes por Mes
          </h3>
          <div className="h-64 bg-slate-50 dark:bg-slate-900 rounded-xl flex items-center justify-center">
            {ordersChart.length > 0 ? (
              <div className="w-full h-full p-4">
                <div className="flex items-end justify-between h-full space-x-2">
                  {ordersChart.slice(-6).map((data, _index) => (
                    <div key={data.month} className="flex-1 flex flex-col items-center">
                      <div
                        className="bg-lime-500 rounded-t w-full transition-all duration-300 hover:bg-lime-600"
                        style={{
                          height: `${Math.max((data.orders / Math.max(...ordersChart.map((d) => d.orders))) * 100, 5)}%`,
                          minHeight: '20px',
                        }}
                      ></div>
                      <span className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                        {new Date(data.month + '-01').toLocaleDateString('es-CL', {
                          month: 'short',
                        })}
                      </span>
                      <span className="text-xs text-slate-600 dark:text-slate-300">
                        {data.orders}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-slate-500 dark:text-slate-400">No hay datos disponibles</p>
            )}
          </div>
        </div>
      </div>

      {/* Top Providers */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
        <div className="p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Top Proveedores
          </h3>
          <div className="space-y-4">
            {topProviders.slice(0, 5).map((provider, index) => (
              <div key={provider.name} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-lime-50 dark:bg-lime-950 rounded-full flex items-center justify-center">
                    <span className="text-sm font-semibold text-lime-600 dark:text-lime-400">
                      {index + 1}
                    </span>
                  </div>
                  <div>
                    <p className="text-slate-700 dark:text-slate-300 font-medium">
                      {provider.name.length > 25
                        ? provider.name.substring(0, 25) + '...'
                        : provider.name}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {provider.orders} órdenes
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-slate-900 dark:text-slate-100 font-semibold">
                    {formatCurrency(provider.amount)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
