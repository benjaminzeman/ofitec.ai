# PS script: rebuild and start Docker stack cleanly
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host '== Checking Docker engine'
# Ensure Docker Desktop/Engine is running and accessible from PowerShell
& docker info *> $null
if ($LASTEXITCODE -ne 0) {
	Write-Error 'Docker engine is not running or docker is not in PATH. Start Docker Desktop and retry.'
	exit 1
}

Write-Host '== Checking docker compose availability'
& docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
	Write-Error 'The docker compose CLI plugin is not available. Ensure Docker Desktop with Compose V2 is installed/enabled.'
	exit 1
}

Write-Host '== Checking required ports are free (5555, 3001)'
$ports = @(5555, 3001)
foreach ($p in $ports) {
	try {
		$inUse = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
		if ($inUse) {
			$pids = ($inUse | Select-Object -ExpandProperty OwningProcess -Unique) -join ', '
			Write-Error "Port $p is already in use by PID(s): $pids. Close the process or change port mapping and retry."
			exit 1
		}
	} catch {
		Write-Warning "Unable to verify port $p usage via Get-NetTCPConnection. Proceeding, but compose may fail if the port is busy."
	}
}

Write-Host '== Docker compose DOWN (remove orphans)'
docker compose down --remove-orphans

Write-Host '== Docker compose BUILD (no cache)'
docker compose build --no-cache

Write-Host '== Docker compose UP (force recreate)'
docker compose up -d --force-recreate

Write-Host '== Docker status'
docker compose ps
