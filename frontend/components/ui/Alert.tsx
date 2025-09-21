import { useState, useCallback, useEffect } from 'react';

interface AlertProps {
  type: 'success' | 'warning' | 'error' | 'info';
  title?: string;
  message: string;
  dismissible?: boolean;
  onDismiss?: () => void;
  className?: string;
  children?: React.ReactNode;
}

export default function Alert({
  type,
  title,
  message,
  dismissible = false,
  onDismiss,
  className = '',
  children,
}: AlertProps) {
  const getTypeConfig = () => {
    switch (type) {
      case 'success':
        return {
          icon: '✔',
          bgColor: 'bg-lime-50 dark:bg-lime-950',
          borderColor: 'border-lime-200 dark:border-lime-800',
          textColor: 'text-lime-800 dark:text-lime-200',
          iconColor: 'text-lime-600 dark:text-lime-400',
        };
      case 'warning':
        return {
          icon: '⚠',
          bgColor: 'bg-amber-50 dark:bg-amber-950',
          borderColor: 'border-amber-200 dark:border-amber-800',
          textColor: 'text-amber-800 dark:text-amber-200',
          iconColor: 'text-amber-600 dark:text-amber-400',
        };
      case 'error':
        return {
          icon: '⚠',
          bgColor: 'bg-red-50 dark:bg-red-950',
          borderColor: 'border-red-200 dark:border-red-800',
          textColor: 'text-red-800 dark:text-red-200',
          iconColor: 'text-red-600 dark:text-red-400',
        };
      case 'info':
      default:
        return {
          icon: 'ℹ',
          bgColor: 'bg-blue-50 dark:bg-blue-950',
          borderColor: 'border-blue-200 dark:border-blue-800',
          textColor: 'text-blue-800 dark:text-blue-200',
          iconColor: 'text-blue-600 dark:text-blue-400',
        };
    }
  };

  const config = getTypeConfig();

  return (
    <div className={`border rounded-xl p-4 ${config.bgColor} ${config.borderColor} ${className}`}>
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 ${config.iconColor}`}>
          <span className="text-lg">{config.icon}</span>
        </div>

        <div className="flex-1 min-w-0">
          {title && <h4 className={`text-sm font-medium ${config.textColor} mb-1`}>{title}</h4>}

          <div className={`text-sm ${config.textColor}`}>{message}</div>

          {children && <div className="mt-3">{children}</div>}
        </div>

        {dismissible && onDismiss && (
          <button
            onClick={onDismiss}
            className={`flex-shrink-0 ${config.textColor} hover:opacity-70 transition-opacity`}
          >
            <span className="text-lg">×</span>
          </button>
        )}
      </div>
    </div>
  );
}

interface ToastProps {
  type: 'success' | 'warning' | 'error' | 'info';
  message: string;
  duration?: number;
  onClose: () => void;
}

export function Toast({ type, message, duration = 5000, onClose }: ToastProps) {
  const config = {
    success: {
      icon: '✔',
      bgColor: 'bg-lime-500',
      textColor: 'text-white',
    },
    warning: {
      icon: '⚠',
      bgColor: 'bg-amber-500',
      textColor: 'text-white',
    },
    error: {
      icon: '⚠',
      bgColor: 'bg-red-500',
      textColor: 'text-white',
    },
    info: {
      icon: 'ℹ',
      bgColor: 'bg-blue-500',
      textColor: 'text-white',
    },
  }[type];

  // Auto-dismiss after duration
  useEffect(() => {
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  return (
    <div
      className={`fixed top-4 right-4 z-50 ${config.bgColor} ${config.textColor} rounded-xl shadow-lg p-4 max-w-sm transform transition-all duration-300`}
    >
      <div className="flex items-start gap-3">
        <span className="text-lg flex-shrink-0">{config.icon}</span>
        <div className="flex-1 text-sm">{message}</div>
        <button onClick={onClose} className="flex-shrink-0 hover:opacity-70 transition-opacity">
          <span className="text-lg">×</span>
        </button>
      </div>
    </div>
  );
}

// Toast Manager Hook

interface ToastItem {
  id: string;
  type: 'success' | 'warning' | 'error' | 'info';
  message: string;
  duration?: number;
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = useCallback((toast: Omit<ToastItem, 'id'>) => {
    const id = Math.random().toString(36).substring(2);
    setToasts((prev) => [...prev, { ...toast, id }]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const showSuccess = useCallback(
    (message: string, duration?: number) => {
      addToast({ type: 'success', message, duration });
    },
    [addToast],
  );

  const showError = useCallback(
    (message: string, duration?: number) => {
      addToast({ type: 'error', message, duration });
    },
    [addToast],
  );

  const showWarning = useCallback(
    (message: string, duration?: number) => {
      addToast({ type: 'warning', message, duration });
    },
    [addToast],
  );

  const showInfo = useCallback(
    (message: string, duration?: number) => {
      addToast({ type: 'info', message, duration });
    },
    [addToast],
  );

  const ToastContainer = useCallback(
    () => (
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            type={toast.type}
            message={toast.message}
            duration={toast.duration}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>
    ),
    [toasts, removeToast],
  );

  return {
    showSuccess,
    showError,
    showWarning,
    showInfo,
    ToastContainer,
  };
}
