'use client';

import { useEffect, useState } from 'react';
import {
  fetchPurchaseOrder,
  fetchPurchaseOrderLines,
  createPurchaseOrderLine,
  formatCurrency,
  formatDate,
} from '@/lib/api';
import DataTable from '@/components/ui/DataTable';
import Modal from '@/components/ui/Modal';
import { useParams } from 'next/navigation';

export default function OrdenCompraDetallePage() {
  const params = useParams() as { id: string };
  const [data, setData] = useState<Record<string, any> | null>(null);
  const [lines, setLines] = useState<any[]>([]);
  const [openAddLine, setOpenAddLine] = useState(false);
  const [lineForm, setLineForm] = useState({
    item_name: '',
    item_desc: '',
    quantity: '1',
    unit_price: '0',
    currency: 'CLP',
  });
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await fetchPurchaseOrder(params.id);
        setData(res);
        const lr = await fetchPurchaseOrderLines(params.id, {
          page: 1,
          page_size: 100,
          order_by: 'id',
          order_dir: 'DESC',
        });
        setLines(lr.items || []);
      } catch (e: any) {
        setError(e?.message || 'Error cargando detalle');
      } finally {
        setLoading(false);
      }
    }
    if (params?.id) load();
  }, [params?.id]);

  if (loading) return <div className="p-6">Cargando…</div>;
  if (error) return <div className="p-6 text-red-600">{error}</div>;
  if (!data) return <div className="p-6">Sin datos</div>;
  const linesTotal = lines.reduce(
    (s, l) => s + Number(l.line_total || Number(l.quantity || 0) * Number(l.unit_price || 0)),
    0,
  );
  const headerTotal = Number(data.total_amount || 0);
  const diff = Math.round((headerTotal - linesTotal) * 100) / 100;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
            Orden de Compra {data.po_number || data.id}
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            Fecha: {data.po_date ? formatDate(String(data.po_date)) : '-'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <h2 className="font-medium mb-3">Resumen</h2>
          <div className="space-y-1 text-sm">
            <div>
              <span className="text-slate-500">Proveedor:</span>{' '}
              {data.zoho_vendor_name || data.vendor_rut || '-'}
            </div>
            <div>
              <span className="text-slate-500">Proyecto:</span> {data.zoho_project_name || '-'}
            </div>
            <div>
              <span className="text-slate-500">Estado:</span> {data.status || '-'}
            </div>
            <div>
              <span className="text-slate-500">Moneda:</span> {data.currency || 'CLP'}
            </div>
            <div>
              <span className="text-slate-500">Monto (cabecera):</span>{' '}
              {formatCurrency(headerTotal)}
            </div>
            <div>
              <span className="text-slate-500">Monto (suma líneas):</span>{' '}
              {formatCurrency(linesTotal)}
            </div>
            <div>
              <span className="text-slate-500">Diferencia:</span> {formatCurrency(diff)}
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <h2 className="font-medium mb-3">Metadatos</h2>
          <div className="text-xs grid grid-cols-2 gap-2">
            {Object.entries(data).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4">
                <span className="text-slate-500">{k}</span>
                <span className="text-slate-800 dark:text-slate-200 break-all">{String(v)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Líneas */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-medium">Líneas</h2>
          <button
            onClick={() => setOpenAddLine(true)}
            className="px-3 py-2 rounded-lg bg-lime-600 text-white"
          >
            Agregar línea
          </button>
        </div>
        <DataTable
          columns={
            [
              { key: 'item_name', label: 'Item' },
              { key: 'item_desc', label: 'Descripción' },
              { key: 'quantity', label: 'Cant.' },
              {
                key: 'unit_price',
                label: 'Precio',
                render: (v: number) => formatCurrency(Number(v || 0)),
              },
              {
                key: 'line_total',
                label: 'Total',
                render: (v: number) => formatCurrency(Number(v || 0)),
              },
              { key: 'currency', label: 'Moneda' },
              { key: 'status', label: 'Estado' },
            ] as any
          }
          data={lines}
          emptyMessage="Sin líneas"
        />
      </div>

      {/* Modal agregar línea */}
      <Modal
        isOpen={openAddLine}
        onClose={() => setOpenAddLine(false)}
        title="Agregar línea"
        size="lg"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Item</label>
            <input
              value={lineForm.item_name}
              onChange={(e) => setLineForm({ ...lineForm, item_name: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
              Descripción
            </label>
            <input
              value={lineForm.item_desc}
              onChange={(e) => setLineForm({ ...lineForm, item_desc: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
              Cantidad
            </label>
            <input
              value={lineForm.quantity}
              onChange={(e) => setLineForm({ ...lineForm, quantity: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
              Precio Unitario
            </label>
            <input
              value={lineForm.unit_price}
              onChange={(e) => setLineForm({ ...lineForm, unit_price: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Moneda</label>
            <select
              value={lineForm.currency}
              onChange={(e) => setLineForm({ ...lineForm, currency: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700"
            >
              <option value="CLP">CLP</option>
              <option value="USD">USD</option>
              <option value="UF">UF</option>
            </select>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={() => setOpenAddLine(false)}
            className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-lg"
          >
            Cancelar
          </button>
          <button
            onClick={async () => {
              try {
                setCreating(true);
                await createPurchaseOrderLine(params.id, {
                  item_name: lineForm.item_name.trim() || undefined,
                  item_desc: lineForm.item_desc.trim() || undefined,
                  quantity: Number(lineForm.quantity || 0),
                  unit_price: Number(lineForm.unit_price || 0),
                  currency: lineForm.currency,
                });
                setOpenAddLine(false);
                setLineForm({
                  item_name: '',
                  item_desc: '',
                  quantity: '1',
                  unit_price: '0',
                  currency: 'CLP',
                });
                const lr = await fetchPurchaseOrderLines(params.id, {
                  page: 1,
                  page_size: 100,
                  order_by: 'id',
                  order_dir: 'DESC',
                });
                setLines(lr.items || []);
              } catch (e: any) {
                alert(e?.message || 'Error agregando línea');
              } finally {
                setCreating(false);
              }
            }}
            disabled={creating}
            className="px-4 py-2 bg-lime-600 text-white rounded-lg"
          >
            {creating ? 'Agregando…' : 'Agregar'}
          </button>
        </div>
      </Modal>
    </div>
  );
}
