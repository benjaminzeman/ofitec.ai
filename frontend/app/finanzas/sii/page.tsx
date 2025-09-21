"use client";

import { useEffect, useMemo, useState } from "react";

function buildApiUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:5555";
  return `${base.replace(/\/$/, "")}${path}`;
}

interface ImportSummary {
  periodo: string;
  ventas: number;
  compras: number;
  inserted_sales: number;
  updated_sales: number;
  inserted_purchases: number;
  updated_purchases: number;
}

const guideSections = [
  {
    title: 'Requisitos previos',
    content: (
      <ul className="list-disc pl-6 space-y-1 text-slate-700">
        <li>Certificado digital SII en formato .p12/.pfx y clave asociada.</li>
        <li>Variables de entorno: <code>SII_RUT</code>, <code>SII_AMBIENTE</code>, <code>SII_CERT_P12_PATH</code>, <code>SII_CERT_P12_PASS</code>, <code>FERNET_KEY</code>.</li>
        <li>Dependencias backend instaladas: <code>requests</code>, <code>lxml</code>, <code>cryptography</code>, <code>signxml</code>.</li>
        <li>Conectividad HTTPS hacia <code>palena.sii.cl</code> o <code>maullin.sii.cl</code> segun ambiente.</li>
      </ul>
    ),
  },
  {
    title: 'Como operarlo en Ofitec',
    content: (
      <ol className="list-decimal pl-6 space-y-1 text-slate-700">
        <li><strong>Probar token:</strong> obtiene el Bearer desde el certificado y muestra su expiracion estimada.</li>
        <li><strong>Importar RCV:</strong> con anno/mes se traen ventas y compras, quedando en <code>sii_rcv_*</code> y en la bitacora.</li>
        <li><strong>Resumen global:</strong> consulta los totales acumulados.</li>
        <li><strong>SSE en vivo:</strong> "Escuchar SSE" abre un stream con nuevos eventos o errores del SII.</li>
      </ol>
    ),
  },
  {
    title: 'Modo demo vs produccion',
    content: (
      <ul className="list-disc pl-6 space-y-1 text-slate-700">
        <li><code>SII_FAKE_MODE=1</code> genera datos deterministas para QA.</li>
        <li>En produccion elimina el modo demo y usa las credenciales oficiales.</li>
        <li>Verifica la tabla <code>sii_eventos</code> y la bitacora de esta pagina para auditoria.</li>
      </ul>
    ),
  },
];

export default function SiiFinanzasPage() {
  const today = useMemo(() => new Date(), []);
  const [year, setYear] = useState<number>(today.getFullYear());
  const [month, setMonth] = useState<number>(today.getMonth() + 1);
  const [log, setLog] = useState<string>("Listo para consultar el SII.");
  const [summary, setSummary] = useState<ImportSummary | null>(null);
  const [sse, setSse] = useState<EventSource | null>(null);

  useEffect(() => {
    return () => {
      if (sse) {
        sse.close();
      }
    };
  }, [sse]);

  function appendLog(message: string) {
    const line = `${new Date().toLocaleTimeString()} — ${message}`;
    setLog((prev) => (prev ? `${prev}\n${line}` : line));
  }

  async function testToken() {
    try {
      const res = await fetch(buildApiUrl("/api/sii/token"));
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        appendLog(`Token error: ${err.detail || res.statusText}`);
        return;
      }
      const data = await res.json();
      appendLog(
        `Token (${data.ambiente}) listo · expira ${data.expires_at} (preview ${data.token_preview})`,
      );
    } catch (error: any) {
      appendLog(`Fallo al solicitar token: ${error.message}`);
    }
  }

  async function runImport() {
    try {
      const res = await fetch(buildApiUrl("/api/sii/rcv/import"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year, month }),
      });
      const data = await res.json();
      if (!res.ok) {
        appendLog(`Importación falló: ${data.detail || data.error || res.statusText}`);
        return;
      }
      setSummary(data);
      appendLog(
        `RCV ${data.periodo}: ventas=${data.ventas} (ins ${data.inserted_sales}/upd ${data.updated_sales}), ` +
          `compras=${data.compras} (ins ${data.inserted_purchases}/upd ${data.updated_purchases})`,
      );
    } catch (error: any) {
      appendLog(`Fallo al importar RCV: ${error.message}`);
    }
  }

  async function refreshSummary() {
    try {
      const res = await fetch(buildApiUrl("/api/sii/rcv/summary"));
      if (!res.ok) {
        appendLog(`Resumen no disponible (${res.status})`);
        return;
      }
      const data = await res.json();
      appendLog(`Resumen global: ventas=${data.ventas}, compras=${data.compras}`);
    } catch (error: any) {
      appendLog(`Fallo al consultar resumen: ${error.message}`);
    }
  }

  function toggleEvents() {
    if (sse) {
      sse.close();
      setSse(null);
      appendLog("SSE desconectado");
      return;
    }
    const source = new EventSource(buildApiUrl("/api/sii/events"));
    source.onmessage = (event) => {
      appendLog(`Evento: ${event.data}`);
    };
    source.onerror = () => {
      appendLog("SSE error/desconectado");
      source.close();
      setSse(null);
    };
    appendLog("SSE conectado");
    setSse(source);
  }

  return (
    <div className="p-6 space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">Integración SII</h1>
        <p className="text-slate-600">
          Consulta token, importa RCV y monitorea eventos en tiempo real. Modo demo usa SII_FAKE_MODE.
        </p>
      </header>

      <section className="space-y-3">
        {guideSections.map((section) => (
          <details
            key={section.title}
            className="group border border-slate-200 rounded-lg bg-white shadow-sm transition hover:border-slate-300"
          >
            <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-800 flex items-center justify-between">
              <span>{section.title}</span>
              <span className="text-xs text-slate-500 group-open:hidden">ver mas</span>
            </summary>
            <div className="px-4 pb-4 text-sm text-slate-700 space-y-2">{section.content}</div>
          </details>
        ))}
      </section>
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-slate-700">Año</span>
          <input
            type="number"
            value={year}
            onChange={(event) => setYear(parseInt(event.target.value, 10) || year)}
            className="border border-slate-200 rounded px-3 py-2"
            min={2000}
            max={2100}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-slate-700">Mes</span>
          <input
            type="number"
            value={month}
            onChange={(event) => setMonth(parseInt(event.target.value, 10) || month)}
            className="border border-slate-200 rounded px-3 py-2"
            min={1}
            max={12}
          />
        </label>
        <div className="flex flex-wrap items-end gap-2">
          <button onClick={testToken} className="px-3 py-2 rounded bg-black text-white">
            Probar token
          </button>
          <button onClick={runImport} className="px-3 py-2 rounded bg-black text-white">
            Importar RCV
          </button>
          <button onClick={refreshSummary} className="px-3 py-2 rounded border border-slate-200">
            Resumen global
          </button>
          <button onClick={toggleEvents} className="px-3 py-2 rounded border border-slate-200">
            {sse ? "Detener SSE" : "Escuchar SSE"}
          </button>
        </div>
      </section>

      {summary && (
        <section className="border border-slate-200 rounded-lg p-4 bg-slate-50">
          <h2 className="text-lg font-semibold text-slate-800">Ultima importación</h2>
          <dl className="grid grid-cols-2 gap-3 mt-2 text-sm text-slate-700">
            <div>
              <dt className="font-medium">Periodo</dt>
              <dd>{summary.periodo}</dd>
            </div>
            <div>
              <dt className="font-medium">Ventas</dt>
              <dd>{summary.ventas}</dd>
            </div>
            <div>
              <dt className="font-medium">Compras</dt>
              <dd>{summary.compras}</dd>
            </div>
            <div>
              <dt className="font-medium">Inserciones</dt>
              <dd>
                Ventas {summary.inserted_sales} · Compras {summary.inserted_purchases}
              </dd>
            </div>
            <div>
              <dt className="font-medium">Actualizaciones</dt>
              <dd>
                Ventas {summary.updated_sales} · Compras {summary.updated_purchases}
              </dd>
            </div>
          </dl>
        </section>
      )}

      <section>
        <h2 className="text-lg font-semibold text-slate-800">Bitácora</h2>
        <pre className="mt-2 rounded border border-slate-200 bg-slate-900 text-slate-100 p-4 whitespace-pre-wrap text-sm">
          {log}
        </pre>
      </section>
    </div>
  );
}
