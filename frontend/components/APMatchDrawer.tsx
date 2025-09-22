'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  fetchApMatchSuggestions,
  previewApMatch,
  confirmApMatch,
  feedbackApMatch,
  getApMatchInvoice,
  getApMatchConfig,
  formatCurrency,
  formatDate,
} from '@/lib/api';
import Button, { IconButton } from './ui/Button';

interface APMatchDrawerProps {
  open: boolean;
  onClose: () => void;
  invoice: {
    id: number | string;
    vendor_rut?: string;
    amount?: number;
    date?: string;
    project_id?: string | number;
  };
  userId?: string;
}

interface LinkDraft {
  po_id: string | number;
  po_line_id?: string | number;
  amount: number;
  qty?: number;
}

export default function APMatchDrawer({ open, onClose, invoice, userId }: APMatchDrawerProps) {
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedLinks, setSelectedLinks] = useState<LinkDraft[]>([]);
  const [preview, setPreview] = useState<any | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [config, setConfig] = useState<any | null>(null);
  const [viewMode, setViewMode] = useState<'suggestions' | 'links' | 'preview'>('suggestions');

  const invoiceId = invoice.id;

  const loadConfig = useCallback(async () => {
    try {
      const cfg = await getApMatchConfig({
        vendor_rut: invoice.vendor_rut,
        project_id: invoice.project_id,
      });
      setConfig(cfg);
    } catch (e: any) {
      // silent
    }
  }, [invoice.vendor_rut, invoice.project_id]);

  const loadExisting = useCallback(async () => {
    try {
      const existing = await getApMatchInvoice(invoiceId);
      if (Array.isArray(existing.links) && existing.links.length > 0) {
        setSelectedLinks(
          existing.links.map((l: any) => ({
            po_id: l.po_id,
            po_line_id: l.po_line_id,
            amount: Number(l.amount || 0),
            qty: l.qty ? Number(l.qty) : undefined,
          })),
        );
      }
    } catch (e) {
      // ignore
    }
  }, [invoiceId]);

  const loadSuggestions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchApMatchSuggestions({
        invoice_id: invoiceId,
        vendor_rut: invoice.vendor_rut,
        amount: invoice.amount,
        date: invoice.date,
        project_id: invoice.project_id,
        days: 30,
      });
      setSuggestions(res.items || []);
    } catch (e: any) {
      setError(e?.message || 'Error obteniendo sugerencias');
    } finally {
      setLoading(false);
    }
  }, [invoiceId, invoice.vendor_rut, invoice.amount, invoice.date, invoice.project_id]);

  useEffect(() => {
    if (!open) return;
    loadConfig();
    loadExisting();
    loadSuggestions();
  }, [open, loadConfig, loadExisting, loadSuggestions]);

  const totalSelected = useMemo(
    () => selectedLinks.reduce((acc, l) => acc + (Number(l.amount) || 0), 0),
    [selectedLinks],
  );

  const addCandidateLines = (cand: any) => {
    if (!cand) return;
    if (cand.candidate?.lines) {
      const merged: LinkDraft[] = [...selectedLinks];
      cand.candidate.lines.forEach((ln: any) => {
        merged.push({
          po_id: Array.isArray(cand.candidate.po_id)
            ? cand.candidate.po_id[0]
            : cand.candidate.po_id,
          po_line_id: ln.po_line_id,
          amount: Number((ln.unit_price ?? 0) * 1) || Number(cand.candidate.coverage?.amount || 0),
        });
      });
      setSelectedLinks(merged);
      setViewMode('links');
    } else if (cand.po_id) {
      // Header style suggestion: allocate amount equally or full?
      if (invoice.amount) {
        setSelectedLinks([
          {
            po_id: Array.isArray(cand.po_id) ? cand.po_id[0] : cand.po_id,
            amount: invoice.amount,
          },
        ]);
      }
      setViewMode('links');
    }
  };

  const removeLink = (idx: number) => {
    setSelectedLinks((prev) => prev.filter((_, i) => i !== idx));
  };

  const runPreview = async () => {
    try {
      setError(null);
      const res = await previewApMatch({
        invoice_id: invoiceId,
        links: selectedLinks.map((l) => ({
          po_id: l.po_id,
          po_line_id: l.po_line_id,
          amount: l.amount,
          qty: l.qty,
        })),
        vendor_rut: invoice.vendor_rut,
        project_id: invoice.project_id,
      });
      setPreview(res);
      setViewMode('preview');
    } catch (e: any) {
      setError(e?.message || 'Error en preview');
    }
  };

  const onConfirm = async () => {
    try {
      if (!selectedLinks.length) return;
      setConfirming(true);
      setMessage(null);
      const res = await confirmApMatch({
        invoice_id: invoiceId,
        links: selectedLinks,
        confidence: suggestions[0]?.confidence,
        reasons: suggestions[0]?.reasons,
        user_id: userId,
      });
      if (res?.ok) {
        setMessage('Enlaces guardados');
      } else {
        setError(res?.error || 'Error al confirmar');
      }
    } catch (e: any) {
      setError(e?.message || 'Error al confirmar');
    } finally {
      setConfirming(false);
    }
  };

  const sendFeedback = async (accepted: boolean) => {
    try {
      await feedbackApMatch({
        invoice_id: invoiceId,
        accepted: accepted ? 1 : 0,
        reason: accepted ? 'accepted_ui' : 'rejected_ui',
        candidates_json: suggestions,
        user_id: userId,
      });
      if (!accepted) setMessage('Feedback registrado (rechazado)');
    } catch (e) {
      // silent
    }
  };

  if (!open) return null;

  const hasViolations = preview?.violations && preview.violations.length > 0;

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <aside className="absolute right-0 top-0 h-full w-full max-w-3xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 shadow-xl flex flex-col">
        <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Asociar OC a Factura
          </h2>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={() => setViewMode('suggestions')}>
              Sugerencias
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setViewMode('links')}>
              Links ({selectedLinks.length})
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={runPreview}
              disabled={!selectedLinks.length}
            >
              Preview
            </Button>
            <IconButton
              variant="ghost"
              size="sm"
              onClick={onClose}
              title="Cerrar"
              icon={<span>✕</span>}
            />
          </div>
        </div>
        <div className="p-4 overflow-auto flex-1 space-y-4 text-sm">
          <div className="text-slate-600 dark:text-slate-300">
            Factura #{invoiceId}
            {invoice.date && <> · {formatDate(invoice.date)}</>}
            {invoice.vendor_rut && <> · RUT {invoice.vendor_rut}</>}
            {invoice.amount !== undefined && <> · {formatCurrency(invoice.amount || 0)}</>}
          </div>
          {config && (
            <div className="text-xs text-slate-500">
              Tolerancia monto: {(config.effective?.amount_tol_pct * 100).toFixed(1)}% · capas:{' '}
              {config.effective?.source_layers?.join('>')}
            </div>
          )}
          {error && <div className="text-red-600 dark:text-red-400 text-sm">{error}</div>}
          {message && <div className="text-lime-700 dark:text-lime-400 text-sm">{message}</div>}

          {viewMode === 'suggestions' && (
            <div>
              {loading ? (
                <div>Cargando sugerencias…</div>
              ) : suggestions.length === 0 ? (
                <div>Sin sugerencias</div>
              ) : (
                <ul className="divide-y divide-slate-200 dark:divide-slate-700">
                  {suggestions.slice(0, 25).map((sug, idx) => (
                    <li key={idx} className="py-3 flex items-start gap-3">
                      <div className="flex-1">
                        <div className="font-medium text-slate-900 dark:text-slate-100 flex items-center gap-2">
                          <span>Conf {Math.round((sug.confidence || 0) * 100)}%</span>
                          {sug.candidate?.coverage && (
                            <span className="text-xs text-slate-500">
                              Cobertura {Math.round((sug.candidate.coverage.pct || 0) * 100)}% (
                              {formatCurrency(sug.candidate.coverage.amount)})
                            </span>
                          )}
                        </div>
                        {Array.isArray(sug.reasons) && sug.reasons.length > 0 && (
                          <div className="text-xs text-slate-500 mt-1 flex flex-wrap gap-1">
                            {sug.reasons.map((r: string, i: number) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
                              >
                                {r}
                              </span>
                            ))}
                          </div>
                        )}
                        {sug.po_number && (
                          <div className="text-xs text-slate-500 mt-1">OC {sug.po_number}</div>
                        )}
                      </div>
                      <div className="flex flex-col gap-2">
                        <Button size="sm" onClick={() => addCandidateLines(sug)}>
                          Añadir
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {viewMode === 'links' && (
            <div className="space-y-3">
              <div className="text-xs text-slate-500">
                Total seleccionado: {formatCurrency(totalSelected)}
              </div>
              {selectedLinks.length === 0 ? (
                <div className="text-slate-500">Sin links</div>
              ) : (
                <ul className="divide-y divide-slate-200 dark:divide-slate-700">
                  {selectedLinks.map((ln, idx) => (
                    <li key={idx} className="py-2 flex items-center justify-between">
                      <div>
                        <div className="text-slate-800 dark:text-slate-100 font-medium">
                          PO {ln.po_id}{' '}
                          {ln.po_line_id && (
                            <span className="text-xs text-slate-500">· línea {ln.po_line_id}</span>
                          )}
                        </div>
                        <div className="text-xs text-slate-500">
                          {formatCurrency(ln.amount)}
                          {ln.qty !== undefined && <> · qty {ln.qty}</>}
                        </div>
                      </div>
                      <IconButton
                        variant="ghost"
                        size="sm"
                        title="Quitar"
                        onClick={() => removeLink(idx)}
                        icon={<span>✕</span>}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {viewMode === 'preview' && preview && (
            <div className="space-y-3">
              <div className="text-xs text-slate-500">
                Violaciones: {preview.violations?.length || 0}
              </div>
              {hasViolations && (
                <ul className="text-xs space-y-1 text-red-600 dark:text-red-400">
                  {preview.violations.map((v: any, i: number) => (
                    <li key={i}>
                      {v.reason} {v.po_id || v.po_line_id ? `(${v.po_id || v.po_line_id})` : ''}
                    </li>
                  ))}
                </ul>
              )}
              <div className="text-xs text-slate-500">
                Tolerancias: monto{' '}
                {Math.round((preview.tolerances?.amount_tol_pct || 0) * 1000) / 10}%
              </div>
            </div>
          )}
        </div>
        <div className="p-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            {viewMode !== 'preview' && (
              <Button
                size="sm"
                variant="secondary"
                disabled={!selectedLinks.length}
                onClick={runPreview}
              >
                Validar
              </Button>
            )}
            <Button
              size="sm"
              variant="primary"
              disabled={!selectedLinks.length || hasViolations || confirming}
              onClick={onConfirm}
              loading={confirming}
            >
              Confirmar
            </Button>
            <Button size="sm" variant="ghost" onClick={() => sendFeedback(false)}>
              Feedback −
            </Button>
          </div>
          <Button size="sm" variant="outline" onClick={onClose}>
            Cerrar
          </Button>
        </div>
      </aside>
    </div>
  );
}
