// Utilidades de animación para ofitec.ai
// Sigue la ESTRATEGIA_VISUAL con transiciones suaves y profesionales

export const animations = {
  // Transiciones de entrada
  fadeIn: 'animate-in fade-in duration-300',
  fadeInUp: 'animate-in fade-in slide-in-from-bottom-4 duration-300',
  fadeInDown: 'animate-in fade-in slide-in-from-top-4 duration-300',
  fadeInLeft: 'animate-in fade-in slide-in-from-left-4 duration-300',
  fadeInRight: 'animate-in fade-in slide-in-from-right-4 duration-300',

  // Transiciones de escala
  scaleIn: 'animate-in zoom-in-95 duration-200',
  scaleOut: 'animate-out zoom-out-95 duration-200',

  // Transiciones de lista/stagger
  staggerFadeIn: (delay: number) =>
    `animate-in fade-in slide-in-from-bottom-2 duration-300 delay-${delay}`,

  // Hover efectos
  hoverScale: 'transition-transform duration-200 hover:scale-[1.02]',
  hoverLift: 'transition-all duration-200 hover:shadow-lg hover:-translate-y-1',
  hoverGlow: 'transition-all duration-200 hover:shadow-lime-200/50 hover:shadow-lg',

  // Estados de carga
  pulse: 'animate-pulse',
  spin: 'animate-spin',
  bounce: 'animate-bounce',

  // Transiciones personalizadas
  slideUp: 'transform transition-transform duration-300 ease-out',
  slideDown: 'transform transition-transform duration-300 ease-out',

  // Micro-interacciones
  buttonPress: 'transition-all duration-100 active:scale-95',
  cardHover:
    'transition-all duration-200 hover:shadow-xl hover:shadow-lime-100/20 hover:-translate-y-1',
  inputFocus:
    'transition-all duration-200 focus:ring-2 focus:ring-lime-500/20 focus:border-lime-500',

  // Animaciones continuas
  float: 'animate-[float_3s_ease-in-out_infinite]',
  shimmer: 'animate-[shimmer_2s_infinite]',
  glow: 'animate-[glow_2s_ease-in-out_infinite_alternate]',
};

export const transitions = {
  // Transiciones base siguiendo estrategia visual
  smooth: 'transition-all duration-200 ease-out',
  fast: 'transition-all duration-100 ease-out',
  slow: 'transition-all duration-500 ease-out',

  // Transiciones específicas
  colors: 'transition-colors duration-200 ease-out',
  transform: 'transition-transform duration-200 ease-out',
  opacity: 'transition-opacity duration-200 ease-out',
  shadow: 'transition-shadow duration-200 ease-out',
};

export const keyframes = {
  // Keyframes personalizados para efectos especiales
  shimmer: 'animate-[shimmer_2s_infinite]',
  float: 'animate-[float_3s_ease-in-out_infinite]',
  glow: 'animate-[glow_2s_ease-in-out_infinite_alternate]',
};

// Hook para manejar animaciones de lista
export function useStaggerAnimation(items: any[], delay = 100) {
  return items.map((item, index) => ({
    ...item,
    animationDelay: `${index * delay}ms`,
    className:
      `${item.className || ''} animate-in fade-in slide-in-from-bottom-2 duration-300`.trim(),
  }));
}

// Configuración de spring para framer-motion (opcional)
export const springConfig = {
  type: 'spring',
  damping: 25,
  stiffness: 120,
  mass: 1,
};

// Variantes para animaciones complejas
export const pageVariants = {
  initial: { opacity: 0, y: 20 },
  enter: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
};

export const cardVariants = {
  initial: { opacity: 0, scale: 0.95 },
  enter: { opacity: 1, scale: 1 },
  hover: { scale: 1.02, y: -4 },
};

export const listVariants = {
  initial: { opacity: 0 },
  enter: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

export const listItemVariants = {
  initial: { opacity: 0, x: -20 },
  enter: { opacity: 1, x: 0 },
};
