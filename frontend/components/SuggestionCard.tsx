'use client';

import { useState } from 'react';
import ConfidenceBar from './ConfidenceBar';

interface ReasonExplanation {
  type: 'alias' | 'drive' | 'history' | 'ep' | 'recon' | 'heuristic' | 'hint';
  title: string;
  description: string;
  icon: string;
}

interface SuggestionCardProps {
  suggestion: {
    project_id: string;
    project_name?: string;
    confidence: number;
    reasons: string[];
    reason?: string;
  };
  onAssign: (projectId: string) => void;
  disabled?: boolean;
  showDetails?: boolean;
}

const REASON_EXPLANATIONS: Record<string, ReasonExplanation> = {
  'alias': {
    type: 'alias',
    title: 'Patrón de Cliente',
    description: 'Coincide con una regla basada en el nombre del cliente',
    icon: '🎯'
  },
  'drive': {
    type: 'drive',
    title: 'Ruta de Archivo',
    description: 'Coincide con la ubicación del documento en Drive',
    icon: '📁'
  },
  'history': {
    type: 'history',
    title: 'Historial',
    description: 'Basado en asignaciones anteriores del mismo cliente',
    icon: '📊'
  },
  'ep': {
    type: 'ep',
    title: 'Estado de Pago',
    description: 'Coincide con montos esperados en el cashflow',
    icon: '💰'
  },
  'recon': {
    type: 'recon',
    title: 'Reconciliación',
    description: 'Conectado a través de conciliaciones bancarias',
    icon: '🔗'
  },
  'heuristic': {
    type: 'heuristic',
    title: 'Heurística',
    description: 'Sugerencia basada en similitudes generales',
    icon: '🧠'
  },
  'hint': {
    type: 'hint',
    title: 'Sugerencia Manual',
    description: 'Proyecto sugerido manualmente por el usuario',
    icon: '👤'
  }
};

function parseReason(reason: string): ReasonExplanation {
  const reasonLower = reason.toLowerCase();
  
  if (reasonLower.includes('alias') || reasonLower.includes('pattern')) {
    return REASON_EXPLANATIONS['alias'];
  }
  if (reasonLower.includes('drive') || reasonLower.includes('path')) {
    return REASON_EXPLANATIONS['drive'];
  }
  if (reasonLower.includes('history') || reasonLower.includes('customer_rut')) {
    return REASON_EXPLANATIONS['history'];
  }
  if (reasonLower.includes('ep') || reasonLower.includes('amount')) {
    return REASON_EXPLANATIONS['ep'];
  }
  if (reasonLower.includes('recon') || reasonLower.includes('linked')) {
    return REASON_EXPLANATIONS['recon'];
  }
  if (reasonLower.includes('hint')) {
    return REASON_EXPLANATIONS['hint'];
  }
  
  return REASON_EXPLANATIONS['heuristic'];
}

export default function SuggestionCard({
  suggestion,
  onAssign,
  disabled = false,
  showDetails = true
}: SuggestionCardProps) {
  const [showExplanation, setShowExplanation] = useState(false);
  
  const reasons = suggestion.reasons || (suggestion.reason ? [suggestion.reason] : []);
  const primaryReason = reasons[0] || '';
  const explanation = parseReason(primaryReason);
  
  const handleAssign = () => {
    onAssign(suggestion.project_id);
  };

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 bg-white dark:bg-slate-800 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-slate-900 dark:text-slate-100 font-medium truncate">
              {suggestion.project_name || suggestion.project_id}
            </span>
            {suggestion.project_name && suggestion.project_id !== suggestion.project_name && (
              <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                {suggestion.project_id}
              </span>
            )}
          </div>
          
          {/* Primary reason */}
          <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <span className="text-base">{explanation.icon}</span>
            <span>{explanation.title}</span>
            {reasons.length > 1 && (
              <span className="text-xs text-slate-400 dark:text-slate-500">
                +{reasons.length - 1} más
              </span>
            )}
          </div>
        </div>

        {/* Assign button */}
        <button
          onClick={handleAssign}
          disabled={disabled}
          className="px-3 py-1.5 rounded-lg bg-lime-600 hover:bg-lime-700 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Asignar
        </button>
      </div>

      {/* Confidence bar */}
      {showDetails && (
        <div className="mt-3">
          <ConfidenceBar
            confidence={suggestion.confidence}
            label="Confianza"
            size="md"
            showPercentage={true}
          />
        </div>
      )}

      {/* Details toggle */}
      {showDetails && reasons.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setShowExplanation(!showExplanation)}
            className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 flex items-center gap-1"
          >
            <span>{showExplanation ? '▼' : '▶'}</span>
            Ver detalles
          </button>
        </div>
      )}

      {/* Explanation details */}
      {showExplanation && (
        <div className="mt-3 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg border border-slate-100 dark:border-slate-600">
          <div className="space-y-2">
            <div>
              <span className="text-xs font-medium text-slate-700 dark:text-slate-200">
                Explicación:
              </span>
              <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">
                {explanation.description}
              </p>
            </div>
            
            {reasons.length > 0 && (
              <div>
                <span className="text-xs font-medium text-slate-700 dark:text-slate-200">
                  Razones detectadas:
                </span>
                <ul className="text-xs text-slate-600 dark:text-slate-300 mt-1 space-y-1">
                  {reasons.slice(0, 3).map((reason, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-slate-400">•</span>
                      <span className="font-mono text-[11px] bg-slate-100 dark:bg-slate-600 px-1.5 py-0.5 rounded">
                        {reason}
                      </span>
                    </li>
                  ))}
                  {reasons.length > 3 && (
                    <li className="text-slate-400 text-[11px] ml-3">
                      ... y {reasons.length - 3} más
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}