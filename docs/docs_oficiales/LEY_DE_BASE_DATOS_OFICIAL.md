# LEY OFICIAL DE BASE DE DATOS OFITEC
## Estándares NASA para Gestión de Datos Críticos

**Versión:** 1.0  
**Fecha:** 12 de Septiembre, 2025  
**Autoridad:** Sistema de Gestión de Datos OFITEC  
**Vigencia:** Inmediata y Permanente  

---

## ARTÍCULO I: PRINCIPIOS FUNDAMENTALES

### 1.1 MISIÓN CRÍTICA
Esta base de datos contiene información financiera y operacional crítica de OFITEC. Su integridad es FUNDAMENTAL para:
- Decisiones ejecutivas basadas en datos reales
- Reportes financieros precisos 
- Cumplimiento legal y tributario
- Operaciones diarias del negocio

### 1.2 ESTÁNDARES DE CALIDAD NASA
Se aplicarán los siguientes estándares de calidad espacial:
- **Tolerancia Cero** a pérdida de datos
- **Redundancia Triple** en validaciones críticas  
- **Trazabilidad Completa** de todas las operaciones
- **Verificación Automática** de integridad referencial

## ARTÍCULO II: ARQUITECTURA DE DATOS

### 2.1 ESTRUCTURA UNIFICADA OBLIGATORIA

#### Tabla Principal: `purchase_orders_unified`
**CAMPOS REQUERIDOS (Inviolables):**
```sql
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- vendor_rut (TEXT NOT NULL)
- po_number (TEXT NOT NULL)
- po_date (TEXT NOT NULL)
- total_amount (REAL NOT NULL CHECK(total_amount >= 0))
- currency (TEXT NOT NULL DEFAULT 'CLP')
- status (TEXT NOT NULL)
- source_platform (TEXT NOT NULL)
- zoho_po_id (TEXT)
- zoho_project_name (TEXT)
- zoho_vendor_name (TEXT NOT NULL)
- created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- migration_id (TEXT NOT NULL)
```

#### Tabla de Proveedores: `vendors_unified`
**CAMPOS REQUERIDOS:**
```sql
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- rut_clean (TEXT UNIQUE NOT NULL)
- name_normalized (TEXT NOT NULL)
- source_platform (TEXT NOT NULL)
- zoho_vendor_name (TEXT)
- created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
```

### 2.2 REGLAS DE INTEGRIDAD REFERENCIAL

1. **Relación Obligatoria:** Todo `purchase_orders_unified.vendor_rut` DEBE existir en `vendors_unified.rut_clean`
2. **Validación de RUT:** Todos los RUTs DEBEN pasar validación de dígito verificador chileno
3. **Normalización de Nombres:** Todos los nombres de proveedores DEBEN estar normalizados sin tildes ni caracteres especiales

## ARTÍCULO III: PREVENCIÓN DE DUPLICADOS

### 3.1 SISTEMA ANTI-DUPLICADOS MULTICAPA

#### Capa 1: Constraints de Base de Datos
```sql
-- Evitar duplicados en órdenes de compra
CREATE UNIQUE INDEX idx_unique_po ON purchase_orders_unified(
    vendor_rut, po_number, po_date, total_amount
);

-- Evitar duplicados en proveedores
CREATE UNIQUE INDEX idx_unique_vendor ON vendors_unified(rut_clean);
```

#### Capa 2: Validación Pre-Inserción
```python
def validate_before_insert(data):
    # Verificar si existe combinación similar
    # Aplicar algoritmo de distancia de Levenshtein
    # Validar rangos de fechas y montos
    # Confirmar con usuario si hay similaridad > 85%
```

#### Capa 3: Monitoreo Post-Inserción
- Análisis diario de duplicados potenciales
- Alertas automáticas si se detectan anomalías
- Reporte semanal de calidad de datos

### 3.2 PROTOCOLO DE DETECCIÓN

1. **Duplicado Exacto:** Mismo vendor_rut + po_number + po_date + total_amount
2. **Duplicado Probable:** Mismo vendor_rut + fecha similar (±3 días) + monto similar (±5%)
3. **Duplicado Sospechoso:** Mismo vendor_rut + mismo día + múltiples órdenes

## ARTÍCULO IV: PROCEDIMIENTOS DE IMPORTACIÓN

### 4.1 PROTOCOLO CHIPAX (CRÍTICO)

#### Fase 1: Validación Pre-Importación
```python
def validate_chipax_import(file_path):
    # 1. Verificar estructura del CSV
    # 2. Validar tipos de datos
    # 3. Verificar RUTs chilenos
    # 4. Detectar duplicados internos en el archivo
    # 5. Comparar con datos existentes
    return validation_report
```

#### Fase 2: Importación Controlada
```python
def controlled_import():
    # 1. Backup automático pre-importación
    # 2. Importación en transacción
    # 3. Validación post-inserción
    # 4. Rollback automático si falla validación
    # 5. Reporte detallado de resultados
```

#### Fase 3: Verificación Post-Importación
- Conteo de registros importados vs. esperados
- Validación de integridad referencial
- Análisis de duplicados introducidos
- Reporte de calidad de datos

### 4.2 CAMPOS OBLIGATORIOS CHIPAX

**De chipax_facturas a purchase_orders_unified:**
```python
MAPPING_CHIPAX = {
    'vendor_rut': 'Bill Vendor Details_RUT',
    'po_number': 'Bill Number',
    'po_date': 'Bill Date',
    'total_amount': 'Bill Item Details_Billable',
    'zoho_vendor_name': 'Bill Vendor Details_Vendor Name',
    'source_platform': 'chipax'
}
```

## ARTÍCULO V: CONSULTAS Y APIS AUTORIZADAS

### 5.1 CONSULTAS ESTÁNDAR APROBADAS

#### Proyectos Reales (ÚNICA FUENTE DE VERDAD)
```sql
SELECT 
    zoho_project_name as project_name,
    COUNT(*) as total_orders,
    SUM(total_amount) as total_amount,
    COUNT(DISTINCT vendor_rut) as unique_providers,
    MIN(po_date) as start_date,
    MAX(po_date) as end_date
FROM purchase_orders_unified 
WHERE zoho_project_name IS NOT NULL 
    AND zoho_project_name != ''
    AND zoho_project_name != 'null'
    AND zoho_project_name != 'NULL'
GROUP BY zoho_project_name
ORDER BY total_amount DESC;
```

#### Proveedores Top (ÚNICA FUENTE DE VERDAD)
```sql
SELECT 
    v.name_normalized as provider_name,
    v.rut_clean,
    COUNT(p.id) as total_orders,
    SUM(p.total_amount) as total_amount
FROM vendors_unified v
LEFT JOIN purchase_orders_unified p ON v.rut_clean = p.vendor_rut
GROUP BY v.id, v.name_normalized, v.rut_clean
ORDER BY total_amount DESC;
```

### 5.2 APIS PROHIBIDAS

**JAMÁS USAR ESTAS CONSULTAS:**
- `SELECT * FROM chipax_facturas` (Datos sin normalizar)
- Consultas que mezclen proveedores con proyectos sin JOIN apropiado
- Consultas que no filtren valores NULL o vacíos
- Consultas que usen campos no normalizados

## ARTÍCULO VI: MONITOREO Y ALERTAS

### 6.1 MÉTRICAS CRÍTICAS DIARIAS

1. **Integridad de Datos:**
   - Registros sin proyecto: < 5%
   - Registros sin proveedor: 0%
   - Registros sin monto: 0%

2. **Calidad de Datos:**
   - RUTs inválidos: 0%
   - Fechas futuras: 0%
   - Montos negativos: < 1%

3. **Duplicados:**
   - Duplicados exactos: 0%
   - Duplicados probables: < 0.1%
   - Duplicados sospechosos: < 0.5%

### 6.2 SISTEMA DE ALERTAS

#### Alerta Crítica (Inmediata)
- Pérdida de conexión a BD
- Falla en backup automático
- Detección de corrupción
- Intento de eliminación masiva

#### Alerta Alta (30 minutos)
- Incremento >5% en duplicados
- Falla en importación Chipax
- Violación de constraints
- Anomalías en montos

#### Alerta Media (2 horas)
- Degradación de performance
- Incremento en registros NULL
- Inconsistencias menores

## ARTÍCULO VII: BACKUP Y RECUPERACIÓN

### 7.1 ESTRATEGIA 3-2-1

- **3 Copias:** Original + 2 backups
- **2 Medios:** Local + Cloud
- **1 Offsite:** Backup remoto diario

### 7.2 PROGRAMACIÓN DE BACKUPS

- **Backup Transaccional:** Cada modificación importante
- **Backup Horario:** Automático durante horas laborales
- **Backup Diario:** 02:00 AM con verificación de integridad
- **Backup Semanal:** Completo con compresión
- **Backup Mensual:** Archivo histórico

## ARTÍCULO VIII: SANCIONES Y CUMPLIMIENTO

### 8.1 VIOLACIONES CRÍTICAS

**Prohibido Absolutamente:**
- Modificar estructura sin aprobación
- Eliminar registros sin backup
- Importar datos sin validación
- Usar consultas no autorizadas
- Acceder sin logging de auditoría

### 8.2 PROCEDIMIENTO DE EMERGENCIA

En caso de corrupción o pérdida:
1. **STOP inmediato** de todas las operaciones
2. Activar protocolo de recuperación
3. Restaurar desde último backup verificado
4. Validar integridad completa
5. Generar reporte de incidente
6. Implementar medidas correctivas

---

## CERTIFICACIÓN DE CUMPLIMIENTO

Esta LEY DE BASE DE DATOS es de cumplimiento **OBLIGATORIO** para todo el sistema OFITEC.

**Responsables de Implementación:**
- Administrador de Base de Datos
- Desarrolladores de APIs
- Analistas de Datos
- Auditores de Calidad

**Revisión:** Trimestral  
**Próxima Actualización:** Diciembre 2025

---

*"Los datos son el petróleo del siglo XXI. Nuestra base de datos es Fort Knox digital."*

**- Sistema de Gestión de Datos OFITEC -**

---

## ARTÍCULO IX: VISTAS FINANCIERAS CANÓNICAS (Finanzas)

Con el objetivo de estandarizar el acceso a información financiera transversal, se establecen las siguientes VISTAS canónicas (prefijo `v_`) en la base de datos principal. Estas vistas son la única interfaz autorizada para consumidores de datos financieros a nivel UI/API.

### 9.1 Listado de Vistas Obligatorias

- v_facturas_compra (OBLIGATORIA – derivada de órdenes de compra mientras se integra DTE)
- v_facturas_venta (PLACEHOLDER – retorna 0 filas hasta integrar ventas)
- v_gastos (PLACEHOLDER)
- v_impuestos (PLACEHOLDER – SII, F29, IVA, retenciones)
- v_previred (PLACEHOLDER – cotizaciones previsionales/seguridad social)
- v_sueldos (PLACEHOLDER – liquidaciones de sueldo)
- v_cartola_bancaria (PLACEHOLDER – movimientos bancarios estandarizados)

### 9.2 Especificación de Columnas

Para asegurar interoperabilidad, cada vista define un contrato mínimo:

1. v_facturas_compra

- documento_numero (TEXT)
- fecha (TEXT, ISO-8601)
- proveedor_rut (TEXT)
- proveedor_nombre (TEXT)
- monto_total (REAL)
- moneda (TEXT, ISO 4217)
- estado (TEXT)
- fuente (TEXT)

Origen temporal: `purchase_orders_unified` (mapeo 1:1 a modo de proxy hasta contar con facturas DTE)

1. v_facturas_venta

- documento_numero, fecha, cliente_rut, cliente_nombre, monto_total, moneda, estado, fuente

1. v_gastos

- gasto_id, fecha, categoria, descripcion, monto, moneda, proveedor_rut, proyecto, fuente

1. v_impuestos

- periodo, tipo, monto_debito, monto_credito, neto, estado, fecha_presentacion, fuente

1. v_previred

- periodo, rut_trabajador, nombre_trabajador, rut_empresa, monto_total, estado, fecha_pago, fuente

1. v_sueldos

- periodo, rut_trabajador, nombre_trabajador, cargo, bruto, liquido, descuentos, fecha_pago, fuente

1. v_cartola_bancaria

- fecha, banco, cuenta, glosa, monto, moneda, tipo, saldo, referencia, fuente

### 9.3 Implementación Autorizada

- La vista `v_facturas_compra` se define mediante mapeo directo desde `purchase_orders_unified`:

```sql
CREATE VIEW v_facturas_compra AS
SELECT
    po_number         AS documento_numero,
    po_date           AS fecha,
    vendor_rut        AS proveedor_rut,
    zoho_vendor_name  AS proveedor_nombre,
    total_amount      AS monto_total,
    COALESCE(currency, 'CLP') AS moneda,
    COALESCE(status, 'unknown') AS estado,
    COALESCE(source_platform, 'unknown') AS fuente
FROM purchase_orders_unified;
```

- Las vistas restantes se crean inicialmente como PLACEHOLDER retornando 0 filas con el esquema normalizado, hasta que se integre su fuente de datos (SII, tesorería, conciliación bancaria, RRHH).


### 9.4 Gobernanza

- Cualquier cambio de esquema en estas vistas requiere RFC y aprobación del Administrador de Base de Datos.
- Se provee script oficial `tools/create_finance_views.py` para crear/actualizar estas vistas de forma idempotente.

---

## ARTÍCULO X: CONCILIACIÓN TRANSVERSAL (Oficial)

### 10.1 Alcance y Principio Rector

La conciliación es una CAPA TRANSVERSAL del sistema: debe poder ejecutarse desde la cartola bancaria, desde facturas de compra y venta, desde gastos, sueldos e impuestos. No es una pantalla aislada: es una capacidad disponible donde se revisan movimientos financieros.

### 10.2 Fuentes Canónicas de Conciliación

La conciliación se alimenta exclusivamente desde vistas/tablas canonizadas:

- v_cartola_bancaria (movimientos bancarios estandarizados)
- v_facturas_compra (pagos/egresos asociados a proveedores)
- v_facturas_venta (cobros/ingresos asociados a clientes)
- v_gastos (egresos no facturados o gastos internos)
- v_sueldos (nómina y pagos de remuneraciones)
- v_impuestos (pagos/compensaciones tributarias)

Nota: Mientras existan placeholders, la conciliación mostrará “sin datos” para dichas fuentes. Está prohibido conciliar contra tablas no normalizadas.

### 10.3 Reglas de Matching Autorizadas

Orden de aplicación (de mayor a menor precisión), todas registradas en logs de auditoría:

1. Match exacto: monto igual y fecha exacta (±0 días), RUT/tercero coincidente
2. Match ventana: monto igual y fecha ±3 días (configurable), RUT/tercero coincidente
3. Match múltiple: 1↔N o N↔1 con suma de montos igual (tolerancia configurable)
4. Match por alias: normalización/alias de glosa vs. proveedor/cliente conocido
5. Match por similitud: monto similar (±1–3%), fecha ±3 días, nombre aproximado (umbral ≥ 0.85)

Todas las reglas deben ser reproducibles, parametrizables y quedar trazadas con: regla aplicada, score, tolerancias, y usuario/robot que confirma.

### 10.4 Estados del Proceso

- pendiente: sin sugerencia
- sugerido: el motor propone un match (con score)
- conciliado: confirmado (automático o manual)
- parcial: conciliación parcial (casos 1↔N/N↔1)
- rechazado: sugerencia descartada

Transiciones deben quedar auditadas (timestamp, usuario, motivo).

### 10.5 Implementación y Límites

- Motor de conciliación oficial: servicio `ofitec_conciliacion_bancaria` (API externa). El Portal consume su API y/o snapshots materializados a vistas canónicas.
- Persistencia de conciliaciones: en la BD del servicio oficial. El Portal solo cachea/consulta; no duplica canónicamente conciliaciones.
- Está prohibido escribir conciliaciones directamente en la BD canónica del Portal sin pasar por el servicio.

### 10.6 Gobierno y Cambios

- Cambios en reglas o tolerancias requieren RFC y aprobación del Administrador de Datos.
- Nuevas fuentes de conciliación deben publicarse primero como vistas canónicas (prefijo `v_`) y documentarse en este documento antes de habilitar el matching.
