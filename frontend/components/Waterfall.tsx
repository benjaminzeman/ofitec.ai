import React from 'react';
import { formatCLP } from './KPI';

export interface WaterfallStep {
  label: string;
  amount: number;
  color?: string;
}

export function Waterfall({ steps }: { steps: WaterfallStep[] }) {
  const maxAbs = Math.max(1, ...steps.map((s) => Math.abs(s.amount)));
  return (
    <div className="space-y-2">
      {steps.map((s, idx) => {
        const widthPct = Math.min(100, Math.round((Math.abs(s.amount) / maxAbs) * 100));
        const positive = s.amount >= 0;
        const color = s.color || (positive ? 'bg-lime-500' : 'bg-red-500');
        return (
          <div key={idx} className="flex items-center gap-3">
            <div className="w-48 text-sm text-slate-600 dark:text-slate-400">{s.label}</div>
            <div className="flex-1 bg-slate-200 dark:bg-slate-700 rounded h-3 overflow-hidden">
              <div className={`h-3 ${color}`} style={{ width: `${widthPct}%` }} />
            </div>
            <div
              className={`w-36 text-right text-sm ${positive ? 'text-lime-700 dark:text-lime-400' : 'text-red-600 dark:text-red-400'}`}
            >
              {formatCLP(s.amount)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
