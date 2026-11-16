$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath 'configuracao\aplicacao.local.php')) {
    throw 'Execute configurar.cmd primeiro para conectar o sistema ao seu MySQL.'
}
Write-Host 'Sistema de Transportes: http://127.0.0.1:8080'
Write-Host 'Para encerrar, pressione Ctrl+C.'
& (Join-Path $PSScriptRoot 'comandos\php.ps1') -S 127.0.0.1:8080 roteador.php
