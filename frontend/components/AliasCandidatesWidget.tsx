'use client';

import { useState, useEffect } from 'react';

interface AliasCandidatesProps {
  className?: string;
  onRefresh?: () => void;
}

interface AliasCandidate {
  pattern: string;
  project_id: string;
  hits: number;
  last_hit: string;
  promoted_at: string | null;
}

async function fetchCandidates(params?: { min_hits?: number; promoted?: '0' | '1' }): Promise<{ items: AliasCandidate[]; count: number }> {
  const qs = params
    ? '?' + Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && String(v) !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join('&')
    : '';
  
  const resp = await fetch(`/api/ar-map/alias_candidates${qs}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export default function AliasCandidatesWidget({ className = '', onRefresh }: AliasCandidatesProps) {
  const [candidates, setCandidates] = useState<AliasCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPromoted, setShowPromoted] = useState(false);
  const [minHits, setMinHits] = useState(3);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchCandidates({
        min_hits: minHits,
        promoted: showPromoted ? undefined : '0'
      });
      setCandidates(data.items || []);
    } catch (e: any) {
      setError(e?.message || 'Error cargando candidatos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [minHits, showPromoted]);

  const pendingCandidates = candidates.filter(c => !c.promoted_at);
  const promotedCandidates = candidates.filter(c => c.promoted_at);
  const highValueCandidates = pendingCandidates.filter(c => c.hits >= 5);

  if (loading) {
    return (
      <div className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 ${className}`}>
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-slate-200 dark:bg-slate-600 rounded w-1/2"></div>
          <div className="space-y-2">
            <div className="h-3 bg-slate-200 dark:bg-slate-600 rounded"></div>
            <div className="h-3 bg-slate-200 dark:bg-slate-600 rounded w-3/4"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-2">
          <span>🎯</span>
          Patrones Aprendidos
        </h3>
        <button
          onClick={() => {
            fetchData();
            onRefresh?.();
          }}
          className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 p-1"
          title="Actualizar"
        >
          🔄
        </button>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 mb-4 text-xs">
        <label className="flex items-center gap-1">
          <span className="text-slate-600 dark:text-slate-300">Min. hits:</span>
          <select
            value={minHits}
            onChange={(e) => setMinHits(Number(e.target.value))}
            className="border rounded px-1 py-0.5 text-xs"
          >
            <option value={1}>1+</option>
            <option value={3}>3+</option>
            <option value={5}>5+</option>
            <option value={10}>10+</option>
          </select>
        </label>
        
        <label className="flex items-center gap-1">
          <input
            type="checkbox"
            checked={showPromoted}
            onChange={(e) => setShowPromoted(e.target.checked)}
            className="rounded"
          />
          <span className="text-slate-600 dark:text-slate-300">Incluir promovidas</span>
        </label>
      </div>

      {/* Error State */}
      {error && (
        <div className="text-center text-red-600 dark:text-red-400 text-sm py-2">
          <span>❌</span> {error}
        </div>
      )}

      {/* Content */}
      {!error && (
        <>
          {/* High Value Candidates Alert */}
          {highValueCandidates.length > 0 && (
            <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
              <div className="text-sm font-medium text-amber-800 dark:text-amber-200 flex items-center gap-2">
                <span>⚡</span>
                {highValueCandidates.length} patrones de alto valor listos para promoción
              </div>
            </div>
          )}

          {/* Stats Row */}
          <div className="grid grid-cols-2 gap-2 mb-4 text-xs">
            <div className="text-center p-2 bg-slate-50 dark:bg-slate-700/50 rounded">
              <div className="font-bold text-slate-900 dark:text-slate-100">
                {pendingCandidates.length}
              </div>
              <div className="text-slate-600 dark:text-slate-300">Pendientes</div>
            </div>
            
            <div className="text-center p-2 bg-slate-50 dark:bg-slate-700/50 rounded">
              <div className="font-bold text-slate-900 dark:text-slate-100">
                {promotedCandidates.length}
              </div>
              <div className="text-slate-600 dark:text-slate-300">Promovidas</div>
            </div>
          </div>

          {/* Candidates List */}
          {candidates.length === 0 ? (
            <div className="text-center text-slate-500 dark:text-slate-400 py-4">
              <div className="text-2xl mb-2">🤷‍♂️</div>
              <div className="text-sm">No hay candidatos con estos filtros</div>
            </div>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {candidates.slice(0, 10).map((candidate, idx) => (
                <div
                  key={`${candidate.pattern}-${candidate.project_id}-${idx}`}
                  className={`p-2 rounded border ${
                    candidate.promoted_at
                      ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800'
                      : candidate.hits >= 5
                      ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'
                      : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-slate-900 dark:text-slate-100 truncate">
                        {candidate.pattern}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400">
                        → Proyecto {candidate.project_id}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2 text-[11px]">
                      <span className={`px-2 py-0.5 rounded ${
                        candidate.hits >= 10
                          ? 'bg-emerald-100 text-emerald-700'
                          : candidate.hits >= 5
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}>
                        {candidate.hits} hits
                      </span>
                      
                      {candidate.promoted_at ? (
                        <span className="text-emerald-600">✅</span>
                      ) : (
                        <span className="text-amber-600">⏳</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              
              {candidates.length > 10 && (
                <div className="text-center text-xs text-slate-500 dark:text-slate-400 py-2">
                  ... y {candidates.length - 10} más
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-600">
        <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between">
          <span>
            Los patrones se promueven automáticamente a reglas después de 3+ coincidencias
          </span>
        </div>
      </div>
    </div>
  );
}