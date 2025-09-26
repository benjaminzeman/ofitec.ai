'use client';

/**
 * OFITEC.AI - SISTEMA DE ICONOS VISUAL
 * 
 * Sistema de iconos usando Lucide React que reemplaza los emojis problemáticos
 * manteniendo la lógica visual oficial según ESTRATEGIA_VISUAL.md
 */

import React from 'react';
import {
  // Estados principales
  CheckCircle,
  Clock,
  AlertTriangle,
  XCircle,
  Circle,
  Dot,
  
  // Métricas financieras  
  DollarSign,
  TrendingUp,
  TrendingDown,
  PieChart,
  BarChart3,
  Calculator,
  
  // Navegación y acciones
  Home,
  Users,
  FileText,
  Settings,
  Search,
  Filter,
  Download,
  Upload,
  RefreshCw,
  
  // Sistema y status
  Database,
  Server,
  Wifi,
  WifiOff,
  CheckSquare,
  Square,
  
  // Proyectos y business
  Briefcase,
  Building2,
  Target,
  Layers,
  Calendar,
  MapPin
} from "lucide-react";

// ==============================================================================
// TIPOS E INTERFACES
// ==============================================================================

interface EstadoConfig {
  icon: React.ComponentType<any>;
  color: string;
  bgColor: string;
  label: string;
}

interface EstadoBadgeProps {
  estado: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

interface MetricaIconoProps {
  tipo: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  className?: string;
}

interface NavIconProps {
  tipo: string;
  active?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

// ==============================================================================
// MAPEO DE ESTADOS SEGÚN ESTRATEGIA OFICIAL
// ==============================================================================

export const EstadoIconos: Record<string, EstadoConfig> = {
  // Estados de documentos/proyectos
  "vigente": { 
    icon: CheckCircle, 
    color: "text-lime-500", 
    bgColor: "bg-lime-100 dark:bg-lime-900/20",
    label: "Vigente" 
  },
  "aprobado": { 
    icon: CheckCircle, 
    color: "text-lime-500", 
    bgColor: "bg-lime-100 dark:bg-lime-900/20",
    label: "Aprobado" 
  },
  "activo": { 
    icon: Dot, 
    color: "text-lime-500", 
    bgColor: "bg-lime-100 dark:bg-lime-900/20",
    label: "Activo" 
  },
  
  // Estados de advertencia
  "por_vencer": { 
    icon: Clock, 
    color: "text-amber-500", 
    bgColor: "bg-amber-100 dark:bg-amber-900/20",
    label: "Por Vencer" 
  },
  "pendiente": { 
    icon: Clock, 
    color: "text-amber-500", 
    bgColor: "bg-amber-100 dark:bg-amber-900/20",
    label: "Pendiente" 
  },
  "en_proceso": { 
    icon: RefreshCw, 
    color: "text-amber-500", 
    bgColor: "bg-amber-100 dark:bg-amber-900/20",
    label: "En Proceso" 
  },
  
  // Estados críticos
  "vencido": { 
    icon: AlertTriangle, 
    color: "text-red-500", 
    bgColor: "bg-red-100 dark:bg-red-900/20",
    label: "Vencido" 
  },
  "rechazado": { 
    icon: XCircle, 
    color: "text-red-500", 
    bgColor: "bg-red-100 dark:bg-red-900/20",
    label: "Rechazado" 
  },
  "inactivo": { 
    icon: Circle, 
    color: "text-gray-500", 
    bgColor: "bg-gray-100 dark:bg-gray-900/20",
    label: "Inactivo" 
  }
};

// ==============================================================================
// ICONOS POR CATEGORÍA DE NEGOCIO
// ==============================================================================

export const CategoriasIconos = {
  // Métricas financieras (KPIs)
  financiero: {
    presupuesto: DollarSign,
    revenue: TrendingUp,
    costos: Calculator,
    profit: PieChart,
    balance: BarChart3,
    tendencia_positiva: TrendingUp,
    tendencia_negativa: TrendingDown
  },
  
  // Navegación principal
  navegacion: {
    home: Home,
    dashboard: BarChart3,
    proyectos: Briefcase,
    clientes: Users,
    documentos: FileText,
    configuracion: Settings,
    buscar: Search,
    filtrar: Filter
  },
  
  // Sistema y conectividad
  sistema: {
    base_datos: Database,
    servidor: Server,
    conectado: Wifi,
    desconectado: WifiOff,
    activo: CheckSquare,
    inactivo: Square,
    recargar: RefreshCw
  },
  
  // Business objects
  negocio: {
    empresa: Building2,
    proyecto: Target,
    proceso: Layers,
    calendario: Calendar,
    ubicacion: MapPin,
    descargar: Download,
    subir: Upload
  }
};

// ==============================================================================
// COMPONENTE BADGE DE ESTADO
// ==============================================================================

export const EstadoBadge: React.FC<EstadoBadgeProps> = ({ estado, size = "sm", showLabel = true, className = "" }) => {
  const config = EstadoIconos[estado] || EstadoIconos["inactivo"];
  const IconComponent = config.icon;
  
  const sizeClasses = {
    xs: "h-3 w-3 text-xs px-1.5 py-0.5",
    sm: "h-4 w-4 text-sm px-2 py-1", 
    md: "h-5 w-5 text-base px-2.5 py-1.5",
    lg: "h-6 w-6 text-lg px-3 py-2"
  };
  
  return (
    <div className={`
      inline-flex items-center gap-1.5 rounded-full font-medium
      ${config.bgColor} ${config.color} ${sizeClasses[size]} ${className}
    `}>
      <IconComponent className={`${sizeClasses[size].split(' ')[0]} ${sizeClasses[size].split(' ')[1]}`} />
      {showLabel && <span>{config.label}</span>}
    </div>
  );
};

// ==============================================================================
// COMPONENTE ICONO DE MÉTRICA
// ==============================================================================

export const MetricaIcono: React.FC<MetricaIconoProps> = ({ tipo, value, trend, size = "md", className = "" }) => {
  const IconComponent = CategoriasIconos.financiero[tipo] || DollarSign;
  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : null;
  
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-5 w-5", 
    lg: "h-6 w-6",
    xl: "h-8 w-8"
  };
  
  const trendColor = trend === "up" ? "text-lime-500" : trend === "down" ? "text-red-500" : "text-gray-500";
  
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="flex items-center gap-1.5">
        <IconComponent className={`${sizeClasses[size]} text-lime-500`} />
        <span className="font-semibold">{value}</span>
      </div>
      {TrendIcon && (
        <TrendIcon className={`h-4 w-4 ${trendColor}`} />
      )}
    </div>
  );
};

// ==============================================================================
// COMPONENTE KPI CARD CON ICONOS
// ==============================================================================

export const KPICard: React.FC<KPICardProps> = ({ 
  title, 
  value, 
  subtitle, 
  icon: iconType, 
  trend, 
  trendValue,
  className = "" 
}) => {
  const IconComponent = CategoriasIconos.financiero[iconType] || DollarSign;
  const trendColor = trend === "up" ? "text-lime-500" : trend === "down" ? "text-red-500" : "text-gray-500";
  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : null;
  
  return (
    <div className={`
      bg-card-bg border border-border rounded-xl p-6
      ${className}
    `}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <IconComponent className="h-5 w-5 text-lime-500" />
            <h3 className="text-sm font-medium text-secondary">{title}</h3>
          </div>
          
          <div className="space-y-1">
            <p className="text-2xl font-bold text-primary">{value}</p>
            {subtitle && (
              <p className="text-sm text-tertiary">{subtitle}</p>
            )}
          </div>
        </div>
        
        {trend && TrendIcon && (
          <div className={`flex items-center gap-1 ${trendColor}`}>
            <TrendIcon className="h-4 w-4" />
            <span className="text-sm font-medium">{trendValue}</span>
          </div>
        )}
      </div>
    </div>
  );
};

// ==============================================================================
// COMPONENTE NAVEGACIÓN CON ICONOS
// ==============================================================================

export const NavIcon: React.FC<NavIconProps> = ({ tipo, active = false, size = "md", className = "" }) => {
  const IconComponent = CategoriasIconos.navegacion[tipo] || Home;
  
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-5 w-5", 
    lg: "h-6 w-6"
  };
  
  const colorClass = active 
    ? "text-lime-500" 
    : "text-secondary hover:text-primary";
  
  return (
    <IconComponent className={`${sizeClasses[size]} ${colorClass} ${className}`} />
  );
};

// ==============================================================================
// UTILIDADES DE ICONOS
// ==============================================================================

// Función para obtener icono por estado
export const getEstadoIcon = (estado) => {
  return EstadoIconos[estado]?.icon || Circle;
};

// Función para obtener color por estado  
export const getEstadoColor = (estado) => {
  return EstadoIconos[estado]?.color || "text-gray-500";
};

// Función para obtener configuración completa de estado
export const getEstadoConfig = (estado) => {
  return EstadoIconos[estado] || EstadoIconos["inactivo"];
};

export default {
  EstadoBadge,
  MetricaIcono, 
  KPICard,
  NavIcon,
  EstadoIconos,
  CategoriasIconos,
  getEstadoIcon,
  getEstadoColor,
  getEstadoConfig
};