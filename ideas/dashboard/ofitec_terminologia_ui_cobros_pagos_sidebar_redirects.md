# OFITEC — Terminología UI **Cobros (CxC)** / **Pagos (CxP)**
> Sustituir **AR/AP** en la **UI** por **Cobros (CxC)** y **Pagos (CxP)**, manteniendo compatibilidad técnica. Incluye **diff** del sidebar, **labels** de breadcrumbs, **redirects** de rutas y **alias de API**.

---

## 0) Decisión
- En **UI**: usar **Cobros (CxC)** y **Pagos (CxP)** (lenguaje directo).  
- En **código/DB**: se puede conservar prefijos `ar_` / `ap_` y rutas técnicas existentes.  
- Se añaden **alias** de rutas y **redirects permanentes** para no romper enlaces.

---

## 1) Sidebar — *diff* (frontend/config/financeNav.ts)
> Solo cambia **títulos/labels**. Las rutas pueden permanecer (`/finanzas/ar/*`, `/finanzas/ap/*`).

```diff
-  {
-    title: 'Cuentas por Cobrar (AR)',
+  {
+    title: 'Cobros (CxC)',
     items: [
       { label: 'Overview', href: '/finanzas/ar/overview', match: /^\/finanzas\/ar\/(overview)?$/, roles: ['CEO','CFO','AR','Treasury','Auditor'] },
-      { label: 'Facturas de Venta', href: '/finanzas/ar/facturas', match: /^\/finanzas\/ar\/facturas/, roles: ['CFO','AR','Treasury','Auditor'] },
-      { label: 'Estados de Pago (EP)', href: '/finanzas/ar/ep', match: /^\/finanzas\/ar\/ep/, roles: ['CFO','AR','Auditor'] },
-      { label: 'Cobranzas', href: '/finanzas/ar/cobranzas', match: /^\/finanzas\/ar\/cobranzas/, roles: ['CFO','AR','Treasury'] }
+      { label: 'Facturas de venta', href: '/finanzas/ar/facturas', match: /^\/finanzas\/ar\/facturas/, roles: ['CFO','AR','Treasury','Auditor'] },
+      { label: 'Estados de Pago (EP)', href: '/finanzas/ar/ep', match: /^\/finanzas\/ar\/ep/, roles: ['CFO','AR','Auditor'] },
+      { label: 'Cobranzas', href: '/finanzas/ar/cobranzas', match: /^\/finanzas\/ar\/cobranzas/, roles: ['CFO','AR','Treasury'] }
     ]
   },
-  {
-    title: 'Cuentas por Pagar (AP)',
+  {
+    title: 'Pagos (CxP)',
     items: [
       { label: 'Overview', href: '/finanzas/ap/overview', match: /^\/finanzas\/ap\/(overview)?$/, roles: ['CEO','CFO','AP','Treasury','Auditor'] },
-      { label: 'Facturas de Compra', href: '/finanzas/ap/facturas', match: /^\/finanzas\/ap\/facturas/, roles: ['CFO','AP','Treasury','Auditor'] },
-      { label: 'Órdenes (vista financiera)', href: '/finanzas/ap/ordenes', match: /^\/finanzas\/ap\/ordenes/, roles: ['CFO','AP','Auditor'] },
-      { label: 'Proveedores', href: '/finanzas/ap/proveedores', match: /^\/finanzas\/ap\/proveedores/, roles: ['CFO','AP','Auditor'] }
+      { label: 'Facturas de compra', href: '/finanzas/ap/facturas', match: /^\/finanzas\/ap\/facturas/, roles: ['CFO','AP','Treasury','Auditor'] },
+      { label: 'Órdenes (vista financiera)', href: '/finanzas/ap/ordenes', match: /^\/finanzas\/ap\/ordenes/, roles: ['CFO','AP','Auditor'] },
+      { label: 'Proveedores', href: '/finanzas/ap/proveedores', match: /^\/finanzas\/ap\/proveedores/, roles: ['CFO','AP','Auditor'] }
     ]
   }
```

> Si prefieres que las **rutas** sean también en español, usa alias `/finanzas/cobros/*` y `/finanzas/pagos/*` (sección 3) sin tocar las técnicas.

---

## 2) Breadcrumbs — labels en español (frontend/config/labels.ts)
```diff
-  '/finanzas/ar': 'AR',
-  '/finanzas/ar/overview': 'Overview',
-  '/finanzas/ar/facturas': 'Facturas de venta',
-  '/finanzas/ar/ep': 'Estados de Pago',
-  '/finanzas/ar/cobranzas': 'Cobranzas',
-  '/finanzas/ap': 'AP',
-  '/finanzas/ap/overview': 'Overview',
-  '/finanzas/ap/facturas': 'Facturas de compra',
-  '/finanzas/ap/ordenes': 'Órdenes (fin.)',
-  '/finanzas/ap/proveedores': 'Proveedores',
+  '/finanzas/ar': 'Cobros (CxC)',
+  '/finanzas/ar/overview': 'Overview',
+  '/finanzas/ar/facturas': 'Facturas de venta',
+  '/finanzas/ar/ep': 'Estados de Pago',
+  '/finanzas/ar/cobranzas': 'Cobranzas',
+  '/finanzas/ap': 'Pagos (CxP)',
+  '/finanzas/ap/overview': 'Overview',
+  '/finanzas/ap/facturas': 'Facturas de compra',
+  '/finanzas/ap/ordenes': 'Órdenes (fin.)',
+  '/finanzas/ap/proveedores': 'Proveedores',

+  /* Alias en español (si habilitas rutas amigables) */
+  '/finanzas/cobros': 'Cobros (CxC)',
+  '/finanzas/cobros/overview': 'Overview',
+  '/finanzas/pagos': 'Pagos (CxP)',
+  '/finanzas/pagos/overview': 'Overview'
```

---

## 3) Redirects / Alias de rutas (Next.js)
> Opción A (recomendada): **mantener** `/finanzas/ar/*` y `/finanzas/ap/*`, pero ofrecer **rutas en español** que redirigen.

```ts
// next.config.js (añadir a redirects())
{ source: '/finanzas/cobros', destination: '/finanzas/ar/overview', permanent: true },
{ source: '/finanzas/cobros/:path*', destination: '/finanzas/ar/:path*', permanent: true },
{ source: '/finanzas/pagos', destination: '/finanzas/ap/overview', permanent: true },
{ source: '/finanzas/pagos/:path*', destination: '/finanzas/ap/:path*', permanent: true },
```

> Opción B: migrar rutas **reales** a `/finanzas/cobros/*` y `/finanzas/pagos/*` y mantener las técnicas como redirects; en ese caso, invierte `source/destination`.

---

## 4) Alias de API (5555)
> Mantener handlers actuales y exponer alias legibles.

```python
# backend/api_alias_finance.py
from flask import Blueprint
from existing_ar_blueprint import bp as ar_bp  # supón que ya existen
from existing_ap_blueprint import bp as ap_bp

bp = Blueprint('finance_alias', __name__)

# Cobros (CxC) → alias de AR
bp.add_url_rule('/api/finance/cobros/<path:path>',
                view_func=ar_bp.view_functions['ar_bp.dispatch_request'],
                defaults={'path': ''})

# Pagos (CxP) → alias de AP
bp.add_url_rule('/api/finance/pagos/<path:path>',
                view_func=ap_bp.view_functions['ap_bp.dispatch_request'],
                defaults={'path': ''})
```
> Alternativa simple si no usas blueprints anidados: duplicar `@app.route` con dos prefijos que llamen a la misma función.

---

## 5) Microcopy y tooltips
- Mostrar **Cobros (CxC)** y **Pagos (CxP)** en títulos/menú.  
- En labels con poco espacio, usar solo **Cobros** / **Pagos**.  
- Tooltip de ayuda (una vez por sesión): “Cobros (CxC) = Cuentas por Cobrar; Pagos (CxP) = Cuentas por Pagar”.

---

## 6) QA
1) El sidebar muestra **Cobros (CxC)** y **Pagos (CxP)**; no aparece “AR/AP”.  
2) Breadcrumbs y headers reflejan la nueva terminología.  
3) Las rutas `/finanzas/cobros/*` y `/finanzas/pagos/*` funcionan (redirects a técnicas o viceversa).  
4) Las API alias responden igual que las rutas técnicas.  
5) No hay emojis; contraste AA; navegación por teclado.

---

### Cierre
Con este paquete, Ofitec habla el idioma del usuario (**Cobros/Pagos**) sin perder compatibilidad con el código existente (`ar_`/`ap_`). Los redirects y alias evitan roturas y facilitan la transición.

