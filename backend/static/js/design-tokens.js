/**
 * ofitec.ai - Design System Tokens
 * Implementación exacta según copilot-rules.md
 */

export const TOKENS = {
  dark: {
    appBg: "#0D0D0D",
    headerBg: "#111111", 
    cardBg: "#1C1C1C",
    border: "#2A2A2A",
    text: "#FFFFFF",
    text2: "#9CA3AF", 
    text3: "#6B7280",
    accent: "#84CC16",
    danger: "#F87171",
    warn: "#F59E0B",
    chartBg: "#101820",
  },
  light: {
    appBg: "#FFFFFF",
    headerBg: "#F5F5F5",
    cardBg: "#FFFFFF", 
    border: "#E5E7EB",
    text: "#111827",
    text2: "#6B7280",
    text3: "#9CA3AF",
    accent: "#84CC16",
    danger: "#DC2626", 
    warn: "#D97706",
    chartBg: "#101820",
  },
};

// Hook para usar tokens según el modo
export function useTokens(mode = 'dark') {
  return TOKENS[mode] || TOKENS.dark;
}

// Estilos CSS variables para uso directo
export const CSS_VARS = {
  dark: {
    '--ofi-app-bg': '#0D0D0D',
    '--ofi-header-bg': '#111111',
    '--ofi-card': '#1C1C1C', 
    '--ofi-border': '#2A2A2A',
    '--ofi-text': '#FFFFFF',
    '--ofi-text2': '#9CA3AF',
    '--ofi-text3': '#6B7280', 
    '--ofi-accent': '#84CC16',
    '--ofi-danger': '#F87171',
    '--ofi-warn': '#F59E0B',
    '--ofi-chart': '#101820',
  },
  light: {
    '--ofi-app-bg': '#FFFFFF',
    '--ofi-header-bg': '#F5F5F5',
    '--ofi-card': '#FFFFFF',
    '--ofi-border': '#E5E7EB', 
    '--ofi-text': '#111827',
    '--ofi-text2': '#6B7280',
    '--ofi-text3': '#9CA3AF',
    '--ofi-accent': '#84CC16',
    '--ofi-danger': '#DC2626',
    '--ofi-warn': '#D97706', 
    '--ofi-chart': '#101820',
  }
};
