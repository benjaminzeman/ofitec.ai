'use client';

import { useEffect, useMemo, useState } from 'react';
import DataTable from '@/components/ui/DataTable';
import ConciliarButton from '@/components/ConciliarButton';
import { fetchBankMovements, fetchReconcileLinks, formatCurrency, formatDate } from '@/lib/api';

interface CartolaRow {
  id?: number;
  fecha: string;
  banco: string;
  cuenta: string;
  glosa: string;
  monto: number;
  moneda: string;
  tipo: string;
  saldo: number;
  referencia: string;
  fuente: string;
  conciliado?: number;
  n_docs?: number;
  monto_conciliado?: number;
}

interface PagedResponse<T> {
  items: T[];
  meta: { total: number; page: number; page_size: number; pages: number };
}

export default function CartolaBancariaPage() {
  const [data, setData] = useState<CartolaRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [linksById, setLinksById] = useState<
    Record<
      number,
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
  const [soloPendientes, setSoloPendientes] = useState(false);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Sorting (safelist: fecha, monto, banco, cuenta, glosa)
  const [sortKey, setSortKey] = useState<'fecha' | 'monto' | 'banco' | 'cuenta' | 'glosa'>('fecha');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const columns = useMemo(
    () => [
      {
        key: 'expand',
        label: '',
        width: '40px',
        render: (_: any, row: CartolaRow) => (
          <button
            className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
            title="Ver enlaces de conciliación"
            onClick={(e) => {
              e.stopPropagation();
              if (!row.id) return;
              const newId = expandedId === row.id ? null : (row.id as number);
              setExpandedId(newId);
              if (newId && !linksById[newId]) {
                setLinksById((prev) => ({ ...prev, [newId]: { loading: true, items: [] } }));
                fetchReconcileLinks({ bank_id: newId })
                  .then((res) =>
                    setLinksById((prev) => ({
                      ...prev,
                      [newId]: { loading: false, items: res.items || [] },
                    })),
                  )
                  .catch((err) =>
                    setLinksById((prev) => ({
                      ...prev,
                      [newId]: {
                        loading: false,
                        items: [],
                        error: err?.message || 'Error cargando enlaces',
                      },
                    })),
                  );
              }
            }}
          >
            {expandedId === row.id ? '▾' : '▸'}
          </button>
        ),
      },
      { key: 'fecha', label: 'Fecha', sortable: true, render: (v: string) => formatDate(v) },
      { key: 'banco', label: 'Banco', sortable: true },
      { key: 'cuenta', label: 'Cuenta', sortable: true },
      { key: 'glosa', label: 'Glosa', sortable: true },
      {
        key: 'monto',
        label: 'Monto',
        sortable: true,
        render: (v: number) => formatCurrency(v || 0),
      },
      { key: 'moneda', label: 'Moneda' },
      { key: 'tipo', label: 'Tipo' },
      {
        key: 'conciliado',
        label: 'Conciliación',
        render: (_: any, row: CartolaRow) => (
          <span
            className={`px-2 py-1 rounded-full text-xs ${row.conciliado ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-200'}`}
          >
            {row.conciliado ? 'Conciliado' : 'Pendiente'}
          </span>
        ),
      },
      { key: 'saldo', label: 'Saldo', render: (v: number) => formatCurrency(v || 0) },
      { key: 'referencia', label: 'Referencia' },
      {
        key: 'n_docs',
        label: 'Docs',
        render: (_: any, row: CartolaRow) =>
          row.conciliado ? (
            <span className="text-slate-600 dark:text-slate-300">
              {row.n_docs} doc(s) · {formatCurrency(row.monto_conciliado || 0)}
            </span>
          ) : (
            '-'
          ),
      },
      { key: 'fuente', label: 'Fuente' },
      {
        key: 'acciones',
        label: 'Acciones',
        render: (_: any, row: CartolaRow) => (
          <div onClick={(e) => e.stopPropagation()}>
            <ConciliarButton
              sourceType="bank"
              getSource={() => ({
                amount: row.monto,
                date: row.fecha,
                ref: row.referencia,
                currency: row.moneda,
              })}
            />
          </div>
        ),
      },
    ],
    [expandedId, linksById],
  );

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const res: PagedResponse<CartolaRow> = await fetchBankMovements({
        page,
        page_size: pageSize,
        order_by: sortKey,
        order_dir: (sortDir || 'desc').toUpperCase(),
        search,
        rut,
        moneda,
        estado: soloPendientes ? 'pendiente' : estado,
        date_from: dateFrom,
        date_to: dateTo,
      } as any);
      setData(res.items || []);
      setTotal(res.meta?.total || 0);
      setPages(res.meta?.pages || 1);
    } catch (e: any) {
      setError(e?.message || 'Error cargando cartola bancaria');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, sortKey, sortDir]);

  const onSort = (key: string, direction: 'asc' | 'desc') => {
    if (['fecha', 'monto', 'banco', 'cuenta', 'glosa'].includes(key)) {
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
          Cartola Bancaria
        </h1>
        <p className="text-slate-500 dark:text-slate-400">Fuente canónica: v_cartola_bancaria</p>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar (glosa o referencia)"
            className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
          />
          <input
            value={rut}
            onChange={(e) => setRut(e.target.value)}
            placeholder="RUT/Referencia"
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
            <option value="confirmado">Confirmado</option>
            <option value="pendiente">Pendiente</option>
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
          <label className="ml-2 inline-flex items-center gap-2 text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              checked={soloPendientes}
              onChange={(e) => {
                setSoloPendientes(e.target.checked);
                setPage(1);
                load();
              }}
            />
            Solo pendientes
          </label>
          <button
            onClick={() => {
              setSearch('');
              setRut('');
              setMoneda('');
              setEstado('');
              setSoloPendientes(false);
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

      {/* Table */}
      <DataTable
        columns={columns as any}
        data={data}
        onSort={onSort}
        sortKey={sortKey}
        sortDirection={sortDir}
        loading={loading}
        rowClassName={(row: CartolaRow) =>
          row.conciliado ? 'bg-emerald-50/40 dark:bg-emerald-900/10' : ''
        }
        emptyMessage="Sin movimientos"
        isRowExpanded={(row: CartolaRow) => !!row.id && expandedId === row.id}
        renderExpandedRow={(row: CartolaRow) => {
          const bankId = row.id as number;
          const entry = linksById[bankId];
          if (!entry) return <div className="text-slate-500">Cargando…</div>;
          if (entry.loading) return <div className="text-slate-500">Cargando…</div>;
          if (entry.error) return <div className="text-red-600">{entry.error}</div>;
          if (!entry.items?.length)
            return (
              <div className="text-slate-500">
                Sin enlaces de conciliación para este movimiento.
              </div>
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
                        className={`px-2 py-0.5 rounded-full text-xs ${it.type === 'sales' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200' : it.type === 'purchase' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-200' : 'bg-slate-100 text-slate-700 dark:bg-slate-900/40 dark:text-slate-200'}`}
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
    </div>
  );
}
