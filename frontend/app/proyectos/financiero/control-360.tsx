'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface KPIs {
  costos: {
    pc: number;
    po_total: number;
    grn_total: number;
    ap_facturado: number;
    ap_pagado: number;
    disponible: number;
  };
  ventas: {
    contrato: number;
    ep_acum: number;
    fact_venta: number;
    cobrado: number;
    avance_fisico_pct: number;
  };
  derivadas: {
    margen_desvio: number;
    has_ventas: boolean;
    risk_score: number;
  };
}

interface Action {
  title: string;
  type: string;
  cta: string;
}

interface Chip {
  label: string;
  type: string;
}

interface FinancialProject {
  project_id: number;
  project_name: string;
  kpis: KPIs;
  status: 'normal' | 'warning' | 'danger';
  actions: Action[];
  chips: Chip[];
  computed_at: string;
}

interface FinancialResponse {
  projects: FinancialProject[];
  meta: {
    total: number;
    view_available: boolean;
    computed_at: string;
    error?: string;
  };
}

const StatusChip = ({ status, score }: { status: string; score: number }) => {
  const getStatusColor = () => {
    if (status === 'danger' || score >= 80) return 'bg-red-100 text-red-800';
    if (status === 'warning' || score >= 60) return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor()}`}>
      Risk: {score}
    </span>
  );
};

const KPICard = ({ title, value, subtitle, type }: { 
  title: string; 
  value: number; 
  subtitle?: string; 
  type: 'currency' | 'percentage' | 'number' 
}) => {
  const formatValue = (val: number) => {
    if (type === 'currency') return `$${val.toLocaleString()}`;
    if (type === 'percentage') return `${val.toFixed(1)}%`;
    return val.toString();
  };

  return (
    <div className="bg-gray-50 p-3 rounded-lg">
      <div className="text-sm text-gray-600">{title}</div>
      <div className="text-lg font-semibold">{formatValue(value)}</div>
      {subtitle && <div className="text-xs text-gray-500">{subtitle}</div>}
    </div>
  );
};

const ActionButton = ({ action }: { action: Action }) => {
  const getActionColor = () => {
    switch (action.type) {
      case 'budget_import': return 'bg-blue-500 hover:bg-blue-600';
      case 'budget_review': return 'bg-red-500 hover:bg-red-600';
      case 'threeway_resolve': return 'bg-yellow-500 hover:bg-yellow-600';
      default: return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  return (
    <button
      onClick={() => window.open(action.cta, '_blank')}
      className={`px-3 py-1 text-xs text-white rounded-md ${getActionColor()}`}
    >
      {action.title}
    </button>
  );
};

export default function ProyectosFinancieroPage() {
  const [data, setData] = useState<FinancialResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api/projects/financial');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const result = await response.json();
        setData(result);
        setError(null);
      } catch (err) {
        console.error('Error fetching financial data:', err);
        setError(err instanceof Error ? err.message : 'Error desconocido');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4"></div>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-red-800 mb-2">Error</h2>
          <p className="text-red-600">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Control Financiero 360°</h1>
        <p className="text-gray-600">Tablero integral de salud financiera por proyecto</p>
        
        {data?.meta.view_available === false && (
          <div className="mt-2 bg-yellow-50 border border-yellow-200 rounded p-2 text-sm text-yellow-800">
            ⚠️ Vista v_project_financial_kpis no disponible. Mostrando datos básicos.
          </div>
        )}
      </div>

      {data && data.projects.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay proyectos</h3>
          <p className="text-gray-600">No se encontraron proyectos para mostrar.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {data?.projects.map((project) => (
            <Card key={project.project_id} className="border-l-4 border-l-blue-500">
              <CardHeader className="pb-4">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-xl">{project.project_name}</CardTitle>
                    <div className="flex gap-2 mt-2">
                      <StatusChip 
                        status={project.status} 
                        score={project.kpis.derivadas.risk_score} 
                      />
                      {project.chips.slice(0, 2).map((chip, idx) => (
                        <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs">
                          {chip.label}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  {project.actions.length > 0 && (
                    <div className="flex gap-2 flex-wrap">
                      {project.actions.map((action, idx) => (
                        <ActionButton key={idx} action={action} />
                      ))}
                    </div>
                  )}
                </div>
              </CardHeader>
              
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Costos */}
                  <div>
                    <h4 className="font-semibold mb-3 text-gray-800">💰 Costos</h4>
                    <div className="space-y-2">
                      <KPICard 
                        title="Presupuesto (PC)" 
                        value={project.kpis.costos.pc} 
                        type="currency" 
                      />
                      <KPICard 
                        title="PO Comprometido" 
                        value={project.kpis.costos.po_total} 
                        type="currency"
                        subtitle={`Disponible: $${project.kpis.costos.disponible.toLocaleString()}`}
                      />
                      <KPICard 
                        title="Recibido (GRN)" 
                        value={project.kpis.costos.grn_total} 
                        type="currency" 
                      />
                      <KPICard 
                        title="Facturado AP" 
                        value={project.kpis.costos.ap_facturado} 
                        type="currency" 
                      />
                      <KPICard 
                        title="Pagado AP" 
                        value={project.kpis.costos.ap_pagado} 
                        type="currency" 
                      />
                    </div>
                  </div>

                  {/* Ventas */}
                  <div>
                    <h4 className="font-semibold mb-3 text-gray-800">📈 Ventas</h4>
                    <div className="space-y-2">
                      <KPICard 
                        title="Contrato Cliente" 
                        value={project.kpis.ventas.contrato} 
                        type="currency" 
                      />
                      <KPICard 
                        title="EP Acumulado" 
                        value={project.kpis.ventas.ep_acum} 
                        type="currency" 
                      />
                      <KPICard 
                        title="Facturado Venta" 
                        value={project.kpis.ventas.fact_venta} 
                        type="currency" 
                      />
                      <KPICard 
                        title="Cobrado" 
                        value={project.kpis.ventas.cobrado} 
                        type="currency" 
                      />
                      <KPICard 
                        title="Avance Físico" 
                        value={project.kpis.ventas.avance_fisico_pct} 
                        type="percentage" 
                      />
                    </div>
                  </div>

                  {/* Análisis */}
                  <div>
                    <h4 className="font-semibold mb-3 text-gray-800">📊 Análisis</h4>
                    <div className="space-y-2">
                      <KPICard 
                        title={project.kpis.derivadas.has_ventas ? "Margen" : "Desvío"} 
                        value={project.kpis.derivadas.margen_desvio} 
                        type="currency"
                        subtitle={project.kpis.derivadas.has_ventas ? "Utilidad esperada" : "vs Presupuesto"}
                      />
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <div className="text-sm text-gray-600">Risk Score</div>
                        <div className="flex items-center gap-2">
                          <div className="text-lg font-semibold">{project.kpis.derivadas.risk_score}</div>
                          <div className={`h-2 flex-1 rounded-full bg-gray-200`}>
                            <div 
                              className={`h-2 rounded-full ${
                                project.kpis.derivadas.risk_score >= 80 ? 'bg-red-500' :
                                project.kpis.derivadas.risk_score >= 60 ? 'bg-yellow-500' : 'bg-green-500'
                              }`}
                              style={{ width: `${project.kpis.derivadas.risk_score}%` }}
                            />
                          </div>
                        </div>
                      </div>
                      
                      {project.kpis.costos.pc === 0 && (
                        <div className="bg-red-50 p-2 rounded text-xs text-red-700">
                          ⚠️ Sin presupuesto cargado
                        </div>
                      )}
                      
                      {project.kpis.costos.po_total > project.kpis.costos.pc && (
                        <div className="bg-red-50 p-2 rounded text-xs text-red-700">
                          🚨 Sobregiro: PO excede PC
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {data && (
        <div className="mt-8 text-center text-sm text-gray-500">
          {data.meta.total} proyecto(s) • Actualizado: {new Date(data.meta.computed_at).toLocaleString()}
        </div>
      )}
    </div>
  );
}