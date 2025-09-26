'use client';

import { useEffect, useState } from 'react';
import { formatCurrency } from '@/lib/api';
import SuggestionCard from './SuggestionCard';

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
  const [showAllSuggestions, setShowAllSuggestions] = useState(false);

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

  // Sort suggestions by confidence
  const sortedItems = [...items].sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
  const topSuggestions = sortedItems.slice(0, 3);
  const additionalSuggestions = sortedItems.slice(3);

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <aside className="absolute right-0 top-0 h-full w-full max-w-2xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 shadow-xl flex flex-col">
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Asignar proyecto
            </h2>
            <div className="text-sm text-slate-600 dark:text-slate-300 mt-1">
              {invoice.invoice_number} · {invoice.customer_name} · {formatCurrency(invoice.total_amount)}
            </div>
          </div>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
          >
            Cerrar
          </button>
        </div>
        
        <div className="flex-1 overflow-auto">
          <div className="p-5 space-y-4">
            {/* Status messages */}
            {error && (
              <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <div className="text-sm text-red-600 dark:text-red-400 flex items-center gap-2">
                  <span>❌</span>
                  <span>{error}</span>
                </div>
              </div>
            )}
            
            {message && (
              <div className="p-3 rounded-lg bg-lime-50 dark:bg-lime-900/20 border border-lime-200 dark:border-lime-800">
                <div className="text-sm text-lime-700 dark:text-lime-400 flex items-center gap-2">
                  <span>✅</span>
                  <span>{message}</span>
                </div>
              </div>
            )}

            {/* Loading state */}
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="flex items-center gap-3 text-slate-600 dark:text-slate-300">
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-slate-300 border-t-slate-600"></div>
                  <span>Cargando sugerencias inteligentes...</span>
                </div>
              </div>
            ) : (
              <>
                {/* No suggestions */}
                {items.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="text-slate-400 text-4xl mb-3">🤔</div>
                    <div className="text-slate-600 dark:text-slate-300 font-medium">
                      No se encontraron sugerencias automáticas
                    </div>
                    <div className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                      Puedes crear una regla manualmente para este cliente
                    </div>
                  </div>
                ) : (
                  <>
                    {/* Top suggestions */}
                    <div>
                      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">
                        Sugerencias Recomendadas
                        <span className="ml-2 text-xs text-slate-500 font-normal">
                          ({topSuggestions.length})
                        </span>
                      </h3>
                      <div className="space-y-3">
                        {topSuggestions.map((suggestion, idx) => (
                          <SuggestionCard
                            key={`${suggestion.project_id}-${idx}`}
                            suggestion={suggestion}
                            onAssign={onConfirm}
                            disabled={confirming}
                            showDetails={true}
                          />
                        ))}
                      </div>
                    </div>

                    {/* Additional suggestions */}
                    {additionalSuggestions.length > 0 && (
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                            Otras Opciones
                            <span className="ml-2 text-xs text-slate-500 font-normal">
                              ({additionalSuggestions.length})
                            </span>
                          </h3>
                          <button
                            onClick={() => setShowAllSuggestions(!showAllSuggestions)}
                            className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 flex items-center gap-1"
                          >
                            <span>{showAllSuggestions ? '▲' : '▼'}</span>
                            {showAllSuggestions ? 'Ocultar' : 'Mostrar'}
                          </button>
                        </div>
                        
                        {showAllSuggestions && (
                          <div className="space-y-3">
                            {additionalSuggestions.map((suggestion, idx) => (
                              <SuggestionCard
                                key={`${suggestion.project_id}-${idx + 3}`}
                                suggestion={suggestion}
                                onAssign={onConfirm}
                                disabled={confirming}
                                showDetails={false}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </>
            )}
          </div>
        </div>

        {/* Footer with stats */}
        <div className="px-5 py-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
          <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>
              Cliente: {invoice.customer_rut} • Fecha: {invoice.issue_date}
            </span>
            {items.length > 0 && (
              <span>
                {items.filter(i => i.confidence >= 0.8).length} sugerencias de alta confianza
              </span>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}
