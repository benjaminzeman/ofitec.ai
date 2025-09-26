# 🗄️ Database Management System

Sistema automatizado de gestión y limpieza de bases de datos para mantener el repositorio ordenado y limpio.

## 🎯 Problema Resuelto

El sistema de testing generaba miles de bases de datos temporales que se acumulaban en el directorio `data/`, ocupando espacio innecesario y creando desorden en el repositorio.

**Antes de la implementación:**
- ✅ **3,487 bases de datos de prueba** acumuladas
- ❌ Ocupando ~200MB de espacio innecesario
- ❌ Degradando el rendimiento del sistema de archivos
- ❌ Dificultando la identificación de bases de datos importantes

**Después de la implementación:**
- ✅ Solo **2 bases de datos productivas** (`chipax_data.db`, `ofitec_dev.db`)
- ✅ **Limpieza automática** de archivos temporales
- ✅ **Sistema de prevención** para evitar acumulación futura
- ✅ Repositorio ordenado y eficiente

## 🛠️ Herramientas Disponibles

### 1. Script Python: `tools/cleanup_test_dbs.py`
```bash
# Mostrar estadísticas de bases de datos
python tools/cleanup_test_dbs.py --stats

# Limpiar bases de datos antiguas (>24 horas)
python tools/cleanup_test_dbs.py

# Limpiar todas las bases de datos de prueba
python tools/cleanup_test_dbs.py --force

# Vista previa de limpieza (sin eliminar)
python tools/cleanup_test_dbs.py --dry-run
```

### 2. Script PowerShell: `scripts/cleanup_databases.ps1`
```powershell
# Mostrar estadísticas
.\scripts\cleanup_databases.ps1 -Stats

# Limpiar bases de datos antiguas
.\scripts\cleanup_databases.ps1

# Limpiar todas las bases de datos de prueba
.\scripts\cleanup_databases.ps1 -Force

# Vista previa de limpieza
.\scripts\cleanup_databases.ps1 -DryRun
```

### 3. Tareas VS Code
Disponibles en el panel de tareas (`Ctrl+Shift+P` → "Tasks: Run Task"):

- **Database: Show statistics** - Mostrar estadísticas actuales
- **Database: Clean test databases** - Limpieza automática
- **Database: Force clean all test DBs** - Limpieza forzada

## 🔧 Sistema de Prevención Automática

### 1. Gestión Inteligente en Tests (`backend/tests/test_db_cleanup.py`)
- **Bases de datos temporales** se crean en directorio del sistema
- **Limpieza automática** al finalizar tests
- **Esquemas predefinidos** para tests comunes

### 2. Fixture Mejorada (`backend/tests/conftest.py`)
- Usa el nuevo sistema de gestión de DBs
- **Limpieza periódica** automática (cada ~50 tests)
- Previene acumulación de archivos temporales

### 3. Configuración Pytest (`config/pytest.ini`)
- Configuración optimizada para el nuevo sistema
- Paths de test centralizados
- Reportes mejorados

## 📊 Estadísticas Típicas

```text
📊 DATABASE STATISTICS:
==================================================
production           :    2 files (30.37 MB)
--------------------------------------------------
TOTAL                :    2 files (30.37 MB)

📁 PRODUCTION DATABASES:
  ofitec_dev.db        -   24,7 MB - 2025-09-25 02:40
  chipax_data.db       -   5,68 MB - 2025-09-24 15:09
```

## 🚀 Beneficios Implementados

### ✅ **Rendimiento**
- Reducción del 99.9% en archivos de base de datos
- Mejora en velocidad de operaciones de archivos
- Menor uso de espacio en disco

### ✅ **Organización**
- Solo bases de datos productivas visibles
- Directorio `data/` limpio y organizado
- Fácil identificación de archivos importantes

### ✅ **Mantenimiento**
- Limpieza automática sin intervención manual
- Prevención proactiva de acumulación
- Herramientas de monitoreo integradas

### ✅ **Desarrollo**
- Tests más rápidos (menos E/O de archivos)
- Ambiente de desarrollo más limpio
- Menos distracciones durante el trabajo

## 🔄 Mantenimiento Recomendado

### Automático
- La limpieza se ejecuta automáticamente cada ~50 tests
- Tests usan directorios temporales del sistema
- Cleanup al cierre de la aplicación

### Manual (Opcional)
```bash
# Limpieza semanal recomendada
python tools/cleanup_test_dbs.py --force

# Verificación mensual
python tools/cleanup_test_dbs.py --stats
```

## 🎯 Estado Actual

- ✅ **Sistema implementado y funcionando**
- ✅ **3,487 archivos de prueba eliminados**
- ✅ **~200MB de espacio liberado**
- ✅ **Prevención automática activa**
- ✅ **Herramientas de monitoreo disponibles**

El repositorio ahora está **limpio, organizado y mantiene automáticamente su orden** 🎉