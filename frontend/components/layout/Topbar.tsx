'use client';

import { useState } from 'react';

interface TopbarProps {
  onSidebarToggle: () => void;
  sidebarOpen: boolean;
}

export default function Topbar({ onSidebarToggle, sidebarOpen }: TopbarProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const notifications = [
    {
      id: 1,
      type: 'info',
      title: 'Nuevo reporte disponible',
      message: 'El reporte mensual de Proyecto Las Condes está listo',
      time: '5 min',
      unread: true,
    },
    {
      id: 2,
      type: 'warning',
      title: 'Presupuesto en riesgo',
      message: 'Centro Comercial Maipú supera 85% del presupuesto',
      time: '15 min',
      unread: true,
    },
    {
      id: 3,
      type: 'success',
      title: 'Pago procesado',
      message: 'Factura F-2024-0891 pagada exitosamente',
      time: '1 h',
      unread: false,
    },
  ];

  const unreadCount = notifications.filter((n) => n.unread).length;

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'success':
        return '✅';
      case 'warning':
        return '⚠️';
      case 'error':
        return '❌';
      default:
        return 'ℹ️';
    }
  };

  return (
    <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Left section */}
        <div className="flex items-center gap-4">
          <button
            onClick={onSidebarToggle}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors lg:hidden"
          >
            <span className="text-lg">☰</span>
          </button>

          {/* Breadcrumbs */}
          <nav className="hidden sm:flex items-center space-x-2 text-sm">
            <span className="text-slate-500 dark:text-slate-400">Inicio</span>
            <span className="text-slate-300 dark:text-slate-600">›</span>
            <span className="text-slate-900 dark:text-slate-100 font-medium">Dashboard</span>
          </nav>
        </div>

        {/* Center section - Search */}
        <div className="flex-1 max-w-md mx-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Buscar proyectos, proveedores, órdenes..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-lime-500 text-sm"
            />
            <div className="absolute left-3 top-1/2 transform -translate-y-1/2">
              <span className="text-slate-400 text-lg">🔍</span>
            </div>
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <span className="text-lg">×</span>
              </button>
            )}
          </div>
        </div>

        {/* Right section */}
        <div className="flex items-center gap-2">
          {/* Quick actions */}
          <button className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <span className="text-lg">📊</span>
          </button>

          <button className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <span className="text-lg">➕</span>
          </button>

          {/* Notifications */}
          <div className="relative">
            <button
              onClick={() => {
                setShowNotifications(!showNotifications);
                setShowUserMenu(false);
              }}
              className="relative p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <span className="text-lg">🔔</span>
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </button>

            {showNotifications && (
              <div className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg z-50">
                <div className="p-4 border-b border-slate-200 dark:border-slate-700">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    Notificaciones
                  </h3>
                </div>

                <div className="max-h-96 overflow-y-auto">
                  {notifications.map((notification) => (
                    <div
                      key={notification.id}
                      className={`p-4 border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors ${
                        notification.unread ? 'bg-lime-50 dark:bg-lime-950/20' : ''
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <span className="flex-shrink-0 text-lg">
                          {getNotificationIcon(notification.type)}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                            {notification.title}
                          </p>
                          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                            {notification.message}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-500 mt-2">
                            hace {notification.time}
                          </p>
                        </div>
                        {notification.unread && (
                          <div className="w-2 h-2 bg-lime-500 rounded-full flex-shrink-0"></div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="p-3 text-center border-t border-slate-200 dark:border-slate-700">
                  <button className="text-sm text-lime-600 dark:text-lime-400 hover:text-lime-700 dark:hover:text-lime-300 font-medium">
                    Ver todas las notificaciones
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* User menu */}
          <div className="relative">
            <button
              onClick={() => {
                setShowUserMenu(!showUserMenu);
                setShowNotifications(false);
              }}
              className="flex items-center gap-2 p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <div className="w-8 h-8 bg-lime-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">A</span>
              </div>
              <span className="text-sm hidden sm:block">▼</span>
            </button>

            {showUserMenu && (
              <div className="absolute right-0 top-full mt-2 w-48 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg z-50">
                <div className="p-3 border-b border-slate-200 dark:border-slate-700">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    Usuario Admin
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">admin@ofitec.cl</p>
                </div>

                <div className="py-2">
                  <button className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
                    👤 Mi Perfil
                  </button>
                  <button className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
                    ⚙️ Configuración
                  </button>
                  <button className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
                    🌙 Tema Oscuro
                  </button>
                  <hr className="my-2 border-slate-200 dark:border-slate-700" />
                  <button className="w-full px-3 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 transition-colors">
                    🚪 Cerrar Sesión
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
