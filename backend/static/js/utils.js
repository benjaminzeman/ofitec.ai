/**
 * ofitec.ai - Utilidades Base
 * Funciones helper siguiendo exactamente copilot-rules.md
 */

/**
 * Formateo de números chilenos (CLP)
 */
export function formatCLP(amount) {
  if (typeof amount !== 'number' || isNaN(amount)) return '$0';
  
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
}

/**
 * Formateo de RUT chileno
 */
export function formatRUT(rut) {
  if (!rut) return '';
  
  // Limpiar RUT
  const cleaned = rut.toString().replace(/[^0-9Kk]/g, '');
  if (cleaned.length < 2) return rut;
  
  const body = cleaned.slice(0, -1);
  const dv = cleaned.slice(-1).toUpperCase();
  
  // Formatear con puntos
  const formatted = body.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  
  return `${formatted}-${dv}`;
}

/**
 * Formateo de fechas
 */
export function formatDate(date, format = 'short') {
  if (!date) return '';
  
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';
  
  const formats = {
    short: { day: '2-digit', month: '2-digit', year: 'numeric' },
    medium: { day: 'numeric', month: 'short', year: 'numeric' },
    long: { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }
  };
  
  return new Intl.DateTimeFormat('es-CL', formats[format]).format(d);
}

/**
 * Calcular días hasta vencimiento
 */
export function diasHastaVencimiento(fechaVencimiento) {
  if (!fechaVencimiento) return null;
  
  const hoy = new Date();
  const vencimiento = new Date(fechaVencimiento);
  
  if (isNaN(vencimiento.getTime())) return null;
  
  const diffTime = vencimiento - hoy;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  return diffDays;
}

/**
 * Obtener estado según días de vencimiento
 */
export function getEstadoVencimiento(fechaVencimiento) {
  const dias = diasHastaVencimiento(fechaVencimiento);
  
  if (dias === null) return 'Sin fecha';
  if (dias < 0) return 'Vencido';
  if (dias <= 7) return 'Por vencer';
  return 'Vigente';
}

/**
 * Truncar texto con elipsis
 */
export function truncateText(text, maxLength = 50) {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * Debounce function
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Generar ID único
 */
export function generateId() {
  return Math.random().toString(36).substr(2, 9);
}

/**
 * Validar RUT chileno
 */
export function validateRUT(rut) {
  if (!rut) return false;
  
  const cleaned = rut.replace(/[^0-9Kk]/g, '');
  if (cleaned.length < 2) return false;
  
  const body = cleaned.slice(0, -1);
  const dv = cleaned.slice(-1).toUpperCase();
  
  let sum = 0;
  let multiplier = 2;
  
  for (let i = body.length - 1; i >= 0; i--) {
    sum += parseInt(body[i]) * multiplier;
    multiplier = multiplier === 7 ? 2 : multiplier + 1;
  }
  
  const calculatedDV = 11 - (sum % 11);
  const finalDV = calculatedDV === 11 ? '0' : calculatedDV === 10 ? 'K' : calculatedDV.toString();
  
  return dv === finalDV;
}

/**
 * Calcular porcentaje de avance
 */
export function calcularPorcentajeAvance(actual, total) {
  if (!total || total === 0) return 0;
  return Math.round((actual / total) * 100);
}

/**
 * Ordenar array por campo
 */
export function sortBy(array, field, direction = 'asc') {
  return [...array].sort((a, b) => {
    const aVal = typeof a[field] === 'string' ? a[field].toLowerCase() : a[field];
    const bVal = typeof b[field] === 'string' ? b[field].toLowerCase() : b[field];
    
    if (aVal < bVal) return direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return direction === 'asc' ? 1 : -1;
    return 0;
  });
}

/**
 * Filtrar array por múltiples campos
 */
export function filterData(data, filters) {
  return data.filter(item => {
    return Object.entries(filters).every(([key, value]) => {
      if (!value) return true;
      
      const itemValue = item[key];
      if (typeof itemValue === 'string') {
        return itemValue.toLowerCase().includes(value.toLowerCase());
      }
      return itemValue === value;
    });
  });
}

/**
 * Agrupar datos por campo
 */
export function groupBy(array, key) {
  return array.reduce((groups, item) => {
    const group = item[key];
    if (!groups[group]) {
      groups[group] = [];
    }
    groups[group].push(item);
    return groups;
  }, {});
}

/**
 * Storage helper con fallback
 */
export const storage = {
  get(key, defaultValue = null) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  },
  
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },
  
  remove(key) {
    try {
      localStorage.removeItem(key);
      return true;
    } catch {
      return false;
    }
  }
};
