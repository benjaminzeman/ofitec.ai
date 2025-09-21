'use client';

import { useCallback, useEffect, useState } from 'react';
import { useDashboardData } from '@/hooks/useDashboardData';
import { fetchProviders } from '@/lib/api';
import { PageLoading } from '@/components/ui/LoadingSpinner';
import { ErrorDisplay, EmptyState } from '@/components/ui/ErrorStates';
import { useToastActions } from '@/components/ui/ToastContext';
import { animations } from '@/lib/animations';

interface Provider {
  id: string;
  name: string;
  rut: string;
  status: 'active' | 'inactive' | 'blocked' | 'pending';
  category: string;
  rating: number;
  totalAmount: number;
  ordersCount?: number; // Para datos de API
  totalOrders?: number; // Para datos mock
  lastOrder?: string; // Para datos de API
  lastOrderDate?: string; // Para datos mock
  projects?: string[];
  contact: string;
  email: string;
  paymentTerms?: string;
}

const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('es-CL');
};

const formatRut = (rut: string) => {
  if (!rut) return '';
  return rut.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.').replace(/(\d+)(\d)$/, '$1-$2');
};

const getStatusBadge = (status: string) => {
  const statusConfig: { [key: string]: { color: string; icon: string; text: string } } = {
    active: { color: 'bg-lime-50 text-lime-700 border-lime-200', icon: '●', text: 'Activo' },
    inactive: {
      color: 'bg-slate-100 text-slate-600 border-slate-200',
      icon: '○',
      text: 'Inactivo',
    },
    pending: {
      color: 'bg-amber-50 text-amber-700 border-amber-200',
      icon: '⏳',
      text: 'Pendiente',
    },
    blocked: { color: 'bg-red-50 text-red-700 border-red-200', icon: '⚠', text: 'Bloqueado' },
  };

  const config = statusConfig[status] || statusConfig['active'];

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-medium border rounded-xl ${config.color}`}
    >
      <span>{config.icon}</span>
      {config.text}
    </span>
  );
};

const getCategoryColor = (category: string) => {
  const colors: { [key: string]: string } = {
    construccion: 'bg-blue-50 text-blue-700 border-blue-200',
    materiales: 'bg-green-50 text-green-700 border-green-200',
    equipos: 'bg-purple-50 text-purple-700 border-purple-200',
    servicios: 'bg-orange-50 text-orange-700 border-orange-200',
    subcontrato: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  };

  return colors[category] || 'bg-slate-50 text-slate-700 border-slate-200';
};

const getRatingStars = (rating: number) => {
  return Array.from({ length: 5 }, (_, i) => (
    <span key={i} className={i < rating ? 'text-yellow-400' : 'text-slate-300'}>
      ★
    </span>
  ));
};

const transformProviderData = (apiProviders: any[]): Provider[] => {
  return apiProviders.map((provider) => ({
    id: provider.id,
    name: provider.name,
    rut: provider.rut,
    status: provider.status,
    category: provider.category,
    rating: provider.rating,
    totalAmount: provider.totalAmount,
    totalOrders: provider.ordersCount || provider.totalOrders || 0,
    lastOrderDate: provider.lastOrder || provider.lastOrderDate,
    contact: provider.contact,
    email: provider.email,
    projects: provider.projects || [],
    paymentTerms: provider.paymentTerms,
  }));
};

const MOCK_PROVIDERS: Provider[] = [
  {
    id: '1',
    name: 'Serviteg SPA',
    status: 'active',
    totalOrders: 1247,
    totalAmount: 10900000000,
    lastOrderDate: '2024-09-10',
    projects: ['Edificio Las Condes', 'Centro Comercial Maipú'],
    category: 'construccion',
    rating: 5,
    rut: '765432101',
    contact: 'Juan Serviteg',
    email: 'contacto@serviteg.cl',
  },
  {
    id: '2',
    name: 'Constructora Alpha Ltda',
    status: 'active',
    totalOrders: 892,
    totalAmount: 8750000000,
    lastOrderDate: '2024-09-08',
    projects: ['Hospital Temuco', 'Planta Pudahuel'],
    category: 'construccion',
    rating: 4,
    rut: '123456782',
    contact: 'María Alpha',
    email: 'maria@alpha.cl',
  },
  {
    id: '3',
    name: 'Materiales Pro S.A.',
    status: 'active',
    totalOrders: 2341,
    totalAmount: 4200000000,
    lastOrderDate: '2024-09-12',
    projects: ['Edificio Las Condes', 'Complejo Ñuñoa', 'Hospital Temuco'],
    category: 'materiales',
    rating: 4,
    rut: '987654323',
    contact: 'Carlos Pro',
    email: 'ventas@materialespro.cl',
  },
  {
    id: '4',
    name: 'Equipos Industriales Chile',
    status: 'pending',
    totalOrders: 156,
    totalAmount: 2800000000,
    lastOrderDate: '2024-08-28',
    projects: ['Planta Pudahuel'],
    category: 'equipos',
    rating: 3,
    rut: '456789124',
    contact: 'Ana Equipos',
    email: 'ana@equiposchile.cl',
  },
  {
    id: '5',
    name: 'Servicios Técnicos Beta',
    status: 'active',
    totalOrders: 634,
    totalAmount: 1950000000,
    lastOrderDate: '2024-09-05',
    projects: ['Centro Comercial Maipú', 'Hospital Temuco'],
    category: 'servicios',
    rating: 5,
    rut: '789123455',
    contact: 'Pedro Beta',
    email: 'pedro@beta.cl',
  },
  {
    id: '6',
    name: 'Subcontratistas Unidos',
    status: 'active',
    totalOrders: 423,
    totalAmount: 1650000000,
    lastOrderDate: '2024-09-11',
    projects: ['Complejo Ñuñoa'],
    category: 'subcontrato',
    rating: 4,
    rut: '321654987',
    contact: 'Luis Unidos',
    email: 'luis@unidos.cl',
  },
  {
    id: '7',
    name: 'Ferreterías del Sur',
    status: 'inactive',
    totalOrders: 89,
    totalAmount: 450000000,
    lastOrderDate: '2024-07-15',
    projects: [],
    category: 'materiales',
    rating: 2,
    rut: '654987321',
    contact: 'Carmen Sur',
    email: 'carmen@ferreteriasur.cl',
  },
];

export default function ProveedoresPage() {
  const { topProviders, loading: dashboardLoading, error: dashboardError } = useDashboardData();
  const { success, error: showError, info } = useToastActions();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [filteredProviders, setFilteredProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [sortBy, setSortBy] = useState('name');

  // Función para transformar datos de API a formato local
  // Cargar datos reales de proveedores
  const loadProviders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const realProviders = await fetchProviders();

      if (realProviders && realProviders.length > 0) {
        const transformedProviders = transformProviderData(realProviders);
        setProviders(transformedProviders);
        success(`Se cargaron ${realProviders.length} proveedores desde la base de datos`);
      } else {
        setProviders(MOCK_PROVIDERS);
        info('Mostrando datos de ejemplo - No hay proveedores en la base de datos');
      }
    } catch (err) {
      console.error('Error loading providers:', err);
      const errorMessage = 'Error al cargar proveedores. Usando datos de ejemplo.';
      setError(errorMessage);
      setProviders(MOCK_PROVIDERS);
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [info, showError, success]);

  useEffect(() => {
    void loadProviders();
  }, [loadProviders]);

  // Mock data expandido para proveedores (como fallback)
  useEffect(() => {
    let filtered = providers;

    // Filtrar por término de búsqueda
    if (searchTerm) {
      filtered = filtered.filter(
        (provider) =>
          provider.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          provider.contact.toLowerCase().includes(searchTerm.toLowerCase()) ||
          provider.rut.includes(searchTerm.replace(/\D/g, '')),
      );
    }

    // Filtrar por estado
    if (statusFilter !== 'all') {
      filtered = filtered.filter((provider) => provider.status === statusFilter);
    }

    // Filtrar por categoría
    if (categoryFilter !== 'all') {
      filtered = filtered.filter((provider) => provider.category === categoryFilter);
    }

    // Ordenar
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'amount':
          return b.totalAmount - a.totalAmount;
        case 'orders':
          return (b.totalOrders || b.ordersCount || 0) - (a.totalOrders || a.ordersCount || 0);
        case 'rating':
          return b.rating - a.rating;
        case 'lastOrder':
          const bDate = new Date(b.lastOrderDate || b.lastOrder || '1970-01-01').getTime();
          const aDate = new Date(a.lastOrderDate || a.lastOrder || '1970-01-01').getTime();
          return bDate - aDate;
        default:
          return 0;
      }
    });

    setFilteredProviders(filtered);
  }, [providers, searchTerm, statusFilter, categoryFilter, sortBy]);

  // Función de retry para recargar datos
  const retryLoadProviders = async () => {
    setError(null);
    setLoading(true);
    info('Reintentando cargar proveedores...');

    try {
      const realProviders = await fetchProviders();
      if (realProviders && realProviders.length > 0) {
        const transformedProviders = transformProviderData(realProviders);
        setProviders(transformedProviders);
        success(`Datos cargados exitosamente: ${realProviders.length} proveedores`);
      } else {
        setProviders(MOCK_PROVIDERS);
        info('Usando datos de ejemplo - No hay proveedores en la base de datos');
      }
    } catch (err) {
      console.error('Error loading providers:', err);
      const errorMessage = 'Error al cargar proveedores. Usando datos de ejemplo.';
      setError(errorMessage);
      showError(errorMessage);
      setProviders(MOCK_PROVIDERS);
    } finally {
      setLoading(false);
    }
  };

  const activeProviders = filteredProviders.filter((p) => p.status === 'active').length;
  const totalAmount = filteredProviders.reduce((sum, p) => sum + p.totalAmount, 0);
  const totalOrders = filteredProviders.reduce(
    (sum, p) => sum + (p.totalOrders || p.ordersCount || 0),
    0,
  );
  const avgRating =
    filteredProviders.length > 0
      ? filteredProviders.reduce((sum, p) => sum + p.rating, 0) / filteredProviders.length
      : 0;

  if (loading) {
    return (
      <PageLoading
        title="Cargando proveedores..."
        description="Obteniendo información de proveedores y evaluaciones"
      />
    );
  }

  if (error && filteredProviders.length === 0) {
    return (
      <ErrorDisplay
        title="Error al cargar proveedores"
        message={error}
        onRetry={retryLoadProviders}
      />
    );
  }

  if (!loading && filteredProviders.length === 0) {
    return (
      <EmptyState
        title="No hay proveedores disponibles"
        message="No se encontraron proveedores que coincidan con los filtros aplicados."
        icon="🏢"
        action={{
          label: 'Recargar datos',
          onClick: retryLoadProviders,
        }}
      />
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Gestión de Proveedores
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Control y evaluación de proveedores estratégicos
          </p>
        </div>
        <button className="px-4 py-2 bg-lime-500 text-white rounded-xl hover:bg-lime-600 transition-colors">
          + Nuevo Proveedor
        </button>
        <button
          onClick={() => success('Proveedor guardado exitosamente')}
          className="px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors"
        >
          Probar Toast
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 stagger-item ${animations.cardHover}`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Proveedores Activos</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {activeProviders}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-500">
                de {filteredProviders.length} total
              </p>
            </div>
            <div
              className={`w-12 h-12 bg-lime-50 dark:bg-lime-950 rounded-xl flex items-center justify-center ${animations.float}`}
            >
              <span className="text-lime-600 dark:text-lime-400 text-xl">🏢</span>
            </div>
          </div>
        </div>

        <div
          className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 stagger-item ${animations.cardHover}`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Volumen Total</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {formatCurrency(totalAmount)}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-500">
                en {totalOrders.toLocaleString()} órdenes
              </p>
            </div>
            <div
              className={`w-12 h-12 bg-lime-50 dark:bg-lime-950 rounded-xl flex items-center justify-center ${animations.float}`}
            >
              <span className="text-lime-600 dark:text-lime-400 text-xl">💰</span>
            </div>
          </div>
        </div>

        <div
          className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 stagger-item ${animations.cardHover}`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Rating Promedio</p>
              <div className="flex items-center gap-2">
                <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                  {avgRating.toFixed(1)}
                </p>
                <div className="flex text-sm">{getRatingStars(Math.round(avgRating))}</div>
              </div>
            </div>
            <div
              className={`w-12 h-12 bg-lime-50 dark:bg-lime-950 rounded-xl flex items-center justify-center ${animations.float}`}
            >
              <span className="text-lime-600 dark:text-lime-400 text-xl">⭐</span>
            </div>
          </div>
        </div>

        <div
          className={`bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 stagger-item ${animations.cardHover}`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Órdenes Promedio</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {Math.round(totalOrders / filteredProviders.length)}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-500">por proveedor</p>
            </div>
            <div
              className={`w-12 h-12 bg-lime-50 dark:bg-lime-950 rounded-xl flex items-center justify-center ${animations.float}`}
            >
              <span className="text-lime-600 dark:text-lime-400 text-xl">📊</span>
            </div>
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className={animations.fadeInLeft}>
            <input
              type="text"
              placeholder="Buscar por nombre, RUT o contacto..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={`w-full px-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-lime-500 ${animations.inputFocus}`}
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={`px-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-lime-500 ${animations.inputFocus} ${animations.fadeInUp}`}
          >
            <option value="all">Todos los estados</option>
            <option value="active">Activos</option>
            <option value="inactive">Inactivos</option>
            <option value="pending">Pendientes</option>
            <option value="blocked">Bloqueados</option>
          </select>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className={`px-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-lime-500 ${animations.inputFocus} ${animations.fadeInUp}`}
          >
            <option value="all">Todas las categorías</option>
            <option value="construccion">Construcción</option>
            <option value="materiales">Materiales</option>
            <option value="equipos">Equipos</option>
            <option value="servicios">Servicios</option>
            <option value="subcontrato">Subcontrato</option>
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className={`px-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-lime-500 ${animations.inputFocus} ${animations.fadeInRight}`}
          >
            <option value="name">Ordenar por Nombre</option>
            <option value="amount">Ordenar por Monto</option>
            <option value="orders">Ordenar por Órdenes</option>
            <option value="rating">Ordenar por Rating</option>
            <option value="lastOrder">Ordenar por Última Orden</option>
          </select>
        </div>
      </div>

      {/* Lista de Proveedores */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Proveedores ({filteredProviders.length})
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 dark:bg-slate-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Proveedor
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Categoría
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Volumen de Negocio
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Rating
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Proyectos
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Última Orden
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {filteredProviders.map((provider) => (
                <tr
                  key={provider.id}
                  className="hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
                >
                  <td className="px-6 py-4">
                    <div>
                      <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                        {provider.name}
                      </div>
                      <div className="text-sm text-slate-500 dark:text-slate-400">
                        RUT: {formatRut(provider.rut)}
                      </div>
                      <div className="text-xs text-slate-400 dark:text-slate-500">
                        {provider.contact} • {provider.email}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">{getStatusBadge(provider.status)}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2 py-1 text-xs font-medium border rounded-xl ${getCategoryColor(provider.category)}`}
                    >
                      {provider.category.charAt(0).toUpperCase() + provider.category.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div>
                      <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                        {formatCurrency(provider.totalAmount)}
                      </div>
                      <div className="text-sm text-slate-500 dark:text-slate-400">
                        {(provider.totalOrders || provider.ordersCount || 0).toLocaleString()}{' '}
                        órdenes
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                        {provider.rating.toFixed(1)}
                      </span>
                      <div className="flex text-xs">{getRatingStars(provider.rating)}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-slate-600 dark:text-slate-400">
                      {provider.projects && provider.projects.length > 0 ? (
                        <div>
                          <div className="font-medium">
                            {provider.projects.length} proyecto
                            {provider.projects.length > 1 ? 's' : ''}
                          </div>
                          <div className="text-xs">
                            {provider.projects
                              .slice(0, 2)
                              .map((project) =>
                                project.length > 20 ? project.substring(0, 20) + '...' : project,
                              )
                              .join(', ')}
                            {provider.projects.length > 2 &&
                              ` +${provider.projects.length - 2} más`}
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-400">Sin proyectos</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-slate-600 dark:text-slate-400">
                      {formatDate(provider.lastOrderDate || provider.lastOrder || '')}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <button className="text-lime-600 hover:text-lime-700 text-sm font-medium">
                        Ver
                      </button>
                      <button className="text-slate-600 hover:text-slate-700 text-sm font-medium">
                        Editar
                      </button>
                      <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">
                        Evaluar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
