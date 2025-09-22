#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Continuous 'y' (or custom token) output for piping into interactive commands.
.DESCRIPTION
  PowerShell implementation similar to GNU yes.
  Usage: ./scripts/yes.ps1 | some-command
  Parameters:
    -Token <string>  Token to repeat (default 'y')
#>
param(
  [string]$Token = 'y'
)
while ($true) {
  Write-Output $Token
}
