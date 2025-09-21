interface ProgressBarProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  color?: 'lime' | 'blue' | 'amber' | 'red' | 'green';
  showLabel?: boolean;
  label?: string;
  className?: string;
}

export default function ProgressBar({
  value,
  max = 100,
  size = 'md',
  color = 'lime',
  showLabel = false,
  label,
  className = '',
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'h-2';
      case 'md':
        return 'h-3';
      case 'lg':
        return 'h-4';
      default:
        return 'h-3';
    }
  };

  const getColorClasses = () => {
    switch (color) {
      case 'lime':
        return 'bg-lime-500';
      case 'blue':
        return 'bg-blue-500';
      case 'amber':
        return 'bg-amber-500';
      case 'red':
        return 'bg-red-500';
      case 'green':
        return 'bg-green-500';
      default:
        return 'bg-lime-500';
    }
  };

  return (
    <div className={className}>
      {(showLabel || label) && (
        <div className="flex items-center justify-between mb-2">
          {label && <span className="text-sm text-slate-700 dark:text-slate-300">{label}</span>}
          {showLabel && (
            <span className="text-sm text-slate-500 dark:text-slate-400">
              {percentage.toFixed(0)}%
            </span>
          )}
        </div>
      )}

      <div
        className={`w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden ${getSizeClasses()}`}
      >
        <div
          className={`${getSizeClasses()} ${getColorClasses()} transition-all duration-300 ease-out rounded-full`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

interface CircularProgressProps {
  value: number;
  max?: number;
  size?: number;
  strokeWidth?: number;
  color?: 'lime' | 'blue' | 'amber' | 'red' | 'green';
  showLabel?: boolean;
  label?: string;
  className?: string;
}

export function CircularProgress({
  value,
  max = 100,
  size = 64,
  strokeWidth = 4,
  color = 'lime',
  showLabel = false,
  label,
  className = '',
}: CircularProgressProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  const getColorClasses = () => {
    switch (color) {
      case 'lime':
        return 'stroke-lime-500';
      case 'blue':
        return 'stroke-blue-500';
      case 'amber':
        return 'stroke-amber-500';
      case 'red':
        return 'stroke-red-500';
      case 'green':
        return 'stroke-green-500';
      default:
        return 'stroke-lime-500';
    }
  };

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-slate-200 dark:text-slate-700"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={`transition-all duration-300 ease-out ${getColorClasses()}`}
        />
      </svg>

      {(showLabel || label) && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            {label && <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>}
            {showLabel && (
              <div className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {percentage.toFixed(0)}%
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

interface StepProgressProps {
  steps: string[];
  currentStep: number;
  completedSteps?: number[];
  color?: 'lime' | 'blue' | 'amber' | 'red' | 'green';
  className?: string;
}

export function StepProgress({
  steps,
  currentStep,
  completedSteps = [],
  color = 'lime',
  className = '',
}: StepProgressProps) {
  const getColorClasses = () => {
    switch (color) {
      case 'lime':
        return {
          completed: 'bg-lime-500 text-white border-lime-500',
          current: 'bg-lime-50 text-lime-600 border-lime-500',
          pending: 'bg-slate-100 text-slate-500 border-slate-300',
          line: 'bg-lime-500',
        };
      case 'blue':
        return {
          completed: 'bg-blue-500 text-white border-blue-500',
          current: 'bg-blue-50 text-blue-600 border-blue-500',
          pending: 'bg-slate-100 text-slate-500 border-slate-300',
          line: 'bg-blue-500',
        };
      default:
        return {
          completed: 'bg-lime-500 text-white border-lime-500',
          current: 'bg-lime-50 text-lime-600 border-lime-500',
          pending: 'bg-slate-100 text-slate-500 border-slate-300',
          line: 'bg-lime-500',
        };
    }
  };

  const colors = getColorClasses();

  const getStepStatus = (index: number) => {
    if (completedSteps.includes(index) || index < currentStep) return 'completed';
    if (index === currentStep) return 'current';
    return 'pending';
  };

  const getStepClasses = (status: string) => {
    switch (status) {
      case 'completed':
        return colors.completed;
      case 'current':
        return colors.current;
      case 'pending':
      default:
        return colors.pending;
    }
  };

  return (
    <div className={`flex items-center justify-between ${className}`}>
      {steps.map((step, index) => {
        const status = getStepStatus(index);
        const isCompleted = status === 'completed';
        const isLast = index === steps.length - 1;

        return (
          <div key={index} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full border-2 flex items-center justify-center text-sm font-medium transition-colors ${getStepClasses(status)}`}
              >
                {isCompleted ? <span>✓</span> : <span>{index + 1}</span>}
              </div>
              <div className="mt-2 text-xs text-center text-slate-600 dark:text-slate-400 max-w-[80px]">
                {step}
              </div>
            </div>

            {!isLast && (
              <div className="flex-1 mx-4">
                <div className="h-0.5 bg-slate-200 dark:bg-slate-700 relative">
                  <div
                    className={`h-full transition-all duration-300 ${
                      status === 'completed' ? colors.line : 'bg-transparent'
                    }`}
                  />
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
