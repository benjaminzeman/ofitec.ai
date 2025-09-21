'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useCallback } from 'react';
import {
  LayoutDashboard,
  DollarSign,
  Building2,
  Wrench,
  FileText,
  Shield,
  Users,
  Bot,
  Settings,
} from 'lucide-react';

const navigation = [
  {
    name: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
    description: 'Control Center Ejecutivo',
  },
  {
    name: 'Finanzas',
    href: '/finanzas',
    icon: DollarSign,
    description: 'Chipax, Cashflow, Conciliación',
    children: [
      { name: 'Resumen Ejecutivo', href: '/finanzas/overview' },
      { name: 'Cobros (CxC)', href: '/finanzas/facturas-venta' },
      { name: 'Pagos (CxP)', href: '/finanzas/facturas-compra' },
      { name: 'Facturas Compra', href: '/finanzas/facturas-compra' },
      { name: 'Facturas Venta', href: '/finanzas/facturas-venta' },
      { name: 'Gastos', href: '/finanzas/gastos' },
      { name: 'Impuestos', href: '/finanzas/impuestos' },
      { name: 'Previred', href: '/finanzas/previred' },
      { name: 'Sueldos', href: '/finanzas/sueldos' },
      { name: 'Cartola Bancaria', href: '/finanzas/cartola-bancaria' },
      { name: 'Ventas (AR)', href: '/ventas' },
      { name: 'Saldos Tesorería', href: '/finanzas/tesoreria' },
      { name: 'Órdenes de Compra', href: '/finanzas/ordenes-compra' },
      { name: 'Cashflow Lab', href: '/finanzas/cashflow' },
      { name: 'Reporte Proyectos', href: '/finanzas/reportes-proyectos' },
      { name: 'Reporte Proveedores', href: '/finanzas/reportes-proveedores' },
      { name: 'Conciliación Bancaria', href: '/finanzas/conciliacion' },
      { name: 'SII Integration', href: '/finanzas/sii' },
      { name: 'Conectores Bancarios', href: '/finanzas/bancos' },
    ],
  },
  {
    name: 'Proyectos',
    href: '/proyectos',
    icon: Building2,
    description: 'Control Integral, Subcontratistas',
    children: [
      { name: 'Resumen Portafolio', href: '/proyectos/overview' },
      { name: 'Control Financiero', href: '/proyectos/financiero' },
      { name: 'Subcontratistas', href: '/proyectos/subcontratistas' },
      { name: 'Órdenes de Cambio', href: '/proyectos/cambios' },
      { name: 'Planning & Scheduling', href: '/proyectos/planning' },
    ],
  },
  {
    name: 'Operaciones',
    href: '/operaciones',
    icon: Wrench,
    description: 'Reportes, HSE, Recursos',
    children: [
      { name: 'Reportes Digitales', href: '/operaciones/reportes' },
      { name: 'HSE Inteligente', href: '/operaciones/hse' },
      { name: 'Control Recursos', href: '/operaciones/recursos' },
      { name: 'Comunicación', href: '/operaciones/comunicacion' },
    ],
  },
  {
    name: 'Documentos',
    href: '/documentos',
    icon: FileText,
    description: 'DocuChat, RFI, IA',
    children: [
      { name: 'DocuChat AI', href: '/documentos/docuchat' },
      { name: 'RFI Digital', href: '/documentos/rfi' },
      { name: 'Biblioteca', href: '/documentos/biblioteca' },
    ],
  },
  {
    name: 'Riesgos',
    href: '/riesgos',
    icon: Shield,
    description: 'Matriz IA, Predicciones',
    children: [
      { name: 'Matriz Riesgos', href: '/riesgos/matriz' },
      { name: 'Predicciones ML', href: '/riesgos/predicciones' },
      { name: 'Alertas', href: '/riesgos/alertas' },
    ],
  },
  {
    name: 'Portal Cliente',
    href: '/cliente',
    icon: Users,
    description: 'Vistas Proyecto, Reportes',
    children: [
      { name: 'Vista Proyecto', href: '/cliente/proyecto' },
      { name: 'Reportes Ejecutivos', href: '/cliente/reportes' },
      { name: 'Interacción', href: '/cliente/interaccion' },
    ],
  },
  {
    name: 'IA & Analytics',
    href: '/ia',
    icon: Bot,
    description: 'Copilots, Análisis',
    children: [
      { name: 'Copilots Especializados', href: '/ia/copilots' },
      { name: 'Analytics Avanzados', href: '/ia/analytics' },
      { name: 'ML Insights', href: '/ia/insights' },
    ],
  },
  {
    name: 'Configuración',
    href: '/config',
    icon: Settings,
    description: 'Usuarios, Seguridad, Integraciones',
    children: [
      { name: 'Gestión Usuarios', href: '/config/usuarios' },
      { name: 'Integraciones', href: '/config/integraciones' },
      { name: 'Personalización', href: '/config/personalizacion' },
    ],
  },
];

interface SidebarProps {
  isOpen?: boolean;
  onToggle?: () => void;
}

export function Sidebar({ isOpen = true, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  const buildStamp = process.env.NEXT_PUBLIC_BUILD_STAMP;

  const getOverviewHref = useCallback(
    (href: string, children?: { name: string; href: string }[]) => {
      // Prefer an explicit "overview" child, otherwise use the first child, else fallback to href
      if (children && children.length > 0) {
        const bySlug = children.find((c) => /\/overview$/.test(c.href));
        if (bySlug) return bySlug.href;
        const byName = children.find((c) => /resumen|overview/i.test(c.name));
        if (byName) return byName.href;
        return children[0].href;
      }
      return href;
    },
    [],
  );

  const onParentClick = useCallback(
    (item: any) => {
      // Toggle submenu visibility
      setOpenSections((prev) => ({ ...prev, [item.href]: !prev[item.href] }));
      // Navigate to its overview
      const dest = getOverviewHref(item.href, item.children);
      if (dest && pathname !== dest) router.push(dest);
    },
    [getOverviewHref, pathname, router],
  );

  return (
    <div
      className={`flex flex-col w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700 transition-transform duration-300 ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      } lg:translate-x-0`}
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-6 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-lime-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">O</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100">Ofitec</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">ofitec.ai</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4">
        <div className="px-3 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            const Icon = item.icon;

            const isOpenSection = !!openSections[item.href];
            const ParentContent = (
              <div
                role={item.children ? 'button' : undefined}
                tabIndex={item.children ? 0 : -1}
                onClick={item.children ? () => onParentClick(item) : undefined}
                onKeyDown={(e) => {
                  if (!item.children) return;
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onParentClick(item);
                  }
                }}
                className={`group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-lime-500/10 text-lime-600 dark:text-lime-400 border-l-2 border-lime-500'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                <Icon className="mr-3 h-5 w-5 flex-shrink-0" />
                <div className="flex-1">
                  <div className="text-sm">{item.name}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    {item.description}
                  </div>
                </div>
                {item.children && (
                  <span className="ml-2 text-xs text-slate-400">{isOpenSection ? '▾' : '▸'}</span>
                )}
              </div>
            );

            return (
              <div key={item.name}>
                {/* Parent row (button-like if has children, otherwise a Link) */}
                {item.children ? (
                  ParentContent
                ) : (
                  <Link href={item.href} className="block">
                    {ParentContent}
                  </Link>
                )}

                {/* Submenu (collapsible) */}
                {item.children && isOpenSection && (
                  <div className="ml-6 mt-1 space-y-1">
                    {item.children.map((child) => (
                      <Link
                        key={child.name}
                        href={child.href}
                        className={`block px-3 py-1 text-xs rounded-md transition-colors ${
                          pathname === child.href
                            ? 'text-lime-600 dark:text-lime-400 bg-lime-500/5'
                            : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                        }`}
                      >
                        {child.name}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-700">
        <div className="text-xs text-slate-500 dark:text-slate-400">
          <div>ofitec.ai v1.0</div>
          <div>34,428 registros integrados</div>
          {buildStamp && <div className="mt-1">{buildStamp}</div>}
        </div>
      </div>
    </div>
  );
}
