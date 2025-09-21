import React, { createContext, useContext, useReducer, useCallback } from 'react';

export interface Toast {
  id: string;
  title?: string;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastState {
  toasts: Toast[];
}

type ToastAction =
  | { type: 'ADD_TOAST'; toast: Toast }
  | { type: 'REMOVE_TOAST'; id: string }
  | { type: 'CLEAR_ALL' };

const ToastContext = createContext<{
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
  clearAll: () => void;
} | null>(null);

function toastReducer(state: ToastState, action: ToastAction): ToastState {
  switch (action.type) {
    case 'ADD_TOAST':
      return {
        ...state,
        toasts: [...state.toasts, action.toast],
      };
    case 'REMOVE_TOAST':
      return {
        ...state,
        toasts: state.toasts.filter((toast) => toast.id !== action.id),
      };
    case 'CLEAR_ALL':
      return {
        ...state,
        toasts: [],
      };
    default:
      return state;
  }
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(toastReducer, { toasts: [] });

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newToast: Toast = {
      ...toast,
      id,
      duration: toast.duration ?? 5000,
    };

    dispatch({ type: 'ADD_TOAST', toast: newToast });

    // Auto-remove toast after duration
    if (newToast.duration > 0) {
      setTimeout(() => {
        dispatch({ type: 'REMOVE_TOAST', id });
      }, newToast.duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    dispatch({ type: 'REMOVE_TOAST', id });
  }, []);

  const clearAll = useCallback(() => {
    dispatch({ type: 'CLEAR_ALL' });
  }, []);

  return (
    <ToastContext.Provider
      value={{
        toasts: state.toasts,
        addToast,
        removeToast,
        clearAll,
      }}
    >
      {children}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

// Hook conveniente para casos comunes
export function useToastActions() {
  const { addToast } = useToast();

  const success = useCallback(
    (message: string, title?: string) => {
      return addToast({ type: 'success', message, title });
    },
    [addToast],
  );

  const error = useCallback(
    (message: string, title?: string) => {
      return addToast({ type: 'error', message, title });
    },
    [addToast],
  );

  const warning = useCallback(
    (message: string, title?: string) => {
      return addToast({ type: 'warning', message, title });
    },
    [addToast],
  );

  const info = useCallback(
    (message: string, title?: string) => {
      return addToast({ type: 'info', message, title });
    },
    [addToast],
  );

  return { success, error, warning, info, addToast };
}
