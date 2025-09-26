# OFITEC.AI - FASE 4: CORRECCIÓN DE IMPORTS

## Objetivo
Corregir todos los imports incorrectos que referencian `backend.algo` cuando deberían referenciar directamente `algo`, eliminando así todos los warnings del servidor.

## Problemas Identificados

### 7 archivos con imports incorrectos:

1. **api_sales_invoices.py**
   - `from backend.db_utils import db_conn` → `from db_utils_centralized import db_conn`

2. **api_sii.py** 
   - `from backend.db_utils import db_conn` → `from db_utils_centralized import db_conn`
   - `from backend.sii_service import` → `from sii_service import`

3. **api_ap_match.py**
   - `from backend.db_utils import db_conn` → `from db_utils_centralized import db_conn`

4. **api_matching_metrics.py**
   - `from backend.db_utils import db_conn` → `from db_utils_centralized import db_conn`
   - `from backend.recon_constants import` → `from recon_constants import`
   - `from backend.api_ap_match import` → `from api_ap_match import`

5. **ep_api.py**
   - `from backend.db_utils import db_conn` → `from db_utils_centralized import db_conn`

6. **sii_service.py**
   - `from backend.db_utils import db_conn` → `from db_utils_centralized import db_conn`

7. **server.py**
   - `from backend import server_utils` → `from server_utils import`

## Warnings Actuales a Eliminar

- ❌ EP blueprint no disponible: No module named 'backend'
- ⚠️ sales_invoices blueprint no disponible: No module named 'backend'  
- ⚠️ sii_integration blueprint no disponible: No module named 'backend'
- ⚠️ ap_match blueprint no disponible: No module named 'backend'
- ⚠️ matching_metrics blueprint no disponible: No module named 'backend'

## Plan de Ejecución

1. Corregir imports en api_sales_invoices.py
2. Corregir imports en api_sii.py
3. Corregir imports en api_ap_match.py
4. Corregir imports en api_matching_metrics.py
5. Corregir imports en ep_api.py
6. Corregir imports en sii_service.py
7. Corregir import en server.py
8. Verificar que todos los módulos se importan correctamente
9. Confirmar eliminación de warnings

## Resultado Esperado

- ✅ 0 warnings en el servidor
- ✅ Todos los blueprints se cargan correctamente
- ✅ Sistema completamente funcional sin errores de importación