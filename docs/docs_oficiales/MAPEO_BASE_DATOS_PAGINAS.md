# 📊 MAPEO BASE DE DATOS - PÁGINAS OFITEC

## **Estado Actual de Datos (12 Sept 2025)**

### **✅ DATOS DISPONIBLES EN ofitec_dev.db**
```
📊 TABLAS PRINCIPALES:
- zoho_ordenes_final (16,289 registros) - Órdenes completas con financieros
- zoho_proveedores_unificado (1,382 registros) - Maestro proveedores con RUT
- zoho_proyectos (78 registros) - Proyectos con presupuestos
- relaciones_zoho_chipax (390 registros) - Links ZOHO-Chipax validados
- dataset_final_integrado (16,289 registros) - Dataset completo integrado

🔍 VISTAS OPTIMIZADAS:
- vista_ordenes_completas - Órdenes con totales válidos
- vista_proyectos_resumen - Agregaciones por proyecto
- vista_proveedores_integrados - Proveedores con matches Chipax
```

## **📋 MAPEO POR PÁGINA**

### **1. Dashboard Ejecutivo**

#### **1.1 Control Center Principal**
```sql
-- DATOS: ✅ DISPONIBLES
SOURCE: vista_proyectos_resumen + vista_ordenes_completas
QUERIES:
  - KPIs Financieros: SUM(valor_total), AVG(valor_promedio)
  - Portfolio: COUNT(Project_ID), COUNT(DISTINCT Vendor_Name)
  - ROI: (Budget_Amount - Project_Cost) / Project_Cost
```

#### **1.2 CEO Copilot**
```sql
-- DATOS: ✅ DISPONIBLES
SOURCE: Todas las tablas (contexto completo)
FEATURES:
  - Búsqueda semántica en 34,428 registros
  - Análisis transaccional completo
  - Insights basados en datos reales
```

#### **1.3 Vista Consolidada**
```sql
-- DATOS: ✅ DISPONIBLES
SOURCE: vista_proyectos_resumen
QUERIES:
  - Multi-proyecto: GROUP BY Project_ID
  - Comparador: ORDER BY valor_total DESC
  - Tendencias: Purchase_Order_Date analysis
```

### **2. Finanzas Avanzadas**

#### **2.1 Chipax Migration Center**
```sql
-- DATOS: ✅ COMPLETAMENTE DISPONIBLES
SOURCE: dataset_final_integrado + relaciones_zoho_chipax
METRICS:
  - Datos migrados: 16,289 órdenes ✅
  - Relaciones: 390 matches ZOHO-Chipax ✅
  - Cobertura: 93.3% proyectos con datos ✅
```

#### **2.2 Cashflow Lab**
```sql
-- DATOS: ✅ BASE DISPONIBLE + 🔄 CALCULADOS
SOURCE: vista_ordenes_completas
DERIVADOS:
  - Flujo entrada: SUM(Total) GROUP BY Purchase_Order_Date
  - Proyecciones: Análisis temporal + ML
  - Escenarios: Multiplicadores sobre base real
```

#### **2.3 SII Integration**
```sql
-- DATOS: 🔄 A CREAR
REQUIRED:
  - Tabla: sii_declaraciones (F29, IVA, etc.)
  - Tabla: dte_documents (facturas electrónicas)
  - Vista: cumplimiento_tributario
```

#### **2.4 Conciliación Bancaria Inteligente**
```sql
-- DATOS: ✅ SISTEMA COMPLETO DESARROLLADO
SOURCE: ofitec_conciliacion_bancaria/ (7 tablas + ML Engine)
AVAILABLE:
  - ofitec_cuentas_corrientes (cuentas bancarias) ✅
  - movimientos_bancarios (transacciones) ✅
  - facturas_compra, facturas_venta (documentos) ✅
  - sueldos, gastos_diversos (categorías) ✅
  - conciliaciones (registros de matches) ✅

INTEGRATION READY:
  - API REST: 8 endpoints funcionales ✅
  - ML Engine: Scoring 0-100%, matching 1↔N/N↔1 ✅
  - RUT Validation: Algoritmo chileno completo ✅
  - Alias Learning: Aprendizaje automático patrones ✅
```

#### **2.5 Tesorería Multi-Banco**
```sql
-- DATOS: 🔄 A CREAR
REQUIRED:
  - Tabla: cuentas_bancarias
  - Tabla: movimientos_bancarios (estilo Chipax)
  - Vista: saldos_consolidados
```

#### **2.6 Vistas Financieras Canónicas (NUEVO)**

```text
VISTAS DISPONIBLES:
- v_facturas_compra ✅ (proxy de purchase_orders_unified)
- v_facturas_venta 🔄 placeholder
- v_gastos 🔄 placeholder
- v_impuestos 🔄 placeholder
- v_previred 🔄 placeholder
- v_sueldos 🔄 placeholder
- v_cartola_bancaria 🔄 placeholder

USO EN PÁGINAS:
- Finanzas/Facturas de Compra → v_facturas_compra
- Finanzas/Facturas de Venta → v_facturas_venta
- Finanzas/Gastos → v_gastos
- Finanzas/Impuestos → v_impuestos
- Finanzas/Previred → v_previred
- Finanzas/Sueldos → v_sueldos
- Finanzas/Cartola Bancaria → v_cartola_bancaria
```

#### **2.7 Conciliación Transversal (NUEVO)**

- La conciliación se habilita en contexto de cada pantalla:
  - Cartola Bancaria → candidatos vs. v_facturas_compra / v_gastos / v_impuestos / v_sueldos
  - Facturas de Compra → candidatos vs. v_cartola_bancaria
  - Facturas de Venta → candidatos vs. v_cartola_bancaria
- El matching (sugerencias, confirmación) se realiza vía API del servicio `ofitec_conciliacion_bancaria`.
- El Portal NO persiste conciliaciones; muestra estado/score y ejecuta acciones sobre el servicio.

### **3. Proyectos & Obras**

#### **3.1 Control Integral Financiero**
```sql
-- DATOS: ✅ PARCIALMENTE DISPONIBLES
SOURCE: zoho_proyectos + vista_proyectos_resumen
AVAILABLE:
  - Presupuesto: Budget_Amount ✅
  - Real ejecutado: SUM(Total) por proyecto ✅
  - Desviaciones: Budget_Amount - valor_total ✅

MISSING: 🔄 A CREAR
  - Tabla: presupuesto_detallado (por WBS/partida)
  - Tabla: avances_fisicos (% completado)
```

#### **3.2 Gestión Subcontratistas**
```sql
-- DATOS: ✅ BASE + 🔄 EXTENSIONES
SOURCE: zoho_proveedores_unificado (1,382 proveedores)
AVAILABLE:
  - Proveedores: Company_Name, RUT, Contact_ID ✅
  - Órdenes: vista_ordenes_completas por proveedor ✅

MISSING: 🔄 A CREAR
  - Tabla: contratos_subcontratistas
  - Tabla: estados_pago_subcontratistas
  - Tabla: evaluaciones_performance
```

#### **3.3 Órdenes de Cambio**
```sql
-- DATOS: 🔄 A CREAR COMPLETAMENTE
REQUIRED:
  - Tabla: ordenes_cambio
  - Tabla: workflow_aprobaciones
  - Vista: impacto_cambios
```

#### **3.4 Planning & Scheduling**
```sql
-- DATOS: 🔄 A CREAR COMPLETAMENTE
REQUIRED:
  - Tabla: cronograma_maestro
  - Tabla: hitos_criticos
  - Tabla: recursos_planificados
```

### **4. Operaciones de Obra**

#### **4.1 Reportes Digitales**
```sql
-- DATOS: 🔄 A CREAR COMPLETAMENTE
REQUIRED:
  - Tabla: reportes_diarios_obra
  - Tabla: fotos_avance
  - Tabla: gps_ubicaciones
```

#### **4.2 HSE Inteligente**
```sql
-- DATOS: 🔄 A CREAR COMPLETAMENTE
REQUIRED:
  - Tabla: incidentes_hse
  - Tabla: inspecciones_seguridad
  - Tabla: epp_detecciones
```

#### **4.3 Control Recursos**
```sql
-- DATOS: 🔄 A CREAR COMPLETAMENTE
REQUIRED:
  - Tabla: materiales_obra
  - Tabla: maquinaria_equipos
  - Tabla: personal_obra
```

### **5. Documentos & IA**

#### **5.1 DocuChat AI**
```sql
-- DATOS: 🔄 A CREAR COMPLETAMENTE
REQUIRED:
  - Tabla: documentos_indexados
  - Tabla: embeddings_vectoriales
  - Vista: busqueda_semantica
```

#### **5.2 RFI Digital**
```sql
-- DATOS: 🔄 A CREAR COMPLETAMENTE
REQUIRED:
  - Tabla: rfi_solicitudes
  - Tabla: rfi_respuestas
  - Vista: rfi_pendientes
```

### **6. Riesgos & Seguridad**

#### **6.1 Matriz IA de Riesgos**
```sql
-- DATOS: 🔄 A CREAR + ✅ DERIVAR DE EXISTENTES
BASE: Análisis de desviaciones en vista_proyectos_resumen
REQUIRED:
  - Tabla: matriz_riesgos
  - Tabla: predicciones_ml
```

### **7. Portal Cliente**

#### **7.1 Vista Proyecto Cliente**
```sql
-- DATOS: ✅ DISPONIBLES CON FILTROS
SOURCE: zoho_proyectos + vista_ordenes_completas
FILTERS: WHERE Customer_Name = 'cliente_especifico'
```

### **8. IA & Analytics**

#### **8.1 Copilots Especializados**
```sql
-- DATOS: ✅ TODAS LAS TABLAS DISPONIBLES
SOURCE: Acceso completo a 34,428 registros
CONTEXT: Especialización por dominio usando datos existentes
```

### **9. Configuración & Admin**

#### **9.1 Gestión Usuarios**
```sql
-- DATOS: 🔄 A CREAR COMPLETAMENTE
REQUIRED:
  - Tabla: usuarios_sistema
  - Tabla: roles_permisos
  - Tabla: sesiones_activas
```

## **📊 RESUMEN ESTADO DATOS**

### **✅ LISTO PARA IMPLEMENTAR (60%)**
```
1. Dashboard Ejecutivo - KPIs, CEO Copilot, Vistas ✅
2. Finanzas - Chipax Migration, Cashflow Base ✅
3. Finanzas - Conciliación Bancaria COMPLETA ✅
4. Proyectos - Control Financiero Base ✅
5. Portal Cliente - Vista básica proyectos ✅
6. IA & Analytics - Base datos completa ✅
```

### **🔄 REQUIERE EXTENSIÓN DATOS (25%)**
```
1. Finanzas - SII Integration, Tesorería avanzada
2. Proyectos - Subcontratistas (extender), Órdenes Cambio
3. Riesgos - Derivar de datos existentes + nuevas tablas
```

### **🆕 CREAR DESDE CERO (15%)**
```
1. Operaciones Obra - Reportes, HSE, Recursos
2. Documentos - DocuChat, RFI
3. Admin - Usuarios, Roles, Sesiones
```

## **🎯 PRIORIDAD IMPLEMENTACIÓN**

### **SPRINT 1 (Inmediato)**
- ✅ Dashboard Ejecutivo (100% datos disponibles)
- ✅ Finanzas - Chipax Migration (100% datos disponibles)
- ✅ Finanzas - Conciliación Bancaria (100% sistema desarrollado)

### **SPRINT 2 (Corto plazo)**
- 🔄 Proyectos - Control Financiero (extender datos existentes)
- 🔄 Portal Cliente (filtrar datos existentes)

### **SPRINT 3+ (Mediano plazo)**
- 🆕 Operaciones Obra, Documentos, Admin (crear nuevas estructuras)

---

**VENTAJA COMPETITIVA**: Con 34,428 registros reales ya procesados + sistema de conciliación bancaria inteligente completamente desarrollado, podemos demostrar valor inmediato en Dashboard, Finanzas y Conciliación desde día 1, diferenciándonos de competidores que requieren meses de implementación.