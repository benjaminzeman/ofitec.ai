// Project 360 API client for ofitec.ai
// Talks to Flask backend endpoints under /api/projects/<project_key>/...

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:5555/api';

export type ProjectKey = string;

export interface ProjectSummary {
  project_key: string;
  name?: string;
  slug?: string;
  sales_contracted: number;
  budget_cost: number;
  committed: number;
  invoiced_ap: number;
  paid: number;
  ar_invoiced: number;
  ar_collected: number;
  // Extended fields from backend summary
  contract_net?: number;
  contract_gross?: number;
  extras_net?: number;
  extras_gross?: number;
  contract_plus_extras_net?: number;
  ep_total_net?: number;
  ep_total_gross?: number;
  billed_pct?: number;
  margin_gross?: number;
  margin_net?: number;
  progress_pct?: number;
  flags?: { [k: string]: boolean };
  next_milestones?: Array<{ name: string; date: string; status?: string }>;
}

export interface BudgetTotals {
  project_key: string;
  pc_total: number;
  committed: number;
  available_conservative: number;
}

export interface PurchaseItem {
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

export interface Paged<T> {
  items: T[];
  meta: { total: number; page: number; page_size: number; pages: number };
}

export interface FinanceData {
  project_key: string;
  ap_invoiced: number;
  payments: number;
  ar_invoiced: number;
  collections: number;
  cashflow?: {
    expected?: Array<{ month: string; amount: number }>;
    actual?: Array<{ month: string; amount: number }>;
    variance?: Array<{ month: string; amount: number }>;
  };
}

export interface TimeData {
  project_key: string;
  milestones?: Array<{ name: string; date: string; status?: string }>;
  progress_pct?: number;
}

export interface DocItem {
  id: string | number;
  name: string;
  url?: string;
  mime_type?: string;
  updated_at?: string;
}
export interface ChatItem {
  id: string | number;
  subject?: string;
  last_message_at?: string;
  participants?: string[];
}

// Contract override types
export interface ContractOverride {
  contract_net?: number;
  contract_gross?: number;
  iva_rate?: number;
  currency?: string;
  note?: string;
  source?: string;
}

// Estados de Pago (Payment States)
export interface PaymentState {
  id?: number;
  ep_number?: string;
  date?: string;
  net_amount: number;
  iva_rate?: number;
  gross_amount?: number;
  note?: string;
}

// Obras Adicionales (Additional Works)
export interface AdditionalWork {
  id?: number;
  name: string;
  status?: string;
  net_amount: number;
  iva_rate?: number;
  gross_amount?: number;
  note?: string;
}

function qs(params?: Record<string, string | number | undefined | null>): string {
  if (!params) return '';
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join('&')}` : '';
}

export async function getProjectSummary(projectKey: ProjectKey): Promise<ProjectSummary> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectKey)}/summary`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const raw = await resp.json();
  return {
    project_key: String(raw.project_id || projectKey),
    name: raw.project_name || projectKey,
    slug: raw.slug,
    sales_contracted: Number(raw.sales_contracted || 0),
    budget_cost: Number(raw.budget_cost || 0),
    committed: Number(raw.committed || 0),
    invoiced_ap: Number(raw.invoiced_ap || 0),
    paid: Number(raw.paid || 0),
    ar_invoiced: Number(raw.ar_invoiced || 0),
    ar_collected: Number(raw.ar_collected || 0),
    contract_net: raw.contract_net != null ? Number(raw.contract_net) : undefined,
    contract_gross: raw.contract_gross != null ? Number(raw.contract_gross) : undefined,
    extras_net: raw.extras_net != null ? Number(raw.extras_net) : undefined,
    extras_gross: raw.extras_gross != null ? Number(raw.extras_gross) : undefined,
    contract_plus_extras_net:
      raw.contract_plus_extras_net != null ? Number(raw.contract_plus_extras_net) : undefined,
    ep_total_net: raw.ep_total_net != null ? Number(raw.ep_total_net) : undefined,
    ep_total_gross: raw.ep_total_gross != null ? Number(raw.ep_total_gross) : undefined,
    billed_pct: raw.billed_pct != null ? Number(raw.billed_pct) : undefined,
    margin_gross: Number(raw.margin_expected || 0),
    margin_net: Number(raw.margin_real || 0),
    progress_pct: Number(raw.progress_pct || 0),
    flags: raw.flags || {},
    next_milestones: raw.next_milestones || [],
  };
}

export async function getProjectBudget(projectKey: ProjectKey): Promise<BudgetTotals> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectKey)}/budget`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const raw = await resp.json();
  const totals = raw?.totals || raw || {};
  return {
    project_key: projectKey,
    pc_total: Number(totals.pc_total || 0),
    committed: Number(totals.committed || 0),
    available_conservative: Number(totals.available_conservative || 0),
  };
}

export async function getProjectPurchases(
  projectKey: ProjectKey,
  params?: { page?: number; page_size?: number },
): Promise<Paged<PurchaseItem>> {
  const resp = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectKey)}/purchases${qs(params as any)}`,
  );
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function getProjectFinance(
  projectKey: ProjectKey,
  params?: { from?: string; to?: string; months?: number },
): Promise<FinanceData> {
  const resp = await fetch(
    `${API_BASE}/projects/${encodeURIComponent(projectKey)}/finance${qs(params as any)}`,
  );
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function getProjectTime(projectKey: ProjectKey): Promise<TimeData> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectKey)}/time`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function getProjectDocs(projectKey: ProjectKey): Promise<{ items: DocItem[] }> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectKey)}/docs`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const raw = await resp.json();
  const files = raw?.files || raw?.items || [];
  return { items: files };
}

export async function getProjectChats(projectKey: ProjectKey): Promise<{ items: ChatItem[] }> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectKey)}/chats`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const raw = await resp.json();
  const threads = raw?.threads || raw?.items || [];
  return { items: threads };
}

// Contract override API
export async function getProjectContract(projectKey: ProjectKey): Promise<ContractOverride | null> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectKey)}/contract`);
  if (!resp.ok) return null;
  const raw = await resp.json();
  if (raw && raw.contract_net == null && raw.contract_gross == null) return null;
  return raw;
}

export async function saveProjectContract(
  projectKey: ProjectKey,
  payload: ContractOverride,
): Promise<boolean> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectKey)}/contract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return resp.ok;
}

// Payment States API
export async function getProjectPayments(
  projectKey: ProjectKey,
): Promise<{ items: PaymentState[]; totals: { net: number; gross: number } }> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectKey)}/payments`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function addProjectPayment(
  projectKey: ProjectKey,
  payload: PaymentState,
): Promise<boolean> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectKey)}/payments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return resp.ok;
}

// Additional Works API
export async function getProjectExtras(
  projectKey: ProjectKey,
): Promise<{ items: AdditionalWork[]; totals: { net: number; gross: number } }> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectKey)}/extras`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return await resp.json();
}

export async function addProjectExtra(
  projectKey: ProjectKey,
  payload: AdditionalWork,
): Promise<boolean> {
  const resp = await fetch(`${API_BASE}/projects/${encodeURIComponent(projectKey)}/extras`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return resp.ok;
}
