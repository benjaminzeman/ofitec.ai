'use client'

import { useEffect, useState } from 'react';
import { EstadoBadge, KPICard, MetricaIcono, NavIcon } from '@/lib/icons';

const peso = (n: number) =>
  new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
  }).format(n || 0);

export default function ControlFinancieroRoute() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://127.0.0.1:5555/api/control_financiero/resumen');
        if (!response.ok) throw new Error('Error en API');
        const d = await response.json();
        setData(d);
      } catch (e: any) {
        console.error(e);
        setError('No se pudo cargar el Control Financiero.');
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
        <div className="bg-white dark:bg-slate-800 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 rounded-xl p-6 flex items-center gap-3">
          <EstadoBadge estado="vencido" showLabel={false} />
          {error || 'Sin datos'}
        </div>
      </div>
    );
  }

  const { items, totals, validations, kpis } = data;

  return (
    <div className="p-6 space-y-6">
      {/* Header con iconos */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-3">
            <NavIcon tipo="dashboard" active={true} size="lg" />
            Control Financiero 360
            <EstadoBadge estado="activo" size="sm" />
          </h1>
          <p className="text-slate-600 dark:text-slate-400 flex items-center gap-2">
            <MetricaIcono tipo="presupuesto" value="" size="sm" />
            {data.sprint_version} • {kpis.total_projects} proyectos monitoreados
          </p>
        </div>
        <div className="flex gap-2">
          <EstadoBadge estado="vigente" showLabel={true} />
          <EstadoBadge estado="aprobado" showLabel={false} size="xs" />
        </div>
      </div>

      {/* KPIs Principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard 
          title="Presupuesto Total" 
          value={peso(totals.presupuesto)} 
          icon="presupuesto" 
          className="border-l-4 border-l-lime-500"
        />
        <KPICard 
          title="Comprometido" 
          value={peso(totals.comprometido)} 
          icon="costos" 
          className="border-l-4 border-l-amber-500"
        />
        <KPICard 
          title="Facturado" 
          value={peso(totals.facturado)} 
          icon="revenue" 
          className="border-l-4 border-l-blue-500"
        />
        <KPICard 
          title="Disponible" 
          value={peso(totals.disponible)} 
          icon="balance" 
          className="border-l-4 border-l-red-500"
        />
      </div>

      {/* Proyectos */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
          <NavIcon tipo="proyectos" size="md" />
          Proyectos Monitoreados
        </h3>
        <div className="space-y-4">
          {Object.entries(items).map(([projectName, project]: [string, any]) => (
            <div key={projectName} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900 rounded-lg">
              <div className="flex items-center gap-4">
                <EstadoBadge 
                  estado={project.health_score > 80 ? "vigente" : project.health_score > 50 ? "pendiente" : "vencido"} 
                  showLabel={false} 
                />
                <div>
                  <h4 className="font-semibold text-slate-900 dark:text-slate-100">{projectName}</h4>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Health Score: {project.health_score}/100
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-6 text-sm">
                <MetricaIcono 
                  tipo="presupuesto" 
                  value={peso(project.presupuesto).replace('$', '').replace('CLP', '')} 
                  size="sm" 
                />
                <MetricaIcono 
                  tipo="balance" 
                  value={peso(project.disponible).replace('$', '').replace('CLP', '')} 
                  size="sm"
                  trend={project.disponible > 0 ? "up" : "down"}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}