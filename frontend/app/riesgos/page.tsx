'use client'

import Link from 'next/link';

export default function RiesgosPage() {
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            Gestión de Riesgos
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Matriz de Riesgos IA, Predicciones ML y Sistema de Alertas
          </p>
        </div>
      </div>

      {/* Grid de módulos */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* Matriz de Riesgos */}
        <Link href="/riesgos/matriz" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">🛡️</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Matriz de Riesgos
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Matriz inteligente de identificación, evaluación y mitigación de riesgos
            </p>
            <div className="mt-4 text-xs text-lime-600 dark:text-lime-400">
              ✅ Disponible
            </div>
          </div>
        </Link>

        {/* Predicciones ML */}
        <Link href="/riesgos/predicciones" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">🔮</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Predicciones ML
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Machine Learning para predicción de riesgos y alertas tempranas
            </p>
            <div className="mt-4 text-xs text-lime-600 dark:text-lime-400">
              ✅ Disponible
            </div>
          </div>
        </Link>

        {/* Sistema de Alertas */}
        <Link href="/riesgos/alertas" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">🚨</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Sistema de Alertas
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Alertas automáticas y notificaciones de riesgos críticos
            </p>
            <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
              🚧 En desarrollo
            </div>
          </div>
        </Link>
      </div>

      {/* Dashboard de riesgos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Resumen de Riesgos */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Estado de Riesgos
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Riesgos Críticos</span>
              <span className="text-lg font-bold text-red-600">0</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Riesgos Altos</span>
              <span className="text-lg font-bold text-amber-600">2</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Riesgos Medios</span>
              <span className="text-lg font-bold text-lime-600">5</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Riesgos Bajos</span>
              <span className="text-lg font-bold text-slate-600">12</span>
            </div>
          </div>
        </div>

        {/* Últimas Predicciones */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Predicciones Recientes
          </h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-amber-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Retraso potencial en Proyecto Alpha
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-lime-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Optimización de recursos disponible
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-amber-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Riesgo climático próxima semana
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}