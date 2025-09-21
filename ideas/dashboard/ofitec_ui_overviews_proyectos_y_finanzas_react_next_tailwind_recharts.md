# OFITEC — UI Overviews (Proyectos y Finanzas)
> Componentes y páginas para aterrizar **/proyectos/overview** y **/finanzas/overview** con KPIs accionables. Sin emojis, accesible, minimal y productivo. Listo para pegar en Ofitec (Next.js + Tailwind). Usa `recharts` para mini‑gráficos y `lucide-react` opcional en iconos.

---

## 0) Instalación (si hace falta)
```bash
npm i recharts lucide-react
```

---

## 1) Componentes base
### 1.1 `components/ui/KpiCard.tsx`
```tsx
import { ReactNode } from 'react';

export default function KpiCard({ title, subtitle, value, footer, children }:{
  title: string;
  subtitle?: string;
  value?: ReactNode;
  footer?: ReactNode;
  children?: ReactNode;
}){
  return (
    <section className="rounded-2xl border bg-white p-4 shadow-sm" aria-label={title}>
      <header className="flex items-baseline justify-between">
        <h3 className="text-sm font-medium text-neutral-600">{title}</h3>
        {subtitle && <span className="text-xs text-neutral-400">{subtitle}</span>}
      </header>
      {value && <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>}
      {children && <div className="mt-3">{children}</div>}
      {footer && <footer className="mt-3 text-xs text-neutral-500">{footer}</footer>}
    </section>
  );
}
```

### 1.2 `components/ui/Sparkline.tsx`
```tsx
'use client';
import { Line, LineChart, ResponsiveContainer, Tooltip, YAxis } from 'recharts';

export default function Sparkline({ data }:{ data: number[] }){
  const ds = (data||[]).map((y,i)=>({ i, y }));
  return (
    <div className="h-12">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={ds} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
          <YAxis hide domain={['auto','auto']} />
          <Tooltip formatter={(v)=>Number(v).toLocaleString()} labelFormatter={()=>''} />
          <Line type="monotone" dataKey="y" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### 1.3 `components/ui/StackedBar.tsx`
```tsx
'use client';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export default function StackedBar({ data }:{ data: Array<Record<string, number|string>> }){
  // data ej.: [{ name:'Costos', PO: 5040, GRN: 900, AP: 600, Pagado: 420 }]
  const keys = Object.keys(data?.[0]||{}).filter(k=>k!=='name');
  return (
    <div className="h-28">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip formatter={(v)=>Number(v).toLocaleString()} />
          <Legend />
          {keys.map((k)=>(<Bar key={k} dataKey={k} stackId="a" />))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### 1.4 `components/ui/ActionsList.tsx`
```tsx
import Link from 'next/link';

export default function ActionsList({ items }:{ items: { title:string; cta:string }[] }){
  if(!items?.length) return <div className="text-sm text-neutral-500">Sin acciones sugeridas.</div>;
  return (
    <ul className="divide-y rounded-2xl border bg-white">
      {items.map((a,i)=> (
        <li key={i} className="p-3 flex items-center justify-between">
          <span className="text-sm">{a.title}</span>
          <Link className="text-sm px-3 py-1 border rounded hover:bg-neutral-50" href={a.cta}>Abrir</Link>
        </li>
      ))}
    </ul>
  );
}
```

---

## 2) **/proyectos/overview**
### 2.1 `app/proyectos/overview/page.tsx`
```tsx
'use client';
import { useEffect, useState } from 'react';
import KpiCard from '@/components/ui/KpiCard';
import Sparkline from '@/components/ui/Sparkline';
import StackedBar from '@/components/ui/StackedBar';
import ActionsList from '@/components/ui/ActionsList';

export default function ProjectsOverview(){
  const [data, setData] = useState<any|null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(()=>{(async()=>{
    try{
      const r = await fetch('http://localhost:5555/api/projects/overview', { cache: 'no-store' });
      const j = await r.json(); setData(j);
    } finally { setLoading(false); }
  })();},[]);

  if(loading) return <div className="p-6">Cargando…</div>;
  if(!data) return <div className="p-6">Sin datos.</div>;

  const pf = data.portfolio||{}; const salud = data.salud||{}; const wip = data.wip||{};

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">Gestión de Proyectos — Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <KpiCard title="Proyectos activos" value={pf.activos} />
        <KpiCard title="PC vs PO" value={<span>${((pf.pc_total||0)).toLocaleString()} • PO ${((pf.po||0)).toLocaleString()}</span>} footer={`Disponible ${(pf.disponible||0).toLocaleString()}`}>
          <StackedBar data={[{ name:'Costos', PO: Math.round((pf.po||0)/1e6), GRN: Math.round((pf.ejecucion?.grn||0)/1e6), AP: Math.round((pf.ejecucion?.ap||0)/1e6), Pagado: Math.round((pf.ejecucion?.pagado||0)/1e6)}]} />
        </KpiCard>
        <KpiCard title="Salud del Portafolio" value={<span>En presupuesto {salud.on_budget||0} / Sobre {salud.over_budget||0}</span>} footer={`Sin presupuesto ${salud.without_pc||0}`} />
        <KpiCard title="Riesgo" value={salud.riesgo?.score ?? 0} footer={(salud.riesgo?.reasons||[]).slice(0,2).join(' • ')}>
          <Sparkline data={[22,24,27,23,31,36,salud.riesgo?.score||0]} />
        </KpiCard>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <KpiCard title="Embudo de costos" subtitle="PO→GRN→AP→Pagado">
          <StackedBar data={[{ name:'Ejecución', PO: Math.round((pf.po||0)/1e6), GRN: Math.round((pf.ejecucion?.grn||0)/1e6), AP: Math.round((pf.ejecucion?.ap||0)/1e6), Pagado: Math.round((pf.ejecucion?.pagado||0)/1e6)}]} />
        </KpiCard>
        <KpiCard title="WIP EP" subtitle="Estados de Pago">
          <div className="text-sm">Aprobados sin FV: <b>{wip.ep_aprobados_sin_fv||0}</b></div>
          <div className="text-sm">En revisión: <b>{wip.ep_en_revision||0}</b></div>
        </KpiCard>
        <KpiCard title="Acciones sugeridas">
          <ActionsList items={data.acciones||[]} />
        </KpiCard>
      </div>
    </div>
  );
}
```

---

## 3) **/finanzas/overview**
### 3.1 `app/finanzas/overview/page.tsx`
```tsx
'use client';
import { useEffect, useState } from 'react';
import KpiCard from '@/components/ui/KpiCard';
import Sparkline from '@/components/ui/Sparkline';
import StackedBar from '@/components/ui/StackedBar';
import ActionsList from '@/components/ui/ActionsList';

export default function FinanceOverview(){
  const [data, setData] = useState<any|null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(()=>{(async()=>{
    try{
      const r = await fetch('http://localhost:5555/api/finance/overview', { cache: 'no-store' });
      const j = await r.json(); setData(j);
    } finally { setLoading(false); }
  })();},[]);

  if(loading) return <div className="p-6">Cargando…</div>;
  if(!data) return <div className="p-6">Sin datos.</div>;

  const cash = data.cash||{}; const revenue = data.revenue||{}; const ar = data.ar||{}; const ap = data.ap||{}; const conc = data.conciliacion||{};

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">Finanzas — Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <KpiCard title="Caja" subtitle="30/60/90 días" value={`$${Number(cash.today||0).toLocaleString()}`} footer={`D7 ${cash.d7 ?? '-'} • D30 ${cash.d30 ?? '-'}`}>
          <Sparkline data={[cash.today||0, cash.d7||0, cash.d30||0, cash.d60||0, cash.d90||0]} />
        </KpiCard>
        <KpiCard title="Ingresos vs Plan" value={`$${Number(revenue?.month?.real||0).toLocaleString()}`} footer={`YTD $${Number(revenue?.ytd?.real||0).toLocaleString()}`}>
          <Sparkline data={revenue?.spark || []} />
        </KpiCard>
        <KpiCard title="AR Aging" subtitle="1-30 / 31-60 / >60">
          <StackedBar data={[{ name:'AR', '1-30': Math.round((ar.d1_30||0)/1e6), '31-60': Math.round((ar.d31_60||0)/1e6), '>60': Math.round((ar.d60_plus||0)/1e6) }]} />
        </KpiCard>
        <KpiCard title="Conciliación" value={`${Math.round(conc.porc_conciliado||0)}%`} footer={`Auto-match ${Math.round(conc.auto_match||0)}%`} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <KpiCard title="Top deudores">
          <ActionsList items={(ar.top_clientes||[]).map((c:any)=>({ title: `${c.nombre} • $${Number(c.pendiente).toLocaleString()}`, cta:`/cobranzas?cliente=${encodeURIComponent(c.nombre)}` }))} />
        </KpiCard>
        <KpiCard title="Próximos pagos">
          <ActionsList items={(ap.top_proveedores||[]).map((p:any)=>({ title: `${p.nombre} • $${Number(p.por_pagar).toLocaleString()}`, cta:`/pagos?proveedor=${encodeURIComponent(p.nombre)}` }))} />
        </KpiCard>
      </div>

      <KpiCard title="Excepciones & Acciones">
        <ActionsList items={data.acciones||[]} />
      </KpiCard>
    </div>
  );
}
```

---

## 4) Contratos esperados por estos UIs
- `/api/projects/overview` con `{ portfolio, salud, wip, acciones }` (como en la especificación).
- `/api/finance/overview` con `{ cash, revenue, margin, ar, ap, conciliacion, acciones }`.

> Si aún no existen, puedes usar payloads “stub” desde `data/ceo_overview.json` para probar layout y luego conectar.

---

## 5) Accesibilidad y estilo
- Sin emojis; usa texto claro y **chips**/bordes para estados.
- **Tabular-nums** en cifras; tooltips de Recharts ayudan a lectura precisa.
- Componentes atómicos reutilizables (KpiCard/Sparkline/StackedBar/ActionsList) evitan duplicación.

---

## 6) QA
- Renderiza sin errores cuando el endpoint devuelve `null` o campos faltantes (defensive UI).
- Revisa contraste AA y navegación con teclado.
- Verifica que todos los botones **abren CTAs existentes** (no placeholders en producción).

---

### Cierre
Con estos archivos puedes activar las landings de **Proyectos** y **Finanzas** centradas en KPI, coherentes con el **CEO Dashboard** y el resto de *docs_oficiales*. Solo conecta los endpoints y empieza a iterar sobre datos reales.

