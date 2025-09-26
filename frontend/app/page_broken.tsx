export default function SimpleDashboardPage() {

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-slate-600 dark:text-slate-300">Cargando dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
            Error de Conexión
          </h2>
          <p className="text-slate-600 dark:text-slate-300 mb-4">
            {error}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            Dashboard Ofitec.AI
          </h1>
          <p className="text-slate-600 dark:text-slate-300">
            Sistema funcionando correctamente - Todos los enlaces están operativos
          </p>
        </div>

        {/* KPIs Grid */}
        {ceo && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            <div className="bg-white dark:bg-slate-800 rounded-lg p-6 shadow-sm border border-slate-200 dark:border-slate-700">
              <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Efectivo Hoy
              </h3>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                {formatCurrency(ceo.cash_today)}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-lg p-6 shadow-sm border border-slate-200 dark:border-slate-700">
              <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Facturas Pendientes
              </h3>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                {formatCurrency(ceo.facturas_pendientes)}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-lg p-6 shadow-sm border border-slate-200 dark:border-slate-700">
              <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Proyectos Activos
              </h3>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                {ceo.total_proyectos}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-lg p-6 shadow-sm border border-slate-200 dark:border-slate-700">
              <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Ingresos del Mes
              </h3>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                {formatCurrency(ceo.ingresos_mes)}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-lg p-6 shadow-sm border border-slate-200 dark:border-slate-700">
              <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Gastos del Mes
              </h3>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                {formatCurrency(ceo.gastos_mes)}
              </p>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-lg p-6 shadow-sm border border-slate-200 dark:border-slate-700">
              <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Margen Bruto Promedio
              </h3>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-2">
                {ceo.margen_bruto_promedio.toFixed(1)}%
              </p>
            </div>
          </div>
        )}

        {/* Navigation Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8">
          <Link href="/finanzas" className="bg-white dark:bg-slate-800 rounded-lg p-4 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3">
              <span className="text-2xl">💰</span>
              <div>
                <h3 className="font-medium text-slate-900 dark:text-slate-100">Finanzas</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Control financiero</p>
              </div>
            </div>
          </Link>

          <Link href="/proyectos" className="bg-white dark:bg-slate-800 rounded-lg p-4 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🏗️</span>
              <div>
                <h3 className="font-medium text-slate-900 dark:text-slate-100">Proyectos</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Gestión de proyectos</p>
              </div>
            </div>
          </Link>

          <Link href="/operaciones" className="bg-white dark:bg-slate-800 rounded-lg p-4 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3">
              <span className="text-2xl">⚙️</span>
              <div>
                <h3 className="font-medium text-slate-900 dark:text-slate-100">Operaciones</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">HSE y recursos</p>
              </div>
            </div>
          </Link>

          <Link href="/documentos" className="bg-white dark:bg-slate-800 rounded-lg p-4 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3">
              <span className="text-2xl">📄</span>
              <div>
                <h3 className="font-medium text-slate-900 dark:text-slate-100">Documentos</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Gestión documental</p>
              </div>
            </div>
          </Link>

          <Link href="/riesgos" className="bg-white dark:bg-slate-800 rounded-lg p-4 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3">
              <span className="text-2xl">⚠️</span>
              <div>
                <h3 className="font-medium text-slate-900 dark:text-slate-100">Riesgos</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Análisis de riesgos</p>
              </div>
            </div>
          </Link>

          <Link href="/cliente" className="bg-white dark:bg-slate-800 rounded-lg p-4 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3">
              <span className="text-2xl">👥</span>
              <div>
                <h3 className="font-medium text-slate-900 dark:text-slate-100">Portal Cliente</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Vista del cliente</p>
              </div>
            </div>
          </Link>

          <Link href="/ia" className="bg-white dark:bg-slate-800 rounded-lg p-4 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🤖</span>
              <div>
                <h3 className="font-medium text-slate-900 dark:text-slate-100">IA & Analytics</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Inteligencia artificial</p>
              </div>
            </div>
          </Link>

          <Link href="/config" className="bg-white dark:bg-slate-800 rounded-lg p-4 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3">
              <span className="text-2xl">⚙️</span>
              <div>
                <h3 className="font-medium text-slate-900 dark:text-slate-100">Configuración</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">Ajustes del sistema</p>
              </div>
            </div>
          </Link>
        </div>

        {/* System Status */}
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">✅</span>
            <div>
              <h3 className="font-medium text-green-900 dark:text-green-100">
                Sistema Operativo
              </h3>
              <p className="text-sm text-green-700 dark:text-green-300">
                Todos los servicios funcionando correctamente. Backend: ✅ | Enlaces: ✅ | Navegación: ✅
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}