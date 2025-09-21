import { useState, useEffect } from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  closable?: boolean;
  className?: string;
}

export default function Modal({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  closable = true,
  className = '',
}: ModalProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setIsVisible(true);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
      setTimeout(() => setIsVisible(false), 150);
    }

    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && closable) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, closable, onClose]);

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'max-w-md';
      case 'md':
        return 'max-w-lg';
      case 'lg':
        return 'max-w-2xl';
      case 'xl':
        return 'max-w-4xl';
      case 'full':
        return 'max-w-full mx-4';
      default:
        return 'max-w-lg';
    }
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className={`fixed inset-0 bg-black transition-opacity duration-300 ${
          isOpen ? 'opacity-50' : 'opacity-0'
        }`}
        onClick={closable ? onClose : undefined}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          className={`relative transform transition-all duration-300 ${
            isOpen ? 'scale-100 opacity-100' : 'scale-95 opacity-0'
          } w-full ${getSizeClasses()}`}
        >
          <div
            className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl ${className}`}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
              {closable && (
                <button
                  onClick={onClose}
                  className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  <span className="text-xl">×</span>
                </button>
              )}
            </div>

            {/* Content */}
            <div className="p-6">{children}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  type?: 'info' | 'warning' | 'danger';
  loading?: boolean;
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  type = 'info',
  loading = false,
}: ConfirmModalProps) {
  const getTypeConfig = () => {
    switch (type) {
      case 'warning':
        return {
          icon: '⚠',
          iconBg: 'bg-amber-50 dark:bg-amber-950',
          iconColor: 'text-amber-600 dark:text-amber-400',
          buttonBg: 'bg-amber-500 hover:bg-amber-600',
        };
      case 'danger':
        return {
          icon: '⚠',
          iconBg: 'bg-red-50 dark:bg-red-950',
          iconColor: 'text-red-600 dark:text-red-400',
          buttonBg: 'bg-red-500 hover:bg-red-600',
        };
      default:
        return {
          icon: 'ℹ',
          iconBg: 'bg-blue-50 dark:bg-blue-950',
          iconColor: 'text-blue-600 dark:text-blue-400',
          buttonBg: 'bg-lime-500 hover:bg-lime-600',
        };
    }
  };

  const config = getTypeConfig();

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <div className="space-y-4">
        <div className="flex items-start gap-4">
          <div
            className={`w-10 h-10 ${config.iconBg} rounded-xl flex items-center justify-center flex-shrink-0`}
          >
            <span className={`text-lg ${config.iconColor}`}>{config.icon}</span>
          </div>
          <div className="flex-1">
            <p className="text-slate-700 dark:text-slate-300">{message}</p>
          </div>
        </div>

        <div className="flex gap-3 pt-4">
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`flex-1 px-4 py-2 text-white rounded-xl focus:outline-none focus:ring-2 focus:ring-opacity-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${config.buttonBg}`}
          >
            {loading ? (
              <div className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Procesando...
              </div>
            ) : (
              confirmLabel
            )}
          </button>

          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {cancelLabel}
          </button>
        </div>
      </div>
    </Modal>
  );
}
