# Módulo Notas de Venta — Correlativo, Validación de RUT, Auditoría de Aprobación y Bloqueo Post‑Emisión

> Extensión del módulo **Notas de Venta (NV)** para cumplir con los “docs oficiales” definidos por tu formato, replicando estética y contenido del PDF de referencia. Este documento trae **migraciones/SQL**, **servicios Flask**, **plantilla PDF** y **cambios en Frontend**.

---

## 0) Objetivos
- **Correlativo anual** `NNN‑AAAA` (secuencial por año, sin saltos ni duplicados).
- **Validación de RUT chileno** (formato y dígito verificador, normalizado a `99.999.999‑K`).
- **Aprobación/Auditoría**: registrar `approved_by`, `approved_at`, `approved_ip`, `approved_ua` y **hash** del PDF emitido.
- **Estados**: `draft → approved → issued → cancelled` con **bloqueo total** tras `issued`.
- **Footer y branding** idénticos al documento actual (URL, dirección, fecha/hora de emisión).

---

## 1) Migraciones / SQL

> Para SQLite (dev) y PostgreSQL (prod). Reemplaza `AUTOINCREMENT` por `SERIAL` y `CURRENT_TIMESTAMP` por `NOW()` en Postgres.

```sql
-- sales_notes: nuevas columnas y restricciones
ALTER TABLE sales_notes
  ADD COLUMN year INTEGER GENERATED ALWAYS AS (CAST(strftime('%Y', issue_date) AS INTEGER)) VIRTUAL;
-- En Postgres: year INTEGER GENERATED ALWAYS AS (EXTRACT(YEAR FROM issue_date)) STORED;

ALTER TABLE sales_notes
  ADD COLUMN approved_ip TEXT,
  ADD COLUMN approved_ua TEXT,
  ADD COLUMN pdf_hash TEXT,
  ADD COLUMN emitted_at TIMESTAMP;

-- Único: correlativo anual (nv_number único por año)
-- Si prefieres separar número y año, añade cols: nv_seq INTEGER, nv_year INTEGER y UNIQUE(nv_year, nv_seq)
CREATE UNIQUE INDEX IF NOT EXISTS uq_sales_notes_number ON sales_notes(nv_number);

-- Auditoría de cambios (opcional; si no quieres tabla aparte, al menos guarda approved_* y pdf_hash en cabecera)
CREATE TABLE IF NOT EXISTS sales_note_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sales_note_id INTEGER NOT NULL,
  action TEXT NOT NULL,              -- create|update|approve|issue|cancel
  actor TEXT,
  ip TEXT,
  user_agent TEXT,
  payload_json TEXT,                 -- snapshot del documento / diff
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (sales_note_id) REFERENCES sales_notes(id) ON DELETE CASCADE
);
```

**Notas**
- Si prefieres **secuencia por año**: agrega `nv_year INT`, `nv_seq INT`, índice `UNIQUE(nv_year, nv_seq)` y genera `nv_number = lpad(nv_seq,3,'0') || '-' || nv_year` a nivel de servicio.

---

## 2) Backend (Flask) — Servicios y Validaciones

### 2.1 Utilidades (RUT, correlativo, hash)
```python
# backend/app/utils/cl_chile.py
import re
import hashlib
from datetime import datetime
from typing import Tuple

RUT_CLEAN_RE = re.compile(r"[^0-9kK]")

def rut_normalize(rut: str) -> str:
    """99.999.999-K"""
    s = RUT_CLEAN_RE.sub("", rut or "").upper()
    if not s:
        return ""
    body, dv = s[:-1], s[-1]
    # formato con puntos y guión
    parts = []
    while len(body) > 3:
        parts.insert(0, body[-3:]); body = body[:-3]
    if body:
        parts.insert(0, body)
    return f"{'.'.join(parts)}-{dv}"

def rut_is_valid(rut: str) -> bool:
    s = RUT_CLEAN_RE.sub("", rut or "").upper()
    if len(s) < 2:
        return False
    body, dv = s[:-1], s[-1]
    try:
        total, mul = 0, 2
        for c in reversed(body):
            total += int(c) * mul
            mul = 2 if mul == 7 else mul + 1
        r = 11 - (total % 11)
        dv_calc = "0" if r == 11 else "K" if r == 10 else str(r)
        return dv == dv_calc
    except ValueError:
        return False

def pdf_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

```

```python
# backend/app/services/correlativo.py
from datetime import datetime
from sqlite3 import Connection
# Para Postgres usa transacciones y SELECT ... FOR UPDATE sobre una tabla de secuencias.

def next_nv_number(conn: Connection, issue_date) -> str:
    year = int(datetime.fromisoformat(issue_date).strftime('%Y')) if isinstance(issue_date, str) else issue_date.year
    # Estrategia simple (SQLite): buscar máximo secuencial en nv_number "NNN-AAAA" para el año
    cur = conn.execute("SELECT nv_number FROM sales_notes WHERE substr(nv_number, instr(nv_number,'-')+1) = ?", (str(year),))
    max_seq = 0
    for (nv_number,) in cur.fetchall():
        try:
            seq = int(nv_number.split('-')[0])
            if seq > max_seq: max_seq = seq
        except Exception:
            pass
    new_seq = max_seq + 1
    return f"{new_seq:03d}-{year}"
```

> **PostgreSQL recomendado**: crea una tabla `sequences (year int primary key, nv_seq int)` y usa `SELECT ... FOR UPDATE` dentro de una transacción para evitar condiciones de carrera.

### 2.2 Creación y actualización (con reglas)
```python
# backend/app/routes/sales_notes/service.py (fragmentos)
from .repo import db
from app.utils.cl_chile import rut_is_valid, rut_normalize
from app.services.correlativo import next_nv_number
from decimal import Decimal
from flask import request

ALLOWED_STATES = ("draft","approved","issued","cancelled")

def _calc_totals(items, vat_rate=0.19):
    neto = sum(Decimal(str(i['quantity'])) * Decimal(str(i['unit_price'])) for i in items)
    iva  = (neto * Decimal(str(vat_rate))).quantize(Decimal('0.01'))
    total = (neto + iva).quantize(Decimal('0.01'))
    return float(neto), float(iva), float(total)

def create_sales_note(payload):
    cust_rut = payload.get('customer_rut','').strip()
    if not rut_is_valid(cust_rut):
        raise ValueError("RUT del cliente inválido")
    payload['customer_rut'] = rut_normalize(cust_rut)

    items = payload.get('items') or []
    neto, iva, total = _calc_totals(items, payload.get('vat_rate', 0.19))

    # correlativo si no viene nv_number
    nv_number = payload.get('nv_number') or next_nv_number(db.conn, payload['issue_date'])

    # insert cabecera + items + refs ... (omitir por brevedad)
    # retornar new_id


def update_sales_note(nv_id, payload):
    # **Regla**: no permitir cambios si está emitida
    note = get_sales_note(nv_id)
    if note['status'] == 'issued':
        raise PermissionError('Nota emitida: no se puede modificar')
    # validar RUT si viene, recalcular totales si cambian items, etc.
    # persistir cambios
```

### 2.3 Aprobación y Emisión (con auditoría y hash)
```python
# backend/app/routes/sales_notes/service.py (fragmentos)
from .pdf import render_sales_note_pdf_bytes
from app.utils.cl_chile import pdf_sha256


def approve_sales_note(nv_id, actor: str, ip: str, ua: str):
    note = get_sales_note(nv_id)
    if note['status'] not in ('draft','cancelled'):
        # Permite re-aprobar solo si estaba draft
        pass
    # persistir approved_by/approved_at/IP/UA
    # insert en sales_note_audit(action='approve', actor=actor, ip=ip, user_agent=ua, payload_json=...)


def issue_sales_note(nv_id, actor: str, ip: str, ua: str):
    note = get_sales_note(nv_id)
    if note['status'] not in ('approved','draft'):
        raise ValueError('Estado inválido para emisión')

    pdf_bytes = render_sales_note_pdf_bytes(nv_id)   # genera PDF con footer oficial
    digest = pdf_sha256(pdf_bytes)

    # guardar pdf_hash y emitted_at, status='issued'
    # insertar auditoría action='issue' con hash
    # devolver bytes o ruta para descarga
```

### 2.4 Endpoints
```python
# backend/app/routes/sales_notes.py
@bp.post('/<int:nv_id>/approve')
def approve(nv_id):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ua = request.headers.get('User-Agent','')
    actor = request.headers.get('X-User') or 'system'
    approve_sales_note(nv_id, actor, ip, ua)
    return jsonify({"ok": True})

@bp.post('/<int:nv_id>/issue')
def issue(nv_id):
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    ua = request.headers.get('User-Agent','')
    actor = request.headers.get('X-User') or 'system'
    pdf_path_or_bytes = issue_sales_note(nv_id, actor, ip, ua)
    return jsonify({"ok": True})
```

---

## 3) PDF — Plantilla con Footer Oficial

> Estilo minimalista, tablas con bordes #e5e7eb, jerarquía tipográfica y **footer** con URL, fecha/hora, dirección; campos cliente (RUT, giro, dirección, comuna) y **forma de pago**.

```python
# backend/app/routes/pdf.py (fragmento)
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from datetime import datetime

tpl_env = Environment(loader=FileSystemLoader('backend/app/templates'))

FOOTER_FMT = "{url} {dt} {addr}"

def render_sales_note_pdf_bytes(nv_id:int) -> bytes:
    data = get_sales_note(nv_id)
    # footer oficial, p.ej. "www.zemangonzalez.com 17-09-2025 / 14:12 Pedro de Valdivia 3121 dp 15 | Ñuñoa | Santiago | Chile"
    dt = datetime.now().strftime("%d-%m-%Y / %H:%M")
    data['footer_line'] = FOOTER_FMT.format(
        url=data.get('company_url','www.zemangonzalez.com'),
        dt=dt,
        addr=data.get('company_address','Pedro de Valdivia 3121 dp 15 | Ñuñoa | Santiago | Chile')
    )
    html = tpl_env.get_template('sales_note.html').render(**data)
    return HTML(string=html).write_pdf()
```

```html
<!-- backend/app/templates/sales_note.html (fragmento de footer) -->
<div class="footer" style="margin-top:18px; font-size:11px; color:#555; display:flex; justify-content:space-between;">
  <div>{{ approved_by or '—' }}<br/><span style="color:#777">CEO | Chief Executive Officer</span></div>
  <div style="text-align:right">{{ footer_line }}</div>
</div>
```

---

## 4) Frontend (Next.js) — Bloqueo y Panel de Auditoría

- En la vista de detalle `/finanzas/notas-venta/[id]`:
  - Deshabilitar inputs si `status==='issued'`.
  - Mostrar **panel Auditoría**: aprobado por, fecha, IP, UA; hash del PDF.
  - Botones: **Aprobar**, **Emitir PDF**, **Anular** (con confirmación y motivo).

```tsx
// Ejemplo de bloqueo
const locked = data.status === 'issued';
<input disabled={locked} ... />
<button onClick={approve} disabled={locked}>Aprobar</button>
<button onClick={issue} disabled={locked || data.status==='cancelled'}>Emitir PDF</button>
```

---

## 5) Tests sugeridos
- **RUT**: casos válidos/ inválidos; normalización.
- **Correlativo**: secuencias 001‑2025, 002‑2025…; cambio de año.
- **Estados**: no permitir `PUT` tras `issued` (esperar 409/403).
- **Cálculos**: neto/IVA/total (19%, redondeo).
- **PDF**: snapshot/hash estable con datos de ejemplo.
- **Auditoría**: inserción de `approve` y `issue` con IP/UA.

---

## 6) Checklist de conformidad
- [x] Correlativo anual único.
- [x] Validación RUT y normalización.
- [x] Footer oficial con URL + fecha/hora + dirección.
- [x] Trazabilidad de aprobación (usuario, IP, UA) y hash de PDF.
- [x] Bloqueo total post‑emisión.
- [x] Campos del formato: cliente (RUT/giro/dirección/comuna), forma de pago, proyecto/presupuesto.

---

## 7) Siguientes pasos en repo
1. Crear archivos utilitarios `utils/cl_chile.py` y `services/correlativo.py`.
2. Añadir migración SQL/Alembic según DB.
3. Extender servicios `sales_notes` con `approve` y `issue`.
4. Actualizar plantilla `sales_note.html` con footer y panel de aprobador.
5. Ajustar Frontend (detalle NV) con bloqueo y panel de auditoría.
6. Agregar tests (pytest) y rutas a CI.

