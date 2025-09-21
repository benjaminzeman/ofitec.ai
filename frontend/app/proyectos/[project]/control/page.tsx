'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

type Summary = {
  presupuesto?: number;
  compras?: number;
  ventas?: number;
  margen?: number;
};

function CLP(n: number) {
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
  }).format(Number(n || 0));
}

export default function ProyectoControlDetailPage() {
  const params = useParams() as { project: string };
  const projectId = decodeURIComponent(params.project);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<Summary>({});

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api';
    // Reutilizamos endpoint existente de resumen por proyecto
    fetch(`${base}/proyectos/${encodeURIComponent(projectId)}/resumen`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => setSummary(data || {}))
      .catch((e) => setError(e?.message || 'Error'))
      .finally(() => setLoading(false));
  }, [projectId]);

  const pc = Number(summary.presupuesto || 0);
  const oc = Number(summary.compras || 0);
  const ap = 0; // placeholder hasta integrar v_facturas_compra a nivel de proyecto
  const paid = 0; // placeholder hasta integrar conciliación por proyecto

  const items = useMemo(
    () => [
      { label: 'Presupuesto (PC)', value: pc, color: 'bg-slate-300 dark:bg-slate-600' },
      { label: 'Comprometido (OC)', value: oc, color: 'bg-lime-500' },
      { label: 'Facturado (AP)', value: ap, color: 'bg-yellow-500' },
      { label: 'Pagado', value: paid, color: 'bg-blue-500' },
    ],
    [pc, oc, ap, paid],
  );

  const exceeds = oc > pc && pc > 0;
  const availableC = Math.max(0, pc - oc);

  return (
    <div className="p-6 space-y-6">
      <div className="text-sm text-slate-500 dark:text-slate-400">
        <Link href="/proyectos" className="hover:underline">
          Proyectos
        </Link>
        <span className="mx-2">/</span>
        <Link href="/proyectos/control" className="hover:underline">
          Control Financiero
        </Link>
        <span className="mx-2">/</span>
        <span className="text-slate-700 dark:text-slate-300">{projectId}</span>
      </div>
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
        Control Financiero — {projectId}
      </h1>
      {loading && <div className="text-slate-500">Cargando...</div>}
      {error && <div className="text-red-600">{error}</div>}

      {!loading && !error && (
        <>
          {exceeds && (
            <div className="rounded-lg border border-red-300 bg-red-50 text-red-800 p-3">
              Advertencia: Comprometido supera Presupuesto.
            </div>
          )}

          <div className="space-y-3">
            {items.map((it, i) => (
              <div key={i} className="w-full">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-700 dark:text-slate-300">{it.label}</span>
                  <span className="font-medium text-slate-900 dark:text-slate-100">
                    {CLP(it.value)}
                  </span>
                </div>
                <div className="w-full h-3 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`${it.color} h-3`}
                    style={{ width: `${pc > 0 ? Math.min(100, (it.value / pc) * 100) : 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-4">
              <div className="text-slate-600 dark:text-slate-400">Disponible Conservador</div>
              <div className="text-xl font-bold">{CLP(availableC)}</div>
            </div>
            <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-4">
              <div className="text-slate-600 dark:text-slate-400">Margen (Ventas - Compras)</div>
              <div className="text-xl font-bold">{CLP(Number(summary.margen || 0))}</div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
