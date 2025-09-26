# Migración de OFITEC.AI a repo independiente
param(
  [string]$SourceRoot = "c:\Odoo\custom_addons",
  [string]$TargetRoot = "c:\Odoo\custom_addons\ofitec.ai"
)

$ErrorActionPreference = "Stop"

function Copy-Safe {
  param([string]$src, [string]$dst)
  if (Test-Path $src) {
    Write-Host "Copiando: $src -> $dst" -ForegroundColor Green
    New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
    Copy-Item -Recurse -Force $src $dst
  } else {
    Write-Host "No existe: $src" -ForegroundColor Yellow
  }
}

# 1) Docs oficiales
Copy-Safe "$SourceRoot\ofitec.ai\docs_oficiales" "$TargetRoot\docs"

# 2) Frontend Next.js
Copy-Safe "$SourceRoot\ofitec.ai\web\*" "$TargetRoot\frontend\"

# 3) Backend Flask (server organizado + templates/static/reportes)
Copy-Safe "$SourceRoot\ofitec.ai\server_organizado.py" "$TargetRoot\backend\server.py"
Copy-Safe "$SourceRoot\ofitec.ai\templates" "$TargetRoot\backend\templates"
Copy-Safe "$SourceRoot\ofitec.ai\static" "$TargetRoot\backend\static"
Copy-Safe "$SourceRoot\ofitec.ai\reportes" "$TargetRoot\backend\reportes"

# 4) Servicio Conciliación Bancaria
Copy-Safe "$SourceRoot\ofitec_conciliacion_bancaria\*" "$TargetRoot\services\conciliacion_bancaria\"

# 5) Scripts útiles (sin Odoo)
$utilScripts = @(
  "mostrar_estructura_db.py",
  "explore_chipax_db.py",
  "verificar_tablas.py"
)
foreach ($s in $utilScripts) {
  if (Test-Path "$SourceRoot\$s") {
    Copy-Safe "$SourceRoot\$s" "$TargetRoot\scripts\$s"
  }
}

# 6) Data (solo copiar si existe, no versionar en git)
if (Test-Path "$SourceRoot\chipax_data.db") {
  Copy-Safe "$SourceRoot\chipax_data.db" "$TargetRoot\data\chipax_data.db"
}
if (Test-Path "$SourceRoot\ofitec_dev.db") {
  Copy-Safe "$SourceRoot\ofitec_dev.db" "$TargetRoot\data\ofitec_dev.db"
}

Write-Host "\nMigración completada. Revisa $TargetRoot" -ForegroundColor Cyan
