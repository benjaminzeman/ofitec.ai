// ofitec.ai - API Data Services
// Connects Next.js frontend to Flask backend with real data

// Prefer relative API path so rewrites work in Docker and dev; fall back to env when needed
const API_BASE_URL =
  typeof window !== 'undefined'
    ? '/api'
    : process.env.NEXT_PUBLIC_API_BASE ||
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5555'}/api`;

// Response types
export interface DashboardData {
  summary: {
    totalProjects: number;
    activeProjects: number;
    totalRevenue: number;
    totalExpenses: number;
    netProfit: number;
    profitMargin: number;
  };
  recentTransactions: Array<{
    id: string;
    description: string;
    amount: number;
    date: string;
    type: 'income' | 'expense';
    project?: string;
  }>;
  projectStatus: Array<{
    id: string;
    name: string;
    status: 'planning' | 'active' | 'completed' | 'on-hold';
    progress: number;
    budget: number;
    spent: number;
    risk: 'low' | 'medium' | 'high';
  }>;
  financialTrends: Array<{
    month: string;
    revenue: number;
    expenses: number;
    profit: number;
  }>;
}

export interface ProviderData {
  id: string;
  rut: string;
  name: string;
  category: string;
  status: 'active' | 'inactive' | 'blocked';
  rating: number;
  totalAmount: number;
  lastOrder: string;
  ordersCount: number;
  paymentTerms: string;
  contact: string;
  email: string;
}

export interface ProjectData {
  id: string;
  name: string;
  client: string;
  status: 'planning' | 'active' | 'completed' | 'on-hold';
  progress: number;
  startDate: string;
  endDate: string;
  budget: number;
  spent: number;
  remaining: number;
  risk: 'low' | 'medium' | 'high';
  manager: string;
  description: string;
  location: string;
  // Opcionales desde projects_v2
  orders?: number;
  providers?: number;
}

export interface FinancialData {
  summary: {
    totalRevenue: number;
    totalExpenses: number;
    netProfit: number;
    profitMargin: number;
    cashflow: number;
    pendingReceivables: number;
    pendingPayables: number;
  };
  bankAccounts: Array<{
    id: string;
    name: string;
    bank: string;
    balance: number;
    currency: string;
    lastUpdate: string;
  }>;
  movements: Array<{
    id: string;
    date: string;
    description: string;
    amount: number;
    type: 'credit' | 'debit';
    account: string;
    reference: string;
    category: string;
  }>;
  siiStatus: {
    lastSync: string;
    pendingInvoices: number;
    pendingBooks: number;
    status: 'synced' | 'pending' | 'error';
  };
}

// Overview payloads (ideas/dashboard alignment)
export interface ProjectsOverview {
  portfolio: {
    activos: number;
    pc_total: number;
    po: number;
    disponible: number;
    ejecucion: { grn: number; ap: number; pagado: number };
  };
  salud: {
    on_budget: number;
    over_budget: number;
    without_pc: number;
    tres_way: number;
    riesgo: number;
  };
  wip: { ep_aprobados_sin_fv: number; ep_en_revision: number };
  acciones: Array<{
    id: string;
    title: string;
    priority?: 'high' | 'medium' | 'low';
    description?: string;
  }>;
}

export interface FinanceOverview {
  cash: { today: number; d7: number; d30: number; d60: number; d90: number };
  revenue: { month: number; ytd: number };
  margin?: { gross?: number; net?: number };
  ar: {
    aging: { d0_30: number; d31_60: number; d61_90: number; d90p: number };
    top_clientes: Array<{ name: string; amount: number }>;
  };
  ap: {
    d7: number;
    d14: number;
    d30: number;
    top_proveedores: Array<{ name: string; amount: number }>;
  };
  conciliacion?: { tasa?: number; pendientes?: number };
  acciones: Array<{
    id: string;
    title: string;
    priority?: 'high' | 'medium' | 'low';
    description?: string;
  }>;
}

export interface CeoOverview {
  cash: { today: number; d7: number; d30: number; d60?: number; d90?: number };
  revenue: { month: number; ytd: number };
  margin?: { month_pct?: number; plan_pct?: number; delta_pp?: number; top_projects?: any[] };
  working_cap?: {
    dso?: number | null;
    dpo?: number | null;
    dio?: number | null;
    ccc?: number | null;
    ar?: { d1_30: number; d31_60: number; d60_plus: number };
    ap?: { d7: number; d14: number; d30: number };
  };
  backlog?: {
    total?: number | null;
    cobertura_meses?: number | null;
    pipeline_weighted?: number | null;
    pipeline_vs_goal_pct?: number | null;
  };
  projects: {
    total: number;
    without_pc: number;
    on_budget?: number | null;
    over_budget?: number | null;
    three_way_violations?: number | null;
    wip_ep_to_invoice?: number | null;
  };
  risk: { high: number; medium: number; reasons?: string[] };
  alerts?: Array<{ kind?: string; title: string; cta?: string }>;
  acciones: Array<{
    id: string;
    title: string;
    priority?: 'high' | 'medium' | 'low';
    description?: string;
    cta?: string;
  }>;
  diagnostics?: any;
}

// API Functions
export async function fetchDashboardData(): Promise<DashboardData> {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching dashboard data:', error);
    throw error;
  }
}

export async function fetchProviders(): Promise<ProviderData[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/providers`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching providers:', error);
    throw error;
  }
}

export async function fetchProjects(): Promise<ProjectData[]> {
  try {
    // Prefer backend v2 (with_meta) when available
    const response = await fetch(`${API_BASE_URL}/projects_v2?with_meta=1`).catch(
      () => null as any,
    );
    if (response && response.ok) {
      const payload = await response.json();
      const items = (payload?.items || []) as any[];
      return items.map((p, idx) => ({
        id: p.id ?? `PROJ-${(idx + 1).toString().padStart(3, '0')}`,
        name: p.name ?? 'Proyecto',
        client: 'Cliente Externo',
        status: (p.status as any) ?? 'active',
        progress: Number((p as any).progress ?? 0),
        startDate: p.startDate ?? '',
        endDate: p.endDate ?? '',
        budget: Number(p.budget ?? 0),
        spent: Number(p.spent ?? 0),
        remaining: Number(p.remaining ?? Math.max(0, Number(p.budget ?? 0) - Number(p.spent ?? 0))),
        risk: (p.risk as any) ?? 'low',
        manager: p.manager ?? 'Gerente de Proyecto',
        description: p.description ?? '',
        location: p.location ?? 'Chile',
        orders: typeof p.orders === 'number' ? p.orders : undefined,
        providers: typeof p.providers === 'number' ? p.providers : undefined,
      }));
    }
    // Fallback to legacy endpoint
    const legacy = await fetch(`${API_BASE_URL}/projects`);
    if (!legacy.ok) {
      throw new Error(`HTTP error! status: ${legacy.status}`);
    }
    return await legacy.json();
  } catch (error) {
    console.error('Error fetching projects:', error);
    throw error;
  }
}

export async function fetchFinancialData(): Promise<FinancialData> {
  try {
    const response = await fetch(`${API_BASE_URL}/financial`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching financial data:', error);
    throw error;
  }
}

export async function fetchProjectsOverview(): Promise<ProjectsOverview> {
  const resp = await fetch(`${API_BASE_URL}/projects/overview`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function fetchFinanceOverview(): Promise<FinanceOverview> {
  const resp = await fetch(`${API_BASE_URL}/finance/overview`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const raw = await resp.json();
  // Normalize backend payload into FinanceOverview expected by UI
  const cash = {
    today: Number(raw?.cash?.today ?? 0),
    d7: Number(raw?.cash?.d7 ?? 0),
    d30: Number(raw?.cash?.d30 ?? 0),
    d60: Number(raw?.cash?.d60 ?? 0),
    d90: Number(raw?.cash?.d90 ?? 0),
  };
  const revenue = {
    month: Number(raw?.revenue?.month?.real ?? raw?.revenue?.month ?? 0),
    ytd: Number(raw?.revenue?.ytd?.real ?? raw?.revenue?.ytd ?? 0),
  };
  const arAging = {
    d0_30: Number(raw?.ar?.d1_30 ?? raw?.ar?.aging?.d0_30 ?? 0),
    d31_60: Number(raw?.ar?.d31_60 ?? raw?.ar?.aging?.d31_60 ?? 0),
    d61_90: Number(raw?.ar?.d61_90 ?? raw?.ar?.aging?.d61_90 ?? 0),
    d90p: Number(raw?.ar?.d60_plus ?? raw?.ar?.aging?.d90p ?? 0),
  };
  const arTop = Array.isArray(raw?.ar?.top_clientes)
    ? raw.ar.top_clientes.map((c: any) => ({
        name: c?.name ?? c?.nombre ?? 'Cliente',
        amount: Number(c?.amount ?? c?.pendiente ?? c?.total ?? 0),
      }))
    : [];
  const apTop = Array.isArray(raw?.ap?.top_proveedores)
    ? raw.ap.top_proveedores.map((p: any) => ({
        name: p?.name ?? p?.nombre ?? 'Proveedor',
        amount: Number(p?.amount ?? p?.por_pagar ?? p?.total ?? 0),
      }))
    : [];
  const conciliacion_raw = Number(raw?.conciliacion?.porc_conciliado ?? 0);
  const conciliacion = {
    // Ensure tasa is 0..1 for the UI which multiplies by 100
    tasa: conciliacion_raw > 1 ? conciliacion_raw / 100 : conciliacion_raw,
    pendientes: Number(raw?.conciliacion?.pendientes ?? 0),
  };
  const acciones = Array.isArray(raw?.acciones)
    ? raw.acciones.map((a: any, i: number) => ({
        id: String(a?.id ?? i),
        title: a?.title ?? a?.mensaje ?? 'Acción',
        description: a?.description,
        priority: a?.priority,
      }))
    : [];
  return {
    cash,
    revenue,
    margin: raw?.margin,
    ar: { aging: arAging, top_clientes: arTop },
    ap: {
      d7: Number(raw?.ap?.d7 ?? 0),
      d14: Number(raw?.ap?.d14 ?? 0),
      d30: Number(raw?.ap?.d30 ?? 0),
      top_proveedores: apTop,
    },
    conciliacion,
    acciones,
  };
}

export async function fetchCeoOverview(): Promise<CeoOverview> {
  const resp = await fetch(`${API_BASE_URL}/ceo/overview`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const raw = await resp.json();
  const cash = {
    today: Number(raw?.cash?.today ?? 0),
    d7: Number(raw?.cash?.d7 ?? 0),
    d30: Number(raw?.cash?.d30 ?? 0),
  };
  const revenue = {
    month: Number(raw?.revenue?.month?.real ?? raw?.revenue?.month ?? 0),
    ytd: Number(raw?.revenue?.ytd?.real ?? raw?.revenue?.ytd ?? 0),
  };
  const projects = {
    total: Number(raw?.projects?.total ?? 0),
    without_pc: Number(raw?.projects?.without_pc ?? 0),
    on_budget: raw?.projects?.on_budget ?? null,
    over_budget: raw?.projects?.over_budget ?? null,
    three_way_violations: raw?.projects?.three_way_violations ?? null,
    wip_ep_to_invoice: raw?.projects?.wip_ep_to_invoice ?? null,
  };
  const riskScore = Number(raw?.risk?.score ?? 0);
  const risk = {
    high: Math.max(0, Math.round(riskScore)),
    medium: Number(raw?.risk?.medium ?? 0),
    reasons: Array.isArray(raw?.risk?.reasons) ? raw.risk.reasons : [],
  };
  const acciones = Array.isArray(raw?.actions ?? raw?.acciones)
    ? (raw.actions ?? raw.acciones).map((a: any, i: number) => ({
        id: String(a?.id ?? i),
        title: a?.title ?? 'Acción',
        description: a?.description,
        priority: a?.priority,
        cta: a?.cta,
      }))
    : [];
  return {
    cash,
    revenue,
    margin: raw?.margin,
    working_cap: raw?.working_cap,
    backlog: raw?.backlog,
    projects,
    risk,
    alerts: raw?.alerts,
    acciones,
    diagnostics: raw?.diagnostics,
  };
}

export async function fetchExecutiveKPIs() {
  try {
    const response = await fetch(`${API_BASE_URL}/kpis/executive`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching executive KPIs:', error);
    throw error;
  }
}

export async function fetchFinancialAnalytics() {
  try {
    const response = await fetch(`${API_BASE_URL}/analytics/financial`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching financial analytics:', error);
    throw error;
  }
}

export async function fetchBankMovements(params?: Record<string, string | number | undefined>) {
  try {
    const qs = params
      ? '?' +
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== null && v !== '')
          .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
          .join('&')
      : '';
    const response = await fetch(`${API_BASE_URL}/finanzas/cartola_bancaria${qs}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching bank movements:', error);
    throw error;
  }
}

export async function fetchInvoicesVenta(params?: Record<string, string | number | undefined>) {
  try {
    const qs = params
      ? '?' +
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== null && v !== '')
          .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
          .join('&')
      : '';
    const response = await fetch(`${API_BASE_URL}/finanzas/facturas_venta${qs}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching sales invoices:', error);
    throw error;
  }
}

export async function fetchInvoicesCompra(params?: Record<string, string | number | undefined>) {
  try {
    const qs = params
      ? '?' +
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== null && v !== '')
          .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
          .join('&')
      : '';
    const response = await fetch(`${API_BASE_URL}/finanzas/facturas_compra${qs}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching purchase invoices:', error);
    throw error;
  }
}

export async function fetchTaxSummary() {
  try {
    const response = await fetch(`${API_BASE_URL}/impuestos/resumen`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching tax summary:', error);
    throw error;
  }
}

// CEO Copilot Integration
export async function sendCopilotMessage(message: string, context?: any) {
  try {
    const response = await fetch(`${API_BASE_URL}/copilot/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        context,
        timestamp: new Date().toISOString(),
      }),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error sending copilot message:', error);
    throw error;
  }
}

// Predictions API
export async function fetchPredictions() {
  try {
    const response = await fetch(`${API_BASE_URL}/predictions`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching predictions:', error);
    throw error;
  }
}

// Reconciliation API
export async function fetchReconcileSuggestions(payload: {
  source_type: 'bank' | 'purchase' | 'sales' | 'expense' | 'payroll' | 'tax';
  id?: number;
  amount?: number;
  date?: string;
  ref?: string;
  currency?: string;
  days?: number;
  amount_tol?: number;
  targets?: string[];
}) {
  const resp = await fetch(`${API_BASE_URL}/conciliacion/sugerencias`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function confirmReconcile(payload: Record<string, any>) {
  const resp = await fetch(`${API_BASE_URL}/conciliacion/confirmar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok && resp.status !== 202) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

// Conciliación Bancaria (servicio externo)
export const CONCILIACION_API_BASE = process.env.NEXT_PUBLIC_CONCILIACION_API_URL || '';

export function conciliacionServiceConfigured(): boolean {
  return !!CONCILIACION_API_BASE;
}

export async function fetchConciliationSuggestions(payload: {
  source: 'cartola' | 'factura_compra' | 'factura_venta';
  item: any;
}) {
  if (!CONCILIACION_API_BASE) {
    console.warn('Conciliación API URL no configurada (NEXT_PUBLIC_CONCILIACION_API_URL)');
    return { suggestions: [] };
  }
  try {
    const response = await fetch(`${CONCILIACION_API_BASE}/suggestions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching conciliation suggestions:', error);
    return { suggestions: [] };
  }
}

export async function confirmConciliation(payload: {
  match_id?: string;
  source: 'cartola' | 'factura_compra' | 'factura_venta';
  item: any;
  target: any;
}) {
  if (!CONCILIACION_API_BASE) {
    console.warn('Conciliación API URL no configurada (NEXT_PUBLIC_CONCILIACION_API_URL)');
    return { ok: false, message: 'Servicio no configurado' };
  }
  try {
    const response = await fetch(`${CONCILIACION_API_BASE}/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error confirming conciliation:', error);
    return { ok: false, message: 'Error en confirmación' };
  }
}

// Conciliación history (backend)
export async function fetchConciliationHistory() {
  const resp = await fetch(`${API_BASE_URL}/conciliacion/historial`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

// List reconciliation links for a bank movement
export type ReconcileLink = {
  id: number;
  amount: number;
  type: string;
  ref: string;
  fecha: string;
};
export type ReconcileLinksParams =
  | { bank_id: number }
  | { sales_doc: string; sales_date: string }
  | { purchase_doc: string; purchase_date: string }
  | { expense_id: number }
  | { payroll_id: number }
  | { payroll_period: string; payroll_rut: string }
  | { tax_id: number }
  | { tax_period: string; tax_tipo: string };
export async function fetchReconcileLinks(params: ReconcileLinksParams) {
  const qs =
    '?' +
    Object.entries(params)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      .join('&');
  const resp = await fetch(`${API_BASE_URL}/conciliacion/links${qs}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()) as { items: Array<ReconcileLink> };
}

// Utility functions
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatRUT(rut: string): string {
  if (!rut) return '';
  const cleaned = rut.replace(/[^0-9kK]/g, '');
  if (cleaned.length < 2) return cleaned;

  const body = cleaned.slice(0, -1);
  const dv = cleaned.slice(-1);
  const formattedBody = body.replace(/\B(?=(\d{3})+(?!\d))/g, '.');

  return `${formattedBody}-${dv}`;
}

export function formatDate(date: string): string {
  return new Date(date).toLocaleDateString('es-CL', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

export function getStatusColor(status: string): string {
  const statusColors: { [key: string]: string } = {
    active: 'text-lime-600 bg-lime-100',
    inactive: 'text-gray-600 bg-gray-100',
    blocked: 'text-red-600 bg-red-100',
    planning: 'text-blue-600 bg-blue-100',
    completed: 'text-green-600 bg-green-100',
    'on-hold': 'text-yellow-600 bg-yellow-100',
    low: 'text-green-600 bg-green-100',
    medium: 'text-yellow-600 bg-yellow-100',
    high: 'text-red-600 bg-red-100',
    synced: 'text-lime-600 bg-lime-100',
    pending: 'text-yellow-600 bg-yellow-100',
    error: 'text-red-600 bg-red-100',
  };
  return statusColors[status] || 'text-gray-600 bg-gray-100';
}

export function getRiskIcon(risk: string): string {
  const riskIcons: { [key: string]: string } = {
    low: '🟢',
    medium: '🟡',
    high: '🔴',
  };
  return riskIcons[risk] || '⚪';
}

export function getProgressColor(progress: number): string {
  if (progress >= 90) return 'bg-lime-500';
  if (progress >= 75) return 'bg-green-500';
  if (progress >= 50) return 'bg-yellow-500';
  if (progress >= 25) return 'bg-orange-500';
  return 'bg-red-500';
}

// Reports & Cashflow API
export async function fetchReporteProyectos(params?: Record<string, string | number | undefined>) {
  const qs =
    params && Object.keys(params).length
      ? '?' +
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== null && v !== '')
          .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
          .join('&')
      : '';
  const resp = await fetch(`${API_BASE_URL}/reportes/proyectos${qs}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function fetchReporteProveedores(
  params?: Record<string, string | number | undefined>,
) {
  const qs =
    params && Object.keys(params).length
      ? '?' +
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== null && v !== '')
          .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
          .join('&')
      : '';
  const resp = await fetch(`${API_BASE_URL}/reportes/proveedores${qs}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function fetchCashflowSemana(params?: { weeks?: number }) {
  const qs = params && params.weeks ? `?weeks=${encodeURIComponent(String(params.weeks))}` : '';
  const resp = await fetch(`${API_BASE_URL}/cashflow/semana${qs}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

// Purchase Orders API
export interface PurchaseOrderListItem {
  id: number | string;
  po_number: string;
  po_date: string;
  total_amount: number;
  currency?: string;
  status?: string;
  zoho_project_name?: string;
  zoho_vendor_name?: string;
  vendor_rut?: string;
}

export interface PagedResponse<T> {
  items: T[];
  meta: { total: number; page: number; page_size: number; pages: number };
}

export async function fetchPurchaseOrders(
  params?: Record<string, string | number | undefined>,
): Promise<PagedResponse<PurchaseOrderListItem>> {
  const qs = params
    ? '?' +
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join('&')
    : '';
  const resp = await fetch(`${API_BASE_URL}/purchase_orders${qs}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function fetchPurchaseOrder(id: number | string): Promise<Record<string, any>> {
  const resp = await fetch(`${API_BASE_URL}/purchase_orders/${id}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function createPurchaseOrder(payload: {
  vendor_rut: string;
  po_number: string;
  po_date: string;
  total_amount: number;
  currency?: string;
  status?: string;
  zoho_project_name?: string;
  zoho_vendor_name?: string;
}): Promise<Record<string, any>> {
  const resp = await fetch(`${API_BASE_URL}/purchase_orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export interface PurchaseOrderLine {
  id?: number;
  item_name?: string;
  item_desc?: string;
  quantity: number;
  unit_price: number;
  line_total?: number;
  currency?: string;
  tax_percent?: number;
  tax_amount?: number;
  uom?: string;
  status?: string;
  zoho_line_id?: string;
}

export async function fetchPurchaseOrderLines(
  id: number | string,
  params?: Record<string, string | number | undefined>,
): Promise<PagedResponse<PurchaseOrderLine>> {
  const qs = params
    ? '?' +
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join('&')
    : '';
  const resp = await fetch(`${API_BASE_URL}/purchase_orders/${id}/lines${qs}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function createPurchaseOrderLine(
  id: number | string,
  payload: PurchaseOrderLine,
): Promise<{ ok: boolean }> {
  const resp = await fetch(`${API_BASE_URL}/purchase_orders/${id}/lines`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

// -----------------------------
// AP ↔ PO Matching API (frontend wrapper)
// -----------------------------
export interface ApMatchSuggestion {
  po_id?: number | string | Array<string | number>;
  confidence: number;
  reasons?: string[];
  candidate?: {
    po_id: Array<string | number>;
    lines?: Array<{ po_line_id: string | number; qty_avail?: number; unit_price?: number | null }>;
    coverage?: { amount: number; pct: number };
  };
  total_amount?: number;
  vendor_rut?: string;
  po_number?: string;
  status?: string;
  po_date?: string;
}

export async function fetchApMatchSuggestions(payload: {
  invoice_id?: number | string;
  vendor_rut?: string;
  amount?: number;
  date?: string;
  project_id?: string | number;
  amount_tol?: number;
  days?: number;
}): Promise<{ items: ApMatchSuggestion[]; invoice_id?: number | string }> {
  const resp = await fetch(`${API_BASE_URL}/ap-match/suggestions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function previewApMatch(payload: {
  invoice_id: number | string;
  links: Array<{
    po_id: string | number;
    po_line_id?: string | number;
    amount: number;
    qty?: number;
  }>;
  vendor_rut?: string;
  project_id?: string | number;
}): Promise<any> {
  const resp = await fetch(`${API_BASE_URL}/ap-match/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function confirmApMatch(payload: {
  invoice_id: number | string;
  links: Array<{
    po_id: string | number;
    po_line_id?: string | number;
    amount: number;
    qty?: number;
  }>;
  confidence?: number;
  reasons?: string[];
  user_id?: string;
}): Promise<any> {
  const resp = await fetch(`${API_BASE_URL}/ap-match/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function feedbackApMatch(payload: {
  invoice_id: number | string;
  accepted?: 0 | 1;
  reason?: string;
  candidates_json?: any;
  chosen_json?: any;
  user_id?: string;
}): Promise<any> {
  const resp = await fetch(`${API_BASE_URL}/ap-match/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function getApMatchInvoice(invoice_id: number | string): Promise<any> {
  const resp = await fetch(`${API_BASE_URL}/ap-match/invoice/${invoice_id}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function getApMatchConfig(params?: {
  vendor_rut?: string;
  project_id?: string | number;
}) {
  const qs = params
    ? '?' +
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join('&')
    : '';
  const resp = await fetch(`${API_BASE_URL}/ap-match/config${qs}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}
