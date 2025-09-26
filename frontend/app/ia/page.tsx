'use client'

import Link from 'next/link';

export default function IAPage() {
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            IA & Analytics
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Copilots Especializados, Analytics Avanzados y ML Insights
          </p>
        </div>
      </div>

      {/* Grid de módulos */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* Copilots Especializados */}
        <Link href="/ia/copilots" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">🤖</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Copilots Especializados
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Asistentes IA especializados para diferentes áreas de la construcción
            </p>
            <div className="mt-4 text-xs text-lime-600 dark:text-lime-400">
              ✅ Disponible
            </div>
          </div>
        </Link>

        {/* Analytics Avanzados */}
        <Link href="/ia/analytics" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">📈</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Analytics Avanzados
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Análisis predictivo y business intelligence para toma de decisiones
            </p>
            <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
              🚧 En desarrollo
            </div>
          </div>
        </Link>

        {/* ML Insights */}
        <Link href="/ia/insights" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">🧠</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              ML Insights
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Insights automáticos y patrones detectados por Machine Learning
            </p>
            <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
              🚧 En desarrollo
            </div>
          </div>
        </Link>
      </div>

      {/* Dashboard IA */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Estado de IA */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Estado del Sistema IA
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Copilots Activos</span>
              <span className="text-lg font-bold text-lime-600">3</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Modelos Entrenados</span>
              <span className="text-lg font-bold text-blue-600">7</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Predicciones Diarias</span>
              <span className="text-lg font-bold text-slate-600">150+</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Precisión Promedio</span>
              <span className="text-lg font-bold text-lime-600">87%</span>
            </div>
          </div>
        </div>

        {/* Insights Recientes */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Insights Recientes
          </h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-lime-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Optimización de costos detectada: -15%
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-amber-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Patrón de retrasos identificado
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-blue-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Nueva correlación financiera encontrada
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-lime-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Modelo de predicción actualizado
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}