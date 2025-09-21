'use client';

import { useEffect, useState } from 'react';

export default function HSEPage() {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api';
      const resp = await fetch(`${base}/hse/resumen`);
      const payload = await resp.json();
      setSummary(payload.summary || {});
      setLoading(false);
    }
    load();
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
          HSE Inteligente
        </h1>
        <p className="text-slate-500 dark:text-slate-400">
          Incidentes, inspecciones y cumplimiento EPP
        </p>
      </div>
      {loading ? (
        <div className="text-slate-500">Cargando…</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
            <div className="text-sm text-slate-500">Incidentes</div>
            <div className="text-3xl font-bold">{summary?.incidentes ?? 0}</div>
            <div className="text-xs text-slate-500">
              Último: {summary?.ult_incidente_fecha || '-'}
            </div>
          </div>
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
            <div className="text-sm text-slate-500">Inspecciones</div>
            <div className="text-3xl font-bold">{summary?.inspecciones ?? 0}</div>
          </div>
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
            <div className="text-sm text-slate-500">Cumplimiento EPP (%)</div>
            <div className="text-3xl font-bold">{summary?.cumplimiento_epp_pct ?? '-'}</div>
          </div>
        </div>
      )}
    </div>
  );
}
