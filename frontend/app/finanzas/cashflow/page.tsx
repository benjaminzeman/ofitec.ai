'use client';

import { useCallback, useEffect, useState } from 'react';
import { fetchCashflowSemana } from '@/lib/api';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function CashflowPage() {
  const [items, setItems] = useState<any[]>([]);
  const [weeks, setWeeks] = useState(12);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (w: number) => {
    try {
      setLoading(true);
      const payload = await fetchCashflowSemana({ weeks: w });
      setItems(payload.items || []);
    } catch (e: any) {
      setError(e?.message || 'Error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(weeks);
  }, [load, weeks]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
            Cashflow Semanal
          </h1>
          <p className="text-slate-500 dark:text-slate-400">
            Serie por categoría (planned, purchase, invoice)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-600 dark:text-slate-400">Semanas</label>
          <select
            value={weeks}
            onChange={(e) => {
              const w = parseInt(e.target.value, 10);
              setWeeks(w);
              load(w);
            }}
            className="px-3 py-2 rounded-lg border bg-white dark:bg-slate-900"
          >
            {[6, 12, 24, 52].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 h-80">
        {loading ? (
          <div className="text-slate-500">Cargando…</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={items} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="income" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#84CC16" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#84CC16" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="expense" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EF4444" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="week" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Area
                type="monotone"
                dataKey="invoice"
                name="Ingresos"
                stroke="#84CC16"
                fillOpacity={1}
                fill="url(#income)"
              />
              <Area
                type="monotone"
                dataKey="purchase"
                name="Egresos"
                stroke="#EF4444"
                fillOpacity={1}
                fill="url(#expense)"
              />
              <Area type="monotone" dataKey="total" name="Total" stroke="#22d3ee" fillOpacity={0} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
