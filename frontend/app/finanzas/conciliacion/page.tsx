'use client';

import { useEffect, useMemo, useState } from 'react';
import DataTable from '@/components/ui/DataTable';
import {
  fetchBankMovements,
  fetchInvoicesCompra,
  conciliacionServiceConfigured,
  fetchConciliationSuggestions,
  confirmConciliation,
  fetchConciliationHistory,
  fetchReconcileSuggestions,
  confirmReconcile,
  formatCurrency,
  formatDate,
} from '@/lib/api';

type Mode = 'cartola' | 'factura_compra';

export default function ConciliacionPage() {
  const [mode, setMode] = useState<Mode>('cartola');
  const [leftData, setLeftData] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<any[]>([]);

  const columnsCartola = useMemo(
    () => [
      { key: 'fecha', label: 'Fecha', sortable: true, render: (v: string) => formatDate(v) },
      { key: 'glosa', label: 'Glosa', sortable: true },
      {
        key: 'monto',
        label: 'Monto',
        sortable: true,
        render: (v: number) => formatCurrency(v || 0),
      },
      { key: 'moneda', label: 'Moneda' },
      { key: 'referencia', label: 'Referencia' },
    ],
    [],
  );

  const columnsCompra = useMemo(
    () => [
      { key: 'fecha', label: 'Fecha', sortable: true, render: (v: string) => formatDate(v) },
      { key: 'proveedor_nombre', label: 'Proveedor', sortable: true },
      {
        key: 'monto_total',
        label: 'Monto',
        sortable: true,
        render: (v: number) => formatCurrency(v || 0),
      },
      { key: 'moneda', label: 'Moneda' },
      { key: 'documento_numero', label: 'Documento' },
    ],
    [],
  );

  async function loadLeft() {
    try {
      setLoading(true);
      setError(null);
      if (mode === 'cartola') {
        const res: any = await fetchBankMovements({
          page: 1,
          page_size: 50,
          order_by: 'fecha',
          order_dir: 'DESC',
        });
        setLeftData(res.items || []);
      } else {
        const res: any = await fetchInvoicesCompra({
          page: 1,
          page_size: 50,
          order_by: 'fecha',
          order_dir: 'DESC',
        });
        setLeftData(res.items || []);
      }
    } catch (e: any) {
      setError(e?.message || 'Error cargando datos');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setSelected(null);
    setSuggestions([]);
    loadLeft();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    // Load reconciliation history (backend) for quick context
    fetchConciliationHistory()
      .then((h) => setHistory(h?.items || []))
      .catch(() => setHistory([]));
  }, []);

  async function solicitarSugerencias() {
    if (!selected) return;
    setLoadingSuggestions(true);
    const configured = conciliacionServiceConfigured();
    if (configured) {
      const resp = await fetchConciliationSuggestions({ source: mode, item: selected });
      setSuggestions(resp?.suggestions || []);
    } else {
      // Map source mode to backend context + item payload
      let source_type: 'bank' | 'purchase' | 'sales' | 'expense' = 'bank';
      let payload: any = {};
      if (mode === 'cartola') {
        source_type = 'bank';
        payload = {
          source_type,
          id: selected.id,
          amount: selected.monto,
          date: selected.fecha,
          ref: selected.referencia,
          currency: selected.moneda || 'CLP',
        };
      } else {
        source_type = 'purchase';
        payload = {
          source_type,
          id: selected.documento_numero,
          amount: selected.monto_total,
          date: selected.fecha,
          currency: selected.moneda || 'CLP',
          extra: {
            proveedor_rut: selected.proveedor_rut,
            proveedor_nombre: selected.proveedor_nombre,
          },
        };
      }
      const resp = await fetchReconcileSuggestions(payload);
      // Backend returns {items: [{candidate, confidence, reasons}]}; normalize to page shape
      const items = (resp?.items || []).map((it: any) => ({
        title: it.candidate?.title || 'Sugerencia',
        detail: it.candidate?.detail || (Array.isArray(it.reasons) ? it.reasons.join(' • ') : ''),
        score: undefined,
        confidence: it.confidence ?? 0,
        candidate: it.candidate,
      }));
      setSuggestions(items);
    }
    setLoadingSuggestions(false);
  }

  async function confirmar(match: any) {
    const configured = conciliacionServiceConfigured();
    let resp;
    if (configured) {
      resp = await confirmConciliation({ source: mode, item: selected, target: match });
    } else {
      // Build backend confirm payload (links list)
      const links: any[] = [];
      if (mode === 'cartola') {
        // bank movement -> candidate could be purchase or sales based on adapter output; assume purchase for now if available
        const bank_movement_id = selected.id;
        const purchase_invoice_id = match?.candidate?.purchase_invoice_id;
        const sales_invoice_id = match?.candidate?.sales_invoice_id;
        const amount = selected.monto;
        links.push({ bank_movement_id, purchase_invoice_id, sales_invoice_id, amount });
      } else {
        // purchase invoice -> bank movement id from candidate
        const purchase_invoice_id =
          match?.candidate?.purchase_invoice_id || selected.documento_numero;
        const bank_movement_id = match?.candidate?.bank_movement_id;
        const amount = selected.monto_total;
        links.push({ bank_movement_id, purchase_invoice_id, amount });
      }
      resp = await confirmReconcile({
        context: mode === 'cartola' ? 'bank' : 'purchase',
        confidence: match?.confidence ?? 0,
        links,
        metadata: { user_id: 'ui' },
      });
    }
    // Simple feedback
    if (resp?.ok) {
      alert('Conciliación confirmada');
      setSelected(null);
      setSuggestions([]);
      loadLeft();
      // Refresh history
      fetchConciliationHistory()
        .then((h) => setHistory(h?.items || []))
        .catch(() => {});
    } else {
      alert(resp?.message || 'No se pudo confirmar');
    }
  }

  const configured = conciliacionServiceConfigured();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
            Conciliación Bancaria
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            Fuentes canónicas: v_cartola_bancaria, v_facturas_compra
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setMode('cartola')}
            className={`px-3 py-2 rounded-lg border ${mode === 'cartola' ? 'bg-lime-50 border-lime-300 text-lime-700' : ''}`}
          >
            Desde Cartola
          </button>
          <button
            onClick={() => setMode('factura_compra')}
            className={`px-3 py-2 rounded-lg border ${mode === 'factura_compra' ? 'bg-lime-50 border-lime-300 text-lime-700' : ''}`}
          >
            Desde Facturas Compra
          </button>
        </div>
      </div>

      {!configured && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-4">
          <div className="font-medium">Servicio de conciliación no configurado</div>
          <div className="text-sm">
            Define <code>NEXT_PUBLIC_CONCILIACION_API_URL</code> para habilitar sugerencias y
            confirmaciones.
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Fuente */}
        <div>
          <div className="mb-2 text-sm text-slate-500">
            {mode === 'cartola' ? 'Movimientos bancarios' : 'Facturas de compra'}
          </div>
          <DataTable
            columns={(mode === 'cartola' ? columnsCartola : columnsCompra) as any}
            data={leftData}
            loading={loading}
            emptyMessage={mode === 'cartola' ? 'Sin movimientos' : 'Sin facturas'}
            onRowClick={(row) => setSelected(row)}
            rowClassName={(row) =>
              selected &&
              (mode === 'cartola'
                ? row.id === selected.id
                : row.documento_numero === selected.documento_numero &&
                  row.fecha === selected.fecha)
                ? 'bg-lime-50/60 dark:bg-lime-900/20'
                : ''
            }
          />
          <div className="mt-3 flex gap-2">
            <button
              disabled={!leftData.length}
              onClick={() => setSelected(leftData[0])}
              className="px-3 py-2 rounded-lg border"
            >
              Seleccionar primero
            </button>
            <button
              disabled={!selected}
              onClick={solicitarSugerencias}
              className={`px-3 py-2 rounded-lg ${selected ? 'bg-lime-600 text-white' : 'bg-slate-200 text-slate-600'}`}
            >
              Solicitar sugerencias
            </button>
          </div>
        </div>

        {/* Right: Sugerencias + Historial */}
        <div>
          <div className="mb-2 text-sm text-slate-500">Sugerencias del servicio</div>
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
            {!selected ? (
              <div className="text-slate-500">Selecciona un elemento a conciliar</div>
            ) : (
              <div className="space-y-3">
                <div className="text-sm text-slate-600 dark:text-slate-400">
                  Seleccionado:{' '}
                  {mode === 'cartola'
                    ? `${formatDate(selected.fecha)} • ${formatCurrency(selected.monto)} • ${selected.glosa}`
                    : `${formatDate(selected.fecha)} • ${formatCurrency(selected.monto_total)} • ${selected.proveedor_nombre}`}
                </div>
                {loadingSuggestions ? (
                  <div className="text-slate-500">Cargando sugerencias…</div>
                ) : suggestions.length ? (
                  <div className="space-y-2">
                    {suggestions.map((s: any, i: number) => (
                      <div
                        key={i}
                        className="flex items-center justify-between border border-slate-200 dark:border-slate-700 rounded-lg p-3"
                      >
                        <div className="text-sm">
                          <div className="font-medium">
                            {s.title || s.descripcion || s.candidate?.title || 'Sugerencia'}
                          </div>
                          <div className="text-slate-500 dark:text-slate-400">
                            {s.detail || s.candidate?.detail || ''}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {typeof s.score === 'number' && (
                            <span className="text-xs px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-700">
                              Score: {Math.round((s.score as number) * 100)}%
                            </span>
                          )}
                          {typeof s.score !== 'number' && typeof s.confidence === 'number' && (
                            <span className="text-xs px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-700">
                              Score: {Math.round((s.confidence as number) * 100)}%
                            </span>
                          )}
                          <button
                            onClick={() => confirmar(s)}
                            className="px-3 py-1 rounded-lg bg-lime-600 text-white"
                          >
                            Conciliar
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-slate-500">Sin sugerencias</div>
                )}
              </div>
            )}
          </div>

          {/* Historial */}
          <div className="mt-4">
            <div className="mb-2 text-sm text-slate-500">Historial reciente</div>
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
              {history.length === 0 ? (
                <div className="text-slate-500">Sin conciliaciones registradas</div>
              ) : (
                <div className="space-y-2">
                  {history.slice(0, 10).map((h: any) => (
                    <div key={h.id} className="flex items-center justify-between text-sm">
                      <div>
                        <div className="font-medium">
                          #{h.id} • {h.context} • {formatDate(h.created_at)}
                        </div>
                        <div className="text-slate-500">
                          Links: {h.links} • Monto: {formatCurrency(h.monto || 0)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
