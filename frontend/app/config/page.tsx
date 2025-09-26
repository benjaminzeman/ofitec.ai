'use client'

import Link from 'next/link';

export default function ConfigPage() {
  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            Configuración del Sistema
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Gestión de Usuarios, Integraciones y Personalización
          </p>
        </div>
      </div>

      {/* Grid de módulos */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* Gestión de Usuarios */}
        <Link href="/config/usuarios" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">👥</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Gestión de Usuarios
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Administración de usuarios, roles y permisos del sistema
            </p>
            <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
              🚧 En desarrollo
            </div>
          </div>
        </Link>

        {/* Integraciones */}
        <Link href="/config/integraciones" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">🔗</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Integraciones
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Configuración de APIs, webhooks y conexiones externas
            </p>
            <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
              🚧 En desarrollo
            </div>
          </div>
        </Link>

        {/* Personalización */}
        <Link href="/config/personalizacion" className="group">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 hover:shadow-lg transition-all duration-200 group-hover:border-lime-500">
            <div className="h-12 w-12 bg-lime-500/10 rounded-xl flex items-center justify-center mb-4">
              <span className="text-2xl">🎨</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Personalización
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Temas, layouts y preferencias personales del usuario
            </p>
            <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
              🚧 En desarrollo
            </div>
          </div>
        </Link>
      </div>

      {/* Sistema Info */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Información del Sistema */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Información del Sistema
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Versión</span>
              <span className="text-lg font-bold text-slate-600">v1.0.0</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Usuarios Activos</span>
              <span className="text-lg font-bold text-lime-600">25</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Integraciones</span>
              <span className="text-lg font-bold text-blue-600">8</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-600 dark:text-slate-400">Uptime</span>
              <span className="text-lg font-bold text-lime-600">99.9%</span>
            </div>
          </div>
        </div>

        {/* Configuraciones Pendientes */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
            Configuraciones Pendientes
          </h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-amber-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Configurar backup automático
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-amber-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Revisar permisos de usuario
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-amber-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Actualizar certificados SSL
              </span>
            </div>
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 bg-lime-500 rounded-full"></div>
              <span className="text-sm text-slate-600 dark:text-slate-400">
                Sistema de logs configurado
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}