import React from 'react';

export interface LinksBadgeProps {
  count: number;
  amountTotal?: number;
  className?: string;
  title?: string;
}

export default function LinksBadge({ count, amountTotal, className = '', title }: LinksBadgeProps) {
  if (!count || count <= 0) return null;
  const tooltip =
    title ||
    (amountTotal
      ? `${count} vínculo(s) · Total ${new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(amountTotal)}`
      : `${count} vínculo(s)`);
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-200 ${className}`}
      title={tooltip}
    >
      🔗 {count}
    </span>
  );
}
