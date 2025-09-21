'use client';

import { useCallback, useEffect, useState } from 'react';
import DataTable from '@/components/ui/DataTable';
import { fetchReporteProyectos } from '@/lib/api';

export default function ReportesProyectosPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [searchDraft, setSearchDraft] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const payload = await fetchReporteProyectos({ page, page_size: pageSize, search });
      setItems(payload.items || []);
    } catch (e: any) {
      setError(e?.message || 'Error');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
            Reporte de Proyectos
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            Resumen de órdenes, proveedores y montos
          </p>
        </div>
        <div className="flex gap-2">
          <input
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            placeholder="Buscar proyecto"
            className="px-3 py-2 rounded-lg border bg-white dark:bg-slate-900"
          />
          <button
            onClick={() => {
              setPage(1);
              setSearch(searchDraft);
            }}
            className="px-3 py-2 bg-lime-600 text-white rounded-lg"
          >
            Buscar
          </button>
        </div>
      </div>
      <DataTable
        columns={
          [
            { key: 'project_id', label: 'ID' },
            { key: 'proyecto', label: 'Proyecto' },
            { key: 'total_ordenes', label: 'Órdenes' },
            { key: 'proveedores_unicos', label: 'Proveedores' },
            {
              key: 'monto_total',
              label: 'Monto',
              render: (v: number) =>
                new Intl.NumberFormat('es-CL', {
                  style: 'currency',
                  currency: 'CLP',
                  minimumFractionDigits: 0,
                }).format(Number(v || 0)),
            },
            { key: 'fecha_min', label: 'Inicio' },
            { key: 'fecha_max', label: 'Fin' },
          ] as any
        }
        data={items}
        loading={loading}
        emptyMessage="Sin proyectos"
      />
      <div className="flex items-center justify-between text-sm">
        <button
          disabled={page <= 1}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          className={`px-3 py-1 rounded border ${page <= 1 ? 'opacity-50' : ''}`}
        >
          Anterior
        </button>
        <div> Página {page} </div>
        <button onClick={() => setPage((p) => p + 1)} className="px-3 py-1 rounded border">
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
  );
}
