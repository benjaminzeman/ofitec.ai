'use client';

import { useState, useEffect } from 'react';

export default function ProyectosFinancieroPage() {
  const [data, setData] = useState<any>(null);
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
        
        {data?.meta?.view_available === false && (
          <div className="mt-2 bg-yellow-50 border border-yellow-200 rounded p-2 text-sm text-yellow-800">
            ⚠️ Vista v_project_financial_kpis no disponible. Mostrando datos básicos.
          </div>
        )}
      </div>

      {data && data.projects?.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay proyectos</h3>
          <p className="text-gray-600">No se encontraron proyectos para mostrar.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {data?.projects?.map((project: any) => (
            <div key={project.project_id} className="bg-white border border-gray-200 rounded-lg shadow-sm">
              <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">{project.project_name}</h2>
                    <div className="flex gap-2 mt-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        project.status === 'danger' || project.kpis?.derivadas?.risk_score >= 80 
                          ? 'bg-red-100 text-red-800' 
                          : project.status === 'warning' || project.kpis?.derivadas?.risk_score >= 60
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-green-100 text-green-800'
                      }`}>
                        Risk: {project.kpis?.derivadas?.risk_score || 0}
                      </span>
                      {project.chips?.slice(0, 2).map((chip: any, idx: number) => (
                        <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs">
                          {chip.label}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  {project.actions?.length > 0 && (
                    <div className="flex gap-2 flex-wrap">
                      {project.actions.map((action: any, idx: number) => (
                        <button
                          key={idx}
                          onClick={() => window.open(action.cta, '_blank')}
                          className={`px-3 py-1 text-xs text-white rounded-md ${
                            action.type === 'budget_import' ? 'bg-blue-500 hover:bg-blue-600' :
                            action.type === 'budget_review' ? 'bg-red-500 hover:bg-red-600' :
                            action.type === 'threeway_resolve' ? 'bg-yellow-500 hover:bg-yellow-600' :
                            'bg-gray-500 hover:bg-gray-600'
                          }`}
                        >
                          {action.title}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Costos */}
                  <div>
                    <h4 className="font-semibold mb-3 text-gray-800">💰 Costos</h4>
                    <div className="space-y-2">
                      {[
                        { title: "Presupuesto (PC)", value: project.kpis?.costos?.pc || 0 },
                        { title: "PO Comprometido", value: project.kpis?.costos?.po_total || 0 },
                        { title: "Recibido (GRN)", value: project.kpis?.costos?.grn_total || 0 },
                        { title: "Facturado AP", value: project.kpis?.costos?.ap_facturado || 0 },
                        { title: "Pagado AP", value: project.kpis?.costos?.ap_pagado || 0 }
                      ].map((item, idx) => (
                        <div key={idx} className="bg-gray-50 p-3 rounded-lg">
                          <div className="text-sm text-gray-600">{item.title}</div>
                          <div className="text-lg font-semibold">${item.value.toLocaleString()}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Ventas */}
                  <div>
                    <h4 className="font-semibold mb-3 text-gray-800">📈 Ventas</h4>
                    <div className="space-y-2">
                      {[
                        { title: "Contrato Cliente", value: project.kpis?.ventas?.contrato || 0 },
                        { title: "EP Acumulado", value: project.kpis?.ventas?.ep_acum || 0 },
                        { title: "Facturado Venta", value: project.kpis?.ventas?.fact_venta || 0 },
                        { title: "Cobrado", value: project.kpis?.ventas?.cobrado || 0 }
                      ].map((item, idx) => (
                        <div key={idx} className="bg-gray-50 p-3 rounded-lg">
                          <div className="text-sm text-gray-600">{item.title}</div>
                          <div className="text-lg font-semibold">${item.value.toLocaleString()}</div>
                        </div>
                      ))}
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <div className="text-sm text-gray-600">Avance Físico</div>
                        <div className="text-lg font-semibold">{(project.kpis?.ventas?.avance_fisico_pct || 0).toFixed(1)}%</div>
                      </div>
                    </div>
                  </div>

                  {/* Análisis */}
                  <div>
                    <h4 className="font-semibold mb-3 text-gray-800">📊 Análisis</h4>
                    <div className="space-y-2">
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <div className="text-sm text-gray-600">
                          {project.kpis?.derivadas?.has_ventas ? "Margen" : "Desvío"}
                        </div>
                        <div className="text-lg font-semibold">
                          ${(project.kpis?.derivadas?.margen_desvio || 0).toLocaleString()}
                        </div>
                        <div className="text-xs text-gray-500">
                          {project.kpis?.derivadas?.has_ventas ? "Utilidad esperada" : "vs Presupuesto"}
                        </div>
                      </div>
                      
                      <div className="bg-gray-50 p-3 rounded-lg">
                        <div className="text-sm text-gray-600">Risk Score</div>
                        <div className="flex items-center gap-2">
                          <div className="text-lg font-semibold">{project.kpis?.derivadas?.risk_score || 0}</div>
                          <div className="h-2 flex-1 rounded-full bg-gray-200">
                            <div 
                              className={`h-2 rounded-full ${
                                (project.kpis?.derivadas?.risk_score || 0) >= 80 ? 'bg-red-500' :
                                (project.kpis?.derivadas?.risk_score || 0) >= 60 ? 'bg-yellow-500' : 'bg-green-500'
                              }`}
                              style={{ width: `${project.kpis?.derivadas?.risk_score || 0}%` }}
                            />
                          </div>
                        </div>
                      </div>
                      
                      {(project.kpis?.costos?.pc || 0) === 0 && (
                        <div className="bg-red-50 p-2 rounded text-xs text-red-700">
                          ⚠️ Sin presupuesto cargado
                        </div>
                      )}
                      
                      {(project.kpis?.costos?.po_total || 0) > (project.kpis?.costos?.pc || 0) && (
                        <div className="bg-red-50 p-2 rounded text-xs text-red-700">
                          🚨 Sobregiro: PO excede PC
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {data && (
        <div className="mt-8 text-center text-sm text-gray-500">
          {data.meta?.total || 0} proyecto(s) • Actualizado: {data.meta?.computed_at ? new Date(data.meta.computed_at).toLocaleString() : 'N/A'}
        </div>
      )}
    </div>
  );
}
