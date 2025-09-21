'use client';

import React from 'react';

export interface ActionItem {
  id: string | number;
  title: string;
  description?: string;
  priority?: 'high' | 'medium' | 'low';
  href?: string;
}

interface ActionsListProps {
  items: ActionItem[];
  emptyText?: string;
}

const badgeByPriority: Record<string, string> = {
  high: 'bg-red-100 text-red-700 border-red-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  low: 'bg-lime-100 text-lime-700 border-lime-200',
};

export default function ActionsList({
  items,
  emptyText = 'Sin acciones pendientes',
}: ActionsListProps) {
  if (!items || items.length === 0) {
    return <div className="text-sm text-slate-500 dark:text-slate-400 italic">{emptyText}</div>;
  }

  return (
    <ul className="space-y-3">
      {items.map((a) => (
        <li key={a.id} className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-medium text-slate-900 dark:text-slate-100">{a.title}</div>
            {a.description && (
              <div className="text-xs text-slate-500 dark:text-slate-400">{a.description}</div>
            )}
          </div>
          {a.priority && (
            <span
              className={`text-xs border px-2 py-1 rounded-lg ${badgeByPriority[a.priority] || 'bg-slate-100 text-slate-700 border-slate-200'}`}
            >
              {a.priority === 'high' ? 'Alta' : a.priority === 'medium' ? 'Media' : 'Baja'}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}
