'use client';

export default function ArAdminPage() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-6">
          Administración AR
        </h1>
        
        <div className="bg-white dark:bg-slate-800 rounded-lg p-6 shadow-sm border border-slate-200 dark:border-slate-700">
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🔧</div>
            <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Módulo en Desarrollo
            </h2>
            <p className="text-slate-600 dark:text-slate-300">
              Panel de administración AR funcionando correctamente.
              Funcionalidades avanzadas próximamente.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}