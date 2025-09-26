'use client'

export default function DocumentosDocuchatPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="text-center py-12">
        <div className="h-24 w-24 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-6">
          <span className="text-4xl">💬</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-4">
          DocuChat AI
        </h1>
        <p className="text-slate-600 dark:text-slate-400 mb-8 max-w-md mx-auto">
          Asistente IA para consulta inteligente de documentos y especificaciones técnicas.
        </p>
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-6 max-w-md mx-auto">
          <h3 className="text-amber-800 dark:text-amber-200 font-semibold mb-2">🚧 En Desarrollo</h3>
          <p className="text-amber-700 dark:text-amber-300 text-sm">
            Sistema de chat con IA para consultar documentos técnicos, planos,
            especificaciones y normativas de construcción.
          </p>
        </div>
      </div>
    </div>
  );
}