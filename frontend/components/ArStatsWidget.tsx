'use client';

import { useState, useEffect } from 'react';
import { formatCurrency } from '@/lib/api';

interface ArStatsProps {
  className?: string;
}

interface ArRuleStats {
  rules_total: number;
  rules_by_kind: Record<string, number>;
  invoices_total: number;
  invoices_with_project: number;
  project_assign_rate: number | null;
  distinct_customer_names: number;
  customer_names_with_rule: number;
  customer_name_rule_coverage: number | null;
  recent_events_30d: number;
  generated_at: string;
}

async function fetchArStats(): Promise<ArRuleStats> {
  const resp = await fetch('/api/ar/rules_stats');
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export default function ArStatsWidget({ className = '' }: ArStatsProps) {
  const [stats, setStats] = useState<ArRuleStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchArStats();
        setStats(data);
      } catch (e: any) {
        setError(e?.message || 'Error cargando estadísticas');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) {
    return (
      <div className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 ${className}`}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-slate-200 dark:bg-slate-600 rounded w-1/3"></div>
          <div className="space-y-2">
            <div className="h-3 bg-slate-200 dark:bg-slate-600 rounded"></div>
            <div className="h-3 bg-slate-200 dark:bg-slate-600 rounded w-2/3"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 ${className}`}>
        <div className="text-center text-slate-500 dark:text-slate-400">
          <span className="text-lg">⚠️</span>
          <div className="text-sm mt-1">{error || 'No hay datos disponibles'}</div>
        </div>
      </div>
    );
  }

  const assignRate = stats.project_assign_rate ? Math.round(stats.project_assign_rate * 100) : 0;
  const coverageRate = stats.customer_name_rule_coverage ? Math.round(stats.customer_name_rule_coverage * 100) : 0;

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          Sistema AR Inteligente
        </h3>
        <span className="text-xs text-slate-500 bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded">
          🤖 ML
        </span>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="text-center p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
            {assignRate}%
          </div>
          <div className="text-xs text-slate-600 dark:text-slate-300">
            Facturas Asignadas
          </div>
        </div>

        <div className="text-center p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
          <div className="text-lg font-bold text-slate-900 dark:text-slate-100">
            {coverageRate}%
          </div>
          <div className="text-xs text-slate-600 dark:text-slate-300">
            Cobertura de Reglas
          </div>
        </div>
      </div>

      {/* Detailed Stats */}
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-600 dark:text-slate-300">Facturas totales:</span>
          <span className="font-medium text-slate-900 dark:text-slate-100">
            {stats.invoices_total.toLocaleString()}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-slate-600 dark:text-slate-300">Con proyecto:</span>
          <span className="font-medium text-slate-900 dark:text-slate-100">
            {stats.invoices_with_project.toLocaleString()}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-slate-600 dark:text-slate-300">Reglas activas:</span>
          <span className="font-medium text-slate-900 dark:text-slate-100">
            {stats.rules_total.toLocaleString()}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-slate-600 dark:text-slate-300">Clientes únicos:</span>
          <span className="font-medium text-slate-900 dark:text-slate-100">
            {stats.distinct_customer_names.toLocaleString()}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-slate-600 dark:text-slate-300">Eventos (30d):</span>
          <span className="font-medium text-slate-900 dark:text-slate-100">
            {stats.recent_events_30d.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Rules Breakdown */}
      {Object.keys(stats.rules_by_kind).length > 0 && (
        <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-600">
          <div className="text-xs font-medium text-slate-700 dark:text-slate-200 mb-2">
            Tipos de Reglas:
          </div>
          <div className="space-y-1">
            {Object.entries(stats.rules_by_kind).map(([kind, count]) => (
              <div key={kind} className="flex justify-between text-xs">
                <span className="text-slate-600 dark:text-slate-300 capitalize">
                  {kind.replace('_', ' ')}:
                </span>
                <span className="font-medium text-slate-900 dark:text-slate-100">
                  {count}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-600">
        <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between">
          <span>Última actualización:</span>
          <span>
            {new Date(stats.generated_at).toLocaleTimeString('es-CL', {
              hour: '2-digit',
              minute: '2-digit'
            })}
          </span>
        </div>
      </div>
    </div>
  );
}