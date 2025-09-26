# =============================================
# OFITEC.AI - DEPLOYMENT DEFINITIVO
# =============================================
# 
# Este script mata todos los procesos conflictivos y 
# levanta la arquitectura unificada definitiva
#

param(
    [switch]$FullAnalysis,
    [switch]$KillAll,
    [int]$WaitSeconds = 5
)

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "OFITEC.AI - DEPLOYMENT ARQUITECTURA UNIFICADA" -ForegroundColor Yellow
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

$WorkspaceRoot = "C:\Users\benja\OneDrive\Escritorio\0. OFITEC.AI\ofitec.ai"
$BackendDir = "$WorkspaceRoot\backend"
$FrontendDir = "$WorkspaceRoot\frontend"

# =============================================
# 1. ANÁLISIS COMPLETO DEL SISTEMA
# =============================================

Write-Host "🔍 1. ANÁLISIS DEL SISTEMA ACTUAL" -ForegroundColor Green
Write-Host "=" * 50

# Verificar estructura de directorios
Write-Host "📁 Directorios:" -ForegroundColor Yellow
Write-Host "   Workspace: $(if (Test-Path $WorkspaceRoot) {'✅ OK'} else {'❌ MISSING'})" 
Write-Host "   Backend:   $(if (Test-Path $BackendDir) {'✅ OK'} else {'❌ MISSING'})"
Write-Host "   Frontend:  $(if (Test-Path $FrontendDir) {'✅ OK'} else {'❌ MISSING'})"
Write-Host ""

# Verificar base de datos
$DatabasePath = "$WorkspaceRoot\data\chipax_data.db"
Write-Host "🗃️ Base de Datos:" -ForegroundColor Yellow
Write-Host "   Path: $DatabasePath"
Write-Host "   Status: $(if (Test-Path $DatabasePath) {'✅ EXISTS'} else {'❌ MISSING'})"

if (Test-Path $DatabasePath) {
    $DbSize = (Get-Item $DatabasePath).Length / 1MB
    Write-Host "   Size: $([math]::Round($DbSize, 2)) MB"
}
Write-Host ""

# Verificar servidores existentes
Write-Host "🖥️ Archivos de Servidor:" -ForegroundColor Yellow
$ServerFiles = Get-ChildItem -Path $BackendDir -Name "server*.py" | Sort-Object
foreach ($file in $ServerFiles) {
    $lines = (Get-Content "$BackendDir\$file" | Measure-Object -Line).Lines
    Write-Host "   $file - $lines líneas"
}
Write-Host ""

# =============================================
# 2. DETECCIÓN DE PROCESOS ACTIVOS
# =============================================

Write-Host "🔍 2. PROCESOS ACTIVOS EN PUERTOS CRÍTICOS" -ForegroundColor Green
Write-Host "=" * 50

$CriticalPorts = @(3000, 3001, 5000, 5555, 8000)
$ActiveProcesses = @()

foreach ($port in $CriticalPorts) {
    try {
        $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($connection) {
            $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
            if ($process) {
                $ActiveProcesses += @{
                    Port = $port
                    PID = $process.Id
                    Name = $process.ProcessName
                    StartTime = $process.StartTime
                }
                Write-Host "   Puerto $port - PID $($process.Id) - $($process.ProcessName) ❌ OCUPADO" -ForegroundColor Red
            }
        } else {
            Write-Host "   Puerto $port - ✅ LIBRE" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "   Puerto $port - ✅ LIBRE" -ForegroundColor Green
    }
}

Write-Host ""

# =============================================
# 3. ELIMINACIÓN DE CONFLICTOS
# =============================================

if ($ActiveProcesses.Count -gt 0 -or $KillAll) {
    Write-Host "⚡ 3. ELIMINANDO PROCESOS CONFLICTIVOS" -ForegroundColor Green
    Write-Host "=" * 50
    
    # Matar procesos Python/Node específicos
    $ConflictProcesses = Get-Process | Where-Object { 
        $_.ProcessName -match "(python|node|npm|yarn)" -and
        $_.MainWindowTitle -notmatch "VS Code"
    }
    
    foreach ($proc in $ConflictProcesses) {
        try {
            Write-Host "   Matando proceso: $($proc.ProcessName) (PID: $($proc.Id))" -ForegroundColor Yellow
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
        catch {
            Write-Host "   Error matando proceso $($proc.Id): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    # Matar procesos específicos por puerto
    foreach ($activeProc in $ActiveProcesses) {
        try {
            Write-Host "   Liberando puerto $($activeProc.Port) - Matando PID $($activeProc.PID)" -ForegroundColor Yellow
            Stop-Process -Id $activeProc.PID -Force -ErrorAction SilentlyContinue
        }
        catch {
            Write-Host "   Error liberando puerto $($activeProc.Port): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    Write-Host "   Esperando $WaitSeconds segundos para liberación completa..." -ForegroundColor Cyan
    Start-Sleep -Seconds $WaitSeconds
    Write-Host ""
}

# =============================================
# 4. VALIDACIÓN DE ARCHIVOS CRÍTICOS
# =============================================

Write-Host "🔍 4. VALIDACIÓN DE ARCHIVOS CRÍTICOS" -ForegroundColor Green
Write-Host "=" * 50

$CriticalFiles = @{
    "server_unified.py" = "$BackendDir\server_unified.py"
    "package.json (frontend)" = "$FrontendDir\package.json"
    "page.tsx (ceo)" = "$FrontendDir\app\ceo\overview\page.tsx"
}

foreach ($file in $CriticalFiles.GetEnumerator()) {
    $exists = Test-Path $file.Value
    $status = if ($exists) { "✅ OK" } else { "❌ MISSING" }
    Write-Host "   $($file.Key): $status"
    
    if ($exists -and $file.Key -eq "server_unified.py") {
        # Verificar endpoints críticos en server_unified.py
        $content = Get-Content $file.Value -Raw
        $hasControlFinanciero = $content -match "/api/control_financiero/resumen"
        $hasCeoOverview = $content -match "/api/ceo/overview"
        
        Write-Host "     - Control Financiero endpoint: $(if ($hasControlFinanciero) {'✅'} else {'❌'})"
        Write-Host "     - CEO Overview endpoint: $(if ($hasCeoOverview) {'✅'} else {'❌'})"
    }
}

Write-Host ""

# =============================================
# 5. LEVANTAMIENTO DEL BACKEND UNIFICADO
# =============================================

Write-Host "🚀 5. INICIANDO BACKEND UNIFICADO" -ForegroundColor Green
Write-Host "=" * 50

# Cambiar al directorio backend
Set-Location $BackendDir

# Verificar Python disponible
try {
    $PythonVersion = python --version 2>&1
    Write-Host "   Python disponible: $PythonVersion" -ForegroundColor Cyan
}
catch {
    Write-Host "   ❌ Python no encontrado" -ForegroundColor Red
    exit 1
}

# Iniciar servidor unificado en background
Write-Host "   Iniciando server_unified.py en puerto 5555..." -ForegroundColor Yellow

$BackendProcess = Start-Process -FilePath "python" -ArgumentList "server_unified.py" -NoNewWindow -PassThru
Write-Host "   Backend iniciado - PID: $($BackendProcess.Id)" -ForegroundColor Green

# Esperar un poco para que el servidor inicie
Start-Sleep -Seconds 3

# Verificar que el backend esté respondiendo
try {
    $Response = Invoke-RestMethod -Uri "http://127.0.0.1:5555/api/status" -TimeoutSec 10
    Write-Host "   ✅ Backend responde correctamente" -ForegroundColor Green
    Write-Host "   Status: $($Response.status)" -ForegroundColor Cyan
}
catch {
    Write-Host "   ❌ Backend no responde: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# =============================================
# 6. LEVANTAMIENTO DEL FRONTEND
# =============================================

Write-Host "🎨 6. INICIANDO FRONTEND" -ForegroundColor Green
Write-Host "=" * 50

Set-Location $FrontendDir

# Verificar Node.js
try {
    $NodeVersion = node --version 2>&1
    Write-Host "   Node.js disponible: $NodeVersion" -ForegroundColor Cyan
}
catch {
    Write-Host "   ❌ Node.js no encontrado" -ForegroundColor Red
    Write-Host "   Continuando solo con backend..." -ForegroundColor Yellow
    return
}

# Instalar dependencias si es necesario
if (-not (Test-Path "node_modules")) {
    Write-Host "   Instalando dependencias..." -ForegroundColor Yellow
    npm install
}

# Iniciar frontend en modo desarrollo
Write-Host "   Iniciando frontend en puerto 3001..." -ForegroundColor Yellow
$env:PORT = "3001"
$FrontendProcess = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -NoNewWindow -PassThru
Write-Host "   Frontend iniciado - PID: $($FrontendProcess.Id)" -ForegroundColor Green

Write-Host ""

# =============================================
# 7. TESTS DE CONECTIVIDAD
# =============================================

Write-Host "🔬 7. TESTS DE CONECTIVIDAD" -ForegroundColor Green
Write-Host "=" * 50

Start-Sleep -Seconds 5  # Esperar que ambos servicios inicien

# Test Backend
Write-Host "   Testing Backend (127.0.0.1:5555):" -ForegroundColor Yellow
$BackendEndpoints = @(
    "/api/status",
    "/api/control_financiero/resumen", 
    "/api/ceo/overview"
)

foreach ($endpoint in $BackendEndpoints) {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:5555$endpoint" -TimeoutSec 5
        Write-Host "     GET $endpoint - ✅ OK" -ForegroundColor Green
    }
    catch {
        Write-Host "     GET $endpoint - ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Test Frontend
Write-Host "   Testing Frontend (127.0.0.1:3001):" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:3001" -TimeoutSec 10 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "     Frontend home - ✅ OK" -ForegroundColor Green
    }
}
catch {
    Write-Host "     Frontend home - ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# =============================================
# 8. RESUMEN FINAL
# =============================================

Write-Host "📊 8. RESUMEN FINAL" -ForegroundColor Green
Write-Host "=" * 50

Write-Host "🖥️ SERVICIOS ACTIVOS:" -ForegroundColor Yellow
Write-Host "   Backend:  http://127.0.0.1:5555 (Unified Server)"
Write-Host "   Frontend: http://127.0.0.1:3001 (Next.js Dev)"
Write-Host ""

Write-Host "📱 ENDPOINTS DISPONIBLES:" -ForegroundColor Yellow
Write-Host "   Status:             http://127.0.0.1:5555/api/status"
Write-Host "   Control Financiero: http://127.0.0.1:5555/api/control_financiero/resumen"
Write-Host "   CEO Overview:       http://127.0.0.1:5555/api/ceo/overview"
Write-Host "   Debug Info:         http://127.0.0.1:5555/api/debug/info"
Write-Host ""

Write-Host "🌐 FRONTEND PAGES:" -ForegroundColor Yellow
Write-Host "   Home:               http://127.0.0.1:3001/"
Write-Host "   Control Financiero: http://127.0.0.1:3001/control-financiero"
Write-Host "   CEO Overview:       http://127.0.0.1:3001/ceo/overview"
Write-Host ""

Write-Host "🎯 PROCESOS ACTIVOS:" -ForegroundColor Yellow
if ($BackendProcess -and !$BackendProcess.HasExited) {
    Write-Host "   Backend PID: $($BackendProcess.Id) ✅ RUNNING"
} else {
    Write-Host "   Backend: ❌ NOT RUNNING"
}

if ($FrontendProcess -and !$FrontendProcess.HasExited) {
    Write-Host "   Frontend PID: $($FrontendProcess.Id) ✅ RUNNING"
} else {
    Write-Host "   Frontend: ❌ NOT RUNNING"
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "✅ ARQUITECTURA UNIFICADA DESPLEGADA CORRECTAMENTE" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan

# Mantener consola abierta para monitoreo
Write-Host ""
Write-Host "Presiona cualquier tecla para monitorear procesos o Ctrl+C para salir..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")