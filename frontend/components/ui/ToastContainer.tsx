import React, { useEffect, useState } from 'react';
import { useToast, Toast } from './ToastContext';

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: (id: string) => void }) {
  const [isVisible, setIsVisible] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  useEffect(() => {
    // Trigger enter animation
    setTimeout(() => setIsVisible(true), 10);
  }, []);

  const handleRemove = () => {
    setIsLeaving(true);
    setTimeout(() => onRemove(toast.id), 200);
  };

  const getToastStyles = () => {
    const baseStyles = 'border-l-4 shadow-lg';

    switch (toast.type) {
      case 'success':
        return `${baseStyles} bg-white dark:bg-slate-800 border-lime-500 text-slate-900 dark:text-slate-100`;
      case 'error':
        return `${baseStyles} bg-white dark:bg-slate-800 border-red-500 text-slate-900 dark:text-slate-100`;
      case 'warning':
        return `${baseStyles} bg-white dark:bg-slate-800 border-amber-500 text-slate-900 dark:text-slate-100`;
      case 'info':
        return `${baseStyles} bg-white dark:bg-slate-800 border-blue-500 text-slate-900 dark:text-slate-100`;
      default:
        return `${baseStyles} bg-white dark:bg-slate-800 border-slate-300 text-slate-900 dark:text-slate-100`;
    }
  };

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return '✅';
      case 'error':
        return '❌';
      case 'warning':
        return '⚠️';
      case 'info':
        return 'ℹ️';
      default:
        return '📝';
    }
  };

  return (
    <div
      className={`
      transform transition-all duration-300 ease-in-out
      ${isVisible && !isLeaving ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
      rounded-xl p-4 pointer-events-auto max-w-sm w-full
      ${getToastStyles()}
    `}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 text-lg">{getIcon()}</div>
        <div className="flex-1 min-w-0">
          {toast.title && <p className="text-sm font-semibold mb-1">{toast.title}</p>}
          <p className="text-sm text-slate-600 dark:text-slate-400">{toast.message}</p>
          {toast.action && (
            <button
              onClick={toast.action.onClick}
              className="mt-2 text-sm font-medium text-lime-600 hover:text-lime-700 dark:text-lime-400 dark:hover:text-lime-300"
            >
              {toast.action.label}
            </button>
          )}
        </div>
        <button
          onClick={handleRemove}
          className="flex-shrink-0 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 ml-2"
        >
          <span className="sr-only">Cerrar</span>✕
        </button>
      </div>
    </div>
  );
}

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={removeToast} />
      ))}
    </div>
  );
}
