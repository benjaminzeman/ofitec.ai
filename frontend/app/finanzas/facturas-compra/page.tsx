'use client';

import { useEffect, useMemo, useState } from 'react';
import DataTable from '@/components/ui/DataTable';
import ConciliarButton from '@/components/ConciliarButton';
import APMatchButton from '@/components/APMatchButton';
import {
  fetchInvoicesCompra,
  fetchReconcileLinks,
  formatCurrency,
  formatDate,
  formatRUT,
} from '@/lib/api';

interface CompraRow {
  documento_numero: string;
  fecha: string;
  proveedor_rut: string;
  proveedor_nombre: string;
  monto_total: number;
  moneda: string;
  estado: string;
  fuente: string;
}

interface PagedResponse<T> {
  items: T[];
  meta: { total: number; page: number; page_size: number; pages: number };
}

export default function FacturasCompraPage() {
  const [data, setData] = useState<CompraRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [linksByKey, setLinksByKey] = useState<
    Record<
      string,
      {
        loading: boolean;
        items: Array<{ id: number; amount: number; type: string; ref: string; fecha: string }>;
        error?: string;
      }
    >
  >({});

  // Drawer handled by ConciliarButton

  // Filters
  const [search, setSearch] = useState('');
  const [rut, setRut] = useState('');
  const [moneda, setMoneda] = useState('');
  const [estado, setEstado] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Sorting
  const [sortKey, setSortKey] = useState<
    'fecha' | 'monto_total' | 'proveedor_nombre' | 'proveedor_rut' | 'documento_numero'
  >('fecha');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const columns = useMemo(
    () => [
      {
        key: 'expand',
        label: '',
        width: '40px',
        render: (_: any, row: CompraRow) => (
          <button
            className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
            title="Ver enlaces de conciliación"
            onClick={(e) => {
              e.stopPropagation();
              const key = `${row.documento_numero}|${row.fecha}`;
              const newKey = expandedKey === key ? null : key;
              setExpandedKey(newKey);
              if (newKey && !linksByKey[newKey]) {
                setLinksByKey((prev) => ({ ...prev, [newKey]: { loading: true, items: [] } }));
                fetchReconcileLinks({
                  purchase_doc: row.documento_numero,
                  purchase_date: row.fecha,
                })
                  .then((res) =>
                    setLinksByKey((prev) => ({
                      ...prev,
                      [newKey]: { loading: false, items: res.items || [] },
                    })),
                  )
                  .catch((err) =>
                    setLinksByKey((prev) => ({
                      ...prev,
                      [newKey]: {
                        loading: false,
                        items: [],
                        error: err?.message || 'Error cargando enlaces',
                      },
                    })),
                  );
              }
            }}
          >
            {expandedKey === `${row.documento_numero}|${row.fecha}` ? '▾' : '▸'}
          </button>
        ),
      },
      { key: 'documento_numero', label: 'Documento', sortable: true },
      { key: 'fecha', label: 'Fecha', sortable: true, render: (v: string) => formatDate(v) },
      {
        key: 'proveedor_rut',
        label: 'RUT Proveedor',
        sortable: true,
        render: (v: string) => formatRUT(v),
      },
      { key: 'proveedor_nombre', label: 'Proveedor', sortable: true },
      {
        key: 'monto_total',
        label: 'Monto',
        sortable: true,
        render: (v: number) => formatCurrency(v || 0),
      },
      { key: 'moneda', label: 'Moneda' },
      { key: 'estado', label: 'Estado' },
      { key: 'fuente', label: 'Fuente' },
      {
        key: 'acciones',
        label: 'Acciones',
        render: (_: any, row: CompraRow) => (
          <div className="flex gap-2">
            <ConciliarButton
              sourceType="purchase"
              getSource={() => ({
                amount: row.monto_total,
                date: row.fecha,
                ref: row.documento_numero,
                currency: row.moneda,
              })}
            />
            <APMatchButton
              invoice={{
                id: row.documento_numero,
                amount: row.monto_total,
                date: row.fecha,
                vendor_rut: row.proveedor_rut,
              }}
            />
          </div>
        ),
      },
    ],
    [expandedKey, linksByKey],
  );

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const res: PagedResponse<CompraRow> = await fetchInvoicesCompra({
        page,
        page_size: pageSize,
        order_by: sortKey,
        order_dir: sortDir.toUpperCase(),
        search,
        rut,
        moneda,
        estado,
        date_from: dateFrom,
        date_to: dateTo,
      } as any);
      setData(res.items || []);
      setTotal(res.meta?.total || 0);
      setPages(res.meta?.pages || 1);
    } catch (e: any) {
      setError(e?.message || 'Error cargando facturas de compra');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, sortKey, sortDir]);

  const onSort = (key: string, direction: 'asc' | 'desc') => {
    if (
      ['fecha', 'monto_total', 'proveedor_nombre', 'proveedor_rut', 'documento_numero'].includes(
        key,
      )
    ) {
      setSortKey(key as any);
      setSortDir(direction);
    }
  };

  const applyFilters = () => {
    setPage(1);
    load();
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
          Facturas de Compra
        </h1>
        <p className="text-slate-500 dark:text-slate-400">Fuente canónica: v_facturas_compra</p>
      </div>

      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar (doc o proveedor)"
            className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
          />
          <input
            value={rut}
            onChange={(e) => setRut(e.target.value)}
            placeholder="RUT"
            className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
          />
          <select
            value={moneda}
            onChange={(e) => setMoneda(e.target.value)}
            className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
          >
            <option value="">Moneda</option>
            <option value="CLP">CLP</option>
            <option value="USD">USD</option>
            <option value="UF">UF</option>
          </select>
          <select
            value={estado}
            onChange={(e) => setEstado(e.target.value)}
            className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
          >
            <option value="">Estado</option>
            <option value="emitida">Emitida</option>
            <option value="pagada">Pagada</option>
            <option value="anulada">Anulada</option>
          </select>
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
        </div>
        <div className="mt-3 flex gap-2">
          <button onClick={applyFilters} className="px-4 py-2 bg-lime-600 text-white rounded-lg">
            Aplicar filtros
          </button>
          <button
            onClick={() => {
              setSearch('');
              setRut('');
              setMoneda('');
              setEstado('');
              setDateFrom('');
              setDateTo('');
              setPage(1);
              load();
            }}
            className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-lg"
          >
            Limpiar
          </button>
        </div>
      </div>

      <DataTable
        columns={columns as any}
        data={data}
        onSort={onSort}
        sortKey={sortKey}
        sortDirection={sortDir}
        loading={loading}
        emptyMessage="Sin facturas de compra"
        isRowExpanded={(row: CompraRow) => expandedKey === `${row.documento_numero}|${row.fecha}`}
        renderExpandedRow={(row: CompraRow) => {
          const key = `${row.documento_numero}|${row.fecha}`;
          const entry = linksByKey[key];
          if (!entry) return <div className="text-slate-500">Cargando…</div>;
          if (entry.loading) return <div className="text-slate-500">Cargando…</div>;
          if (entry.error) return <div className="text-red-600">{entry.error}</div>;
          if (!entry.items?.length)
            return (
              <div className="text-slate-500">Sin enlaces de conciliación para esta factura.</div>
            );
          return (
            <div className="space-y-2">
              <div className="text-xs text-slate-500">
                Enlaces de conciliación ({entry.items.length})
              </div>
              <ul className="space-y-1">
                {entry.items.map((it, i) => (
                  <li key={i} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs ${it.type === 'bank' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200' : it.type === 'sales' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200' : 'bg-slate-100 text-slate-700 dark:bg-slate-900/40 dark:text-slate-200'}`}
                      >
                        {it.type}
                      </span>
                      <span className="text-slate-700 dark:text-slate-200">{it.ref || 's/n'}</span>
                      <span className="text-slate-500">· {formatDate(it.fecha)}</span>
                    </div>
                    <div className="font-medium">{formatCurrency(it.amount || 0)}</div>
                  </li>
                ))}
              </ul>
            </div>
          );
        }}
      />

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
    </div>
  );
}
