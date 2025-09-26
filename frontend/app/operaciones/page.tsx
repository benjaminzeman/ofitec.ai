'use client'

import Link from 'next/link';

export default function OperacionesPage() {
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            Operaciones
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Reportes Digitales, HSE Inteligente y Control de Recursos
          </p>
        </div>
      </div>

      {/* Grid de módulos */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* Reportes Digitales */}
        <Link href="/operaciones/reportes" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">📊</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Reportes Digitales
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Sistema de reportes digitales para seguimiento de obra en tiempo real
            </p>
            <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
              🚧 En desarrollo
            </div>
          </div>
        </Link>

        {/* HSE Inteligente */}
        <Link href="/operaciones/hse" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">🛡️</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              HSE Inteligente
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Gestión de Salud, Seguridad y Medio Ambiente con IA predictiva
            </p>
            <div className="mt-4 text-xs text-lime-600 dark:text-lime-400">
              ✅ Disponible
            </div>
          </div>
        </Link>

        {/* Control de Recursos */}
        <Link href="/operaciones/recursos" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">🏗️</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Control Recursos
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Gestión de recursos humanos, materiales y equipos de obra
            </p>
            <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
              🚧 En desarrollo
            </div>
          </div>
        </Link>

        {/* Comunicación */}
        <Link href="/operaciones/comunicacion" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">💬</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Comunicación
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Sistema de comunicación interna y coordinación de equipos
            </p>
            <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
              🚧 En desarrollo
            </div>
          </div>
        </Link>
      </div>

      {/* Stats rápidas */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Resumen Operacional
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-lime-600">1</div>
            <div className="text-sm text-slate-600 dark:text-slate-400">Módulo Activo</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-amber-600">3</div>
            <div className="text-sm text-slate-600 dark:text-slate-400">En Desarrollo</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-slate-600">0</div>
            <div className="text-sm text-slate-600 dark:text-slate-400">Reportes Activos</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-slate-600">0</div>
            <div className="text-sm text-slate-600 dark:text-slate-400">Alertas HSE</div>
          </div>
        </div>
      </div>
    </div>
  );
}