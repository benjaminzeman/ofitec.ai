'use client'

import Link from 'next/link';

export default function ClientePage() {
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            Portal Cliente
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Vista de Proyectos, Reportes Ejecutivos e Interacción Cliente
          </p>
        </div>
      </div>

      {/* Grid de módulos */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* Vista de Proyecto */}
        <Link href="/cliente/proyecto" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">🏗️</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Vista de Proyecto
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Dashboard ejecutivo con estado de proyecto y avance en tiempo real
            </p>
            <div className="mt-4 text-xs text-lime-600 dark:text-lime-400">
              ✅ Disponible
            </div>
          </div>
        </Link>

        {/* Reportes Ejecutivos */}
        <Link href="/cliente/reportes" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">📊</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Reportes Ejecutivos
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Reportes personalizados y dashboards para nivel ejecutivo
            </p>
            <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
              🚧 En desarrollo
            </div>
          </div>
        </Link>

        {/* Interacción Cliente */}
        <Link href="/cliente/interaccion" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">💬</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Interacción Cliente
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Sistema de comunicación directa y feedback de clientes
            </p>
            <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
              🚧 En desarrollo
            </div>
          </div>
        </Link>
      </div>

      {/* Dashboard cliente */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Proyectos Activos */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Proyectos en Portal
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Total Proyectos</span>
              <span className="text-lg font-bold text-slate-600">3</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">En Progreso</span>
              <span className="text-lg font-bold text-lime-600">2</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Completados</span>
              <span className="text-lg font-bold text-blue-600">1</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Usuarios Activos</span>
              <span className="text-lg font-bold text-slate-600">12</span>
            </div>
          </div>
        </div>

        {/* Interacciones Recientes */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Actividad Reciente
          </h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-lime-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Cliente revisó avance Proyecto Alpha
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-blue-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Reporte mensual entregado
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-amber-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Solicitud de información pendiente
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}