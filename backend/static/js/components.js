/**
 * ofitec.ai - Core Components
 * Componentes base siguiendo exactamente copilot-rules.md
 */

import { useTokens } from './design-tokens.js';

/**
 * Card base - siempre plano, sin sombras, radius 12px
 */
export function Card({ children, className = "", mode = 'dark' }) {
  const T = useTokens(mode);
  
  return `
    <div class="rounded-xl border ${className}" 
         style="background: ${T.cardBg}; border-color: ${T.border}; border-width: 1px;">
      ${children}
    </div>
  `;
}

/**
 * Badge de estado - verde/ámbar/rojo según reglas
 */
export function Badge({ mode = 'dark', estado, className = "" }) {
  const T = useTokens(mode);
  
  const stateMap = {
    "Vigente": { color: T.accent, icon: "✔" },
    "Aprobado": { color: T.accent, icon: "✔" },
    "Por vencer": { color: T.warn, icon: "⏳" },
    "Pendiente": { color: T.warn, icon: "⏳" },
    "Vencido": { color: T.danger, icon: "⚠" },
    "Activo": { color: T.accent, icon: "●" },
    "Inactivo": { color: T.text3, icon: "○" },
  };
  
  const config = stateMap[estado] || { color: T.text2, icon: "●" };
  
  return `
    <span class="inline-flex items-center gap-1 px-2 py-1 rounded text-sm ${className}"
          style="color: ${config.color};">
      <span>${config.icon}</span>
      <span>${estado}</span>
    </span>
  `;
}

/**
 * KPI Card - para métricas principales
 */
export function KPICard({ title, value, subtitle, trend, mode = 'dark', className = "" }) {
  const T = useTokens(mode);
  
  const trendColor = trend > 0 ? T.accent : trend < 0 ? T.danger : T.text2;
  const trendIcon = trend > 0 ? "↗" : trend < 0 ? "↘" : "→";
  
  return Card({
    children: `
      <div class="p-6">
        <div style="color: ${T.text2}; font-size: 14px; margin-bottom: 8px;">
          ${title}
        </div>
        <div style="color: ${T.text}; font-size: 32px; font-weight: 700; line-height: 1;">
          ${value}
        </div>
        ${subtitle ? `
          <div style="color: ${T.text3}; font-size: 12px; margin-top: 4px;">
            ${subtitle}
          </div>
        ` : ''}
        ${trend !== undefined ? `
          <div style="color: ${trendColor}; font-size: 14px; margin-top: 8px;">
            <span>${trendIcon}</span>
            <span>${Math.abs(trend)}%</span>
          </div>
        ` : ''}
      </div>
    `,
    mode,
    className
  });
}

/**
 * Progress Bar - para barras de avance
 */
export function ProgressBar({ percentage, mode = 'dark', className = "" }) {
  const T = useTokens(mode);
  
  return `
    <div class="w-full ${className}">
      <div class="w-full rounded-full" 
           style="background: ${T.border}; height: 8px;">
        <div class="rounded-full transition-all duration-300" 
             style="background: ${T.accent}; height: 8px; width: ${Math.min(100, Math.max(0, percentage))}%;">
        </div>
      </div>
    </div>
  `;
}

/**
 * Table - cabecera gris, filas con borde
 */
export function Table({ headers, rows, mode = 'dark', className = "" }) {
  const T = useTokens(mode);
  
  return Card({
    children: `
      <div class="overflow-hidden">
        <table class="w-full">
          <thead>
            <tr style="background: ${T.headerBg};">
              ${headers.map(header => `
                <th class="px-6 py-3 text-left text-sm font-medium"
                    style="color: ${T.text2}; border-bottom: 1px solid ${T.border};">
                  ${header}
                </th>
              `).join('')}
            </tr>
          </thead>
          <tbody>
            ${rows.map((row, index) => `
              <tr style="border-bottom: 1px solid ${T.border};">
                ${row.map(cell => `
                  <td class="px-6 py-4 text-sm" style="color: ${T.text};">
                    ${cell}
                  </td>
                `).join('')}
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `,
    mode,
    className
  });
}

/**
 * Input - borde 1px, fondo card, sin sombras
 */
export function Input({ type = 'text', placeholder, value = '', mode = 'dark', className = "" }) {
  const T = useTokens(mode);
  
  return `
    <input type="${type}" 
           placeholder="${placeholder}"
           value="${value}"
           class="w-full px-4 py-2 rounded-lg border ${className}"
           style="background: ${T.cardBg}; 
                  border-color: ${T.border}; 
                  color: ${T.text};
                  border-width: 1px;"
           />
  `;
}

/**
 * Button - según reglas, sin gradientes ni sombras
 */
export function Button({ children, variant = 'primary', mode = 'dark', className = "", onClick = "" }) {
  const T = useTokens(mode);
  
  const variants = {
    primary: {
      background: T.accent,
      color: '#000000', // Negro sobre lime para contraste
      border: T.accent
    },
    secondary: {
      background: 'transparent',
      color: T.text,
      border: T.border
    },
    danger: {
      background: T.danger,
      color: '#FFFFFF',
      border: T.danger
    }
  };
  
  const config = variants[variant];
  
  return `
    <button class="px-4 py-2 rounded-lg border font-medium transition-all ${className}"
            style="background: ${config.background}; 
                   color: ${config.color}; 
                   border-color: ${config.border};
                   border-width: 1px;"
            onclick="${onClick}">
      ${children}
    </button>
  `;
}
