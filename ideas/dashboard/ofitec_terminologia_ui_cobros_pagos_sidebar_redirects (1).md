# OFITEC — Terminología UI (Cobros/Pagos) + Sidebar + Redirects
> Sustituir **AR/AP** en la **UI** por **Cobros (CxC)** y **Pagos (CxP)**, manteniendo compatibilidad técnica. Incluye **sidebar** con labels correctos, **breadcrumbs**, **redirects** de rutas y **alias de API**.

---

## 0) Decisión
- En **UI** usar **Cobros (CxC)** y **Pagos (CxP)**.  
- En **código/DB** pueden conservarse prefijos `ar_`/`ap_` y rutas técnicas existentes.  
- Se añaden **alias** y **redirects permanentes** para no romper enlaces.

---

## 1) Sidebar (labels correctos)
**Archivo**: `frontend/config/financeNav.ts`
```ts
export type Role = 'CEO'|'CFO'|'Treasury'|'AR'|'AP'|'Auditor';
export type NavItem = { label: string; href: string; match: RegExp; roles: Role[] };
export type NavGroup = { title: string; items: NavItem[] };

export const financeNav: NavGroup[] = [
  {
    title: 'Tesorería',
    items: [
      { label: 'Overview', href: '/finanzas/tesoreria/overview', match: /^\/finanzas\/tesoreria\/(overview)?$/, roles: ['CEO','CFO','Treasury','Auditor'] },
      { label: 'Cuentas bancarias', href: '/finanzas/tesoreria/cuentas', match: /^\/finanzas\/tesoreria\/cuentas/, roles: ['CFO','Treasury','Auditor'] },
      { label: 'Cartola', href: '/finanzas/tesoreria/cartola', match: /^\/finanzas\/tesoreria\/cartola/, roles: ['CFO','Treasury','Auditor'] },
      { label: 'Conciliación', href: '/finanzas/tesoreria/conciliacion', match: /^\/finanzas\/tesoreria\/conciliacion/, roles: ['CFO','Treasury','AR','AP'] },
      { label: 'Pagos programados', href: '/finanzas/tesoreria/pagos-programados', match: /^\/finanzas\/tesoreria\/pagos-programados/, roles: ['CFO','Treasury'] }
    ]
  },
  {
    title: 'Cobros (CxC)',
    items: [
      { label: 'Overview', href: '/finanzas/ar/overview', match: /^\/finanzas\/ar\/(overview)?$/, roles: ['CEO','CFO','AR','Treasury','Auditor'] },
      { label: 'Facturas de venta', href: '/finanzas/ar/facturas', match: /^\/finanzas\/ar\/facturas/, roles: ['CFO','AR','Treasury','Auditor'] },
      { label: 'Estados de Pago (EP)', href: '/finanzas/ar/ep', match: /^\/finanzas\/ar\/ep/, roles: ['CFO','AR','Auditor'] },
      { label: 'Cobranzas', href: '/finanzas/ar/cobranzas', match: /^\/finanzas\/ar\/cobranzas/, roles: ['CFO','AR','Treasury'] }
    ]
  },
  {
    title: 'Pagos (CxP)',
    items: [
      { label: 'Overview', href: '/finanzas/ap/overview', match: /^\/finanzas\/ap\/(overview)?$/, roles: ['CEO','CFO','AP','Treasury','Auditor'] },
      { label: 'Facturas de compra', href: '/finanzas/ap/facturas', match: /^\/finanzas\/ap\/facturas/, roles: ['CFO','AP','Treasury','Auditor'] },
      { label: 'Órdenes (vista financiera)', href: '/finanzas/ap/ordenes', match: /^\/finanzas\/ap\/ordenes/, roles: ['CFO','AP','Auditor'] },
      { label: 'Proveedores', href: '/finanzas/ap/proveedores', match: /^\/finanzas\/ap\/proveedores/, roles: ['CFO','AP','Auditor'] }
    ]
  },
  {
    title: 'Inteligencia financiera',
    items: [
      { label: 'Reportes', href: '/finanzas/reportes', match: /^\/finanzas\/reportes/, roles: ['CEO','CFO','COO','Auditor'] }
    ]
  },
  {
    title: 'Integraciones',
    items: [
      { label: 'Conectores bancarios', href: '/finanzas/integraciones/bancos', match: /^\/finanzas\/integraciones\/bancos/, roles: ['CFO','Treasury'] },
      { label: 'SII', href: '/finanzas/integraciones/sii', match: /^\/finanzas\/integraciones\/sii/, roles: ['CFO'] },
      { label: 'Logs', href: '/finanzas/integraciones/logs', match: /^\/finanzas\/integraciones\/logs/, roles: ['CFO','Auditor'] }
    ]
  }
];
```

---

## 2) Breadcrumbs (labels correctos)
**Archivo**: `frontend/config/labels.ts`
```ts
export const labelMap: Record<string,string> = {
  '/finanzas': 'Finanzas',
  '/finanzas/tesoreria': 'Tesorería',
  '/finanzas/tesoreria/overview': 'Overview',
  '/finanzas/tesoreria/cuentas': 'Cuentas bancarias',
  '/finanzas/tesoreria/cartola': 'Cartola',
  '/finanzas/tesoreria/conciliacion': 'Conciliación',
  '/finanzas/tesoreria/pagos-programados': 'Pagos programados',

  '/finanzas/ar': 'Cobros (CxC)',
  '/finanzas/ar/overview': 'Overview',
  '/finanzas/ar/facturas': 'Facturas de venta',
  '/finanzas/ar/ep': 'Estados de Pago',
  '/finanzas/ar/cobranzas': 'Cobranzas',

  '/finanzas/ap': 'Pagos (CxP)',
  '/finanzas/ap/overview': 'Overview',
  '/finanzas/ap/facturas': 'Facturas de compra',
  '/finanzas/ap/ordenes': 'Órdenes (fin.)',
  '/finanzas/ap/proveedores': 'Proveedores',

  '/finanzas/reportes': 'Reportes',
  '/finanzas/integraciones/bancos': 'Conectores bancarios',
  '/finanzas/integraciones/sii': 'SII',
  '/finanzas/integraciones/logs': 'Logs',

  // Alias en español, si habilitas rutas amigables
  '/finanzas/cobros': 'Cobros (CxC)',
  '/finanzas/cobros/overview': 'Overview',
  '/finanzas/pagos': 'Pagos (CxP)',
  '/finanzas/pagos/overview': 'Overview'
};
```

---

## 3) Redirects / alias de rutas (Next.js)
**Archivo**: `next.config.js` (en `redirects()`)
```ts
// Alias legibles hacia rutas técnicas
{ source: '/finanzas/cobros', destination: '/finanzas/ar/overview', permanent: true },
{ source: '/finanzas/cobros/:path*', destination: '/finanzas/ar/:path*', permanent: true },
{ source: '/finanzas/pagos', destination: '/finanzas/ap/overview', permanent: true },
{ source: '/finanzas/pagos/:path*', destination: '/finanzas/ap/:path*', permanent: true },
```
> Si prefieres migrar las rutas reales a español, invierte `source/destination` y conserva los paths anteriores como redirects.

---

## 4) Alias de API (5555)
**Archivo sugerido**: `backend/api_alias_finance.py`
```python
from flask import Blueprint
from api_finance_ar import bp as ar_bp  # blueprints existentes
from api_finance_ap import bp as ap_bp

bp = Blueprint('finance_alias', __name__)

# Cobros (CxC) → alias de AR
bp.add_url_rule('/api/finance/cobros/<path:subpath>',
                view_func=ar_bp.view_functions.get('ar_bp.dispatch_request'),
                defaults={'subpath': ''})

# Pagos (CxP) → alias de AP
bp.add_url_rule('/api/finance/pagos/<path:subpath>',
                view_func=ap_bp.view_functions.get('ap_bp.dispatch_request'),
                defaults={'subpath': ''})
```
> Alternativa simple: duplicar `@app.route` con ambos prefijos si no usas blueprints anidados.

---

## 5) Microcopy y tooltips
- Títulos/menú: **Cobros (CxC)** y **Pagos (CxP)**.  
- En espacios reducidos: **Cobros** / **Pagos**.  
- Tooltip al pasar por el grupo del sidebar: “Cobros (CxC) = Cuentas por Cobrar; Pagos (CxP) = Cuentas por Pagar”.

---

## 6) QA
1) El sidebar muestra **Cobros (CxC)** y **Pagos (CxP)** (no AR/AP).  
2) Breadcrumbs y headers reflejan la nueva terminología.  
3) Rutas `/finanzas/cobros/*` y `/finanzas/pagos/*` funcionan (redirects o rutas reales).  
4) Los alias de API responden equivalente a las rutas técnicas.  
5) Sin emojis; contraste AA; navegación por teclado.

---

### Cierre
Con este paquete, Ofitec habla el idioma del usuario (**Cobros/Pagos**) sin perder compatibilidad interna (`ar_`/`ap_`). Los **redirects** y **alias** facilitan la transición y evitan rupturas en enlaces existentes.

