import { useState } from 'react';

interface FormField {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'number' | 'select' | 'textarea' | 'date' | 'checkbox';
  required?: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
  validation?: (value: any) => string | null;
  disabled?: boolean;
  description?: string;
}

interface FormProps {
  fields: FormField[];
  onSubmit: (data: any) => void;
  submitLabel?: string;
  cancelLabel?: string;
  onCancel?: () => void;
  loading?: boolean;
  initialData?: any;
  className?: string;
}

export default function Form({
  fields,
  onSubmit,
  submitLabel = 'Guardar',
  cancelLabel = 'Cancelar',
  onCancel,
  loading = false,
  initialData = {},
  className = '',
}: FormProps) {
  const [formData, setFormData] = useState(() => {
    const initial: any = {};
    fields.forEach((field) => {
      initial[field.name] = initialData[field.name] || (field.type === 'checkbox' ? false : '');
    });
    return initial;
  });

  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [touched, setTouched] = useState<{ [key: string]: boolean }>({});

  const validateField = (field: FormField, value: any) => {
    if (field.required && (!value || (typeof value === 'string' && value.trim() === ''))) {
      return `${field.label} es requerido`;
    }

    if (field.validation) {
      return field.validation(value);
    }

    return null;
  };

  const handleChange = (field: FormField, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field.name]: value,
    }));

    // Validate on change if field was touched
    if (touched[field.name]) {
      const error = validateField(field, value);
      setErrors((prev) => ({
        ...prev,
        [field.name]: error || '',
      }));
    }
  };

  const handleBlur = (field: FormField) => {
    setTouched((prev) => ({
      ...prev,
      [field.name]: true,
    }));

    const error = validateField(field, formData[field.name]);
    setErrors((prev) => ({
      ...prev,
      [field.name]: error || '',
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate all fields
    const newErrors: { [key: string]: string } = {};
    let hasErrors = false;

    fields.forEach((field) => {
      const error = validateField(field, formData[field.name]);
      if (error) {
        newErrors[field.name] = error;
        hasErrors = true;
      }
    });

    setErrors(newErrors);
    setTouched(() => {
      const allTouched: { [key: string]: boolean } = {};
      fields.forEach((field) => {
        allTouched[field.name] = true;
      });
      return allTouched;
    });

    if (!hasErrors) {
      onSubmit(formData);
    }
  };

  const renderField = (field: FormField) => {
    const hasError = touched[field.name] && errors[field.name];
    const inputClass = `w-full px-4 py-2 bg-slate-50 dark:bg-slate-900 border ${
      hasError ? 'border-red-300 dark:border-red-700' : 'border-slate-200 dark:border-slate-700'
    } rounded-xl focus:outline-none focus:ring-2 focus:ring-lime-500 transition-colors ${
      field.disabled ? 'opacity-50 cursor-not-allowed' : ''
    }`;

    switch (field.type) {
      case 'select':
        return (
          <select
            value={formData[field.name]}
            onChange={(e) => handleChange(field, e.target.value)}
            onBlur={() => handleBlur(field)}
            disabled={field.disabled || loading}
            className={inputClass}
          >
            <option value="">{field.placeholder || `Seleccionar ${field.label}`}</option>
            {field.options?.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );

      case 'textarea':
        return (
          <textarea
            value={formData[field.name]}
            onChange={(e) => handleChange(field, e.target.value)}
            onBlur={() => handleBlur(field)}
            placeholder={field.placeholder}
            disabled={field.disabled || loading}
            className={`${inputClass} min-h-[100px] resize-y`}
            rows={4}
          />
        );

      case 'checkbox':
        return (
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={formData[field.name]}
              onChange={(e) => handleChange(field, e.target.checked)}
              onBlur={() => handleBlur(field)}
              disabled={field.disabled || loading}
              className="w-4 h-4 text-lime-600 bg-slate-50 dark:bg-slate-900 border-slate-300 dark:border-slate-600 rounded focus:ring-lime-500 focus:ring-2"
            />
            <label className="text-sm text-slate-700 dark:text-slate-300">{field.label}</label>
          </div>
        );

      default:
        return (
          <input
            type={field.type}
            value={formData[field.name]}
            onChange={(e) => handleChange(field, e.target.value)}
            onBlur={() => handleBlur(field)}
            placeholder={field.placeholder}
            disabled={field.disabled || loading}
            className={inputClass}
          />
        );
    }
  };

  return (
    <form onSubmit={handleSubmit} className={`space-y-6 ${className}`}>
      {fields.map((field) => (
        <div
          key={field.name}
          className={field.type === 'checkbox' ? 'flex items-start' : 'space-y-2'}
        >
          {field.type !== 'checkbox' && (
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </label>
          )}

          {renderField(field)}

          {field.description && (
            <p className="text-xs text-slate-500 dark:text-slate-400">{field.description}</p>
          )}

          {touched[field.name] && errors[field.name] && (
            <p className="text-xs text-red-600 dark:text-red-400 flex items-center gap-1">
              <span>⚠</span>
              {errors[field.name]}
            </p>
          )}
        </div>
      ))}

      <div className="flex gap-3 pt-4">
        <button
          type="submit"
          disabled={loading}
          className="flex-1 px-4 py-2 bg-lime-500 text-white rounded-xl hover:bg-lime-600 focus:outline-none focus:ring-2 focus:ring-lime-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <div className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              Guardando...
            </div>
          ) : (
            submitLabel
          )}
        </button>

        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {cancelLabel}
          </button>
        )}
      </div>
    </form>
  );
}
