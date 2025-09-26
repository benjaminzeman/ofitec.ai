'use client';

import { useEffect, useState } from 'react';
import KpiCard from '@/components/ui/KpiCard';
import ActionsList from '@/components/ui/ActionsList';
import { fetchCeoOverview, CeoOverview } from '@/lib/api';
import { EstadoBadge } from '@/lib/icons';

const peso = (n: number) =>
  new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
  }).format(n || 0);

export default function CeoOverviewPage() {
  const [data, setData] = useState<CeoOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const d = await fetchCeoOverview();
        setData(d);
      } catch (e: any) {
        console.error(e);
        setError('No se pudo cargar el resumen ejecutivo (CEO).');
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

  const { cash, revenue, projects, risk, acciones, working_cap, backlog, margin, alerts } = data;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-3">
            Resumen Ejecutivo (CEO)
            <EstadoBadge estado="activo" size="sm" />
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Caja, facturación, proyectos y riesgos
          </p>
        </div>
        <div className="flex gap-2">
          <EstadoBadge estado="vigente" showLabel={true} />
          <EstadoBadge estado="pendiente" showLabel={false} size="xs" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard 
          title="Caja Hoy" 
          value={peso(cash.today)} 
          icon="balance" 
          accent="lime"
          trend={{ value: 5.2, direction: 'up' }}
        />
        <KpiCard 
          title="Facturación Mes" 
          value={peso(revenue.month)} 
          icon="revenue" 
          accent="blue"
          trend={{ value: 12.5, direction: 'up' }}
        />
        <KpiCard 
          title="Proyectos Activos" 
          value={projects.total} 
          icon="presupuesto" 
          accent="amber"
          subtitle="proyectos en ejecución"
        />
        <KpiCard 
          title="Score de Riesgo" 
          value={`${risk.high}/100`} 
          icon="profit" 
          accent={risk.high > 70 ? "red" : "lime"}
          trend={{ value: risk.high > 70 ? -5 : 3, direction: risk.high > 70 ? "down" : "up" }}
        />
      </div>

      {/* Working Capital */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Working Capital
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard title="DSO" value={working_cap?.dso ?? 0} />
          <KpiCard title="DPO" value={working_cap?.dpo ?? 0} />
          <KpiCard title="DIO" value={working_cap?.dio ?? 0} />
          <KpiCard title="CCC" value={working_cap?.ccc ?? 0} />
        </div>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              AR Aging
            </h4>
            <div className="text-sm text-slate-600 dark:text-slate-400">
              0-30: {peso(working_cap?.ar?.d1_30 ?? 0)} · 31-60:{' '}
              {peso(working_cap?.ar?.d31_60 ?? 0)} · 60+: {peso(working_cap?.ar?.d60_plus ?? 0)}
            </div>
          </div>
          <div>
            <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
              AP Próximos
            </h4>
            <div className="text-sm text-slate-600 dark:text-slate-400">
              7d: {peso(working_cap?.ap?.d7 ?? 0)} · 14d: {peso(working_cap?.ap?.d14 ?? 0)} · 30d:{' '}
              {peso(working_cap?.ap?.d30 ?? 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Backlog & Margen */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">Backlog</h3>
          <div className="grid grid-cols-2 gap-4">
            <KpiCard title="Backlog Total" value={backlog?.total ?? 0} />
            <KpiCard title="Cobertura (meses)" value={backlog?.cobertura_meses ?? 0} />
            <KpiCard title="Pipeline Weighted" value={backlog?.pipeline_weighted ?? 0} />
            <KpiCard title="Pipeline vs Meta" value={backlog?.pipeline_vs_goal_pct ?? 0} />
          </div>
        </div>
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">Margen</h3>
          <div className="grid grid-cols-3 gap-4">
            <KpiCard title="Mes %" value={margin?.month_pct ?? 0} />
            <KpiCard title="Plan %" value={margin?.plan_pct ?? 0} />
            <KpiCard title="Δ pp" value={margin?.delta_pp ?? 0} />
          </div>
        </div>
      </div>

      {/* Salud Proyectos y Riesgos */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            Salud de Proyectos
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <KpiCard title="On Budget" value={projects.on_budget ?? 0} />
            <KpiCard title="Over Budget" value={projects.over_budget ?? 0} />
            <KpiCard title="Sin PC" value={projects.without_pc ?? 0} />
            <KpiCard title="3-Way" value={projects.three_way_violations ?? 0} />
            <KpiCard title="EP→FV" value={projects.wip_ep_to_invoice ?? 0} />
          </div>
        </div>
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            Riesgo y Alertas
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <KpiCard title="Riesgo (score)" value={risk.high} accent="red" />
            <KpiCard title="Riesgo Medio" value={risk.medium} />
          </div>
          {risk.reasons && risk.reasons.length > 0 && (
            <ul className="list-disc list-inside text-sm text-slate-600 dark:text-slate-400">
              {risk.reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          )}
          {alerts && alerts.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                Alertas
              </h4>
              <ul className="list-disc list-inside text-sm text-slate-600 dark:text-slate-400">
                {alerts.map((a, i) => (
                  <li key={i}>{a.title}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Acciones Sugeridas
        </h3>
        <ActionsList items={acciones} />
      </div>
    </div>
  );
}
