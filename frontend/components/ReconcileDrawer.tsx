'use client';

import { useEffect, useState } from 'react';
import { confirmReconcile, fetchReconcileSuggestions, formatCurrency, formatDate } from '@/lib/api';
import { StatusChip } from './StatusChip';

interface Props {
  open: boolean;
  onClose: () => void;
  sourceType: 'bank' | 'purchase' | 'sales' | 'expense' | 'payroll' | 'tax';
  source: { id?: number; amount?: number; date?: string; ref?: string; currency?: string };
}

export default function ReconcileDrawer({ open, onClose, sourceType, source }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<Array<any>>([]);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const payload: any = { source_type: sourceType, days: 5, amount_tol: 0.01 };
        if (source.id) payload.id = source.id;
        if (source.amount !== undefined) payload.amount = source.amount;
        if (source.date) payload.date = source.date;
        if (source.ref) payload.ref = source.ref;
        if (source.currency) payload.currency = source.currency;
        const res = await fetchReconcileSuggestions(payload);
        setItems(res.items || []);
      } catch (e: any) {
        setError(e?.message || 'Error obteniendo sugerencias');
      } finally {
        setLoading(false);
      }
    })();
  }, [open, sourceType, source]);

  const onConfirm = async (target: any) => {
    try {
      setConfirming(true);
      setMessage(null);
      const payload = {
        source_type: sourceType,
        source_ref: source.ref || String(source.id ?? ''),
        target_type: target.target_kind,
        target_ref: String(target.doc ?? ''),
        metadata: { fecha: target.fecha, amount: target.amount },
      };
      const res = await confirmReconcile(payload);
      if (res?.accepted) setMessage('Conciliación confirmada');
      else setMessage('Solicitud aceptada (no-op si servicio no configurado)');
    } catch (e: any) {
      setError(e?.message || 'Error al confirmar conciliación');
    } finally {
      setConfirming(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <aside className="absolute right-0 top-0 h-full w-full max-w-xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 shadow-xl flex flex-col">
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Conciliar</h2>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200"
          >
            Cerrar
          </button>
        </div>
        <div className="p-4 space-y-3 overflow-auto">
          <div className="text-sm text-slate-500 dark:text-slate-400">
            Origen: <span className="font-medium">{sourceType}</span>
            {source.date ? ` · ${formatDate(source.date)}` : ''}
            {source.amount !== undefined ? ` · ${formatCurrency(source.amount || 0)}` : ''}
            {source.ref ? ` · Ref ${source.ref}` : ''}
          </div>
          {error && <div className="text-sm text-red-600 dark:text-red-400">{error}</div>}
          {message && <div className="text-sm text-lime-700 dark:text-lime-400">{message}</div>}
          {loading ? (
            <div className="text-sm text-slate-500">Cargando sugerencias…</div>
          ) : (
            <div className="space-y-2">
              {items.length === 0 ? (
                <div className="text-sm text-slate-500">Sin sugerencias</div>
              ) : (
                <ul className="divide-y divide-slate-200 dark:divide-slate-700">
                  {items.slice(0, 20).map((it, idx) => (
                    <li key={idx} className="py-3">
                      {/* COMBINACIÓN MÚLTIPLE vs Documento Individual */}
                      {it.type === 'combination' ? (
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="text-slate-900 dark:text-slate-100 font-medium flex items-center gap-2">
                                <StatusChip kind="active" size="sm">
                                  COMBO
                                </StatusChip>
                                <span>{it.combination_count} documentos</span>
                                <span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-2 py-1 rounded border border-slate-200 dark:border-slate-700">
                                  {formatCurrency(it.amount || 0)}
                                </span>
                              </div>
                              <div className="text-sm text-slate-500 dark:text-slate-400">
                                Score {(it.score * 100).toFixed(1)}% • Diferencia:{' '}
                                {formatCurrency(it.amount_difference || 0)}
                              </div>
                            </div>
                            <button
                              disabled={confirming}
                              onClick={() => onConfirm(it)}
                              className="px-3 py-1.5 rounded-lg bg-lime-600 text-white disabled:opacity-60 hover:bg-lime-700 font-medium"
                            >
                              Confirmar Combo
                            </button>
                          </div>

                          {/* Mostrar documentos individuales del combo */}
                          <div className="ml-4 border-l-2 border-slate-200 dark:border-slate-700 pl-3 space-y-1">
                            {it.documents?.map((doc: any, docIdx: number) => (
                              <div
                                key={docIdx}
                                className="text-sm text-slate-600 dark:text-slate-300 flex justify-between"
                              >
                                <span>
                                  {doc.target_kind?.toUpperCase()} #{doc.doc}
                                </span>
                                <span>{formatCurrency(doc.amount || 0)}</span>
                              </div>
                            ))}
                          </div>

                          {Array.isArray(it.reasons) && it.reasons.length > 0 && (
                            <div className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                              {it.reasons.map((r: any, rIdx: number) => r.detail).join(' • ')}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-slate-900 dark:text-slate-100 font-medium">
                              {it.target_kind?.toUpperCase()} • #{it.doc || 's/n'}
                            </div>
                            <div className="text-sm text-slate-500 dark:text-slate-400">
                              {formatDate(it.fecha)} • {formatCurrency(it.amount || 0)} • score{' '}
                              {((it.score || 0) * 100).toFixed(1)}%
                            </div>
                            {Array.isArray(it.reasons) && it.reasons.length > 0 && (
                              <div className="text-xs text-slate-500 mt-1">
                                {it.reasons.map((r: any) => r.detail || r).join(' • ')}
                              </div>
                            )}
                          </div>
                          <button
                            disabled={confirming}
                            onClick={() => onConfirm(it)}
                            className="px-3 py-1.5 rounded-lg bg-lime-600 text-white disabled:opacity-60 hover:bg-lime-700 font-medium"
                          >
                            Confirmar
                          </button>
                        </div>
                      )}
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
