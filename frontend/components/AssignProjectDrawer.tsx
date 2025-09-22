'use client';

import { useEffect, useState } from 'react';
import { formatCurrency } from '@/lib/api';

type Invoice = {
  invoice_id: number;
  customer_rut: string;
  customer_name: string;
  invoice_number: string;
  issue_date: string;
  total_amount: number;
};

async function fetchSuggestions(invoice: Invoice) {
  const resp = await fetch('/api/ar-map/suggestions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ invoice }),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

async function confirmMapping(payload: any) {
  const resp = await fetch('/api/ar-map/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok && resp.status !== 201) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export default function AssignProjectDrawer({
  invoice,
  onClose,
}: {
  invoice: Invoice;
  onClose: () => void;
}) {
  const [items, setItems] = useState<Array<any>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await fetchSuggestions(invoice);
        setItems(res.items || []);
      } catch (e: any) {
        setError(e?.message || 'Error obteniendo sugerencias');
      } finally {
        setLoading(false);
      }
    })();
  }, [invoice]);

  const onConfirm = async (project_id: string) => {
    try {
      setConfirming(true);
      setMessage(null);
      const rules = [{ kind: 'customer_name_like', pattern: invoice.customer_name, project_id }];
      const _res = await confirmMapping({
        rules,
        assignment: { invoice_id: invoice.invoice_id, project_id },
        metadata: { user_id: 'ui' },
      });
      setMessage('Proyecto asignado y regla guardada');
      setTimeout(() => onClose(), 700);
    } catch (e: any) {
      setError(e?.message || 'Error al confirmar asignación');
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <aside className="absolute right-0 top-0 h-full w-full max-w-xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 shadow-xl flex flex-col">
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Asignar proyecto
          </h2>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200"
          >
            Cerrar
          </button>
        </div>
        <div className="p-4 space-y-3 overflow-auto">
          <div className="text-sm text-slate-600 dark:text-slate-300">
            {invoice.invoice_number} · {invoice.customer_name} ·{' '}
            {formatCurrency(invoice.total_amount)}
          </div>
          {error && <div className="text-sm text-red-600 dark:text-red-400">{error}</div>}
          {message && <div className="text-sm text-lime-700 dark:text-lime-400">{message}</div>}
          {loading ? (
            <div className="text-sm text-slate-500">Cargando sugerencias…</div>
          ) : (
            <div className="space-y-2">
              {items.length === 0 ? (
                <div className="text-sm text-slate-500">Sin sugerencias disponibles</div>
              ) : (
                <ul className="divide-y divide-slate-200 dark:divide-slate-700">
                  {items.map((it, idx) => (
                    <li key={idx} className="py-3 flex items-center justify-between">
                      <div>
                        <div className="text-slate-900 dark:text-slate-100 font-medium">
                          {it.project_name || it.project_id}
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">
                          {(it.reason || it.reasons)?.toString()} · conf{' '}
                          {(it.confidence ?? it.score ?? 0).toFixed(2)}
                        </div>
                      </div>
                      <button
                        disabled={confirming}
                        onClick={() => onConfirm(String(it.project_id))}
                        className="px-3 py-1.5 rounded-lg bg-lime-600 text-white disabled:opacity-60"
                      >
                        Asignar
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
