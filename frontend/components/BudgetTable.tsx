import React from 'react';
import { formatCLP } from './KPI';

export function BudgetTable({
  totals,
  chapters,
}: {
  totals: { pc_total: number; committed: number; available_conservative: number };
  chapters?: Array<{ name: string; amount: number }>;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-sm text-slate-500">
            <th className="py-2">Concepto</th>
            <th className="py-2 text-right">Monto</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
          <tr>
            <td className="py-2">Presupuesto Total (PC)</td>
            <td className="py-2 text-right font-medium">{formatCLP(totals.pc_total || 0)}</td>
          </tr>
          <tr>
            <td className="py-2">Comprometido (OC)</td>
            <td className="py-2 text-right">{formatCLP(totals.committed || 0)}</td>
          </tr>
          <tr>
            <td className="py-2">Disponible Conservador</td>
            <td className="py-2 text-right">{formatCLP(totals.available_conservative || 0)}</td>
          </tr>
          {Array.isArray(chapters) && chapters.length > 0 && (
            <tr>
              <td colSpan={2} className="pt-4 text-sm text-slate-500">
                Capítulos
              </td>
            </tr>
          )}
          {Array.isArray(chapters) &&
            chapters.map((c, i) => (
              <tr key={i}>
                <td className="py-2">{c.name}</td>
                <td className="py-2 text-right">{formatCLP(c.amount || 0)}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
