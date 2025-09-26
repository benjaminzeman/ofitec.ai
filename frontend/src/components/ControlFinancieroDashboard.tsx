'use client'

import React, { useState, useEffect } from 'react'

interface Project {
  id: string;
  nombre: string;
  presupuesto: number;
  comprometido: number;
  facturado: number;
  pagado: number;
  disponible: number;
  health_score: number;
  validations: {
    budget_ok: boolean;
    commitment_reasonable: boolean;
    invoice_payment_ratio_ok: boolean;
    all_validations_passed: boolean;
  };
}

interface ControlFinancieroData {
  items: { [key: string]: Project };
  totals: {
    presupuesto: number;
    comprometido: number;
    facturado: number;
    pagado: number;
    disponible: number;
  };
  validations: {
    total_projects: number;
    projects_ok: number;
    projects_with_warnings: number;
    projects_with_errors: number;
    critical_issues: string[];
  };
  kpis: {
    average_financial_health: number;
    critical_validations_failed: number;
    projects_over_budget: number;
    projects_with_high_commitment: number;
    total_budget_utilization: number;
  };
  meta: {
    total: number;
  };
  sprint_version: string;
  timestamp: string;
}

const ControlFinancieroDashboard: React.FC = () => {
  const [data, setData] = useState<ControlFinancieroData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://127.0.0.1:5555/api/control_financiero/resumen');
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        setData(result);
        setError(null);
      } catch (err) {
        console.error('Error cargando datos:', err);
        setError(err instanceof Error ? err.message : 'Error desconocido');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <h3 className="text-lg font-medium text-red-800">Error de conexión</h3>
            <p className="text-red-600 mt-2">{error}</p>
            <button 
              onClick={() => window.location.reload()}
              className="mt-4 bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
            >
              Reintentar
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <p>No hay datos disponibles</p>
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

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 60) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Control Financiero 360</h1>
              <p className="text-sm text-gray-500">{data.sprint_version} - {data.timestamp}</p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                {data.meta.total} proyectos activos
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* KPIs Principales */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                    <span className="text-white text-sm font-bold">$</span>
                  </div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Presupuesto Total</dt>
                    <dd className="text-lg font-medium text-gray-900">{formatCurrency(data.totals.presupuesto)}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-orange-500 rounded-md flex items-center justify-center">
                    <span className="text-white text-sm font-bold">C</span>
                  </div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Comprometido</dt>
                    <dd className="text-lg font-medium text-gray-900">{formatCurrency(data.totals.comprometido)}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                    <span className="text-white text-sm font-bold">F</span>
                  </div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Facturado</dt>
                    <dd className="text-lg font-medium text-gray-900">{formatCurrency(data.totals.facturado)}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                    <span className="text-white text-sm font-bold">P</span>
                  </div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Pagado</dt>
                    <dd className="text-lg font-medium text-gray-900">{formatCurrency(data.totals.pagado)}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-gray-500 rounded-md flex items-center justify-center">
                    <span className="text-white text-sm font-bold">D</span>
                  </div>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Disponible</dt>
                    <dd className="text-lg font-medium text-gray-900">{formatCurrency(data.totals.disponible)}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* KPIs de Salud Financiera */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white overflow-hidden shadow rounded-lg p-5">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Salud Financiera Promedio</h3>
            <div className={`inline-flex px-3 py-1 rounded-full text-2xl font-bold ${getHealthColor(data.kpis.average_financial_health)}`}>
              {data.kpis.average_financial_health.toFixed(1)}%
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg p-5">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Validaciones Críticas</h3>
            <div className="text-2xl font-bold text-red-600">
              {data.kpis.critical_validations_failed}
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg p-5">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Proyectos Sobrepresupuesto</h3>
            <div className="text-2xl font-bold text-orange-600">
              {data.kpis.projects_over_budget}
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg p-5">
            <h3 className="text-lg font-medium text-gray-900 mb-2">Utilización de Presupuesto</h3>
            <div className="text-2xl font-bold text-blue-600">
              {data.kpis.total_budget_utilization.toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Lista de Proyectos */}
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900">
              Proyectos en Detalle
            </h3>
            <p className="mt-1 max-w-2xl text-sm text-gray-500">
              Estado financiero y validaciones por proyecto
            </p>
          </div>
          <ul className="divide-y divide-gray-200">
            {Object.entries(data.items).map(([id, project]) => (
              <li key={id}>
                <div className="px-4 py-4 sm:px-6 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h4 className="text-lg font-medium text-gray-900">{project.nombre}</h4>
                      <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                        <div>
                          <span className="font-medium">Presupuesto:</span>
                          <div className="text-gray-900">{formatCurrency(project.presupuesto)}</div>
                        </div>
                        <div>
                          <span className="font-medium">Comprometido:</span>
                          <div className="text-gray-900">{formatCurrency(project.comprometido)}</div>
                        </div>
                        <div>
                          <span className="font-medium">Facturado:</span>
                          <div className="text-gray-900">{formatCurrency(project.facturado)}</div>
                        </div>
                        <div>
                          <span className="font-medium">Pagado:</span>
                          <div className="text-gray-900">{formatCurrency(project.pagado)}</div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className={`px-3 py-1 rounded-full text-sm font-medium ${getHealthColor(project.health_score)}`}>
                        {project.health_score}%
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-500">Validaciones</div>
                        <div className={`font-medium ${project.validations.all_validations_passed ? 'text-green-600' : 'text-red-600'}`}>
                          {project.validations.all_validations_passed ? '✅ OK' : '❌ Issues'}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>

      </div>
    </div>
  );
};

export default ControlFinancieroDashboard;