'use client';

import React from 'react';
import { CategoriasIconos } from '@/lib/icons';

type Trend = {
  value: number;
  label?: string;
  direction?: 'up' | 'down' | 'flat';
};

export interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode | string; // Permite tanto ReactNode como string para iconos
  trend?: Trend;
  accent?: 'lime' | 'blue' | 'amber' | 'red' | 'slate';
}

const accentMap: Record<string, { box: string; text: string }> = {
  lime: { box: 'bg-lime-50 dark:bg-lime-950', text: 'text-lime-600 dark:text-lime-400' },
  blue: { box: 'bg-blue-50 dark:bg-blue-950', text: 'text-blue-600 dark:text-blue-400' },
  amber: { box: 'bg-amber-50 dark:bg-amber-950', text: 'text-amber-600 dark:text-amber-400' },
  red: { box: 'bg-red-50 dark:bg-red-950', text: 'text-red-600 dark:text-red-400' },
  slate: { box: 'bg-slate-100 dark:bg-slate-900', text: 'text-slate-600 dark:text-slate-400' },
};

export default function KpiCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  accent = 'slate',
}: KpiCardProps) {
  const colors = accentMap[accent];
  const trendSymbol = trend?.direction === 'up' ? '↑' : trend?.direction === 'down' ? '↓' : '→';
  const trendColor =
    trend?.direction === 'down'
      ? 'text-red-600 dark:text-red-400'
      : trend?.direction === 'up'
        ? 'text-lime-600 dark:text-lime-400'
        : 'text-slate-500 dark:text-slate-400';

  // Renderizar ícono - soporta tanto string (para iconos de Lucide) como ReactNode
  const renderIcon = () => {
    if (typeof icon === 'string') {
      // Si es string, buscar en CategoriasIconos.financiero
      const IconComponent = CategoriasIconos.financiero[icon];
      if (IconComponent) {
        return <IconComponent className={`w-6 h-6 ${colors.text}`} />;
      }
    }
    // Si es ReactNode o no se encontró el icono, renderizar como antes
    return <span className={`${colors.text} text-xl`}>{icon}</span>;
  };

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-600 dark:text-slate-400">{title}</p>
          <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">{value}</p>
          {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>}
          {trend && (
            <p className={`mt-1 text-xs font-medium ${trendColor}`}>
              <span className="mr-1">{trendSymbol}</span>
              {trend.value}
              {typeof trend.value === 'number' ? '%' : ''} {trend.label || ''}
            </p>
          )}
        </div>
        <div className={`w-12 h-12 ${colors.box} rounded-xl flex items-center justify-center`}>
          {renderIcon()}
        </div>
      </div>
    </div>
  );
}
