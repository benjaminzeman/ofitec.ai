'use client';

import { useEffect, useMemo, useState } from 'react';
import DataTable from '@/components/ui/DataTable';
import Modal from '@/components/ui/Modal';
import Link from 'next/link';
import {
  fetchPurchaseOrders,
  createPurchaseOrder,
  formatCurrency,
  formatDate,
  formatRUT,
  PagedResponse,
  PurchaseOrderListItem,
} from '@/lib/api';

export default function OrdenesCompraPage() {
  const [data, setData] = useState<PurchaseOrderListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [vendorRut, setVendorRut] = useState('');
  const [project, setProject] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Sorting
  const [sortKey, setSortKey] = useState<'po_date' | 'total_amount' | 'po_number' | 'id'>(
    'po_date',
  );
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  // Create modal
  const [openCreate, setOpenCreate] = useState(false);
  const [form, setForm] = useState({
    vendor_rut: '',
    zoho_vendor_name: '',
    zoho_project_name: '',
    zoho_project_id: '',
    zoho_po_id: '',
    po_number: '',
    po_date: '',
    total_amount: '',
    currency: 'CLP',
    status: 'draft',
  });
  const [creating, setCreating] = useState(false);

  const columns = useMemo(
    () => [
      {
        key: 'po_number',
        label: 'OC',
        sortable: true,
        render: (v: string, row: any) => (
          <Link
            href={`/finanzas/ordenes-compra/${row.id}`}
            className="text-lime-700 dark:text-lime-400 hover:underline"
          >
            {v}
          </Link>
        ),
      },
      { key: 'po_date', label: 'Fecha', sortable: true, render: (v: string) => formatDate(v) },
      {
        key: 'total_amount',
        label: 'Monto',
        sortable: true,
        render: (v: number) => formatCurrency(v || 0),
      },
      { key: 'zoho_project_name', label: 'Proyecto' },
      { key: 'zoho_vendor_name', label: 'Proveedor' },
    ],
    [],
  );

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const res: PagedResponse<PurchaseOrderListItem> = await fetchPurchaseOrders({
        page,
        page_size: pageSize,
        order_by: sortKey,
        order_dir: sortDir.toUpperCase(),
        search,
        vendor_rut: vendorRut,
        project,
        date_from: dateFrom,
        date_to: dateTo,
      });
      setData(res.items || []);
      setTotal(res.meta?.total || 0);
      setPages(res.meta?.pages || 1);
    } catch (e: any) {
      setError(e?.message || 'Error cargando Órdenes de Compra');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, sortKey, sortDir]);

  const onSort = (key: string, direction: 'asc' | 'desc') => {
    if (['po_date', 'total_amount', 'po_number', 'id'].includes(key)) {
      setSortKey(key as any);
      setSortDir(direction);
    }
  };

  const applyFilters = () => {
    setPage(1);
    load();
  };

  const submitCreate = async () => {
    try {
      setCreating(true);
      const payload = {
        vendor_rut: form.vendor_rut.trim(),
        zoho_vendor_name: form.zoho_vendor_name.trim() || undefined,
        zoho_project_name: form.zoho_project_name.trim() || undefined,
        zoho_project_id: form.zoho_project_id.trim() || undefined,
        zoho_po_id: form.zoho_po_id.trim() || undefined,
        po_number: form.po_number.trim(),
        po_date: form.po_date,
        total_amount: Number(form.total_amount || 0),
        currency: form.currency,
        status: form.status,
      };
      await createPurchaseOrder(payload as any);
      setOpenCreate(false);
      setForm({
        vendor_rut: '',
        zoho_vendor_name: '',
        zoho_project_name: '',
        zoho_project_id: '',
        zoho_po_id: '',
        po_number: '',
        po_date: '',
        total_amount: '',
        currency: 'CLP',
        status: 'draft',
      });
      setPage(1);
      load();
    } catch (e: any) {
      alert(e?.message || 'Error creando OC');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
            Órdenes de Compra
          </h1>
          <p className="text-slate-500 dark:text-slate-400">Fuente: purchase_orders_unified</p>
        </div>
        <button
          onClick={() => setOpenCreate(true)}
          className="px-4 py-2 bg-lime-600 text-white rounded-lg"
        >
          Nueva Orden
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar (OC o proveedor)"
            className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
          />
          <input
            value={vendorRut}
            onChange={(e) => setVendorRut(e.target.value)}
            placeholder="RUT Proveedor"
            className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
          />
          <input
            value={project}
            onChange={(e) => setProject(e.target.value)}
            placeholder="Proyecto"
            className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
          />
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
          />
          <button
            onClick={applyFilters}
            className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-lg"
          >
            Aplicar
          </button>
        </div>
      </div>

      {/* Table */}
      <DataTable
        columns={columns as any}
        data={data}
        onSort={onSort}
        sortKey={sortKey}
        sortDirection={sortDir}
        loading={loading}
        emptyMessage="Sin órdenes de compra"
      />

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-slate-600 dark:text-slate-400">
        <div>
          Total: {total.toLocaleString()} — Página {page} de {pages}
        </div>
        <div className="flex gap-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className={`px-3 py-1 rounded border ${page <= 1 ? 'opacity-50' : ''}`}
          >
            Anterior
          </button>
          <button
            disabled={page >= pages}
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            className={`px-3 py-1 rounded border ${page >= pages ? 'opacity-50' : ''}`}
          >
            Siguiente
          </button>
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(parseInt(e.target.value, 10));
              setPage(1);
            }}
            className="px-2 py-1 rounded border"
          >
            {[10, 20, 50, 100].map((n) => (
              <option key={n} value={n}>
                {n}/página
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Create Modal */}
      <Modal
        isOpen={openCreate}
        onClose={() => setOpenCreate(false)}
        title="Nueva Orden de Compra"
        size="lg"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
              RUT Proveedor
            </label>
            <input
              value={form.vendor_rut}
              onChange={(e) => setForm({ ...form, vendor_rut: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
              Nombre Proveedor
            </label>
            <input
              value={form.zoho_vendor_name}
              onChange={(e) => setForm({ ...form, zoho_vendor_name: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
              Proyecto
            </label>
            <input
              value={form.zoho_project_name}
              onChange={(e) => setForm({ ...form, zoho_project_name: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
              Project ID (opcional)
            </label>
            <input
              value={form.zoho_project_id}
              onChange={(e) => setForm({ ...form, zoho_project_id: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
              Número OC
            </label>
            <input
              value={form.po_number}
              onChange={(e) => setForm({ ...form, po_number: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
              Zoho PO ID (opcional)
            </label>
            <input
              value={form.zoho_po_id}
              onChange={(e) => setForm({ ...form, zoho_po_id: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Fecha</label>
            <input
              type="date"
              value={form.po_date}
              onChange={(e) => setForm({ ...form, po_date: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Monto</label>
            <input
              value={form.total_amount}
              onChange={(e) => setForm({ ...form, total_amount: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Moneda</label>
            <select
              value={form.currency}
              onChange={(e) => setForm({ ...form, currency: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            >
              <option value="CLP">CLP</option>
              <option value="USD">USD</option>
              <option value="UF">UF</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Estado</label>
            <select
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            >
              <option value="draft">Borrador</option>
              <option value="approved">Aprobada</option>
              <option value="cancelled">Anulada</option>
            </select>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={() => setOpenCreate(false)}
            className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-lg"
          >
            Cancelar
          </button>
          <button
            onClick={submitCreate}
            disabled={creating}
            className="px-4 py-2 bg-lime-600 text-white rounded-lg"
          >
            {creating ? 'Creando…' : 'Crear'}
          </button>
        </div>
      </Modal>
    </div>
  );
}
