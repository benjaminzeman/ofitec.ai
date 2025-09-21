'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

type ControlRow = {
  project_name: string;
  budget_cost: number;
  committed: number;
  available_conservative: number;
  flags?: string[];
};

function CLP(n: number) {
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
  }).format(Number(n || 0));
}

export default function ProyectosControlPage() {
  const [rows, setRows] = useState<ControlRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api';
    fetch(`${base}/projects/control?with_meta=1`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => setRows(data.projects || []))
      .catch((e) => setError(e?.message || 'Error'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
        Control Financiero de Proyectos
      </h1>
      <p className="text-slate-600 dark:text-slate-400">
        Presupuesto (PC), Comprometido (OC) y Disponible Conservador
      </p>

      {loading && <div className="text-slate-500">Cargando...</div>}
      {error && <div className="text-red-600">{error}</div>}

      {!loading && !error && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200">
                <th className="p-3 text-left">Proyecto</th>
                <th className="p-3 text-right">Presupuesto (PC)</th>
                <th className="p-3 text-right">Comprometido (OC)</th>
                <th className="p-3 text-right">Disponible (PC-OC)</th>
                <th className="p-3 text-left">Flags</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, idx) => (
                <tr key={idx} className="border-b border-slate-200 dark:border-slate-700">
                  <td className="p-3">
                    <Link
                      className="text-lime-700 dark:text-lime-400 hover:underline"
                      href={`/proyectos/${encodeURIComponent(r.project_name)}/control`}
                    >
                      {r.project_name}
                    </Link>
                  </td>
                  <td className="p-3 text-right">{CLP(r.budget_cost)}</td>
                  <td className="p-3 text-right">{CLP(r.committed)}</td>
                  <td className="p-3 text-right">{CLP(r.available_conservative)}</td>
                  <td className="p-3">{(r.flags || []).join(', ')}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td className="p-3 text-slate-500" colSpan={5}>
                    Sin proyectos
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
