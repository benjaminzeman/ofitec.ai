# Integración de BSale con OFITEC (Facturas, Ítems y Reconciliación)

Este documento describe cómo integrar la API de **BSale** con el proyecto **OFITEC** (https://github.com/benjaminzeman/ofitec.ai), una herramienta de automatización financiera para reconciliación de AP/PO, EP y AR, con backend en **Flask**, frontend en **Next.js 15**, y base de datos **SQLite** (`data/chipax_data.db`). La integración extrae **facturas de compra y venta**, sus **ítems** (detalles de productos) y **XML**, sincronizándolos en la base de datos, y los conecta con la lógica de reconciliación en `reconcile_engine.py`. Es concordante con los lineamientos de la carpeta `docs_oficiales`.

## Resumen
- **Objetivo**: Sincronizar facturas de compra y venta, sus ítems y XML desde BSale, y usarlos para reconciliación en OFITEC.
- **Método**: Crear un módulo `bsale_integration.py` con endpoints para sincronizar y consultar facturas, y extender `reconcile_engine.py` para matching.
- **Datos extraídos**:
  - Facturas: `bsale_id`, `document_type_id`, `emission_date`, `amount`, `client_id`, `xml`.
  - Ítems: `document_id`, `product_id`, `quantity`, `net_unit_value`.
- **Concordancia con `docs_oficiales`**:
  - Usa Flask Blueprints y endpoints `/api/*` (`backend.md`).
  - Almacena datos en `data/chipax_data.db` (`architecture.md`, `schema.sql`).
  - Sigue patrones de importación de datos externos (`README.md`, `reconcile_engine.md`).
  - Integra con el frontend Next.js (`frontend.md`).
- **Uso**: Los datos se guardan en tablas `bsale_documents` y `bsale_document_details`, accesibles desde el frontend y usables en `reconcile_engine.py`.

## Requisitos previos
- **Token de BSale**: Obtén un `access_token` desde el panel de BSale (https://developers.bsale.io/).
- **Dependencias**: Instala las librerías necesarias:
  ```bash
  pip install requests python-dotenv
  ```
- **Entorno**: Asegúrate de que el backend Flask (`backend/server.py`) y la base de datos SQLite (`data/chipax_data.db`) estén configurados.
- **Proyecto**: Clona el repositorio:
  ```bash
  git clone https://github.com/benjaminzeman/ofitec.ai
  cd ofitec.ai
  ```

## Código

### 1. Módulo de integración con BSale
Crea `backend/bsale_integration.py` con el siguiente contenido. Define un Blueprint con endpoints para sincronizar y consultar facturas e ítems.

```python
import requests
import json
import os
from flask import Blueprint, jsonify, current_app, request
from typing import List, Dict, Optional
import sqlite3
from sqlite3 import Error

# Blueprint para los endpoints de BSale
bsale_bp = Blueprint('bsale', __name__, url_prefix='/api/bsale')

class BSaleIntegrator:
    def __init__(self, access_token: str):
        self.base_url = "https://api.bsale.io/v1"
        self.headers = {
            "access_token": access_token,
            "Content-Type": "application/json"
        }
        self.db_path = "data/chipax_data.db"  # Ruta a la DB de OFITEC
    
    def get_documents(self, limit: int = 50, is_purchase: Optional[bool] = None) -> List[Dict]:
        """
        Obtiene facturas de compra y/o venta desde BSale.
        is_purchase: True (compras), False (ventas), None (ambas).
        """
        url = f"{self.base_url}/documents.json?limit={limit}"
        if is_purchase is not None:
            url += f"&isPurchase={str(is_purchase).lower()}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error al obtener documentos de BSale: {e}")
            return []
    
    def get_document_xml(self, document_id: int) -> Optional[str]:
        """
        Obtiene el XML de un documento en Base64.
        """
        url = f"{self.base_url}/documents/{document_id}/xml.json"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("xml", None)
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error al obtener XML del documento {document_id}: {e}")
            return None
    
    def sync_documents_to_ofitec(self, documents: List[Dict]) -> Dict[str, int]:
        """
        Sincroniza facturas y sus ítems a las tablas 'bsale_documents' y 'bsale_document_details'.
        Incluye XML en Base64.
        """
        synced_docs = 0
        synced_details = 0
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Crear tablas si no existen
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bsale_documents (
                    id INTEGER PRIMARY KEY,
                    bsale_id INTEGER UNIQUE,
                    document_type_id INTEGER,
                    emission_date TEXT,
                    amount REAL,
                    client_id INTEGER,
                    xml TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bsale_document_details (
                    id INTEGER PRIMARY KEY,
                    document_id INTEGER,
                    product_id INTEGER,
                    quantity REAL,
                    net_unit_value REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES bsale_documents (bsale_id)
                )
            ''')
            
            for doc in documents:
                bsale_id = doc.get('id')
                document_type_id = doc.get('documentTypeId')
                emission_date = doc.get('emissionDate')
                amount = doc.get('amount', 0)
                client_id = doc.get('clientId')
                
                # Obtener XML
                xml_content = self.get_document_xml(bsale_id) if bsale_id else None
                
                # Insertar/actualizar factura
                cursor.execute('''
                    INSERT OR REPLACE INTO bsale_documents (
                        bsale_id, document_type_id, emission_date, amount, client_id, xml
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (bsale_id, document_type_id, emission_date, amount, client_id, xml_content))
                
                if cursor.rowcount > 0:
                    synced_docs += 1
                
                # Sincronizar ítems (details)
                details = doc.get('details', [])
                for detail in details:
                    cursor.execute('''
                        INSERT OR REPLACE INTO bsale_document_details (
                            document_id, product_id, quantity, net_unit_value
                        ) VALUES (?, ?, ?, ?)
                    ''', (bsale_id, detail.get('productId'), detail.get('quantity'), detail.get('netUnitValue')))
                    if cursor.rowcount > 0:
                        synced_details += 1
            
            conn.commit()
            return {"synced_documents": synced_docs, "synced_details": synced_details}
        
        except Error as e:
            current_app.logger.error(f"Error en DB: {e}")
            return {"error": str(e)}
        finally:
            if conn:
                conn.close()

# Configuración: usa variable de entorno para el token
BSALE_TOKEN = os.getenv('BSALE_TOKEN', 'TU_ACCESS_TOKEN_AQUI')  # Reemplaza en .env

integrator = BSaleIntegrator(BSALE_TOKEN)

@bsale_bp.route('/documents/sync', methods=['POST'])
def sync_documents():
    """
    Endpoint para sincronizar facturas y sus ítems de BSale.
    Parámetros: limit (int), isPurchase (true/false/omitir).
    Ejemplo: POST /api/bsale/documents/sync?limit=10&isPurchase=true
    """
    limit = int(request.args.get('limit', 50))
    is_purchase = request.args.get('isPurchase', None)
    is_purchase = {'true': True, 'false': False}.get(is_purchase.lower()) if is_purchase else None
    documents = integrator.get_documents(limit=limit, is_purchase=is_purchase)
    if not documents:
        return jsonify({"error": "No se obtuvieron documentos"}), 500
    
    result = integrator.sync_documents_to_ofitec(documents)
    return jsonify(result)

@bsale_bp.route('/documents', methods=['GET'])
def get_synced_documents():
    """
    Obtiene facturas sincronizadas con sus ítems desde la DB de OFITEC.
    """
    conn = None
    try:
        conn = sqlite3.connect(integrator.db_path)
        cursor = conn.cursor()
        
        # Obtener facturas
        cursor.execute('SELECT * FROM bsale_documents ORDER BY updated_at DESC LIMIT 50')
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        documents = [dict(zip(columns, row)) for row in rows]
        
        # Obtener ítems para cada factura
        for doc in documents:
            cursor.execute('SELECT * FROM bsale_document_details WHERE document_id = ?', (doc['bsale_id'],))
            detail_rows = cursor.fetchall()
            detail_columns = [description[0] for description in cursor.description]
            doc['details'] = [dict(zip(detail_columns, row)) for row in detail_rows]
        
        return jsonify({"items": documents})
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
```

### 2. Extensión de reconciliación
Edita `backend/reconcile_engine.py` para añadir una función que realice matching de facturas de BSale con `invoices` o `purchase_orders`. Agrega al final del archivo:

```python
def match_bsale_invoices(self):
    """
    Realiza matching de facturas de BSale con invoices o purchase_orders.
    Compara por amount y emission_date.
    """
    conn = None
    try:
        conn = sqlite3.connect('data/chipax_data.db')
        cursor = conn.cursor()
        
        # Matching con invoices (ejemplo para facturas de venta)
        cursor.execute('''
            SELECT bd.bsale_id, bd.amount, bd.emission_date, i.id AS invoice_id, i.amount AS invoice_amount
            FROM bsale_documents bd
            LEFT JOIN invoices i
            ON ABS(bd.amount - i.amount) < 0.01
            AND bd.emission_date = i.date
            WHERE bd.document_type_id IN (5, 7)  -- Facturas electrónicas de venta
        ''')
        matches = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        invoice_matches = [dict(zip(columns, row)) for row in matches]
        
        # Matching con purchase_orders (ejemplo para facturas de compra)
        cursor.execute('''
            SELECT bd.bsale_id, bd.amount, bd.emission_date, po.id AS po_id, po.amount AS po_amount
            FROM bsale_documents bd
            LEFT JOIN purchase_orders po
            ON ABS(bd.amount - po.amount) < 0.01
            AND bd.emission_date = po.date
            WHERE bd.document_type_id IN (11, 13)  -- Facturas de compra
        ''')
        matches = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        po_matches = [dict(zip(columns, row)) for row in matches]
        
        return {
            "invoice_matches": invoice_matches,
            "purchase_order_matches": po_matches
        }
    
    except Error as e:
        current_app.logger.error(f"Error en reconciliación: {e}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()
```

Añade un endpoint en `reconcile_engine.py` para exponer la reconciliación:

```python
from flask import jsonify

@reconcile_bp.route('/match_bsale_invoices', methods=['GET'])
def match_bsale_invoices_endpoint():
    reconciler = ReconcileEngine()  # Asume que ReconcileEngine es la clase definida
    result = reconciler.match_bsale_invoices()
    return jsonify(result)
```

Asegúrate de registrar el Blueprint `reconcile_bp` en `server.py` si no está registrado.

## Instrucciones para integrar en OFITEC

Sigue estos pasos en **Visual Studio Code** para añadir la integración, respetando `docs_oficiales`.

### 1. Crea el archivo Markdown
- Abre Visual Studio Code y tu proyecto (`ofitec.ai/`).
- Crea un nuevo archivo: `docs_oficiales/BSale_Integration_OFITEC.md`.
- Copia este documento completo y guárdalo.

### 2. Configura el entorno
- Instala las dependencias:
  ```bash
  pip install requests python-dotenv
  ```
- Edita `.env` en la raíz del proyecto y añade el token:
  ```bash
  BSALE_TOKEN=tu_access_token_aqui
  ```
- En `backend/server.py`, carga variables de entorno:
  ```python
  from dotenv import load_dotenv
  load_dotenv()
  ```

### 3. Crea el módulo de integración
- Crea `backend/bsale_integration.py` y copia el código de la sección **Código: Módulo de integración con BSale**.
- Verifica que `BSALE_TOKEN` use la variable de entorno.

### 4. Registra los Blueprints
- Abre `backend/server.py` y añade:
  ```python
  from bsale_integration import bsale_bp
  app.register_blueprint(bsale_bp)
  ```
- Asegúrate de que `from flask import request` esté importado:
  ```python
  from flask import Flask, request
  ```
- Si el Blueprint `reconcile_bp` no está registrado, añádelo:
  ```python
  from reconcile_engine import reconcile_bp
  app.register_blueprint(reconcile_bp)
  ```

### 5. Configura la base de datos
- Actualiza `tools/apply_schema.py` para incluir las tablas `bsale_documents` y `bsale_document_details`:
  ```python
  cursor.execute('''
      CREATE TABLE IF NOT EXISTS bsale_documents (
          id INTEGER PRIMARY KEY,
          bsale_id INTEGER UNIQUE,
          document_type_id INTEGER,
          emission_date TEXT,
          amount REAL,
          client_id INTEGER,
          xml TEXT,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
  ''')
  cursor.execute('''
      CREATE TABLE IF NOT EXISTS bsale_document_details (
          id INTEGER PRIMARY KEY,
          document_id INTEGER,
          product_id INTEGER,
          quantity REAL,
          net_unit_value REAL,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (document_id) REFERENCES bsale_documents (bsale_id)
      )
  ''')
  ```
- Ejecuta las migraciones:
  ```bash
  python tools/apply_schema.py
  ```

### 6. Extiende la reconciliación
- Edita `backend/reconcile_engine.py` y añade la función `match_bsale_invoices` y el endpoint `match_bsale_invoices_endpoint` (sección **Código: Extensión de reconciliación**).
- Asegúrate de que `ReconcileEngine` sea la clase correcta o ajusta según tu implementación.

### 7. Prueba la integración
- Inicia el backend:
  ```bash
  cd backend
  python server.py
  ```
- Sincroniza facturas de compra:
  ```bash
  curl -X POST "http://localhost:5000/api/bsale/documents/sync?limit=5&isPurchase=true"
  ```
- Sincroniza facturas de venta:
  ```bash
  curl -X POST "http://localhost:5000/api/bsale/documents/sync?limit=5&isPurchase=false"
  ```
- Consulta facturas e ítems:
  ```bash
  curl "http://localhost:5000/api/bsale/documents"
  ```
- Prueba la reconciliación:
  ```bash
  curl "http://localhost:5000/api/reconcile/match_bsale_invoices"
  ```
- Verifica la base de datos:
  ```bash
  sqlite3 data/chipax_data.db
  SELECT * FROM bsale_documents;
  SELECT * FROM bsale_document_details;
  ```

### 8. Integra con el frontend
- Edita `app/dashboard/page.tsx` para mostrar facturas e ítems:
  ```tsx
  'use client';
  import { useState } from 'react';

  export default function BSaleDocuments() {
    const [result, setResult] = useState(null);
    const [matches, setMatches] = useState(null);

    async function syncBSaleDocuments(isPurchase) {
      const url = `/api/bsale/documents/sync?limit=10${isPurchase !== null ? `&isPurchase=${isPurchase}` : ''}`;
      const res = await fetch(url, { method: 'POST' });
      const data = await res.json();
      setResult(data);
    }

    async function fetchDocuments() {
      const res = await fetch('/api/bsale/documents');
      const data = await res.json();
      setResult(data);
    }

    async function fetchMatches() {
      const res = await fetch('/api/reconcile/match_bsale_invoices');
      const data = await res.json();
      setMatches(data);
    }

    return (
      <div>
        <button onClick={() => syncBSaleDocuments(true)}>Sincronizar Facturas de Compra</button>
        <button onClick={() => syncBSaleDocuments(false)}>Sincronizar Facturas de Venta</button>
        <button onClick={() => syncBSaleDocuments(null)}>Sincronizar Todas</button>
        <button onClick={fetchDocuments}>Ver Facturas</button>
        <button onClick={fetchMatches}>Ver Reconciliaciones</button>
        <h3>Facturas:</h3>
        <pre>{JSON.stringify(result, null, 2)}</pre>
        <h3>Reconciliaciones:</h3>
        <pre>{JSON.stringify(matches, null, 2)}</pre>
      </div>
    );
  }
  ```
- Para caching, usa `useSWR`:
  ```tsx
  import useSWR from 'swr';
  const fetcher = (url) => fetch(url).then((res) => res.json());
  const { data: documents, error: docError } = useSWR('/api/bsale/documents', fetcher);
  const { data: matches, error: matchError } = useSWR('/api/reconcile/match_bsale_invoices', fetcher);
  ```

### 9. Commitea los cambios
- Usa Visual Studio Code (`Ctrl + Shift + G`):
  ```bash
  git add .
  git commit -m "Añade integración con BSale para facturas, ítems y reconciliación"
  git push origin main
  ```

## Extender la integración
- **XML**: Procesa el XML (Base64) si necesitas extraer datos específicos:
  ```python
  import base64
  xml_string = base64.b64decode(xml_content).decode('utf-8')
  ```
- **Filtros avanzados**: Añade parámetros a `get_documents` (ej. `documentTypeId=5` para facturas electrónicas).
- **Reconciliación avanzada**: Incluye ítems en el matching comparando `bsale_document_details` con `invoices` o `purchase_orders`.
- **Seguridad**: Añade JWT a los endpoints (`backend.md`).
- **Reintentos**: Usa `tenacity`:
  ```bash
  pip install tenacity
  ```
  ```python
  from tenacity import retry, stop_after_attempt, wait_fixed

  @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
  def get_documents(self, limit: int = 50, is_purchase: Optional[bool] = None):
      ...
  ```

## Notas
- **Datos extraídos**: Facturas (`bsale_id`, `document_type_id`, `emission_date`, `amount`, `client_id`, `xml`) y sus ítems (`document_id`, `product_id`, `quantity`, `net_unit_value`).
- **Concordancia**:
  - **Arquitectura**: Usa Flask Blueprints y SQLite (`architecture.md`, `backend.md`).
  - **Schema**: Extiende `schema.sql` con `bsale_documents` y `bsale_document_details`.
  - **Frontend**: Endpoints consumibles por Next.js (`frontend.md`).
  - **Reconciliación**: Matching con `invoices` y `purchase_orders` (`reconcile_engine.md`).
- **Depuración**: Revisa logs (`current_app.logger.error`) o usa `sqlite3 data/chipax_data.db`.
- **Soporte**: Si necesitas más campos o ajustes en la reconciliación, describe el caso.