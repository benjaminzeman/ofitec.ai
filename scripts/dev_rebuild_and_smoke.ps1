# PS script: Rebuild docker stack and run SC EP smoke test
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$compose = Join-Path $root 'dev_compose_rebuild.ps1'
$smoke   = Join-Path $root 'smoke_sc_ep.ps1'

& $compose
& $smoke
