# OFITEC — **Prohibición de Emojis** (Auditoría + Remediación + Enforcements)
> Documento operativo para Copilot. Implementa la política de *docs_oficiales* (Estrategia Visual): **no se permiten emojis en la UI**. Este plan detecta, corrige y evita regresiones en todo el proyecto (frontend 3001, plantillas, backend 5555, seeds y contenidos).

---

## 0) Política y alcance
**Regla**: *Queda prohibido el uso de emojis en la interfaz* (copys, botones, labels, toasts, placeholders, títulos, estados, etc.).  
**Excepciones**: datos **externos** (p.ej., nombre legal de un cliente con emoji). Por defecto **se muestran sin emoji** (sanitizados). Nota: si más adelante se define una excepción de negocio, debe quedar documentada.

**Sustituciones permitidas**:
- Usar **iconografía** del sistema (p. ej. `lucide-react`) cuando sea estrictamente necesario **y** esté en la guía visual.  
- Preferir **texto claro** y **chips/badges** con color/borde para estados (ej.: `Conciliado`, `Pendiente`, `Error`).

---

## 1) Plan de acción (resumen)
1. **Auditar** el repo (frontend + backend/templates) y listar ficheros con emojis.  
2. **Remediar**: reemplazos automáticos + revisiones manuales con una **tabla de mapeo**.  
3. **Enforce**: ESLint + script Node + hook pre-commit + chequeo CI.  
4. **Sanitizar runtime** para datos externos (evitar que entren emojis a la UI).  
5. **Tests** (unit + snapshot) que rompen si vuelve un emoji.

---

## 2) Auditoría automática (detector de emojis)
> Añadir en `tools/emoji_check.js` y ejecutarlo en CI + pre-commit.

```js
// tools/emoji_check.js
// Escanea archivos de UI buscando cualquier emoji (Unicode Extended Pictographic) o variantes VS16/ZWS.
// Salida: lista de archivos/líneas con violaciones. Exit code>0 si hay alguna.

const fs = require('fs');
const path = require('path');

const ROOTS = [
  'frontend',               // Next/React
  'backend/templates',      // Jinja/HTML
  'services',               // UIs auxiliares
  'docs',                   // opcional: docs visibles a usuario
];

const EMOJI_RE = /[\p{Extended_Pictographic}\uFE0F\u200D]/u;
const EXT_WHITELIST = new Set(['.tsx','.ts','.jsx','.js','.html','.htm','.md','.css','.scss','.svg']);

let violations = [];

function walk(dir){
  for(const entry of fs.readdirSync(dir, {withFileTypes:true})){
    const p = path.join(dir, entry.name);
    if(entry.isDirectory()){ walk(p); continue; }
    const ext = path.extname(p).toLowerCase();
    if(!EXT_WHITELIST.has(ext)) continue;
    const text = fs.readFileSync(p,'utf8');
    const lines = text.split(/\r?\n/);
    lines.forEach((ln, i)=>{
      if(EMOJI_RE.test(ln)){
        violations.push(`${p}:${i+1}: ${ln.trim().slice(0,160)}`);
      }
    });
  }
}

ROOTS.filter(fs.existsSync).forEach(walk);

if(violations.length){
  console.error('\n🚫 Emojis detectados (prohibidos):');
  console.error(violations.join('\n'));
  process.exit(2);
}else{
  console.log('✅ Sin emojis en UI code.');
}
```

**NPM script**
```json
// package.json
{
  "scripts": {
    "check:emoji": "node tools/emoji_check.js"
  }
}
```

---

## 3) Remediación (reemplazos sugeridos)
> Usar **codemods** + búsqueda manual. Mapa de reemplazos comunes:

| Emoji | Reemplazo UI | Observación |
|------:|:-------------|:------------|
| ✅ | Chip `Conciliado` | Estado de conciliación. |
| ❌ | Chip `Error` | Con link a detalle. |
| ⚠️ | Chip `Advertencia` | Acceso al panel de 3-way o validaciones. |
| ⏳ | `Spinner` componente | Carga/busy. |
| 🔍 | Ícono `Search` (lucide) | Input de búsqueda. |
| 💡 | Texto `Sugerencia` | Evitar metáforas. |
| 📎 | Ícono `Paperclip` (lucide) | Adjuntos. |
| 📄 | Ícono `File` (lucide) | Documento. |
| 📈/📉 | Mini‑gráfico/Badge | No usar emoji. |

**Ejemplo de chip de estado (Tailwind)**
```tsx
export function StatusChip({ kind, children }:{ kind:'ok'|'warn'|'err'|"neutral"; children:React.ReactNode }){
  const tone = kind==='ok'?'border-emerald-500 text-emerald-700': kind==='warn'?'border-amber-500 text-amber-700': kind==='err'?'border-rose-600 text-rose-700':'border-neutral-300 text-neutral-700';
  return <span className={`px-2 py-0.5 text-xs rounded-full border ${tone}`}>{children}</span>;
}
```

---

## 4) Enforcements (ESLint + Hook + CI)

### 4.1 Regla ESLint personalizada
> Crear `eslint-rules/no-emoji.js` y referenciarla en el `.eslintrc.*`.

```js
// eslint-rules/no-emoji.js
module.exports = {
  meta: { type: 'problem', docs: { description: 'Prohíbe emojis en literales, JSXText y atributos' } },
  create(context) {
    const source = context.getSourceCode();
    const RE = /[\p{Extended_Pictographic}\uFE0F\u200D]/u;
    function check(node){
      const text = source.getText(node);
      if(RE.test(text)) context.report({ node, message: 'Emoji prohibido según docs_oficiales.' });
    }
    return {
      Literal: check,
      TemplateLiteral: check,
      JSXText: check,
      JSXAttribute: check,
    };
  }
};
```

**Config ESLint**
```json
// .eslintrc.json
{
  "plugins": ["local"],
  "parser": "@typescript-eslint/parser",
  "parserOptions": { "ecmaFeatures": { "jsx": true } },
  "rules": {
    "local/no-emoji": "error"
  },
  "settings": {
    "import/resolver": { "typescript": {} }
  }
}
```
> Nota: carga la regla local ya sea vía `eslint-plugin-local` o usando `overrides` con `require` en config JS (`.eslintrc.cjs`).

### 4.2 Hook pre-commit
- Si usas **Husky**:
```bash
npx husky add .husky/pre-commit "npm run lint && npm run check:emoji"
```
- Si usas **pre-commit** (Python): añade un `repo: local` que llame `node tools/emoji_check.js`.

### 4.3 CI (Github Actions)
```yaml
# .github/workflows/ci.yml (extracto)
- name: Emoji policy
  run: npm run check:emoji
```

---

## 5) Sanitización de **datos externos**
> Para evitar que textos de terceros (nombres de clientes, glosas bancarias) rompan la política de UI.

```ts
// frontend/lib/sanitize.ts
export function stripEmojis(input: string): string {
  if(!input) return input;
  return input.replace(/[\p{Extended_Pictographic}\uFE0F\u200D]/gu, '').trim();
}
```

Usar en renderizado de textos **externos**, p. ej.:
```tsx
<td>{stripEmojis(invoice.customer_name)}</td>
```

> **Configurable**: si en el futuro autorizas emojis en datos externos, desactiva esta llamada en componentes de “detalle” (log/acta), pero **nunca** en la **chrome** de la UI.

---

## 6) Codemod de limpieza (reemplazos masivos)
> Para los casos típicos (✅ ❌ ⚠️ ⏳ 🔍 💡 📎 📄), añade `tools/codemod_emoji_to_ui.js`.

```js
// tools/codemod_emoji_to_ui.js
// Reemplaza emojis por componentes/labels estándar. Ejecutar con precaución y revisar diffs.
const fs = require('fs'); const path = require('path');
const MAP = new Map([
  ['✅', "<StatusChip kind='ok'>Conciliado</StatusChip>"],
  ['❌', "<StatusChip kind='err'>Error</StatusChip>"],
  ['⚠️', "<StatusChip kind='warn'>Advertencia</StatusChip>"],
  ['⏳', "<Spinner />"],
  ['🔍', "<SearchIcon />"],
  ['💡', "Sugerencia"],
  ['📎', "<PaperclipIcon />"],
  ['📄', "<FileIcon />"],
]);

function apply(str){ for(const [k,v] of MAP) str = str.split(k).join(v); return str; }
function walk(dir){
  for(const e of fs.readdirSync(dir,{withFileTypes:true})){
    const p = path.join(dir,e.name);
    if(e.isDirectory()) walk(p); else if(/\.(tsx|jsx|ts|js|html|md)$/.test(p)){
      const t = fs.readFileSync(p,'utf8'); const nt = apply(t); if(t!==nt){ fs.writeFileSync(p, nt); console.log('Rewrote', p); }
    }
  }
}
walk('frontend'); walk('backend/templates');
```

---

## 7) Puntos típicos a revisar
- **Botones** (“Conciliar”, “Asociar OC”, “Sugerencias”, “Preview/Confirmar”).
- **Toasts/alerts** (éxito, error, advertencias 3‑way).
- **Badges/Chips** de estado (conciliado, pendiente, en revisión, riesgo, EP, pagos).
- **Placeholders** de inputs y **tooltips**.
- **Títulos** de páginas/sections.
- **Seeds** de datos y **fixtures** de pruebas.
- **Docs visibles al usuario** (README público, ayuda en línea).

---

## 8) QA — Criterios de aceptación
1) `npm run check:emoji` → **pasa** (0 violaciones) en CI.  
2) ESLint `local/no-emoji` → **pasa**.  
3) Navegar **todas** las páginas principales sin ver emojis: Proyectos, Control Financiero, Conciliación, Órdenes de Compra, Ventas/Compras, EP, Proveedores.  
4) Datos externos con emoji → se **renderizan sin emoji** (sanitizados) o según excepción documentada.  
5) Nuevos PRs que introducen emojis → **fallan** en CI (bloqueo de merge).

---

## 9) Rollout recomendado (rápido y seguro)
- **Día 1**: agregar checker + ESLint + hook; correr **codemod**; PR de limpieza.  
- **Día 2**: reemplazos manuales finos (chips/spinner/iconos), QA completo.  
- **Día 3**: activar **CI gate** (fallo si detecta emojis) y documentar en `CONTRIBUTING.md`.

---

## 10) Anexo — Ejemplos antes/después
**Antes**
```tsx
<button>Conciliar ✅</button>
<span>⚠️ Factura mayor a recepción</span>
```
**Después**
```tsx
<button><span className="sr-only">Conciliar</span>Conciliar</button>
<StatusChip kind="warn">Factura mayor a recepción</StatusChip>
```

**Antes**
```tsx
<input placeholder="🔍 Buscar…" />
```
**Después**
```tsx
<div className="relative">
  <input placeholder="Buscar" className="pl-7" />
  {/* <SearchIcon className="absolute left-2 top-2.5 h-4 w-4 text-neutral-400"/> */}
</div>
```

---

### Cierre
Con este paquete, Copilot puede **eliminar** los emojis existentes, **evitar** que vuelvan a entrar y **mantener** la UI alineada a *docs_oficiales*. El resultado: una interfaz consistente, profesional y auditable.

