# SPRINT 5: Integración SII y Infraestructura Productiva

## Objetivos

- Implementar integración completa con SII (servicios oficiales + sesión manual)
- Establecer infraestructura productiva con CI/CD robusto
- Implementar sistema de backups 3-2-1 y monitorización
- Preparar deployment blue/green con alta disponibilidad

## Tareas Priority 1

### 1. Integración SII Completa

**Archivos:** `backend/sii/`, `frontend/app/integraciones/sii/`

#### 1.1 Cliente SII con firma digital

```python
# backend/sii/sii_client.py
import os
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree
import base64

class SiiClient:
    def __init__(self):
        self.ambiente = os.getenv('SII_AMBIENTE', 'cert')  # cert|prod
        self.rut = os.getenv('SII_RUT')
        self.dv = os.getenv('SII_DV')
        self.cert_path = os.getenv('SII_CERT_P12_PATH')
        self.cert_password = os.getenv('SII_CERT_P12_PASS')
        self.base_url = self._get_base_url()
        self._token_cache = {}
    
    def _get_base_url(self):
        if self.ambiente == 'prod':
            return 'https://palena.sii.cl'
        return 'https://maullin.sii.cl'  # certificación
    
    def get_token(self):
        """Obtener token de autenticación via semilla firmada"""
        if 'token' in self._token_cache and not self._is_token_expired():
            return self._token_cache['token']
        
        # 1. Solicitar semilla
        semilla = self._get_semilla()
        
        # 2. Firmar semilla
        semilla_firmada = self._sign_seed(semilla)
        
        # 3. Obtener token
        token = self._get_token_from_signed_seed(semilla_firmada)
        
        self._token_cache = {
            'token': token,
            'expires_at': datetime.utcnow() + timedelta(minutes=50)
        }
        
        return token
    
    def _get_semilla(self):
        """Solicitar semilla al SII"""
        url = f"{self.base_url}/DTEWS/CrSeed.jws"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parsear respuesta XML
        root = etree.fromstring(response.content)
        semilla = root.find('.//SEMILLA').text
        return semilla
    
    def _sign_seed(self, semilla):
        """Firmar semilla con certificado digital"""
        # Cargar certificado P12
        with open(self.cert_path, 'rb') as f:
            p12_data = f.read()
        
        from cryptography.hazmat.primitives.serialization import pkcs12
        private_key, certificate, _ = pkcs12.load_key_and_certificates(
            p12_data, 
            self.cert_password.encode()
        )
        
        # Crear XML para firmar
        seed_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <getToken>
            <item>
                <Semilla>{semilla}</Semilla>
            </item>
        </getToken>"""
        
        # Firmar XML (simplificado - en producción usar signxml)
        signature = private_key.sign(
            seed_xml.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        signed_xml = self._wrap_signature(seed_xml, signature, certificate)
        return signed_xml
    
    def _get_token_from_signed_seed(self, signed_seed):
        """Obtener token enviando semilla firmada"""
        url = f"{self.base_url}/DTEWS/GetTokenFromSeed.jws"
        headers = {'Content-Type': 'application/xml'}
        
        response = requests.post(url, data=signed_seed, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parsear token de respuesta
        root = etree.fromstring(response.content)
        token = root.find('.//TOKEN').text
        return token
    
    def get_rcv_sales(self, year, month):
        """Obtener Registro Compra y Venta - Ventas"""
        token = self.get_token()
        
        url = f"{self.base_url}/DTEWS/QueryEstUp.jws"
        params = {
            'TOKEN': token,
            'RUT': self.rut,
            'DV': self.dv,
            'ESTADO': 'ACTIVO',
            'TIPO': 'VENTAS',
            'PERIODO': f"{year}{month:02d}"
        }
        
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        return self._parse_rcv_response(response.content)
    
    def get_rcv_purchases(self, year, month):
        """Obtener Registro Compra y Venta - Compras"""
        token = self.get_token()
        
        url = f"{self.base_url}/DTEWS/QueryEstUp.jws"  
        params = {
            'TOKEN': token,
            'RUT': self.rut,
            'DV': self.dv,
            'ESTADO': 'ACTIVO', 
            'TIPO': 'COMPRAS',
            'PERIODO': f"{year}{month:02d}"
        }
        
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        return self._parse_rcv_response(response.content)
    
    def _parse_rcv_response(self, xml_content):
        """Parsear respuesta XML del RCV"""
        root = etree.fromstring(xml_content)
        documentos = []
        
        for doc in root.findall('.//DOCUMENTO'):
            documento = {
                'rut_emisor': doc.find('RUT_EMISOR')?.text,
                'rut_receptor': doc.find('RUT_RECEPTOR')?.text, 
                'tipo_dte': doc.find('TIPO_DTE')?.text,
                'folio': doc.find('FOLIO')?.text,
                'fecha_emision': doc.find('FECHA_EMISION')?.text,
                'neto': float(doc.find('NETO')?.text or 0),
                'iva': float(doc.find('IVA')?.text or 0),
                'exento': float(doc.find('EXENTO')?.text or 0), 
                'total': float(doc.find('TOTAL')?.text or 0),
                'estado_sii': doc.find('ESTADO')?.text
            }
            documentos.append(documento)
        
        return documentos
```

#### 1.2 API endpoints SII

```python
# backend/api_sii.py
from flask import Blueprint, request, jsonify, Response
import json
from datetime import datetime

bp = Blueprint('sii', __name__)

@bp.route('/api/sii/token', methods=['GET'])
def get_sii_token():
    """Verificar token SII"""
    try:
        client = SiiClient()
        token = client.get_token()
        
        return jsonify({
            'status': 'ok',
            'token_preview': token[:20] + '...',
            'ambiente': client.ambiente
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/sii/rcv/import', methods=['POST'])
def import_rcv_data():
    """Importar datos RCV del SII"""
    data = request.get_json()
    year = int(data.get('year'))
    month = int(data.get('month'))
    
    try:
        client = SiiClient()
        
        # Obtener datos
        ventas = client.get_rcv_sales(year, month)
        compras = client.get_rcv_purchases(year, month)
        
        # Persistir en BD
        periodo = f"{year:04d}-{month:02d}"
        
        # Ventas
        for venta in ventas:
            record = SiiRcvSale(
                periodo=periodo,
                rut_emisor=venta['rut_emisor'],
                rut_receptor=venta['rut_receptor'],
                tipo_dte=venta['tipo_dte'],
                folio=venta['folio'],
                fecha_emision=datetime.strptime(venta['fecha_emision'], '%Y-%m-%d').date(),
                neto=venta['neto'],
                iva=venta['iva'],
                exento=venta['exento'],
                total=venta['total'],
                estado_sii=venta['estado_sii']
            )
            db.session.merge(record)  # upsert
        
        # Compras  
        for compra in compras:
            record = SiiRcvPurchase(
                periodo=periodo,
                rut_emisor=compra['rut_emisor'],
                rut_receptor=compra['rut_receptor'],
                tipo_dte=compra['tipo_dte'],
                folio=compra['folio'],
                fecha_emision=datetime.strptime(compra['fecha_emision'], '%Y-%m-%d').date(),
                neto=compra['neto'],
                iva=compra['iva'],
                exento=compra['exento'],
                total=compra['total'],
                estado_sii=compra['estado_sii']
            )
            db.session.merge(record)
        
        db.session.commit()
        
        return jsonify({
            'ok': True,
            'periodo': periodo,
            'ventas_importadas': len(ventas),
            'compras_importadas': len(compras)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/sii/events', methods=['GET'])
def sii_events_stream():
    """Stream SSE de eventos SII"""
    def generate():
        yield f"data: {json.dumps({'event': 'connected', 'timestamp': datetime.now().isoformat()})}\n\n"
        
        # En implementación real, esto sería un stream de eventos reales
        import time
        for i in range(5):
            time.sleep(2)
            event = {
                'event': 'import_progress',
                'progress': (i + 1) * 20,
                'message': f'Procesando datos SII... {(i + 1) * 20}%'
            }
            yield f"data: {json.dumps(event)}\n\n"
    
    return Response(generate(), mimetype='text/plain')
```

### 2. Infraestructura CI/CD

**Archivos:** `.github/workflows/deploy.yml`, `docker-compose.prod.yml`, `scripts/deploy.sh`

#### 2.1 Pipeline CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install Python dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov black flake8
      
      - name: Install Node dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Lint Python
        run: |
          cd backend
          black --check .
          flake8 .
      
      - name: Lint Frontend
        run: |
          cd frontend
          npm run lint
      
      - name: Test Python
        run: |
          cd backend
          pytest --cov=. --cov-report=xml
      
      - name: Test Frontend
        run: |
          cd frontend
          npm run test
      
      - name: Verify Ports Compliance
        run: |
          # Verificar que solo se usan puertos 3001 y 5555
          if grep -r ":300[0|2-9]\|:8000\|:8080" . --exclude-dir=.git --exclude-dir=node_modules; then
            echo "ERROR: Puertos no autorizados detectados"
            exit 1
          fi
          echo "✅ Cumplimiento Ley de Puertos verificado"

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/master'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker Images
        run: |
          docker build -t ofitec-backend:${{ github.sha }} ./backend
          docker build -t ofitec-frontend:${{ github.sha }} ./frontend
      
      - name: Push to Registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push ofitec-backend:${{ github.sha }}
          docker push ofitec-frontend:${{ github.sha }}

  deploy:
    needs: [test, build]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/master'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Pre-Deploy Backup
        run: |
          ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} '
            cd /opt/ofitec &&
            sudo -u postgres pg_dump ofitec_prod > backup_pre_deploy_$(date +%Y%m%d_%H%M%S).sql
          '
      
      - name: Deploy Blue/Green
        run: |
          ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} '
            cd /opt/ofitec &&
            ./scripts/blue_green_deploy.sh ${{ github.sha }}
          '
      
      - name: Health Check
        run: |
          # Verificar que la aplicación responde correctamente
          for i in {1..30}; do
            if curl -f http://prod.ofitec.ai:5555/api/status; then
              echo "✅ Health check passed"
              break
            fi
            sleep 10
          done
      
      - name: Notify Success
        run: |
          curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
          -H 'Content-type: application/json' \
          --data '{"text":"✅ Ofitec.ai deployed successfully to production"}'
```

### 3. Sistema de Backups 3-2-1

**Archivos:** `scripts/backup_system.sh`, `scripts/restore.sh`

#### 3.1 Script de backup automatizado

```bash
#!/bin/bash
# scripts/backup_system.sh

set -e

# Configuración
DB_NAME="ofitec_prod"
DB_USER="postgres"
BACKUP_DIR="/opt/backups/ofitec"
S3_BUCKET="ofitec-backups"
RETENTION_DAYS=30

# Crear directorio de backup
mkdir -p "$BACKUP_DIR"

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="ofitec_backup_${TIMESTAMP}.sql"
BACKUP_COMPRESSED="ofitec_backup_${TIMESTAMP}.sql.gz"

echo "🔄 Iniciando backup de Ofitec.ai - $(date)"

# 1. Backup de base de datos
echo "📊 Creando backup de PostgreSQL..."
sudo -u postgres pg_dump \
  --format=custom \
  --compress=9 \
  --verbose \
  --file="${BACKUP_DIR}/${BACKUP_FILE}.custom" \
  "$DB_NAME"

# Backup en formato SQL plano también
sudo -u postgres pg_dump \
  --format=plain \
  --verbose \
  --file="${BACKUP_DIR}/${BACKUP_FILE}" \
  "$DB_NAME"

# Comprimir backup plano
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

# 2. Verificar integridad
echo "🔍 Verificando integridad del backup..."
if pg_restore --list "${BACKUP_DIR}/${BACKUP_FILE}.custom" > /dev/null 2>&1; then
  echo "✅ Backup verificado correctamente"
else
  echo "❌ Error en verificación de backup"
  exit 1
fi

# 3. Subir a S3 (copia offsite)
echo "☁️ Subiendo backup a S3..."
aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}.custom" \
  "s3://${S3_BUCKET}/database/${BACKUP_FILE}.custom" \
  --storage-class STANDARD_IA

aws s3 cp "${BACKUP_DIR}/${BACKUP_COMPRESSED}" \
  "s3://${S3_BUCKET}/database/${BACKUP_COMPRESSED}"

# 4. Backup de archivos de aplicación
echo "📁 Backup de archivos de aplicación..."
tar -czf "${BACKUP_DIR}/app_files_${TIMESTAMP}.tar.gz" \
  /opt/ofitec/data/ \
  /opt/ofitec/logs/ \
  /opt/ofitec/config/

# Subir archivos a S3
aws s3 cp "${BACKUP_DIR}/app_files_${TIMESTAMP}.tar.gz" \
  "s3://${S3_BUCKET}/files/app_files_${TIMESTAMP}.tar.gz"

# 5. Limpieza de backups antiguos (local)
echo "🧹 Limpiando backups antiguos..."
find "$BACKUP_DIR" -name "ofitec_backup_*.sql*" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "app_files_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# 6. Limpieza S3 (lifecycle policy - configurado por separado)

# 7. Notificación
echo "✅ Backup completado: ${BACKUP_FILE}"
echo "📊 Tamaño del backup:"
ls -lh "${BACKUP_DIR}/${BACKUP_FILE}.custom" "${BACKUP_DIR}/${BACKUP_COMPRESSED}"

# Notificar a Slack
curl -X POST $SLACK_WEBHOOK_BACKUPS \
  -H 'Content-type: application/json' \
  --data "{\"text\":\"✅ Backup Ofitec.ai completado: ${BACKUP_FILE}\"}"

echo "🎉 Proceso de backup finalizado - $(date)"
```

### 4. Monitorización y Alertas

**Archivos:** `docker-compose.monitoring.yml`, `monitoring/grafana/dashboards/`

#### 4.1 Stack de monitorización

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning

  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager:/etc/alertmanager

  node_exporter:
    image: prom/node-exporter:latest
    container_name: node_exporter
    ports:
      - "9100:9100"

  postgres_exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: postgres_exporter
    environment:
      - DATA_SOURCE_NAME=postgresql://monitor:password@postgres:5432/ofitec_prod?sslmode=disable
    ports:
      - "9187:9187"

volumes:
  prometheus_data:
  grafana_data:
```

## APIs Requeridas

### Integración SII
- `GET /api/sii/token` - Verificar token SII
- `POST /api/sii/rcv/import` - Importar RCV
- `GET /api/sii/events` - Stream SSE de progreso
- `GET /api/sii/summary` - Resumen datos importados

### Monitorización
- `GET /api/health` - Health check detallado
- `GET /api/metrics` - Métricas Prometheus
- `GET /api/backup/status` - Estado de backups

## Criterios de Aceptación

- [ ] Integración SII funcionando con certificado digital
- [ ] Pipeline CI/CD con tests, build y deploy automático
- [ ] Sistema de backups 3-2-1 implementado y probado
- [ ] Monitorización con Prometheus/Grafana operativa
- [ ] Alertas configuradas para incidencias críticas
- [ ] Deploy blue/green funcionando
- [ ] Verificación automática de puertos en CI
- [ ] Restoration testing de backups mensual

## Riesgos y Mitigaciones

- **Riesgo:** Falla en certificado digital SII
- **Mitigación:** Monitorización de vencimiento + renovación automática

- **Riesgo:** Pérdida de datos durante deploy
- **Mitigación:** Backup automático pre-deploy + rollback rápido

## Estimación: 18 días

## Dependencias

- Sprint 4 completado (portal y analítica)
- Certificado digital SII válido
- Infraestructura cloud configurada
- Credenciales de servicios externos