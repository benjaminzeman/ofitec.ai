# 📋 LEY DE PUERTOS OFICIAL - OFITEC.AI

## 🎯 **PRINCIPIOS FUNDAMENTALES**

Esta ley se basa en los **3 documentos estratégicos** del ofitec.ai:
1. **ESTRATEGIA_CREACION_PAGINAS.md** - Define qué páginas crear
2. **ESTRATEGIA_VISUAL.md** - Define cómo se ven las páginas  
3. **MAPEO_BASE_DATOS_PAGINAS.md** - Define qué datos usar

## 🔌 **ARQUITECTURA DE PUERTOS**

### **Puerto 3001 - FRONTEND PRINCIPAL** ⭐
- **Función:** Portal moderno Next.js 14 con React/TypeScript
- **URL Base:** http://localhost:3001
- **Estado:** ✅ ACTIVO (Puerto oficial del frontend)
- **Responsabilidad:** Interfaz de usuario moderna siguiendo ESTRATEGIA_VISUAL
- **Páginas:**
  - `/` → Dashboard principal
  - `/proyectos` → Gestión de proyectos (según ESTRATEGIA_CREACION_PAGINAS)
  - `/proveedores` → Gestión de proveedores
  - `/finanzas` → Panel financiero
  - `/ordenes` → Gestión de órdenes

### **Puerto 5555 - BACKEND API** 🔧
- **Función:** Servidor Flask con APIs REST y datos reales
- **URL Base:** http://localhost:5555
- **Estado:** ✅ ACTIVO (Servidor de APIs)
- **Responsabilidad:** APIs REST siguiendo MAPEO_BASE_DATOS_PAGINAS
- **Endpoints:**
  - `/api/projects` → Datos de proyectos reales
  - `/api/providers` → Datos de proveedores
  - `/api/financial` → Datos financieros
  - `/api/dashboard` → KPIs y métricas
  - **NO SIRVE PÁGINAS HTML** (solo APIs JSON)

### **Puertos RESERVADOS** 🚫
- **3000:** Reservado para desarrollo/testing
- **3002:** NO USAR (era temporal por conflictos)
- **8000-8999:** Reservados para Odoo
- **5000-5554:** Reservados para otros servicios

## ⚖️ **REGLAS OBLIGATORIAS**

### **Regla #1: Un Solo Frontend**
- ✅ **USAR:** Puerto 3001 para TODAS las páginas del usuario
- ❌ **NO USAR:** Múltiples puertos frontend (3000, 3002, etc.)

### **Regla #2: APIs Centralizadas**
- ✅ **USAR:** Puerto 5555 para TODAS las APIs
- ❌ **NO USAR:** APIs dispersas en múltiples puertos

### **Regla #3: Separación de Responsabilidades**
- **Frontend (3001):** Solo UI/UX, consume APIs
- **Backend (5555):** Solo datos y lógica de negocio
- **NO mezclar:** HTML rendering en backend

### **Regla #4: Documentos Estratégicos**
- **ANTES** de crear una página: consultar ESTRATEGIA_CREACION_PAGINAS
- **ANTES** de diseñar UI: consultar ESTRATEGIA_VISUAL  
- **ANTES** de crear API: consultar MAPEO_BASE_DATOS_PAGINAS

### **Regla #5: Consistencia**
- **NO cambios arbitrarios** de puertos
- **NO servidores temporales** sin documentar
- **SÍ seguir** esta ley en todo momento

## 🛡️ **PROCESO DE CAMBIOS**

Para cambiar esta ley:
1. **Justificación técnica** documentada
2. **Actualización** de los 3 documentos estratégicos si es necesario
3. **Aprobación** explícita
4. **Actualización** de toda la documentación

## 📊 **MONITOREO**

### **Comandos de Verificación:**
```bash
# Verificar puertos activos
netstat -an | findstr ":300"
netstat -an | findstr ":5555"

# Probar frontend
curl http://localhost:3001
curl http://localhost:3001/proyectos

# Probar APIs
curl http://localhost:5555/api/projects
curl http://localhost:5555/api/providers
```

### **URLs Oficiales:**
- **Portal Usuario:** http://localhost:3001
- **API Documentación:** http://localhost:5555/api
- **Health Check:** http://localhost:5555/health

## 🔧 **COMANDOS ESTÁNDAR**

### **Inicio del Sistema Completo:**
```bash
# Terminal 1: Backend
cd c:\Odoo\custom_addons\ofitec.ai
python server.py

# Terminal 2: Frontend  
cd c:\Odoo\custom_addons\ofitec.ai\web
npm run dev
```

### **Verificación de Estado:**
```bash
# Frontend debe estar en 3001
curl http://localhost:3001/api/health

# Backend debe estar en 5555
curl http://localhost:5555/api/health
```

## 📋 **CHECKLIST DE CUMPLIMIENTO**

- [ ] Frontend corriendo en puerto 3001
- [ ] Backend corriendo en puerto 5555  
- [ ] No hay servidores en puertos no autorizados
- [ ] Todas las páginas funcionan en 3001
- [ ] Todas las APIs responden en 5555
- [ ] Documentos estratégicos actualizados

---

**⚡ Esta ley es OBLIGATORIA y debe seguirse en todo momento**
**📅 Última actualización:** 12 de Septiembre 2025
**👨‍💻 Responsable:** Equipo OFITEC.AI
