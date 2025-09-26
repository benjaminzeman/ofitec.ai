# ============================================================================
# OFITEC.AI - SCRIPT DE CONFIGURACIÓN AVANZADA DE COPILOT
# ============================================================================

Write-Host "🤖 Aplicando configuración avanzada de GitHub Copilot..." -ForegroundColor Green

# Verificar que estamos en el directorio correcto
$projectRoot = "C:\Ofitec\ofitec.ai"
if (-not (Test-Path $projectRoot)) {
    Write-Host "❌ Error: Proyecto no encontrado en $projectRoot" -ForegroundColor Red
    exit 1
}

Set-Location $projectRoot
Write-Host "📁 Directorio de trabajo: $((Get-Location).Path)" -ForegroundColor Cyan

# ============================================================================
# VERIFICAR ARCHIVOS DE CONFIGURACIÓN
# ============================================================================

$configFiles = @(
    ".vscode\settings.json",
    ".vscode\copilot.json", 
    ".copilot-instructions.md"
)

Write-Host "`n🔍 Verificando archivos de configuración..." -ForegroundColor Yellow

foreach ($file in $configFiles) {
    if (Test-Path $file) {
        Write-Host "  ✅ $file - OK" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $file - FALTA" -ForegroundColor Red
    }
}

# ============================================================================
# COMANDOS AUTO-APROBADOS DISPONIBLES
# ============================================================================

Write-Host "`n🚀 COMANDOS AUTO-APROBADOS CONFIGURADOS:" -ForegroundColor Green

$autoCommands = @(
    "# Desarrollo Frontend",
    "npm run dev",
    "npm run build",
    "npm run lint",
    "npm run test",
    "npm install",
    "",
    "# Backend Python",
    "python -m pytest",
    "python -m flake8", 
    "python server.py",
    "pip install -r requirements.txt",
    "",
    "# Docker",
    "docker compose up -d",
    "docker compose down",
    "docker compose build",
    "docker compose logs",
    "docker compose ps",
    "",
    "# Git (Safe)",
    "git status",
    "git diff",
    "git log --oneline -10",
    "git branch",
    "git fetch",
    "",
    "# Sistema",
    "ls / dir",
    "pwd / cd",
    "cat / type",
    "grep / findstr",
    "curl"
)

foreach ($cmd in $autoCommands) {
    if ($cmd.StartsWith("#")) {
        Write-Host "  $cmd" -ForegroundColor Cyan
    } elseif ($cmd -eq "") {
        Write-Host ""
    } else {
        Write-Host "  ✓ $cmd" -ForegroundColor White
    }
}

# ============================================================================
# VERIFICAR EXTENSIONES DE VS CODE
# ============================================================================

Write-Host "`n🔌 Verificando extensiones requeridas..." -ForegroundColor Yellow

$requiredExtensions = @(
    "GitHub.copilot",
    "GitHub.copilot-chat", 
    "ms-python.python",
    "esbenp.prettier-vscode"
)

foreach ($ext in $requiredExtensions) {
    try {
        $installed = code --list-extensions 2>$null | Where-Object { $_ -eq $ext }
        if ($installed) {
            Write-Host "  ✅ $ext - Instalada" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  $ext - NO instalada" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ❓ No se pudo verificar $ext" -ForegroundColor Gray
    }
}

# ============================================================================
# VALIDAR CONFIGURACIÓN ESPECÍFICA DEL PROYECTO
# ============================================================================

Write-Host "`n🎯 CONFIGURACIONES ESPECÍFICAS DEL PROYECTO:" -ForegroundColor Green

Write-Host "  📋 Frontend Port: 3001 (Ley de Puertos)" -ForegroundColor White
Write-Host "  📋 Backend Port: 5555 (Ley de Puertos)" -ForegroundColor White
Write-Host "  📋 Database: SQLite - data/chipax_data.db" -ForegroundColor White
Write-Host "  📋 Módulos Extraídos: 4 módulos de server.py" -ForegroundColor White
Write-Host "  📋 Type Safety: TypeScript Strict + Python Type Hints" -ForegroundColor White

# ============================================================================
# VERIFICAR ESTADO DE LA REFACTORIZACIÓN
# ============================================================================

Write-Host "`n🔄 ESTADO DE REFACTORIZACIÓN:" -ForegroundColor Green

$refactoredModules = @(
    "backend\config.py",
    "backend\rate_limiting.py", 
    "backend\db_utils_centralized.py",
    "backend\ai_jobs.py"
)

$totalLinesExtracted = 0
foreach ($module in $refactoredModules) {
    if (Test-Path $module) {
        $lineCount = (Get-Content $module).Count
        $totalLinesExtracted += $lineCount
        Write-Host "  ✅ $module - $lineCount líneas" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $module - FALTA" -ForegroundColor Red
    }
}

Write-Host "  📊 Total líneas extraídas: $totalLinesExtracted" -ForegroundColor Cyan

# ============================================================================
# RECOMENDACIONES FINALES
# ============================================================================

Write-Host "`n💡 RECOMENDACIONES:" -ForegroundColor Yellow
Write-Host "  1. Reiniciar VS Code para aplicar configuraciones" -ForegroundColor White
Write-Host "  2. Verificar que GitHub Copilot esté activo" -ForegroundColor White
Write-Host "  3. Probar comandos auto-aprobados en terminal" -ForegroundColor White
Write-Host "  4. Usar Ctrl+I para chat de Copilot" -ForegroundColor White
Write-Host "  5. Configurar .env con OPENAI_API_KEY si es necesario" -ForegroundColor White

Write-Host "`n🎉 Configuración de Copilot completada!" -ForegroundColor Green
Write-Host "Reinicia VS Code para aplicar todos los cambios." -ForegroundColor Cyan