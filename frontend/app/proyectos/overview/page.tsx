'use client';

import { useEffect, useState } from 'react';
import KpiCard from '@/components/ui/KpiCard';
import StackedBar from '@/components/ui/StackedBar';
import ActionsList from '@/components/ui/ActionsList';
import { fetchProjectsOverview, ProjectsOverview } from '@/lib/api';

const peso = (n: number) =>
  new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
  }).format(n || 0);

export default function ProjectsOverviewPage() {
  const [data, setData] = useState<ProjectsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const d = await fetchProjectsOverview();
        setData(d);
      } catch (e: any) {
        console.error(e);
        setError('No se pudo cargar el resumen de proyectos.');
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

  const { portfolio, salud, wip, acciones } = data;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Resumen de Proyectos
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Visión ejecutiva del portafolio y estado de ejecución
          </p>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard title="Proyectos Activos" value={portfolio.activos} accent="lime" />
        <KpiCard title="Presupuesto Total (PC)" value={peso(portfolio.pc_total)} accent="blue" />
        <KpiCard title="OC Emitidas" value={peso(portfolio.po)} accent="amber" />
        <KpiCard title="Disponible" value={peso(portfolio.disponible)} accent="lime" />
      </div>

      {/* Ejecución */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Ejecución</h3>
        </div>
        <StackedBar
          segments={[
            { label: 'GRN', value: portfolio.ejecucion.grn, color: '#65a30d' },
            { label: 'AP', value: portfolio.ejecucion.ap, color: '#f59e0b' },
            { label: 'Pagado', value: portfolio.ejecucion.pagado, color: '#0ea5e9' },
          ]}
        />
      </div>

      {/* Salud del Portafolio */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">Salud</h3>
          <div className="grid grid-cols-2 gap-4">
            <KpiCard title="On Budget" value={salud.on_budget} accent="lime" />
            <KpiCard title="Over Budget" value={salud.over_budget} accent="red" />
            <KpiCard title="Sin PC" value={salud.without_pc} accent="amber" />
            <KpiCard title="3-Way Match" value={salud.tres_way} accent="blue" />
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
            WIP y EP
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <KpiCard title="EP Aprobados sin FV" value={wip.ep_aprobados_sin_fv} />
            <KpiCard title="EP en Revisión" value={wip.ep_en_revision} />
          </div>
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
