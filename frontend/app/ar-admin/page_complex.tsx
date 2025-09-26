'use client';

import { useState } from 'react';
import ArStatsWidget from '@/components/ArStatsWidget';
import AliasCandidatesWidget from '@/components/AliasCandidatesWidget';

export default function ArAdminPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
          Administración AR
        </h1>
        <p className="text-slate-600 dark:text-slate-300">
          Gestión del sistema de asignación automática de proyectos a facturas de venta
        </p>
      </div>

      {/* Overview Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* AR Statistics */}
        <ArStatsWidget key={`stats-${refreshKey}`} />
        
        {/* Alias Candidates */}
        <AliasCandidatesWidget 
          key={`candidates-${refreshKey}`}
          onRefresh={handleRefresh}
        />
      </div>

      {/* Detailed Management Sections */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Rules Management */}
        <div className="xl:col-span-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Gestión de Reglas
          </h3>
          
          <div className="space-y-4">
            {/* Coming Soon Placeholder */}
            <div className="text-center py-12 text-slate-500 dark:text-slate-400">
              <div className="text-4xl mb-3">🔧</div>
              <div className="font-medium mb-2">Panel de Reglas en Desarrollo</div>
              <div className="text-sm">
                Próximamente: Crear, editar y eliminar reglas de mapeo AR
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Acciones Rápidas
          </h3>
          
          <div className="space-y-3">
            {/* Auto-assign Button */}
            <button
              onClick={() => {
                alert('Función de auto-asignación masiva en desarrollo');
              }}
              className="w-full px-4 py-3 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:hover:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg text-left transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">⚡</span>
                <div>
                  <div className="font-medium text-blue-900 dark:text-blue-100 text-sm">
                    Auto-asignar Facturas
                  </div>
                  <div className="text-xs text-blue-700 dark:text-blue-300">
                    Procesar facturas sin proyecto con IA
                  </div>
                </div>
              </div>
            </button>

            {/* Rules Import */}
            <button
              onClick={() => {
                alert('Importación de reglas en desarrollo');
              }}
              className="w-full px-4 py-3 bg-green-50 hover:bg-green-100 dark:bg-green-900/20 dark:hover:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg text-left transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">📥</span>
                <div>
                  <div className="font-medium text-green-900 dark:text-green-100 text-sm">
                    Importar Reglas
                  </div>
                  <div className="text-xs text-green-700 dark:text-green-300">
                    Cargar reglas desde CSV
                  </div>
                </div>
              </div>
            </button>

            {/* Export Data */}
            <button
              onClick={() => {
                alert('Exportación de datos en desarrollo');
              }}
              className="w-full px-4 py-3 bg-amber-50 hover:bg-amber-100 dark:bg-amber-900/20 dark:hover:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg text-left transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">📊</span>
                <div>
                  <div className="font-medium text-amber-900 dark:text-amber-100 text-sm">
                    Exportar Reportes
                  </div>
                  <div className="text-xs text-amber-700 dark:text-amber-300">
                    Descargar estadísticas AR
                  </div>
                </div>
              </div>
            </button>

            {/* Refresh System */}
            <button
              onClick={handleRefresh}
              className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 dark:bg-slate-700/50 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-left transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">🔄</span>
                <div>
                  <div className="font-medium text-slate-900 dark:text-slate-100 text-sm">
                    Actualizar Vista
                  </div>
                  <div className="text-xs text-slate-600 dark:text-slate-300">
                    Recargar estadísticas y candidatos
                  </div>
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* System Health */}
      <div className="mt-8 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Estado del Sistema
        </h3>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="flex items-center gap-3 p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
            <span className="text-2xl">✅</span>
            <div>
              <div className="font-medium text-emerald-900 dark:text-emerald-100 text-sm">
                API Activa
              </div>
              <div className="text-xs text-emerald-700 dark:text-emerald-300">
                Sugerencias funcionando
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <span className="text-2xl">🧠</span>
            <div>
              <div className="font-medium text-blue-900 dark:text-blue-100 text-sm">
                ML Operativo
              </div>
              <div className="text-xs text-blue-700 dark:text-blue-300">
                8 algoritmos activos
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
            <span className="text-2xl">📚</span>
            <div>
              <div className="font-medium text-amber-900 dark:text-amber-100 text-sm">
                Base de Datos
              </div>
              <div className="text-xs text-amber-700 dark:text-amber-300">
                13K+ movimientos
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <span className="text-2xl">🎯</span>
            <div>
              <div className="font-medium text-purple-900 dark:text-purple-100 text-sm">
                Aprendizaje
              </div>
              <div className="text-xs text-purple-700 dark:text-purple-300">
                Auto-mejora activa
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}