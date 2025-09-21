'use client';

import { useState, useEffect } from 'react';
import { fetchFinancialData, FinancialData as APIFinancialData } from '@/lib/api';
import { useDashboardData } from '@/hooks/useDashboardData';
import { PageLoading } from '@/components/ui/LoadingSpinner';
import Link from 'next/link';
import { ErrorDisplay } from '@/components/ui/ErrorStates';

interface FinancialData {
  orders: number;
  revenue: number;
  expenses: number;
  profit: number;
  cashflow: number;
  accounts_receivable: number;
  accounts_payable: number;
  margin: number;
}

interface CashflowItem {
  date: string;
  income: number;
  expenses: number;
  balance: number;
  description: string;
  category: string;
}

interface BankAccount {
  id: string;
  name: string;
  balance: number;
  currency: string;
  last_update: string;
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

const getCategoryColor = (category: string) => {
  const colors: { [key: string]: string } = {
    ingresos: 'bg-lime-50 text-lime-700 border-lime-200',
    materiales: 'bg-blue-50 text-blue-700 border-blue-200',
    mano_obra: 'bg-purple-50 text-purple-700 border-purple-200',
    servicios: 'bg-orange-50 text-orange-700 border-orange-200',
    gastos_admin: 'bg-red-50 text-red-700 border-red-200',
    impuestos: 'bg-slate-50 text-slate-700 border-slate-200',
  };

  return colors[category] || 'bg-slate-50 text-slate-700 border-slate-200';
};

const MOCK_FINANCIAL_DATA: FinancialData = {
  orders: 16289,
  revenue: 35900000000,
  expenses: 27120000000,
  profit: 8780000000,
  cashflow: 2340000000,
  accounts_receivable: 4560000000,
  accounts_payable: 3210000000,
  margin: 24.5,
};

export default function FinanzasPage() {
  const { kpis, loading: dashboardLoading, error: dashboardError } = useDashboardData();
  const [financialData, setFinancialData] = useState<FinancialData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState('month');
  const [selectedView, setSelectedView] = useState('overview');

  // Cargar datos financieros reales
  useEffect(() => {
    const loadFinancialData = async () => {
      try {
        setLoading(true);
        setError(null);

        const api = await fetchFinancialData();

        if (api && (api as any).summary) {
          const s = (api as any).summary;
          const mapped: FinancialData = {
            orders: 0,
            revenue: Number(s.totalRevenue || 0),
            expenses: Number(s.totalExpenses || 0),
            profit: Number(s.netProfit || 0),
            cashflow: Number(s.cashflow || 0),
            accounts_receivable: Number(s.pendingReceivables || 0),
            accounts_payable: Number(s.pendingPayables || 0),
            margin: Number(s.profitMargin || 0),
          };
          setFinancialData(mapped);
        } else {
          setFinancialData(MOCK_FINANCIAL_DATA);
        }
      } catch (err) {
        console.error('Error loading financial data:', err);
        setError('Error al cargar datos financieros. Usando datos de ejemplo.');
        setFinancialData(MOCK_FINANCIAL_DATA);
      } finally {
        setLoading(false);
      }
    };

    loadFinancialData();
  }, []);

  // Función helper para obtener datos actuales
  const getCurrentFinancialData = (): FinancialData => {
    return financialData || MOCK_FINANCIAL_DATA;
  };

  // Mock data financiero expandido (como fallback)
  const mockCashflow: CashflowItem[] = [
    {
      date: '2024-09-12',
      income: 125000000,
      expenses: 89000000,
      balance: 36000000,
      description: 'Pago factura Edificio Las Condes',
      category: 'ingresos',
    },
    {
      date: '2024-09-11',
      income: 0,
      expenses: 45000000,
      balance: -45000000,
      description: 'Compra materiales Centro Comercial',
      category: 'materiales',
    },
    {
      date: '2024-09-10',
      income: 89000000,
      expenses: 0,
      balance: 89000000,
      description: 'Anticipo proyecto Hospital Temuco',
      category: 'ingresos',
    },
    {
      date: '2024-09-09',
      income: 0,
      expenses: 156000000,
      balance: -156000000,
      description: 'Pago nómina mensual',
      category: 'mano_obra',
    },
    {
      date: '2024-09-08',
      income: 234000000,
      expenses: 78000000,
      balance: 156000000,
      description: 'Estado de pago EP-2024-09',
      category: 'ingresos',
    },
  ];

  const mockBankAccounts: BankAccount[] = [
    {
      id: '1',
      name: 'Banco Santander - Cuenta Corriente',
      balance: 2340000000,
      currency: 'CLP',
      last_update: '2024-09-12T08:30:00',
    },
    {
      id: '2',
      name: 'BCI - Línea de Crédito',
      balance: 890000000,
      currency: 'CLP',
      last_update: '2024-09-12T09:15:00',
    },
    {
      id: '3',
      name: 'Banco Estado - Cta. Proyecto',
      balance: 567000000,
      currency: 'CLP',
      last_update: '2024-09-11T16:45:00',
    },
  ];

  const totalBankBalance = mockBankAccounts.reduce((sum, account) => sum + account.balance, 0);

  const getBalanceColor = (balance: number) => {
    if (balance > 0) return 'text-lime-600 dark:text-lime-400';
    if (balance < 0) return 'text-red-600 dark:text-red-400';
    return 'text-slate-600 dark:text-slate-400';
  };

  // Función de retry para recargar datos
  const retryLoadFinancialData = async () => {
    setError(null);
    setLoading(true);
    try {
      const api = await fetchFinancialData();
      if (api && (api as any).summary) {
        const s = (api as any).summary;
        setFinancialData({
          orders: 0,
          revenue: Number(s.totalRevenue || 0),
          expenses: Number(s.totalExpenses || 0),
          profit: Number(s.netProfit || 0),
          cashflow: Number(s.cashflow || 0),
          accounts_receivable: Number(s.pendingReceivables || 0),
          accounts_payable: Number(s.pendingPayables || 0),
          margin: Number(s.profitMargin || 0),
        });
      } else {
        setFinancialData(MOCK_FINANCIAL_DATA);
      }
    } catch (err) {
      console.error('Error loading financial data:', err);
      setError('Error al cargar datos financieros. Usando datos de ejemplo.');
      setFinancialData(MOCK_FINANCIAL_DATA);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <PageLoading
        title="Cargando datos financieros..."
        description="Obteniendo información de ingresos, gastos y flujo de caja"
      />
    );
  }

  if (error && !financialData) {
    return (
      <ErrorDisplay
        title="Error al cargar datos financieros"
        message={error}
        onRetry={retryLoadFinancialData}
      />
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Control Financiero
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Gestión integral de finanzas empresariales
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/finanzas/overview"
            className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-xl border border-slate-200 dark:border-slate-600 hover:bg-slate-200 dark:hover:bg-slate-600"
          >
            Resumen Ejecutivo
          </Link>
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="px-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-lime-500"
          >
            <option value="week">Esta Semana</option>
            <option value="month">Este Mes</option>
            <option value="quarter">Este Trimestre</option>
            <option value="year">Este Año</option>
          </select>
          <button className="px-4 py-2 bg-lime-500 text-white rounded-xl hover:bg-lime-600 transition-colors">
            Exportar
          </button>
        </div>
      </div>

      {/* Navegación de Vistas */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <div className="flex flex-wrap gap-2">
          {[
            { id: 'overview', label: 'Resumen Ejecutivo', icon: '📊' },
            { id: 'cashflow', label: 'Flujo de Caja', icon: '💰' },
            { id: 'accounts', label: 'Cuentas Bancarias', icon: '🏦' },
            { id: 'chipax', label: 'Migración Chipax', icon: '🔄' },
            { id: 'sii', label: 'SII Integration', icon: '📋' },
          ].map((view) => (
            <button
              key={view.id}
              onClick={() => setSelectedView(view.id)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                selectedView === view.id
                  ? 'bg-lime-500 text-white'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
              }`}
            >
              <span className="mr-2">{view.icon}</span>
              {view.label}
            </button>
          ))}
        </div>
      </div>

      {/* Vista Resumen Ejecutivo */}
      {selectedView === 'overview' && (
        <>
          {/* KPIs Principales */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Ingresos Totales</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {formatCurrency(getCurrentFinancialData().revenue)}
                  </p>
                  <p className="text-xs text-lime-600 dark:text-lime-400 font-medium">
                    +12.3% vs mes anterior
                  </p>
                </div>
                <div className="w-12 h-12 bg-lime-50 dark:bg-lime-950 rounded-xl flex items-center justify-center">
                  <span className="text-lime-600 dark:text-lime-400 text-xl">📈</span>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Gastos Totales</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {formatCurrency(getCurrentFinancialData().expenses)}
                  </p>
                  <p className="text-xs text-amber-600 dark:text-amber-400 font-medium">
                    +8.7% vs mes anterior
                  </p>
                </div>
                <div className="w-12 h-12 bg-amber-50 dark:bg-amber-950 rounded-xl flex items-center justify-center">
                  <span className="text-amber-600 dark:text-amber-400 text-xl">📉</span>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">Utilidad Neta</p>
                  <p className="text-2xl font-bold text-lime-600 dark:text-lime-400">
                    {formatCurrency(MOCK_FINANCIAL_DATA.profit)}
                  </p>
                  <p className="text-xs text-lime-600 dark:text-lime-400 font-medium">
                    Margen: {MOCK_FINANCIAL_DATA.margin}%
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
                  <p className="text-sm text-slate-600 dark:text-slate-400">Flujo de Caja</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {formatCurrency(MOCK_FINANCIAL_DATA.cashflow)}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-500">Liquidez: Buena</p>
                </div>
                <div className="w-12 h-12 bg-blue-50 dark:bg-blue-950 rounded-xl flex items-center justify-center">
                  <span className="text-blue-600 dark:text-blue-400 text-xl">🌊</span>
                </div>
              </div>
            </div>
          </div>

          {/* Cuentas por Cobrar y Pagar */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
                Cuentas por Cobrar
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600 dark:text-slate-400">
                    Total Pendiente
                  </span>
                  <span className="text-lg font-bold text-slate-900 dark:text-slate-100">
                    {formatCurrency(MOCK_FINANCIAL_DATA.accounts_receivable)}
                  </span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400">0-30 días</span>
                    <span className="font-medium text-lime-600 dark:text-lime-400">
                      {formatCurrency(MOCK_FINANCIAL_DATA.accounts_receivable * 0.6)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400">31-60 días</span>
                    <span className="font-medium text-amber-600 dark:text-amber-400">
                      {formatCurrency(MOCK_FINANCIAL_DATA.accounts_receivable * 0.25)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400">+60 días</span>
                    <span className="font-medium text-red-600 dark:text-red-400">
                      {formatCurrency(MOCK_FINANCIAL_DATA.accounts_receivable * 0.15)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
                Cuentas por Pagar
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600 dark:text-slate-400">
                    Total Pendiente
                  </span>
                  <span className="text-lg font-bold text-slate-900 dark:text-slate-100">
                    {formatCurrency(MOCK_FINANCIAL_DATA.accounts_payable)}
                  </span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400">0-30 días</span>
                    <span className="font-medium text-lime-600 dark:text-lime-400">
                      {formatCurrency(MOCK_FINANCIAL_DATA.accounts_payable * 0.7)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400">31-60 días</span>
                    <span className="font-medium text-amber-600 dark:text-amber-400">
                      {formatCurrency(MOCK_FINANCIAL_DATA.accounts_payable * 0.2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400">+60 días</span>
                    <span className="font-medium text-red-600 dark:text-red-400">
                      {formatCurrency(MOCK_FINANCIAL_DATA.accounts_payable * 0.1)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Vista Flujo de Caja */}
      {selectedView === 'cashflow' && (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
          <div className="p-6 border-b border-slate-200 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Flujo de Caja Detallado
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 dark:bg-slate-900">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Fecha
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Descripción
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Categoría
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Ingresos
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Egresos
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Balance
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {mockCashflow.map((item, index) => (
                  <tr
                    key={index}
                    className="hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
                  >
                    <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-400">
                      {formatDate(item.date)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-slate-900 dark:text-slate-100">
                        {item.description}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2 py-1 text-xs font-medium border rounded-xl ${getCategoryColor(item.category)}`}
                      >
                        {item.category.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {item.income > 0 && (
                        <span className="text-sm font-medium text-lime-600 dark:text-lime-400">
                          +{formatCurrency(item.income)}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {item.expenses > 0 && (
                        <span className="text-sm font-medium text-red-600 dark:text-red-400">
                          -{formatCurrency(item.expenses)}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`text-sm font-medium ${getBalanceColor(item.balance)}`}>
                        {formatCurrency(item.balance)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Vista Cuentas Bancarias */}
      {selectedView === 'accounts' && (
        <div className="space-y-6">
          {/* Resumen Total */}
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  Balance Total de Cuentas
                </h3>
                <p className="text-3xl font-bold text-lime-600 dark:text-lime-400 mt-2">
                  {formatCurrency(totalBankBalance)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-slate-600 dark:text-slate-400">Última actualización</p>
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                  {formatDate(new Date().toISOString())}
                </p>
              </div>
            </div>
          </div>

          {/* Lista de Cuentas */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {mockBankAccounts.map((account) => (
              <div
                key={account.id}
                className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100">
                      {account.name}
                    </h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{account.currency}</p>
                  </div>
                  <span className="w-3 h-3 bg-lime-500 rounded-full"></span>
                </div>

                <div className="space-y-2">
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                    {formatCurrency(account.balance)}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Actualizado: {formatDate(account.last_update)}
                  </p>
                </div>

                <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                  <div className="flex gap-2">
                    <button className="flex-1 px-3 py-1 text-xs bg-lime-50 dark:bg-lime-950 text-lime-600 dark:text-lime-400 rounded-lg hover:bg-lime-100 dark:hover:bg-lime-900 transition-colors">
                      Ver Movimientos
                    </button>
                    <button className="flex-1 px-3 py-1 text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors">
                      Conciliar
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Vista Migración Chipax */}
      {selectedView === 'chipax' && (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-lime-50 dark:bg-lime-950 rounded-xl flex items-center justify-center mx-auto mb-4">
              <span className="text-lime-600 dark:text-lime-400 text-2xl">🔄</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Migración Chipax Completada
            </h3>
            <p className="text-slate-600 dark:text-slate-400 mb-4">
              Se han migrado exitosamente 34,428 registros desde Chipax
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
              <div className="text-center">
                <p className="text-2xl font-bold text-lime-600 dark:text-lime-400">16,289</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">Órdenes</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-lime-600 dark:text-lime-400">548</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">Proveedores</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-lime-600 dark:text-lime-400">100%</p>
                <p className="text-sm text-slate-600 dark:text-slate-400">Completado</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Vista SII Integration */}
      {selectedView === 'sii' && (
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-blue-50 dark:bg-blue-950 rounded-xl flex items-center justify-center mx-auto mb-4">
              <span className="text-blue-600 dark:text-blue-400 text-2xl">📋</span>
            </div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
              Integración SII
            </h3>
            <p className="text-slate-600 dark:text-slate-400 mb-4">
              Próximamente: Conexión automática con Servicio de Impuestos Internos
            </p>
            <button className="px-6 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors">
              Configurar Integración
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
