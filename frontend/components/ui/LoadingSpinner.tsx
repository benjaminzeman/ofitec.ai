import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  className?: string;
}

export function LoadingSpinner({ size = 'md', text, className = '' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <div
        className={`${sizeClasses[size]} animate-spin rounded-full border-2 border-slate-200 border-t-lime-500`}
      ></div>
      {text && <p className="text-sm text-slate-600 dark:text-slate-400 animate-pulse">{text}</p>}
    </div>
  );
}

interface PageLoadingProps {
  title?: string;
  description?: string;
}

export function PageLoading({
  title = 'Cargando...',
  description = 'Por favor espera mientras cargamos los datos',
}: PageLoadingProps) {
  return (
    <div className="p-6">
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl">
        <div className="p-12 text-center">
          <LoadingSpinner size="lg" />
          <h3 className="mt-4 text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{description}</p>
        </div>
      </div>
    </div>
  );
}

interface SkeletonProps {
  className?: string;
  rows?: number;
}

export function Skeleton({ className = '', rows = 1 }: SkeletonProps) {
  return (
    <div className="animate-pulse">
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className={`bg-slate-200 dark:bg-slate-700 rounded ${className} ${i > 0 ? 'mt-2' : ''}`}
        ></div>
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
      <div className="p-6 border-b border-slate-200 dark:border-slate-700">
        <Skeleton className="h-6 w-1/4" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-50 dark:bg-slate-900">
            <tr>
              {Array.from({ length: cols }, (_, i) => (
                <th key={i} className="px-6 py-3">
                  <Skeleton className="h-4 w-full" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {Array.from({ length: rows }, (_, i) => (
              <tr key={i}>
                {Array.from({ length: cols }, (_, j) => (
                  <td key={j} className="px-6 py-4">
                    <Skeleton className="h-4 w-full" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
