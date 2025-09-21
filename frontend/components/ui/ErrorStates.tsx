import React from 'react';

interface ErrorDisplayProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorDisplay({
  title = 'Error al cargar datos',
  message = 'Ha ocurrido un error inesperado. Por favor intenta nuevamente.',
  onRetry,
  className = '',
}: ErrorDisplayProps) {
  return (
    <div className={`p-6 ${className}`}>
      <div className="bg-white dark:bg-slate-800 border border-red-200 dark:border-red-700 rounded-xl">
        <div className="p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-red-50 dark:bg-red-950 rounded-xl flex items-center justify-center">
            <span className="text-red-600 dark:text-red-400 text-2xl">⚠</span>
          </div>
          <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">{title}</h3>
          <p className="text-sm text-red-700 dark:text-red-300 mb-6">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-4 py-2 bg-red-600 text-white rounded-xl hover:bg-red-700 transition-colors"
            >
              Intentar nuevamente
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

interface EmptyStateProps {
  title?: string;
  message?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  icon?: string;
  className?: string;
}

export function EmptyState({
  title = 'No hay datos disponibles',
  message = 'No se encontraron datos para mostrar en este momento.',
  action,
  icon = '📁',
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`p-6 ${className}`}>
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
        <div className="p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-slate-50 dark:bg-slate-900 rounded-xl flex items-center justify-center">
            <span className="text-slate-400 text-2xl">{icon}</span>
          </div>
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">{title}</h3>
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">{message}</p>
          {action && (
            <button
              onClick={action.onClick}
              className="px-4 py-2 bg-lime-600 text-white rounded-xl hover:bg-lime-700 transition-colors"
            >
              {action.label}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

interface NetworkErrorProps {
  onRetry?: () => void;
}

export function NetworkError({ onRetry }: NetworkErrorProps) {
  return (
    <ErrorDisplay
      title="Error de conexión"
      message="No se pudo conectar con el servidor. Verifica tu conexión a internet e intenta nuevamente."
      onRetry={onRetry}
    />
  );
}

interface TimeoutErrorProps {
  onRetry?: () => void;
}

export function TimeoutError({ onRetry }: TimeoutErrorProps) {
  return (
    <ErrorDisplay
      title="Tiempo de espera agotado"
      message="La carga de datos está tomando más tiempo del esperado. Por favor intenta nuevamente."
      onRetry={onRetry}
    />
  );
}

interface DataErrorProps {
  onRetry?: () => void;
}

export function DataError({ onRetry }: DataErrorProps) {
  return (
    <ErrorDisplay
      title="Error en los datos"
      message="Los datos recibidos no tienen el formato esperado. Estamos usando información de ejemplo."
      onRetry={onRetry}
    />
  );
}
