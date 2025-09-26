'use client';

import { useEffect, useState } from 'react';
import AssignProjectDrawer from '@/components/AssignProjectDrawer';
import ArStatsWidget from '@/components/ArStatsWidget';
import { formatCurrency } from '@/lib/api';

type Row = {
  invoice_id: number;
  customer_rut: string;
  customer_name: string;
  invoice_number: string;
  issue_date: string;
  due_date?: string;
  currency?: string;
  total_amount: number;
  project_id?: number | null;
  paid_amount?: number | null;
  status?: 'paid' | 'pending' | 'overdue' | 'partial';
};

export default function Ventas() {
  const [rows, setRows] = useState<Row[]>([]);
  const [sel, setSel] = useState<Row | null>(null);
  const [search, setSearch] = useState('');
  const [projectId, setProjectId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [aging, setAging] = useState<{
    d0_30: number;
    d31_60: number;
    d61_90: number;
    d90p: number;
  } | null>(null);
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [bulkAssigning, setBulkAssigning] = useState(false);

  async function fetchRows() {
    setLoading(true);
    try {
      const qs = new URLSearchParams({
        page: '1',
        page_size: '50',
        order_by: 'fecha',
        order_dir: 'DESC',
      });
      if (search) qs.set('search', search);
      if (projectId) qs.set('project_id', projectId);
      if (dateFrom) qs.set('date_from', dateFrom);
      if (dateTo) qs.set('date_to', dateTo);
      if (statusFilter) qs.set('status', statusFilter);
      
      const url = `/api/sales_invoices?${qs.toString()}`;
      const r = await fetch(url).catch(() => null as any);
      
      if (r && r.ok) {
        const j = await r.json();
        const items = (j.items || []).map((x: any) => {
          const totalAmount = Number(x.total_amount ?? x.monto_total ?? 0);
          const paidAmount = Number(x.paid_amount ?? 0);
          const outstandingAmount = totalAmount - paidAmount;
          const daysOverdue = x.days_overdue ?? x.dias_vencidos ?? 0;
          
          let status: 'paid' | 'pending' | 'overdue' | 'partial' = 'pending';
          if (paidAmount >= totalAmount) {
            status = 'paid';
          } else if (daysOverdue > 0 && outstandingAmount > 0) {
            status = 'overdue';
          } else if (paidAmount > 0) {
            status = 'partial';
          }

          return {
            invoice_id: x.invoice_id ?? x.id ?? 0,
            customer_rut: x.customer_rut ?? x.cliente_rut ?? '',
            customer_name: x.customer_name ?? x.cliente_nombre ?? '',
            invoice_number: x.invoice_number ?? x.documento_numero ?? '',
            issue_date: x.issue_date ?? x.fecha ?? '',
            due_date: x.due_date,
            currency: x.currency ?? x.moneda,
            total_amount: totalAmount,
            project_id: x.project_id ?? null,
            paid_amount: paidAmount,
            status,
          } as Row;
        });
        setRows(items);
      } else {
        // Fallback to canonical finanzas endpoint (v_facturas_venta)
        const r2 = await fetch('/api/finanzas/facturas_venta?page=1&page_size=50');
        const j2 = await r2.json();
        const items2 = (j2.items || []).map((x: any) => ({
          invoice_id: 0,
          customer_rut: x.cliente_rut ?? '',
          customer_name: x.cliente_nombre ?? '',
          invoice_number: x.documento_numero ?? '',
          issue_date: x.fecha ?? '',
          total_amount: Number(x.monto_total ?? 0),
          project_id: null,
          paid_amount: 0,
          status: 'pending' as const,
        })) as Row[];
        setRows(items2);
      }
    } catch (e) {
      console.error('Ventas load error', e);
    } finally {
      setLoading(false);
    }
  }

  async function fetchAging() {
    try {
      const res = await fetch('/api/ar_aging_by_project');
      if (!res.ok) return setAging(null);
      const data = await res.json();
      const items: Array<any> = data.items || [];
      const filtered = projectId
        ? items.filter((x) => String(x.project_id) === String(projectId))
        : items;
      const sum = filtered.reduce(
        (acc, x) => ({
          d0_30: acc.d0_30 + Number(x.d0_30 || 0),
          d31_60: acc.d31_60 + Number(x.d31_60 || 0),
          d61_90: acc.d61_90 + Number(x.d61_90 || 0),
          d90p: acc.d90p + Number(x.d90p || 0),
        }),
        { d0_30: 0, d31_60: 0, d61_90: 0, d90p: 0 },
      );
      setAging(sum);
    } catch (e) {
      setAging(null);
    }
  }

  const handleBulkAssign = async (projectId: string) => {
    if (selectedRows.size === 0) return;

    setBulkAssigning(true);
    try {
      const assignments = Array.from(selectedRows).map(invoice_id => ({
        invoice_id,
        project_id: projectId
      }));

      const resp = await fetch('/api/ar-map/bulk_assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          assignments,
          create_rules: true,
          user_id: 'ui'
        })
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const result = await resp.json();

      // Refresh data and clear selection
      setSelectedRows(new Set());
      fetchRows();
      fetchAging();

      alert(`Asignadas ${result.assigned} facturas, creadas ${result.rules_created} reglas`);
    } catch (e: any) {
      alert(`Error en asignación masiva: ${e.message}`);
    } finally {
      setBulkAssigning(false);
    }
  };

  const handleRowSelect = (invoiceId: number, selected: boolean) => {
    const newSelection = new Set(selectedRows);
    if (selected) {
      newSelection.add(invoiceId);
    } else {
      newSelection.delete(invoiceId);
    }
    setSelectedRows(newSelection);
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      paid: { label: 'Pagada', class: 'bg-emerald-100 text-emerald-700' },
      pending: { label: 'Pendiente', class: 'bg-amber-100 text-amber-700' },
      overdue: { label: 'Vencida', class: 'bg-red-100 text-red-700' },
      partial: { label: 'Parcial', class: 'bg-blue-100 text-blue-700' },
    };
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    
    return (
      <span className={`text-xs px-2 py-1 rounded-full ${config.class}`}>
        {config.label}
      </span>
    );
  };

  useEffect(() => {
    fetchRows();
    fetchAging();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const unassignedRows = rows.filter(row => !row.project_id);
  const hasSelection = selectedRows.size > 0;

  return (
    <div className="p-4">
      <div className="flex items-start gap-4 mb-6">
        <div className="flex-1">
          <h1 className="text-2xl font-semibold mb-2">Facturas de Venta</h1>
          <div className="text-sm text-slate-600 dark:text-slate-300">
            Gestión inteligente de cuentas por cobrar con asignación automática de proyectos
          </div>
        </div>
        
        {/* AR Stats Widget */}
        <div className="w-80">
          <ArStatsWidget />
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3 items-end">
        <div className="flex flex-col">
          <label className="text-xs text-neutral-500 mb-1">Buscar</label>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="cliente o folio"
            className="border rounded px-3 py-2 w-48"
          />
        </div>
        
        <div className="flex flex-col">
          <label className="text-xs text-neutral-500 mb-1">Proyecto ID</label>
          <input
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            placeholder="2306"
            className="border rounded px-3 py-2 w-32"
          />
        </div>
        
        <div className="flex flex-col">
          <label className="text-xs text-neutral-500 mb-1">Estado</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border rounded px-3 py-2"
          >
            <option value="">Todos</option>
            <option value="pending">Pendiente</option>
            <option value="overdue">Vencida</option>
            <option value="partial">Parcial</option>
            <option value="paid">Pagada</option>
          </select>
        </div>
        
        <div className="flex flex-col">
          <label className="text-xs text-neutral-500 mb-1">Desde</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="border rounded px-3 py-2"
          />
        </div>
        
        <div className="flex flex-col">
          <label className="text-xs text-neutral-500 mb-1">Hasta</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="border rounded px-3 py-2"
          />
        </div>
        
        <button
          onClick={() => {
            fetchRows();
            fetchAging();
          }}
          className="px-4 py-2 rounded bg-slate-900 text-white hover:bg-slate-700 transition-colors"
          disabled={loading}
        >
          {loading ? 'Cargando…' : 'Aplicar'}
        </button>
        
        {/* Aging Summary */}
        {aging && (
          <div className="ml-auto flex gap-2 text-xs">
            <span className="px-3 py-2 rounded bg-emerald-50 text-emerald-700">
              0-30: {formatCurrency(aging.d0_30)}
            </span>
            <span className="px-3 py-2 rounded bg-amber-50 text-amber-700">
              31-60: {formatCurrency(aging.d31_60)}
            </span>
            <span className="px-3 py-2 rounded bg-orange-50 text-orange-700">
              61-90: {formatCurrency(aging.d61_90)}
            </span>
            <span className="px-3 py-2 rounded bg-rose-50 text-rose-700">
              90+: {formatCurrency(aging.d90p)}
            </span>
          </div>
        )}
      </div>

      {/* Bulk Actions */}
      {hasSelection && (
        <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="text-sm text-blue-700 dark:text-blue-300">
              {selectedRows.size} facturas seleccionadas
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="ID del proyecto"
                className="text-sm border rounded px-2 py-1 w-32"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                    handleBulkAssign(e.currentTarget.value.trim());
                  }
                }}
              />
              <button
                onClick={() => setSelectedRows(new Set())}
                className="text-xs px-3 py-1 border rounded hover:bg-slate-50"
                disabled={bulkAssigning}
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="rounded-2xl border overflow-auto bg-white dark:bg-slate-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-neutral-500">
              <th className="p-3">
                <input
                  type="checkbox"
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedRows(new Set(unassignedRows.map(r => r.invoice_id)));
                    } else {
                      setSelectedRows(new Set());
                    }
                  }}
                  checked={unassignedRows.length > 0 && selectedRows.size === unassignedRows.length}
                  className="rounded"
                />
              </th>
              <th className="p-3">Folio</th>
              <th className="p-3">Cliente</th>
              <th className="p-3">Fecha</th>
              <th className="p-3">Estado</th>
              <th className="p-3">Total</th>
              <th className="p-3">Proyecto</th>
              <th className="p-3">Cobrado</th>
              <th className="p-3">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => {
              const outstanding = Number(x.total_amount || 0) - Number(x.paid_amount || 0);
              const canSelect = !x.project_id;
              
              return (
                <tr key={`${x.invoice_id}-${x.invoice_number}`} className="border-t hover:bg-slate-50 dark:hover:bg-slate-700/50">
                  <td className="p-3">
                    {canSelect && (
                      <input
                        type="checkbox"
                        checked={selectedRows.has(x.invoice_id)}
                        onChange={(e) => handleRowSelect(x.invoice_id, e.target.checked)}
                        className="rounded"
                      />
                    )}
                  </td>
                  <td className="p-3 font-mono text-xs">{x.invoice_number}</td>
                  <td className="p-3">
                    <div>
                      <div className="font-medium truncate max-w-48">{x.customer_name}</div>
                      <div className="text-xs text-slate-500 font-mono">{x.customer_rut}</div>
                    </div>
                  </td>
                  <td className="p-3">{x.issue_date}</td>
                  <td className="p-3">{getStatusBadge(x.status || 'pending')}</td>
                  <td className="p-3 font-mono">{formatCurrency(Number(x.total_amount || 0))}</td>
                  <td className="p-3">
                    {x.project_id ? (
                      <span className="text-blue-600 font-mono">{x.project_id}</span>
                    ) : (
                      <span className="text-amber-600 text-xs">(sin proyecto)</span>
                    )}
                  </td>
                  <td className="p-3 font-mono">{formatCurrency(Number(x.paid_amount || 0))}</td>
                  <td className="p-3">
                    {!x.project_id && (
                      <button 
                        className="text-xs px-3 py-1.5 border rounded hover:bg-slate-50" 
                        onClick={() => setSel(x)}
                      >
                        Asignar proyecto
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        
        {rows.length === 0 && !loading && (
          <div className="text-center py-12 text-slate-500">
            {search || projectId || dateFrom || dateTo || statusFilter
              ? 'No se encontraron facturas con los filtros aplicados'
              : 'No hay facturas disponibles'}
          </div>
        )}
      </div>
      
      {/* Assignment Drawer */}
      {sel && (
        <AssignProjectDrawer
          invoice={sel}
          onClose={() => {
            setSel(null);
            // Refresh list after assignment
            fetchRows();
            fetchAging();
          }}
        />
      )}
    </div>
  );
}
