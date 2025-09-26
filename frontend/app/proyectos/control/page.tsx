'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

// SPRINT 1: Interfaces actualizadas con validaciones críticas
interface ControlRow {
  project_name: string;
  presupuesto: number;
  comprometido: number;
  facturado: number;
  pagado: number;
  disponible_conservador: number;
  flags: string[];
  severity: 'OK' | 'WARNING' | 'ERROR' | 'CRITICAL';
  kpis: {
    budget_utilization: number;
    invoice_ratio: number;
    payment_ratio: number;
    financial_health_score: number;
  };
}

interface ValidationSummary {
  total_projects: number;
  projects_ok: number;
  projects_with_warnings: number;
  projects_with_errors: number;
  critical_issues: Array<{
    project: string;
    issue: string;
    excess: number;
  }>;
}

interface ApiResponse {
  items: ControlRow[];
  meta: { total: number };
  totals: {
    presupuesto: number;
    comprometido: number;
    facturado: number;
    pagado: number;
    disponible: number;
  };
  validations: ValidationSummary;
  kpis: {
    total_budget_utilization: number;
    projects_over_budget: number;
    projects_with_high_commitment: number;
    critical_validations_failed: number;
    average_financial_health: number;
  };
  sprint_version?: string;
}

// SPRINT 1: Componentes de UI mejorados
function SeverityBadge({ severity }: { severity: string }) {
  const colors = {
    'OK': 'bg-green-100 text-green-800 border-green-300',
    'WARNING': 'bg-yellow-100 text-yellow-800 border-yellow-300', 
    'ERROR': 'bg-red-100 text-red-800 border-red-300',
    'CRITICAL': 'bg-red-500 text-white border-red-600'
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${colors[severity as keyof typeof colors] || colors.OK}`}>
      {severity}
    </span>
  );
}

function ValidationFlags({ flags }: { flags: string[] }) {
  const flagLabels: Record<string, string> = {
    'OK': '✅',
    'NO_BUDGET': '📝 Sin Presupuesto',
    'EXCEEDS_BUDGET': '🚫 Excede Presupuesto',
    'INVOICE_OVER_PO': '⚠️ Factura > OC',
    'PAYMENT_OVER_INVOICE': '🚨 Pago > Factura',
    'HIGH_COMMITMENT': '⏳ Alto Compromiso',
    'NEGATIVE_AVAILABLE': '📉 Disponible Negativo',
    'THREE_WAY_VIOLATIONS': '🔗 Violación 3-way',
    'ORPHAN_INVOICES': '🔍 Facturas sin OC'
  };

  return (
    <div className="flex flex-wrap gap-1">
      {flags.map((flag, idx) => (
        <span
          key={idx}
          className="px-2 py-1 text-xs rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
          title={flag}
        >
          {flagLabels[flag] || flag}
        </span>
      ))}
    </div>
  );
}

function HealthScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500';
  
  return (
    <div className="flex items-center gap-2">
      <div className="text-sm font-medium">{score.toFixed(0)}</div>
      <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color} transition-all duration-300`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
    </div>
  );
}

function WaterfallChart({ project }: { project: ControlRow }) {
  const { presupuesto, comprometido, facturado, pagado } = project;
  const maxValue = Math.max(presupuesto, comprometido, facturado, pagado) || 1;
  
  const bars = [
    { label: 'Presupuesto', value: presupuesto, color: 'bg-blue-500' },
    { label: 'Comprometido', value: comprometido, color: 'bg-yellow-500' },
    { label: 'Facturado', value: facturado, color: 'bg-orange-500' },
    { label: 'Pagado', value: pagado, color: 'bg-green-500' }
  ];
  
  return (
    <div className="space-y-2">
      {bars.map((bar, idx) => (
        <div key={idx} className="flex items-center gap-3">
          <div className="w-20 text-xs text-gray-600 dark:text-gray-400">
            {bar.label}
          </div>
          <div className="flex-1 h-4 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden">
            <div 
              className={`h-full ${bar.color} transition-all duration-300`}
              style={{ width: `${(bar.value / maxValue) * 100}%` }}
            />
          </div>
          <div className="w-24 text-xs text-right font-mono">
            ${bar.value.toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}

function KPICard({ title, value, accent }: { title: string; value: string | number; accent?: string }) {
  const accentColors = {
    'green': 'border-green-300 bg-green-50 text-green-800',
    'red': 'border-red-300 bg-red-50 text-red-800',
    'yellow': 'border-yellow-300 bg-yellow-50 text-yellow-800',
    'blue': 'border-blue-300 bg-blue-50 text-blue-800'
  };
  
  return (
    <div className={`p-4 rounded-xl border-2 ${accentColors[accent as keyof typeof accentColors] || 'border-gray-300 bg-gray-50 text-gray-800'}`}>
      <div className="text-sm font-medium opacity-80">{title}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  );
}

function CLP(n: number) {
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
  }).format(Number(n || 0));
}

export default function ProyectosControlPage() {
  const [data, setData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedProject, setExpandedProject] = useState<string | null>(null);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api';
    fetch(`${base}/control_financiero/resumen`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((responseData) => setData(responseData))
      .catch((e) => setError(e?.message || 'Error'))
      .finally(() => setLoading(false));
  }, []);

  const formatCLP = (amount: number) => CLP(amount);
  const formatPercent = (value: number) => `${value.toFixed(1)}%`;

  return (
    <div className="p-6 space-y-6">
      {/* Header del Sprint 1 */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">
            Control Financiero 360
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mt-1">
            Sistema de validaciones críticas y monitoreo en tiempo real
          </p>
          {data?.sprint_version && (
            <div className="mt-2 text-xs text-green-700 bg-green-100 px-2 py-1 rounded">
              {data.sprint_version}
            </div>
          )}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-lime-600"></div>
          <span className="ml-2">Cargando análisis financiero...</span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-300 text-red-800 p-4 rounded-xl">
          <strong>Error:</strong> {error}
        </div>
      )}

      {!loading && !error && data && (
        <>
          {/* KPIs Globales del Sprint 1 */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <KPICard 
              title="Salud Financiera Promedio" 
              value={`${data.kpis.average_financial_health.toFixed(0)}%`}
              accent={data.kpis.average_financial_health >= 80 ? 'green' : data.kpis.average_financial_health >= 60 ? 'yellow' : 'red'}
            />
            <KPICard 
              title="Proyectos sobre Presupuesto" 
              value={data.kpis.projects_over_budget}
              accent={data.kpis.projects_over_budget > 0 ? 'red' : 'green'}
            />
            <KPICard 
              title="Alto Nivel de Compromiso" 
              value={data.kpis.projects_with_high_commitment}
              accent="yellow"
            />
            <KPICard 
              title="Validaciones Críticas Fallidas" 
              value={data.kpis.critical_validations_failed}
              accent={data.kpis.critical_validations_failed > 0 ? 'red' : 'green'}
            />
            <KPICard 
              title="Utilización Presupuestal" 
              value={formatPercent(data.kpis.total_budget_utilization)}
              accent="blue"
            />
          </div>

          {/* Resumen de Validaciones */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
            <h2 className="text-lg font-semibold mb-4">Resumen de Validaciones</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{data.validations.projects_ok}</div>
                <div className="text-sm text-gray-600">Proyectos OK</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">{data.validations.projects_with_warnings}</div>
                <div className="text-sm text-gray-600">Con Advertencias</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{data.validations.projects_with_errors}</div>
                <div className="text-sm text-gray-600">Con Errores</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{data.validations.total_projects}</div>
                <div className="text-sm text-gray-600">Total Proyectos</div>
              </div>
            </div>

            {/* Issues Críticos */}
            {data.validations.critical_issues.length > 0 && (
              <div className="mt-4">
                <h3 className="font-medium text-red-600 mb-2">⚠️ Issues Críticos</h3>
                <div className="space-y-2">
                  {data.validations.critical_issues.map((issue, idx) => (
                    <div key={idx} className="bg-red-50 border border-red-200 p-3 rounded-lg">
                      <div className="font-medium text-red-800">{issue.project}</div>
                      <div className="text-sm text-red-700">{issue.issue}</div>
                      <div className="text-xs text-red-600">Exceso: {formatCLP(issue.excess)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Tabla Mejorada de Proyectos */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="p-6 border-b border-slate-200 dark:border-slate-700">
              <h2 className="text-lg font-semibold">Proyectos - Control Financiero Detallado</h2>
            </div>
            
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-slate-50 dark:bg-slate-900">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-medium text-slate-700 dark:text-slate-200">Proyecto</th>
                    <th className="px-6 py-4 text-right text-sm font-medium text-slate-700 dark:text-slate-200">Presupuesto</th>
                    <th className="px-6 py-4 text-right text-sm font-medium text-slate-700 dark:text-slate-200">Comprometido</th>
                    <th className="px-6 py-4 text-right text-sm font-medium text-slate-700 dark:text-slate-200">Facturado</th>
                    <th className="px-6 py-4 text-right text-sm font-medium text-slate-700 dark:text-slate-200">Pagado</th>
                    <th className="px-6 py-4 text-right text-sm font-medium text-slate-700 dark:text-slate-200">Disponible</th>
                    <th className="px-6 py-4 text-center text-sm font-medium text-slate-700 dark:text-slate-200">Salud</th>
                    <th className="px-6 py-4 text-center text-sm font-medium text-slate-700 dark:text-slate-200">Estado</th>
                    <th className="px-6 py-4 text-left text-sm font-medium text-slate-700 dark:text-slate-200">Flags</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {data.items.map((project, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-700">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <Link 
                            href={`/proyectos/${encodeURIComponent(project.project_name)}/control`}
                            className="font-medium text-lime-600 hover:text-lime-700 hover:underline"
                          >
                            {project.project_name}
                          </Link>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-sm">{formatCLP(project.presupuesto)}</td>
                      <td className="px-6 py-4 text-right font-mono text-sm">{formatCLP(project.comprometido)}</td>
                      <td className="px-6 py-4 text-right font-mono text-sm">{formatCLP(project.facturado)}</td>
                      <td className="px-6 py-4 text-right font-mono text-sm">{formatCLP(project.pagado)}</td>
                      <td className={`px-6 py-4 text-right font-mono text-sm ${project.disponible_conservador < 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {formatCLP(project.disponible_conservador)}
                      </td>
                      <td className="px-6 py-4">
                        <HealthScoreBar score={project.kpis.financial_health_score} />
                      </td>
                      <td className="px-6 py-4 text-center">
                        <SeverityBadge severity={project.severity} />
                      </td>
                      <td className="px-6 py-4">
                        <ValidationFlags flags={project.flags} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Totales Consolidados */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
            <h2 className="text-lg font-semibold mb-4">Totales Consolidados</h2>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="text-center">
                <div className="text-sm text-gray-600 mb-1">Presupuesto Total</div>
                <div className="text-xl font-bold">{formatCLP(data.totals.presupuesto)}</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-600 mb-1">Comprometido Total</div>
                <div className="text-xl font-bold">{formatCLP(data.totals.comprometido)}</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-600 mb-1">Facturado Total</div>
                <div className="text-xl font-bold">{formatCLP(data.totals.facturado)}</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-600 mb-1">Pagado Total</div>
                <div className="text-xl font-bold">{formatCLP(data.totals.pagado)}</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-600 mb-1">Disponible Total</div>
                <div className={`text-xl font-bold ${data.totals.disponible < 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {formatCLP(data.totals.disponible)}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
