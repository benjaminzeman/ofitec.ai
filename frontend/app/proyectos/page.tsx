'use client';

import { useCallback, useEffect, useState } from 'react';
import { fetchProjects } from '@/lib/api';
import { useDashboardData } from '@/hooks/useDashboardData';
import { PageLoading } from '@/components/ui/LoadingSpinner';
import { ErrorDisplay, EmptyState } from '@/components/ui/ErrorStates';
import Link from 'next/link';

interface Project {
  id: string;
  name: string;
  status: string;
  budget: number;
  spent: number;
  progress: number;
  manager: string;
  startDate: string;
  endDate: string;
  orders: number;
  providers: number;
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

const getStatusBadge = (status: string) => {
  const statusConfig: { [key: string]: { color: string; icon: string; text: string } } = {
    active: { color: 'bg-lime-50 text-lime-700 border-lime-200', icon: '●', text: 'Activo' },
    completed: {
      color: 'bg-green-50 text-green-700 border-green-200',
      icon: '✔',
      text: 'Completado',
    },
    delayed: {
      color: 'bg-amber-50 text-amber-700 border-amber-200',
      icon: '⏳',
      text: 'Retrasado',
    },
    on_hold: { color: 'bg-slate-100 text-slate-600 border-slate-200', icon: '○', text: 'En Pausa' },
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

const transformProjectData = (apiProjects: any[]): Project[] => {
  return apiProjects.map((project) => ({
    id: project.id,
    name: project.name,
    status: project.status,
    budget: project.budget,
    spent: project.spent || project.gastado || 0,
    progress: project.progress,
    manager: project.manager || project.gerente || 'No asignado',
    startDate: project.startDate || project.fechaInicio || '',
    endDate: project.endDate || project.fechaFin || '',
    orders: project.orders || 0,
    providers: project.providers || 0,
  }));
};

const MOCK_PROJECTS: Project[] = [
  {
    id: '1',
    name: 'Edificio Corporativo Las Condes',
    status: 'active',
    budget: 2500000000,
    spent: 1875000000,
    progress: 75,
    manager: 'Juan Pérez',
    startDate: '2024-01-15',
    endDate: '2025-06-30',
    orders: 245,
    providers: 38,
  },
  {
    id: '2',
    name: 'Centro Comercial Maipú',
    status: 'active',
    budget: 4200000000,
    spent: 2940000000,
    progress: 70,
    manager: 'María González',
    startDate: '2023-08-01',
    endDate: '2025-12-15',
    orders: 389,
    providers: 52,
  },
  {
    id: '3',
    name: 'Planta Industrial Pudahuel',
    status: 'delayed',
    budget: 1800000000,
    spent: 1440000000,
    progress: 65,
    manager: 'Carlos Silva',
    startDate: '2024-03-01',
    endDate: '2025-03-30',
    orders: 178,
    providers: 29,
  },
  {
    id: '4',
    name: 'Complejo Habitacional Ñuñoa',
    status: 'completed',
    budget: 3100000000,
    spent: 2945000000,
    progress: 100,
    manager: 'Ana López',
    startDate: '2023-02-15',
    endDate: '2024-11-30',
    orders: 412,
    providers: 45,
  },
  {
    id: '5',
    name: 'Hospital Regional Temuco',
    status: 'active',
    budget: 8500000000,
    spent: 4250000000,
    progress: 50,
    manager: 'Roberto Martínez',
    startDate: '2024-06-01',
    endDate: '2026-08-15',
    orders: 623,
    providers: 78,
  },
];

export default function ProyectosPage() {
  const { loading: dashboardLoading, error: dashboardError } = useDashboardData();
  const [projects, setProjects] = useState<Project[]>([]);
  const [filteredProjects, setFilteredProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortBy, setSortBy] = useState('name');

  // Función para transformar datos de API a formato local
  // Cargar datos reales de proyectos
  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const realProjects = await fetchProjects();

      if (realProjects && realProjects.length > 0) {
        const transformedProjects = transformProjectData(realProjects);
        setProjects(transformedProjects);
      } else {
        setProjects(MOCK_PROJECTS);
      }
    } catch (err) {
      console.error('Error loading projects:', err);
      setError('Error al cargar proyectos. Usando datos de ejemplo.');
      setProjects(MOCK_PROJECTS);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  // Mock data para proyectos mientras se implementa la API
  useEffect(() => {
    let filtered = projects;

    // Filtrar por término de búsqueda
    if (searchTerm) {
      filtered = filtered.filter(
        (project) =>
          project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          project.manager.toLowerCase().includes(searchTerm.toLowerCase()),
      );
    }

    // Filtrar por estado
    if (statusFilter !== 'all') {
      filtered = filtered.filter((project) => project.status === statusFilter);
    }

    // Ordenar
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'budget':
          return b.budget - a.budget;
        case 'progress':
          return b.progress - a.progress;
        case 'startDate':
          return new Date(b.startDate).getTime() - new Date(a.startDate).getTime();
        default:
          return 0;
      }
    });

    setFilteredProjects(filtered);
  }, [projects, searchTerm, statusFilter, sortBy]);

  const getProgressColor = (progress: number, status: string) => {
    if (status === 'completed') return 'bg-green-500';
    if (status === 'delayed') return 'bg-amber-500';
    if (progress >= 80) return 'bg-lime-500';
    if (progress >= 60) return 'bg-lime-400';
    return 'bg-lime-300';
  };

  const getRiskLevel = (budget: number, spent: number, progress: number) => {
    const spentPercentage = (spent / budget) * 100;
    const progressGap = spentPercentage - progress;

    if (progressGap > 10) return { level: 'Alto', color: 'text-red-600' };
    if (progressGap > 5) return { level: 'Medio', color: 'text-amber-600' };
    return { level: 'Bajo', color: 'text-lime-600' };
  };

  // Función de retry para recargar datos
  const retryLoadProjects = async () => {
    setError(null);
    setLoading(true);
    try {
      const realProjects = await fetchProjects();
      if (realProjects && realProjects.length > 0) {
        const transformedProjects = transformProjectData(realProjects);
        setProjects(transformedProjects);
      } else {
        setProjects(MOCK_PROJECTS);
      }
    } catch (err) {
      console.error('Error loading projects:', err);
      setError('Error al cargar proyectos. Usando datos de ejemplo.');
      setProjects(MOCK_PROJECTS);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <PageLoading
        title="Cargando proyectos..."
        description="Obteniendo información de proyectos y presupuestos"
      />
    );
  }

  if (error && filteredProjects.length === 0) {
    return (
      <ErrorDisplay title="Error al cargar proyectos" message={error} onRetry={retryLoadProjects} />
    );
  }

  if (!loading && filteredProjects.length === 0) {
    return (
      <EmptyState
        title="No hay proyectos disponibles"
        message="No se encontraron proyectos que coincidan con los filtros aplicados."
        icon="🏗️"
        action={{
          label: 'Recargar datos',
          onClick: retryLoadProjects,
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
            Gestión de Proyectos
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Control integral de proyectos de construcción
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/proyectos/control"
            className="px-4 py-2 bg-white text-lime-700 border border-lime-300 rounded-xl hover:bg-lime-50 dark:bg-slate-900 dark:text-lime-400 dark:border-lime-700"
            title="Ver Control Financiero de Proyectos"
          >
            Control Financiero
          </Link>
          <Link
            href="/proyectos/overview"
            className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-xl border border-slate-200 dark:border-slate-600 hover:bg-slate-200 dark:hover:bg-slate-600"
            title="Ver Resumen Portafolio"
          >
            Resumen
          </Link>
          <button className="px-4 py-2 bg-lime-500 text-white rounded-xl hover:bg-lime-600 transition-colors">
            + Nuevo Proyecto
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Proyectos Activos</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {filteredProjects.filter((p) => p.status === 'active').length}
              </p>
            </div>
            <div className="w-12 h-12 bg-lime-50 dark:bg-lime-950 rounded-xl flex items-center justify-center">
              <span className="text-lime-600 dark:text-lime-400 text-xl">🏗️</span>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Presupuesto Total</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {formatCurrency(filteredProjects.reduce((sum, p) => sum + p.budget, 0))}
              </p>
            </div>
            <div className="w-12 h-12 bg-lime-50 dark:bg-lime-950 rounded-xl flex items-center justify-center">
              <span className="text-lime-600 dark:text-lime-400 text-xl">💰</span>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Progreso Promedio</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {Math.round(
                  filteredProjects.reduce((sum, p) => sum + p.progress, 0) /
                    filteredProjects.length,
                )}
                %
              </p>
            </div>
            <div className="w-12 h-12 bg-lime-50 dark:bg-lime-950 rounded-xl flex items-center justify-center">
              <span className="text-lime-600 dark:text-lime-400 text-xl">📊</span>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">Proyectos en Riesgo</p>
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                {
                  filteredProjects.filter(
                    (p) => getRiskLevel(p.budget, p.spent, p.progress).level === 'Alto',
                  ).length
                }
              </p>
            </div>
            <div className="w-12 h-12 bg-red-50 dark:bg-red-950 rounded-xl flex items-center justify-center">
              <span className="text-red-600 dark:text-red-400 text-xl">⚠</span>
            </div>
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Buscar proyectos..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-lime-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-lime-500"
          >
            <option value="all">Todos los estados</option>
            <option value="active">Activos</option>
            <option value="completed">Completados</option>
            <option value="delayed">Retrasados</option>
            <option value="on_hold">En Pausa</option>
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-lime-500"
          >
            <option value="name">Ordenar por Nombre</option>
            <option value="budget">Ordenar por Presupuesto</option>
            <option value="progress">Ordenar por Progreso</option>
            <option value="startDate">Ordenar por Fecha</option>
          </select>
        </div>
      </div>

      {/* Lista de Proyectos */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Proyectos ({filteredProjects.length})
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50 dark:bg-slate-900">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Proyecto
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Estado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Presupuesto
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Progreso
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Riesgo
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Fechas
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {filteredProjects.map((project) => {
                const risk = getRiskLevel(project.budget, project.spent, project.progress);
                return (
                  <tr
                    key={project.id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div>
                        <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                          {project.name}
                        </div>
                        <div className="text-sm text-slate-500 dark:text-slate-400">
                          PM: {project.manager}
                        </div>
                        <div className="text-xs text-slate-400 dark:text-slate-500">
                          {project.orders} órdenes • {project.providers} proveedores
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">{getStatusBadge(project.status)}</td>
                    <td className="px-6 py-4">
                      <div>
                        <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                          {formatCurrency(project.budget)}
                        </div>
                        <div className="text-sm text-slate-500 dark:text-slate-400">
                          Gastado: {formatCurrency(project.spent)}
                        </div>
                        <div className="text-xs text-slate-400 dark:text-slate-500">
                          Disponible: {formatCurrency(project.budget - project.spent)}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                            {project.progress}%
                          </span>
                        </div>
                        <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all duration-300 ${getProgressColor(project.progress, project.status)}`}
                            style={{ width: `${project.progress}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`text-sm font-medium ${risk.color}`}>{risk.level}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-slate-600 dark:text-slate-400">
                        <div>Inicio: {formatDate(project.startDate)}</div>
                        <div>Fin: {formatDate(project.endDate)}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <Link
                          href={`/proyectos/${encodeURIComponent(project.name)}/control`}
                          className="text-lime-600 hover:text-lime-700 text-sm font-medium"
                          title="Ir al Control Financiero"
                        >
                          Control
                        </Link>
                        <Link
                          href={`/proyectos/${encodeURIComponent(project.name)}`}
                          className="text-slate-600 hover:text-slate-700 text-sm font-medium"
                          title="Ir al 360"
                        >
                          360
                        </Link>
                        <button className="text-slate-600 hover:text-slate-700 text-sm font-medium">
                          Editar
                        </button>
                        <button className="text-red-600 hover:text-red-700 text-sm font-medium">
                          Reportar
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
