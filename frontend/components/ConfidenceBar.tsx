'use client';

interface ConfidenceBarProps {
  confidence: number;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  showPercentage?: boolean;
  className?: string;
}

export default function ConfidenceBar({
  confidence,
  label,
  size = 'md',
  showPercentage = true,
  className = '',
}: ConfidenceBarProps) {
  // Normalize confidence to 0-1 range
  const normalizedConfidence = Math.min(1, Math.max(0, confidence));
  const percentage = Math.round(normalizedConfidence * 100);

  // Color based on confidence level
  const getColorClass = (conf: number): string => {
    if (conf >= 0.9) return 'bg-emerald-500 text-emerald-50';
    if (conf >= 0.75) return 'bg-lime-500 text-lime-50';
    if (conf >= 0.6) return 'bg-yellow-500 text-yellow-50';
    if (conf >= 0.4) return 'bg-orange-500 text-orange-50';
    return 'bg-red-500 text-red-50';
  };

  const getBgClass = (conf: number): string => {
    if (conf >= 0.9) return 'bg-emerald-100 dark:bg-emerald-900/30';
    if (conf >= 0.75) return 'bg-lime-100 dark:bg-lime-900/30';
    if (conf >= 0.6) return 'bg-yellow-100 dark:bg-yellow-900/30';
    if (conf >= 0.4) return 'bg-orange-100 dark:bg-orange-900/30';
    return 'bg-red-100 dark:bg-red-900/30';
  };

  // Size classes
  const sizeClasses = {
    sm: 'h-2 text-xs',
    md: 'h-3 text-sm',
    lg: 'h-4 text-base',
  };

  const textSizeClasses = {
    sm: 'text-[10px]',
    md: 'text-xs',
    lg: 'text-sm',
  };

  const colorClass = getColorClass(normalizedConfidence);
  const bgClass = getBgClass(normalizedConfidence);

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {label && (
        <span className={`${textSizeClasses[size]} text-slate-600 dark:text-slate-300 font-medium`}>
          {label}
        </span>
      )}
      
      <div className={`relative ${sizeClasses[size]} flex-1 max-w-24 ${bgClass} rounded-full overflow-hidden`}>
        <div
          className={`h-full ${colorClass} rounded-full transition-all duration-300 ease-out flex items-center justify-center`}
          style={{ width: `${percentage}%` }}
        >
          {size === 'lg' && showPercentage && (
            <span className={`${textSizeClasses[size]} font-medium`}>
              {percentage}%
            </span>
          )}
        </div>
        
        {/* Percentage text outside for smaller bars */}
        {showPercentage && size !== 'lg' && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`${textSizeClasses[size]} font-medium text-slate-700 dark:text-slate-200`}>
              {percentage}%
            </span>
          </div>
        )}
      </div>

      {/* Confidence level indicator */}
      <div className={`${textSizeClasses[size]} text-slate-500 dark:text-slate-400`}>
        {normalizedConfidence >= 0.9 && '🎯'}
        {normalizedConfidence >= 0.75 && normalizedConfidence < 0.9 && '✅'}
        {normalizedConfidence >= 0.6 && normalizedConfidence < 0.75 && '⚠️'}
        {normalizedConfidence < 0.6 && '❓'}
      </div>
    </div>
  );
}