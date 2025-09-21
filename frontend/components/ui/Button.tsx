interface ButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  onClick,
  type = 'button',
  className = '',
  icon,
  iconPosition = 'left',
}: ButtonProps) {
  const getVariantClasses = () => {
    switch (variant) {
      case 'primary':
        return 'bg-lime-500 text-white hover:bg-lime-600 focus:ring-lime-500';
      case 'secondary':
        return 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 focus:ring-slate-500';
      case 'danger':
        return 'bg-red-500 text-white hover:bg-red-600 focus:ring-red-500';
      case 'ghost':
        return 'bg-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 focus:ring-slate-500';
      case 'outline':
        return 'bg-transparent border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 focus:ring-slate-500';
      default:
        return 'bg-lime-500 text-white hover:bg-lime-600 focus:ring-lime-500';
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'px-3 py-1.5 text-sm';
      case 'md':
        return 'px-4 py-2 text-sm';
      case 'lg':
        return 'px-6 py-3 text-base';
      default:
        return 'px-4 py-2 text-sm';
    }
  };

  const baseClasses =
    'inline-flex items-center justify-center gap-2 font-medium rounded-xl focus:outline-none focus:ring-2 focus:ring-opacity-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
  const variantClasses = getVariantClasses();
  const sizeClasses = getSizeClasses();

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${baseClasses} ${variantClasses} ${sizeClasses} ${className}`}
    >
      {loading ? (
        <>
          <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
          Cargando...
        </>
      ) : (
        <>
          {icon && iconPosition === 'left' && icon}
          {children}
          {icon && iconPosition === 'right' && icon}
        </>
      )}
    </button>
  );
}

interface IconButtonProps {
  icon: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
  title?: string;
}

export function IconButton({
  icon,
  variant = 'ghost',
  size = 'md',
  disabled = false,
  loading = false,
  onClick,
  type = 'button',
  className = '',
  title,
}: IconButtonProps) {
  const getVariantClasses = () => {
    switch (variant) {
      case 'primary':
        return 'bg-lime-500 text-white hover:bg-lime-600 focus:ring-lime-500';
      case 'secondary':
        return 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 focus:ring-slate-500';
      case 'danger':
        return 'bg-red-500 text-white hover:bg-red-600 focus:ring-red-500';
      case 'ghost':
        return 'bg-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 focus:ring-slate-500';
      default:
        return 'bg-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 focus:ring-slate-500';
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'w-8 h-8 text-sm';
      case 'md':
        return 'w-10 h-10 text-base';
      case 'lg':
        return 'w-12 h-12 text-lg';
      default:
        return 'w-10 h-10 text-base';
    }
  };

  const baseClasses =
    'inline-flex items-center justify-center rounded-xl focus:outline-none focus:ring-2 focus:ring-opacity-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
  const variantClasses = getVariantClasses();
  const sizeClasses = getSizeClasses();

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      title={title}
      className={`${baseClasses} ${variantClasses} ${sizeClasses} ${className}`}
    >
      {loading ? (
        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        icon
      )}
    </button>
  );
}

interface ButtonGroupProps {
  children: React.ReactNode;
  className?: string;
}

export function ButtonGroup({ children, className = '' }: ButtonGroupProps) {
  return (
    <div
      className={`inline-flex rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 ${className}`}
    >
      {children}
    </div>
  );
}
