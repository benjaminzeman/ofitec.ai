# Integración con SII (Chile) — Ofitec.ai (Next.js + Flask + PostgreSQL)

Este documento te deja **explicación y programación lista para pegar** (drop‑in) en tu monorepo (Visual Studio). Cubre **consulta/ingesta** de datos del SII por dos vías:

1) **Servicios Oficiales (FEA .p12/.pfx)** → flujo semilla → firma → token → consulta de **RCV** y **estado DTE**.
2) **Sesión con usuario/clave** (solo si no hay WS) → login controlado, cookies cifradas y descarga de archivos (CSV/Excel/HTML) para normalizar.

Se ajusta a tus **docs oficiales**: *Ley de Puertos* (un frontend 3001 / un backend 5555), *Ley de BD* (auditoría, hash, backups 3‑2‑1) y *Portal/Visual* (página de integraciones con progreso en vivo).

---

## 0) Requisitos

### Python (backend)
```bash
pip install flask flask_sqlalchemy sqlalchemy alembic requests cryptography
pip install signxml lxml zeep
pip install celery redis cachetools itsdangerous
```
> Puedes omitir `celery/redis` si no usarás tareas asíncronas (ver §4.4 plan B).

### Node (frontend)
No requiere librerías adicionales. Usaremos fetch y EventSource (SSE).

### Infra/entorno
- Backend en **5555** y Frontend en **3001** (Ley de Puertos).
- Variables de entorno:
```
SII_CERT_P12_PATH=/secure/empresa.p12
SII_CERT_P12_PASS=********
SII_RUT=76123456
SII_DV=K
SII_AMBIENTE=cert|prod
# Opcional si usas Celery
REDIS_URL=redis://localhost:6379/0
# Cifrado de cookies de sesión (si usas user/clave)
FERNET_KEY=base64urlfernetkey...
```

---

## 1) Modelo de Datos (SQLAlchemy) + Alembic

### 1.1 `backend/app/models/sii.py`
```python
# backend/app/models/sii.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()

class SiiToken(db.Model):
    __tablename__ = 'sii_tokens'
    id = db.Column(db.Integer, primary_key=True)
    ambiente = db.Column(db.String(10), nullable=False)
    token = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SiiEnvio(db.Model):
    __tablename__ = 'sii_envios'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # DTE, BOLETA
    track_id = db.Column(db.String(64), index=True)
    estado = db.Column(db.String(20), default='enviado')  # enviado|aceptado|observado|rechazado
    xml_hash = db.Column(db.String(64), nullable=False)
    rut_emisor = db.Column(db.String(12), nullable=False)
    periodo = db.Column(db.String(7))  # YYYY-MM para agrupaciones
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SiiEvento(db.Model):
    __tablename__ = 'sii_eventos'
    id = db.Column(db.Integer, primary_key=True)
    envio_id = db.Column(db.Integer, db.ForeignKey('sii_envios.id'), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)  # seguimiento, error, cambio_estado
    detalle = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SiiRcvSale(db.Model):
    __tablename__ = 'sii_rcv_sales'
    id = db.Column(db.Integer, primary_key=True)
    periodo = db.Column(db.String(7), index=True)  # YYYY-MM
    rut_receptor = db.Column(db.String(12))
    rut_emisor = db.Column(db.String(12))
    tipo_dte = db.Column(db.String(4))
    folio = db.Column(db.String(20))
    fecha_emision = db.Column(db.Date)
    neto = db.Column(db.Numeric)
    iva = db.Column(db.Numeric)
    exento = db.Column(db.Numeric)
    total = db.Column(db.Numeric)
    estado_sii = db.Column(db.String(20))
    xml_hash = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint('periodo','rut_emisor','tipo_dte','folio', name='uq_rcv_sale_doc'),
    )

class SiiRcvPurchase(db.Model):
    __tablename__ = 'sii_rcv_purchases'
    id = db.Column(db.Integer, primary_key=True)
    periodo = db.Column(db.String(7), index=True)
    rut_emisor = db.Column(db.String(12))
    rut_receptor = db.Column(db.String(12))
    tipo_dte = db.Column(db.String(4))
    folio = db.Column(db.String(20))
    fecha_emision = db.Column(db.Date)
    neto = db.Column(db.Numeric)
    iva = db.Column(db.Numeric)
    exento = db.Column(db.Numeric)
    total = db.Column(db.Numeric)
    estado_sii = db.Column(db.String(20))
    xml_hash = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint('periodo','rut_emisor','tipo_dte','folio', name='uq_rcv_purchase_doc'),
    )

class SiiSession(db.Model):
    __tablename__ = 'sii_sessions'
    id = db.Column(db.Integer, primary_key=True)
    owner_user_id = db.Column(db.Integer, index=True)
    cookies_cipher = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### 1.2 Alembic (migración)
```bash
alembic revision -m "sii tables"
```
```python
# alembic/versions/<hash>_sii_tables.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('sii_tokens',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('ambiente', sa.String(10), nullable=False),
        sa.Column('token', sa.Text, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime))
    op.create_table('sii_envios',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('track_id', sa.String(64)),
        sa.Column('estado', sa.String(20)),
        sa.Column('xml_hash', sa.String(64), nullable=False),
        sa.Column('rut_emisor', sa.String(12), nullable=False),
        sa.Column('periodo', sa.String(7)),
        sa.Column('created_at', sa.DateTime),
        sa.Column('updated_at', sa.DateTime))
    op.create_index('ix_envio_track', 'sii_envios', ['track_id'])

    op.create_table('sii_eventos',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('envio_id', sa.Integer, sa.ForeignKey('sii_envios.id'), nullable=False),
        sa.Column('tipo', sa.String(30), nullable=False),
        sa.Column('detalle', sa.Text),
        sa.Column('created_at', sa.DateTime))

    op.create_table('sii_rcv_sales',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('periodo', sa.String(7)),
        sa.Column('rut_receptor', sa.String(12)),
        sa.Column('rut_emisor', sa.String(12)),
        sa.Column('tipo_dte', sa.String(4)),
        sa.Column('folio', sa.String(20)),
        sa.Column('fecha_emision', sa.Date),
        sa.Column('neto', sa.Numeric),
        sa.Column('iva', sa.Numeric),
        sa.Column('exento', sa.Numeric),
        sa.Column('total', sa.Numeric),
        sa.Column('estado_sii', sa.String(20)),
        sa.Column('xml_hash', sa.String(64)),
        sa.Column('created_at', sa.DateTime))
    op.create_unique_constraint('uq_rcv_sale_doc','sii_rcv_sales', ['periodo','rut_emisor','tipo_dte','folio'])

    op.create_table('sii_rcv_purchases',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('periodo', sa.String(7)),
        sa.Column('rut_emisor', sa.String(12)),
        sa.Column('rut_receptor', sa.String(12)),
        sa.Column('tipo_dte', sa.String(4)),
        sa.Column('folio', sa.String(20)),
        sa.Column('fecha_emision', sa.Date),
        sa.Column('neto', sa.Numeric),
        sa.Column('iva', sa.Numeric),
        sa.Column('exento', sa.Numeric),
        sa.Column('total', sa.Numeric),
        sa.Column('estado_sii', sa.String(20)),
        sa.Column('xml_hash', sa.String(64)),
        sa.Column('created_at', sa.DateTime))
    op.create_unique_constraint('uq_rcv_purchase_doc','sii_rcv_purchases', ['periodo','rut_emisor','tipo_dte','folio'])

    op.create_table('sii_sessions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('owner_user_id', sa.Integer),
        sa.Column('cookies_cipher', sa.Text, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime))

def downgrade():
    op.drop_table('sii_sessions')
    op.drop_constraint('uq_rcv_purchase_doc','sii_rcv_purchases', type_='unique')
    op.drop_table('sii_rcv_purchases')
    op.drop_constraint('uq_rcv_sale_doc','sii_rcv_sales', type_='unique')
    op.drop_table('sii_rcv_sales')
    op.drop_table('sii_eventos')
    op.drop_index('ix_envio_track','sii_envios')
    op.drop_table('sii_envios')
    op.drop_table('sii_tokens')
```

---

## 2) Servicios SII (cliente + firma XML)

### 2.1 `backend/app/services/sii/xmlsign.py`
```python
# backend/app/services/sii/xmlsign.py
from signxml import XMLSigner, methods
from OpenSSL import crypto

def load_p12(p12_path: str, password: str):
    with open(p12_path, 'rb') as f:
        p12 = crypto.load_pkcs12(f.read(), password.encode())
    cert = crypto.dump_certificate(crypto.FILETYPE_PEM, p12.get_certificate())
    key = crypto.dump_privatekey(crypto.FILETYPE_PEM, p12.get_privatekey())
    return cert, key

def sign_xml(xml_bytes: bytes, cert_pem: bytes, key_pem: bytes) -> bytes:
    signer = XMLSigner(method=methods.enveloped, digest_algorithm='sha256')
    return signer.sign(xml_bytes, key=key_pem, cert=cert_pem)
```

### 2.2 `backend/app/services/sii/client.py`
```python
# backend/app/services/sii/client.py
import os, datetime
from cachetools import TTLCache
from .xmlsign import load_p12, sign_xml
# from zeep import Client  # opcional, si usas SOAP

class SiiClient:
    def __init__(self, ambiente: str = None):
        self.ambiente = ambiente or os.getenv('SII_AMBIENTE','cert')
        self.rut = os.getenv('SII_RUT')
        self.dv = os.getenv('SII_DV')
        self.p12 = os.getenv('SII_CERT_P12_PATH')
        self.pwd = os.getenv('SII_CERT_P12_PASS')
        self._tk_cache = TTLCache(maxsize=1, ttl=50*60)  # ~50 min

    # --- Semilla/Token (esqueleto) ---
    def _get_seed_xml(self) -> bytes:
        # Llamada al endpoint de semilla → devuelve XML (bytes)
        # Ej: requests.get(url_semilla).content
        raise NotImplementedError

    def _get_token_from_signed_seed(self, signed_seed_xml: bytes) -> str:
        # POST XML firmado → respuesta con token
        raise NotImplementedError

    def token(self) -> str:
        if 'token' in self._tk_cache:
            return self._tk_cache['token']
        cert_pem, key_pem = load_p12(self.p12, self.pwd)
        seed_xml = self._get_seed_xml()
        signed = sign_xml(seed_xml, cert_pem, key_pem)
        tk = self._get_token_from_signed_seed(signed)
        self._tk_cache['token'] = tk
        return tk

    # --- Estado DTE (ejemplo de firma y consulta) ---
    def get_dte_status(self, track_id: str) -> dict:
        tk = self.token()
        # Llamar endpoint estado con header Token= tk
        # Normalizar a {estado, glosa, observaciones: []}
        raise NotImplementedError

    # --- RCV (ventas/compras) ---
    def fetch_rcv_sales(self, year: int, month: int) -> list[dict]:
        tk = self.token()
        # GET/POST a servicio RCV ventas → lista de dicts normalizados
        raise NotImplementedError

    def fetch_rcv_purchases(self, year: int, month: int) -> list[dict]:
        tk = self.token()
        raise NotImplementedError
```
> **Nota:** Los `NotImplementedError` marcan el punto donde debes invocar el servicio real del SII (SOAP/REST) y parsear la respuesta. La estructura del cliente, autenticación y firma ya queda preparada.

---

## 3) Endpoints Flask (API REST + SSE)

### 3.1 `backend/app/routes/sii.py`
```python
# backend/app/routes/sii.py
import os, json, base64
from datetime import datetime, timedelta, date
from flask import Blueprint, request, jsonify, Response
from ..models.sii import db, SiiToken, SiiEnvio, SiiEvento, SiiRcvSale, SiiRcvPurchase, SiiSession
from ..services.sii.client import SiiClient
from itsdangerous import TimestampSigner
from cryptography.fernet import Fernet

bp = Blueprint('sii', __name__, url_prefix='/api/v1/sii')

# --- Helpers cifrado de cookies (para user/clave) ---
FERNET_KEY = os.getenv('FERNET_KEY').encode() if os.getenv('FERNET_KEY') else None
fernet = Fernet(FERNET_KEY) if FERNET_KEY else None

@bp.get('/token')
def get_token():
    tk = SiiClient().token()
    return jsonify({ 'token': tk })

@bp.get('/dte/estado/<track_id>')
def dte_estado(track_id):
    st = SiiClient().get_dte_status(track_id)
    return jsonify(st)

@bp.post('/rcv/import')
def rcv_import():
    data = request.get_json() or {}
    year = int(data.get('year'))
    month = int(data.get('month'))
    cli = SiiClient()
    ventas = cli.fetch_rcv_sales(year, month)
    compras = cli.fetch_rcv_purchases(year, month)
    periodo = f"{year:04d}-{month:02d}"

    # upsert simple (ejemplo)
    for v in ventas:
        rec = SiiRcvSale(
            periodo=periodo,
            rut_receptor=v.get('rut_receptor'),
            rut_emisor=v.get('rut_emisor'),
            tipo_dte=v.get('tipo_dte'), folio=v.get('folio'),
            fecha_emision=v.get('fecha_emision'),
            neto=v.get('neto'), iva=v.get('iva'), exento=v.get('exento'), total=v.get('total'),
            estado_sii=v.get('estado_sii'), xml_hash=v.get('xml_hash')
        )
        db.session.merge(rec)
    for c in compras:
        rec = SiiRcvPurchase(
            periodo=periodo,
            rut_receptor=c.get('rut_receptor'),
            rut_emisor=c.get('rut_emisor'),
            tipo_dte=c.get('tipo_dte'), folio=c.get('folio'),
            fecha_emision=c.get('fecha_emision'),
            neto=c.get('neto'), iva=c.get('iva'), exento=c.get('exento'), total=c.get('total'),
            estado_sii=c.get('estado_sii'), xml_hash=c.get('xml_hash')
        )
        db.session.merge(rec)
    db.session.commit()
    return jsonify({'ok': True, 'periodo': periodo, 'ventas': len(ventas), 'compras': len(compras)})

# --- Sesión user/clave (opcional) ---
@bp.post('/session/start')
def session_start():
    # Recibe {username, password}; no almacenamos password, sólo cookies cifradas
    # Aquí deberías automatizar un login controlado (requests+headers, resolver captcha con input del user)
    cookies_str = 'SIISESSION=...'  # placeholder tras login
    exp = datetime.utcnow() + timedelta(hours=2)
    cipher = fernet.encrypt(cookies_str.encode()).decode() if fernet else cookies_str
    sess = SiiSession(owner_user_id=0, cookies_cipher=cipher, expires_at=exp)
    db.session.add(sess); db.session.commit()
    return jsonify({'session_id': sess.id, 'expires_at': exp.isoformat()})

@bp.post('/session/pull')
def session_pull():
    # Descarga páginas/CSV usando cookies de una sesión válida y normaliza a RCV
    # Implementación específica depende de la pantalla objetivo
    return jsonify({'ok': True})

# --- SSE de progreso (simple demo) ---
@bp.get('/events')
def events():
    def stream():
        yield 'event: ping\n'
        yield 'data: {"ts": "%s"}\n\n' % datetime.utcnow().isoformat()
    return Response(stream(), mimetype='text/event-stream')
```

> **Registro en tu app**: `app.register_blueprint(sii.bp)` y añade el `db.init_app(app)` si aún no lo tienes.

---

## 4) Tareas en segundo plano (opcional)

### 4.1 Celery (broker Redis)
```python
# backend/celery_app.py
import os
from celery import Celery

celery = Celery(__name__, broker=os.getenv('REDIS_URL','redis://localhost:6379/0'))
celery.conf.result_backend = os.getenv('REDIS_URL','redis://localhost:6379/0')
```

### 4.2 Tasks de seguimiento/ingesta
```python
# backend/app/tasks/sii_tasks.py
from . import celery
from ..services.sii.client import SiiClient
from ..models.sii import db, SiiEnvio, SiiEvento

@celery.task
def seguimiento_dte(track_id: str):
    st = SiiClient().get_dte_status(track_id)
    ev = SiiEvento(envio_id=None, tipo='seguimiento', detalle=str(st))
    db.session.add(ev); db.session.commit()
    return st

@celery.task
def importar_rcv(year: int, month: int):
    cli = SiiClient()
    v = cli.fetch_rcv_sales(year, month)
    c = cli.fetch_rcv_purchases(year, month)
    # Reusar lógica de persistencia del endpoint
    return {'ventas': len(v), 'compras': len(c)}
```

### 4.3 Llamado desde API
```python
# desde /rcv/import si quieres async
# task = importar_rcv.delay(year, month)
# return jsonify({'job_id': task.id})
```

### 4.4 Plan B sin Redis/Celery
Usa un `threading.Thread` para no bloquear la petición. Menos robusto, pero suficiente si no quieres añadir Redis ahora.

---

## 5) Frontend (Next.js 14) — Página /integraciones/sii

### 5.1 `frontend/app/integraciones/sii/page.tsx`
```tsx
'use client'
import { useState } from 'react'

export default function SiiIntegrationPage(){
  const [year,setYear]=useState<number>(new Date().getFullYear())
  const [month,setMonth]=useState<number>(new Date().getMonth()+1)
  const [log,setLog]=useState<string>('')

  async function fetchToken(){
    const res = await fetch(process.env.NEXT_PUBLIC_API_BASE+"/sii/token")
    const j = await res.json();
    setLog(l=>l+`\nToken OK: ${j.token?.slice(0,10)}...`)
  }
  async function importRCV(){
    const res = await fetch(process.env.NEXT_PUBLIC_API_BASE+"/sii/rcv/import",{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({year, month})
    })
    const j = await res.json();
    setLog(l=>l+`\nRCV ${j.periodo}: ventas=${j.ventas}, compras=${j.compras}`)
  }
  function startSSE(){
    const es = new EventSource(process.env.NEXT_PUBLIC_API_BASE+"/sii/events")
    es.onmessage = (e)=> setLog(l=>l+`\nSSE: ${e.data}`)
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Integración SII</h1>
      <div className="flex gap-2 items-center">
        <label>Año</label>
        <input type="number" value={year} onChange={e=>setYear(parseInt(e.target.value))} className="border px-2 py-1 rounded"/>
        <label>Mes</label>
        <input type="number" value={month} onChange={e=>setMonth(parseInt(e.target.value))} className="border px-2 py-1 rounded"/>
        <button onClick={fetchToken} className="px-3 py-1 rounded bg-black text-white">Probar Token</button>
        <button onClick={importRCV} className="px-3 py-1 rounded bg-black text-white">Importar RCV</button>
        <button onClick={startSSE} className="px-3 py-1 rounded border">Conectar SSE</button>
      </div>
      <pre className="bg-gray-100 p-3 rounded whitespace-pre-wrap">{log}</pre>
    </div>
  )
}
```

---

## 6) Seguridad y Cumplimiento (resumen operativo)
- **Certificados**: guarda el .p12 en ruta protegida (`/secure`) y restringe permisos del sistema.
- **Vault/KMS**: ideal para `SII_CERT_P12_PASS` y `FERNET_KEY`.
- **Auditoría**: registra cada importación/consulta en `sii_eventos` con timestamp.
- **Hashing**: calcula SHA‑256 del XML/CSV que guardes; almacena en `xml_hash`.
- **Backups**: incluye las nuevas tablas en tus jobs 3‑2‑1.
- **Roles**: expón `/integraciones/sii` solo a **Finanzas/Admin**.

---

## 7) Pruebas rápidas (pytest)
```python
# tests/test_sii_api.py
from app import create_app

def test_token(client):
    r = client.get('/api/v1/sii/token')
    assert r.status_code in (200, 501)  # 501 si aún no implementaste el WS real

def test_rcv_import_shape(client, monkeypatch):
    from app.services.sii.client import SiiClient
    monkeypatch.setattr(SiiClient,'fetch_rcv_sales', lambda self,y,m: [])
    monkeypatch.setattr(SiiClient,'fetch_rcv_purchases', lambda self,y,m: [])
    r = client.post('/api/v1/sii/rcv/import', json={'year':2025,'month':8})
    assert r.status_code==200
```

---

## 8) Cómo encajar todo (checklist)
1. Crear archivos tal cual en rutas indicadas y correr **Alembic upgrade**.
2. Registrar `sii.bp` en tu app Flask y exponer `/api/v1/sii/*` junto a `/api/health`.
3. Configurar variables de entorno y, si usas Celery, **Redis**.
4. Añadir la página `/integraciones/sii` al menú del portal (solo Finanzas/Admin).
5. Implementar las llamadas reales del SII donde dice `NotImplementedError`.
6. Probar en **ambiente certificación** y luego pasar a **producción**.

---

## 9) Extensiones sugeridas
- **Conciliación RCV ↔ AR/AP**: endpoint que compare `sii_rcv_*` con tus facturas internas y muestre diffs.
- **Alertas**: si RCV trae DTE observado/rechazado → Slack/email.
- **Importador masivo**: job que recorra meses atrasados automáticamente.

---

> Cualquier parte que quieras que entregue ya con **código final (sin NotImplemented)**, dime el servicio exacto del SII que usaremos y lo completo en este mismo archivo del chat.

