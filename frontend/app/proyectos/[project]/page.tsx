'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { KPICard, formatCLP } from '@/components/KPI';
import { BudgetTable } from '@/components/BudgetTable';
import { Waterfall } from '@/components/Waterfall';
import {
  getProjectSummary,
  getProjectBudget,
  getProjectPurchases,
  getProjectContract,
  saveProjectContract,
  getProjectPayments,
  addProjectPayment,
  getProjectExtras,
  addProjectExtra,
} from '@/lib/projectsApi';

// Use rest param to keep first argument type as 'any' for Next.js PageProps compatibility,
// and derive the project route param via useParams (client-side) instead of typed prop.
export default function Proyecto360Page(..._args: any[]) {
  const routeParams = useParams() as { project?: string };
  const projectKey = decodeURIComponent(routeParams.project || '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<any>(null);
  const [budget, setBudget] = useState<any>(null);
  const [purchases, setPurchases] = useState<any>({
    items: [],
    meta: { total: 0, page: 1, page_size: 10, pages: 1 },
  });
  const [contract, setContract] = useState<any>(null);
  const [payments, setPayments] = useState<{
    items: any[];
    totals: { net: number; gross: number };
  } | null>(null);
  const [extras, setExtras] = useState<{
    items: any[];
    totals: { net: number; gross: number };
  } | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const [s, b, po, co, pay, ex] = await Promise.all([
          getProjectSummary(projectKey),
          getProjectBudget(projectKey),
          getProjectPurchases(projectKey, { page: 1, page_size: 5 }),
          getProjectContract(projectKey),
          getProjectPayments(projectKey),
          getProjectExtras(projectKey),
        ]);
        if (!mounted) return;
        setSummary(s);
        setBudget(b);
        setPurchases(po);
        setContract(co);
        setPayments(pay);
        setExtras(ex);
      } catch (e: any) {
        console.error('Error cargando Proyecto 360:', e);
        setError('No se pudo cargar la información del proyecto');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, [projectKey]);

  const waterfall = useMemo(() => {
    if (!summary) return [];
    const sales = summary.sales_contracted || 0;
    const budgetCost = summary.budget_cost || 0;
    const committed = summary.committed || 0;
    const apInvoiced = summary.invoiced_ap || 0;
    const paid = summary.paid || 0;
    return [
      { label: 'Venta Contratada', amount: sales, color: 'bg-lime-600' },
      { label: 'Presupuesto (Costo)', amount: -budgetCost, color: 'bg-slate-500' },
      { label: 'Comprometido (OC)', amount: -committed, color: 'bg-amber-500' },
      { label: 'Facturado (AP)', amount: -apInvoiced, color: 'bg-orange-500' },
      { label: 'Pagado (AP)', amount: -paid, color: 'bg-red-500' },
    ];
  }, [summary]);

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse text-slate-500">Cargando proyecto...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 text-red-700 border border-red-200 rounded-xl p-4">{error}</div>
        <div className="mt-4">
          <Link href="/proyectos" className="text-lime-700 hover:underline">
            Volver a Proyectos
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Breadcrumbs */}
      <div className="text-sm text-slate-500">
        <Link href="/proyectos" className="text-lime-700">
          Proyectos
        </Link>
        <span> / </span>
        <span className="text-slate-700">{summary?.name || projectKey}</span>
      </div>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            {summary?.name || projectKey}
          </h1>
          <p className="text-slate-600 dark:text-slate-400">Módulo 360 del Proyecto</p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={`/proyectos/${encodeURIComponent(projectKey)}/control`}
            className="px-4 py-2 bg-white text-lime-700 border border-lime-300 rounded-xl hover:bg-lime-50"
          >
            Control Financiero
          </Link>
          <Link
            href={`/proyectos/${encodeURIComponent(projectKey)}/ep`}
            className="px-4 py-2 bg-white text-lime-700 border border-lime-300 rounded-xl hover:bg-lime-50"
          >
            Estados de Pago
          </Link>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard title="Venta Contratada" value={formatCLP(summary?.sales_contracted || 0)} />
        <KPICard
          title="Presupuesto (Costo)"
          value={formatCLP(summary?.budget_cost || 0)}
          accent="amber"
        />
        <KPICard
          title="Comprometido (OC)"
          value={formatCLP(summary?.committed || 0)}
          accent="amber"
        />
        <KPICard
          title="Facturado (AP)"
          value={formatCLP(summary?.invoiced_ap || 0)}
          accent="amber"
        />
      </div>

      {/* Waterfall */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">Flujo Económico del Proyecto</h2>
        <Waterfall steps={waterfall as any} />
      </div>

      {/* Contract + EP + Extras */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Contract editor */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 space-y-3">
          <h2 className="text-lg font-semibold">Contrato</h2>
          <div className="text-sm text-slate-500">
            Neto y bruto con IVA. Puedes ajustar el override local.
          </div>
          <form
            className="space-y-2"
            onSubmit={async (e) => {
              e.preventDefault();
              const form = e.target as HTMLFormElement;
              const net = Number(
                (form.elements.namedItem('contract_net') as HTMLInputElement).value || '',
              );
              const gross = Number(
                (form.elements.namedItem('contract_gross') as HTMLInputElement).value || '',
              );
              const iva = Number(
                (form.elements.namedItem('iva_rate') as HTMLInputElement).value || '0.19',
              );
              const ok = await saveProjectContract(projectKey, {
                contract_net: isNaN(net) ? undefined : net,
                contract_gross: isNaN(gross) ? undefined : gross,
                iva_rate: isNaN(iva) ? undefined : iva,
                source: 'ui',
              });
              if (ok) {
                const [s, co] = await Promise.all([
                  getProjectSummary(projectKey),
                  getProjectContract(projectKey),
                ]);
                setSummary(s);
                setContract(co);
              }
            }}
          >
            <div className="grid grid-cols-2 gap-2">
              <label className="text-sm">
                Neto
                <input
                  name="contract_net"
                  type="number"
                  step="1"
                  defaultValue={contract?.contract_net ?? summary?.contract_net ?? ''}
                  className="w-full mt-1 px-2 py-1 border rounded"
                />
              </label>
              <label className="text-sm">
                Bruto
                <input
                  name="contract_gross"
                  type="number"
                  step="1"
                  defaultValue={contract?.contract_gross ?? summary?.contract_gross ?? ''}
                  className="w-full mt-1 px-2 py-1 border rounded"
                />
              </label>
              <label className="text-sm col-span-2">
                IVA (%)
                <input
                  name="iva_rate"
                  type="number"
                  step="0.01"
                  defaultValue={contract?.iva_rate ?? 0.19}
                  className="w-full mt-1 px-2 py-1 border rounded"
                />
              </label>
            </div>
            <button type="submit" className="mt-2 px-3 py-2 bg-lime-600 text-white rounded-xl">
              Guardar Contrato
            </button>
          </form>
          <div className="text-sm text-slate-600">
            <div>
              Contrato Neto:{' '}
              <strong>{formatCLP(summary?.contract_net ?? summary?.sales_contracted ?? 0)}</strong>
            </div>
            <div>
              Contrato Bruto: <strong>{formatCLP(summary?.contract_gross ?? 0)}</strong>
            </div>
          </div>
        </div>

        {/* Estados de Pago */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 space-y-3">
          <h2 className="text-lg font-semibold">Estados de Pago</h2>
          <div className="text-sm text-slate-500">
            Agrega EP con monto neto. Se calcula el bruto con IVA.
          </div>
          <form
            className="space-y-2"
            onSubmit={async (e) => {
              e.preventDefault();
              const form = e.target as HTMLFormElement;
              const ep_number = (form.elements.namedItem('ep_number') as HTMLInputElement).value;
              const date = (form.elements.namedItem('ep_date') as HTMLInputElement).value;
              const net = Number(
                (form.elements.namedItem('ep_net') as HTMLInputElement).value || '',
              );
              const iva = Number(
                (form.elements.namedItem('ep_iva') as HTMLInputElement).value || '0.19',
              );
              const note = (form.elements.namedItem('ep_note') as HTMLInputElement).value;
              const ok = await addProjectPayment(projectKey, {
                ep_number,
                date,
                net_amount: net,
                iva_rate: iva,
                note,
              });
              if (ok) {
                const [pay, s] = await Promise.all([
                  getProjectPayments(projectKey),
                  getProjectSummary(projectKey),
                ]);
                setPayments(pay);
                setSummary(s);
                form.reset();
              }
            }}
          >
            <div className="grid grid-cols-2 gap-2">
              <input
                name="ep_number"
                placeholder="EP #"
                className="w-full px-2 py-1 border rounded"
              />
              <input name="ep_date" type="date" className="w-full px-2 py-1 border rounded" />
              <input
                name="ep_net"
                type="number"
                step="1"
                placeholder="Monto Neto"
                className="w-full px-2 py-1 border rounded col-span-2"
              />
              <input
                name="ep_iva"
                type="number"
                step="0.01"
                defaultValue={0.19}
                className="w-full px-2 py-1 border rounded col-span-2"
              />
              <input
                name="ep_note"
                placeholder="Nota"
                className="w-full px-2 py-1 border rounded col-span-2"
              />
            </div>
            <button type="submit" className="mt-2 px-3 py-2 bg-lime-600 text-white rounded-xl">
              Agregar EP
            </button>
          </form>
          <div className="text-sm text-slate-600">
            <div>
              Total EP Neto: <strong>{formatCLP(payments?.totals.net || 0)}</strong>
            </div>
            <div>
              Total EP Bruto: <strong>{formatCLP(payments?.totals.gross || 0)}</strong>
            </div>
            <div>
              % Cobrado vs Contrato+Extras: <strong>{summary?.billed_pct ?? 0}%</strong>
            </div>
          </div>
          <div className="max-h-48 overflow-auto border rounded">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="py-1 px-2">EP</th>
                  <th className="py-1 px-2">Fecha</th>
                  <th className="py-1 px-2 text-right">Neto</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(payments?.items || []).map((it: any) => (
                  <tr key={it.id}>
                    <td className="py-1 px-2">{it.ep_number || '-'}</td>
                    <td className="py-1 px-2">{it.date || '-'}</td>
                    <td className="py-1 px-2 text-right">{formatCLP(it.net_amount || 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Obras Adicionales */}
        <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 space-y-3">
          <h2 className="text-lg font-semibold">Obras Adicionales</h2>
          <form
            className="space-y-2"
            onSubmit={async (e) => {
              e.preventDefault();
              const form = e.target as HTMLFormElement;
              const name = (form.elements.namedItem('ex_name') as HTMLInputElement).value;
              const status = (form.elements.namedItem('ex_status') as HTMLInputElement).value;
              const net = Number(
                (form.elements.namedItem('ex_net') as HTMLInputElement).value || '',
              );
              const iva = Number(
                (form.elements.namedItem('ex_iva') as HTMLInputElement).value || '0.19',
              );
              const note = (form.elements.namedItem('ex_note') as HTMLInputElement).value;
              const ok = await addProjectExtra(projectKey, {
                name,
                status,
                net_amount: net,
                iva_rate: iva,
                note,
              });
              if (ok) {
                const [ex, s] = await Promise.all([
                  getProjectExtras(projectKey),
                  getProjectSummary(projectKey),
                ]);
                setExtras(ex);
                setSummary(s);
                form.reset();
              }
            }}
          >
            <div className="grid grid-cols-2 gap-2">
              <input
                name="ex_name"
                placeholder="Nombre"
                className="w-full px-2 py-1 border rounded col-span-2"
              />
              <input
                name="ex_status"
                placeholder="Estado"
                className="w-full px-2 py-1 border rounded col-span-2"
              />
              <input
                name="ex_net"
                type="number"
                step="1"
                placeholder="Monto Neto"
                className="w-full px-2 py-1 border rounded col-span-2"
              />
              <input
                name="ex_iva"
                type="number"
                step="0.01"
                defaultValue={0.19}
                className="w-full px-2 py-1 border rounded col-span-2"
              />
              <input
                name="ex_note"
                placeholder="Nota"
                className="w-full px-2 py-1 border rounded col-span-2"
              />
            </div>
            <button type="submit" className="mt-2 px-3 py-2 bg-lime-600 text-white rounded-xl">
              Agregar Obra Adicional
            </button>
          </form>
          <div className="text-sm text-slate-600">
            <div>
              Total Extras Neto: <strong>{formatCLP(extras?.totals.net || 0)}</strong>
            </div>
            <div>
              Total Extras Bruto: <strong>{formatCLP(extras?.totals.gross || 0)}</strong>
            </div>
          </div>
          <div className="max-h-48 overflow-auto border rounded">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="py-1 px-2">Nombre</th>
                  <th className="py-1 px-2">Estado</th>
                  <th className="py-1 px-2 text-right">Neto</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(extras?.items || []).map((it: any) => (
                  <tr key={it.id}>
                    <td className="py-1 px-2">{it.name || '-'}</td>
                    <td className="py-1 px-2">{it.status || '-'}</td>
                    <td className="py-1 px-2 text-right">{formatCLP(it.net_amount || 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Budget Summary */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold">Presupuesto</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <KPICard title="Presupuesto Total (PC)" value={formatCLP(budget?.pc_total || 0)} />
          <KPICard title="Comprometido" value={formatCLP(budget?.committed || 0)} accent="amber" />
          <KPICard
            title="Disponible Conservador"
            value={formatCLP(budget?.available_conservative || 0)}
            accent="green"
          />
        </div>
        <BudgetTable
          totals={{
            pc_total: budget?.pc_total || 0,
            committed: budget?.committed || 0,
            available_conservative: budget?.available_conservative || 0,
          }}
        />
      </div>

      {/* Purchases */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Órdenes de Compra Recientes</h2>
          <Link
            href={`/operaciones/ordenes?project=${encodeURIComponent(projectKey)}`}
            className="text-lime-700"
          >
            Ver todas
          </Link>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-slate-500">
                <th className="py-2">OC</th>
                <th className="py-2">Fecha</th>
                <th className="py-2">Proveedor</th>
                <th className="py-2 text-right">Monto</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {(purchases?.items || []).map((po: any) => (
                <tr key={po.id}>
                  <td className="py-2">{po.po_number}</td>
                  <td className="py-2">{po.po_date}</td>
                  <td className="py-2">{po.vendor_name || '-'}</td>
                  <td className="py-2 text-right">{formatCLP(po.total_amount || 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
