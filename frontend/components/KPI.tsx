import React from 'react';

export function KPICard({
  title,
  value,
  subtitle,
  accent = 'lime',
}: {
  title: string;
  value: string;
  subtitle?: string;
  accent?: 'lime' | 'green' | 'amber' | 'red' | 'blue';
}) {
  const accentMap: Record<string, string> = {
    lime: 'text-lime-700 bg-lime-50 dark:text-lime-400 dark:bg-lime-950',
    green: 'text-green-700 bg-green-50 dark:text-green-400 dark:bg-green-950',
    amber: 'text-amber-700 bg-amber-50 dark:text-amber-400 dark:bg-amber-950',
    red: 'text-red-700 bg-red-50 dark:text-red-400 dark:bg-red-950',
    blue: 'text-blue-700 bg-blue-50 dark:text-blue-400 dark:bg-blue-950',
  };
  const accentCls = accentMap[accent] || accentMap.lime;
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5">
      <div className="text-sm text-slate-500 dark:text-slate-400">{title}</div>
      <div className={`mt-2 inline-flex px-3 py-2 rounded-lg text-xl font-semibold ${accentCls}`}>
        {value}
      </div>
      {subtitle && (
        <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">{subtitle}</div>
      )}
    </div>
  );
}

export function formatCLP(n: number) {
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n || 0);
}
