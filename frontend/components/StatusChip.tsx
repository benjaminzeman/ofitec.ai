'use client';

/**
 * StatusChip - Componente de estado según ESTRATEGIA_VISUAL.md
 * Reemplaza emojis con badges semánticos usando tokens del design system
 */

interface StatusChipProps {
  kind: 'ok' | 'warn' | 'error' | 'neutral' | 'pending' | 'active' | 'inactive';
  children: React.ReactNode;
  size?: 'sm' | 'md';
}

export function StatusChip({ kind, children, size = 'sm' }: StatusChipProps) {
  // Tokens del design system - paleta oficial
  const styles = {
    ok: 'border-lime-500 text-lime-700 bg-lime-50 dark:border-lime-400 dark:text-lime-300 dark:bg-lime-950',
    warn: 'border-amber-500 text-amber-700 bg-amber-50 dark:border-amber-400 dark:text-amber-300 dark:bg-amber-950',
    error:
      'border-red-500 text-red-700 bg-red-50 dark:border-red-400 dark:text-red-300 dark:bg-red-950',
    neutral:
      'border-slate-300 text-slate-700 bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:bg-slate-900',
    pending:
      'border-amber-500 text-amber-700 bg-amber-50 dark:border-amber-400 dark:text-amber-300 dark:bg-amber-950',
    active:
      'border-lime-500 text-lime-700 bg-lime-50 dark:border-lime-400 dark:text-lime-300 dark:bg-lime-950',
    inactive:
      'border-slate-300 text-slate-500 bg-slate-50 dark:border-slate-600 dark:text-slate-400 dark:bg-slate-900',
  };

  // Iconos de estado sin emojis - usando símbolos simples
  const icons = {
    ok: '✓', // Check mark
    warn: '!', // Exclamation
    error: '×', // Cross
    neutral: '•', // Dot
    pending: '○', // Circle
    active: '●', // Filled circle
    inactive: '○', // Empty circle
  };

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm';

  return (
    <span
      className={`
        inline-flex items-center gap-1 rounded-full border font-medium
        ${styles[kind]}
        ${sizeClasses}
      `}
    >
      <span className="leading-none">{icons[kind]}</span>
      {children}
    </span>
  );
}

/**
 * Chips específicos para estados comunes del sistema
 */
export const ConciliadoChip = ({ children }: { children?: React.ReactNode }) => (
  <StatusChip kind="ok">{children || 'Conciliado'}</StatusChip>
);

export const PendienteChip = ({ children }: { children?: React.ReactNode }) => (
  <StatusChip kind="pending">{children || 'Pendiente'}</StatusChip>
);

export const ErrorChip = ({ children }: { children?: React.ReactNode }) => (
  <StatusChip kind="error">{children || 'Error'}</StatusChip>
);

export const AdvertenciaChip = ({ children }: { children?: React.ReactNode }) => (
  <StatusChip kind="warn">{children || 'Advertencia'}</StatusChip>
);
