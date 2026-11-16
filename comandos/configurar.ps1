$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (Test-Path -LiteralPath 'configuracao\aplicacao.local.php') {
    Write-Host 'A configuração local já existe. Vou conferir o banco e aplicar as migrações pendentes.'
    & (Join-Path $PSScriptRoot 'php.ps1') comandos/preparar.php
    exit $LASTEXITCODE
}
function Ler-ComPadrao([string]$Pergunta, [string]$Padrao) {
    $resposta = Read-Host "$Pergunta [$Padrao]"
    if ([string]::IsNullOrWhiteSpace($resposta)) { return $Padrao }
    return $resposta.Trim()
}
$variaveisAnteriores = @{}
$nomesVariaveis = @('CTIC_BANCO_HOST','CTIC_BANCO_PORTA','CTIC_BANCO_NOME','CTIC_BANCO_ADMIN','CTIC_BANCO_SENHA','CTIC_ADMIN_EMAIL','CTIC_ADMIN_NOME')
foreach ($nomeVariavel in $nomesVariaveis) { $variaveisAnteriores[$nomeVariavel] = [Environment]::GetEnvironmentVariable($nomeVariavel, 'Process') }
try {
    $env:CTIC_BANCO_HOST = Ler-ComPadrao 'Servidor do Workbench' '127.0.0.1'
    $env:CTIC_BANCO_PORTA = Ler-ComPadrao 'Porta' '3306'
    $env:CTIC_BANCO_NOME = Ler-ComPadrao 'Banco do sistema' 'transporte_ctic'
    $env:CTIC_BANCO_ADMIN = Ler-ComPadrao 'Usuário administrativo do MySQL' 'root'
    $senhaBancoSegura = Read-Host 'Senha desse usuário MySQL (não será exibida)' -AsSecureString
    $env:CTIC_BANCO_SENHA = [System.Net.NetworkCredential]::new('', $senhaBancoSegura).Password
    $env:CTIC_ADMIN_EMAIL = Ler-ComPadrao 'E-mail do primeiro administrador do sistema' 'admin.transporte@uea.edu.br'
    $env:CTIC_ADMIN_NOME = Ler-ComPadrao 'Nome do administrador' 'Administrador de Transportes'
    & (Join-Path $PSScriptRoot 'php.ps1') comandos/configurar.php
    if ($LASTEXITCODE -ne 0) { throw 'A configuração não foi concluída.' }
    & (Join-Path $PSScriptRoot 'php.ps1') comandos/preparar.php
    if ($LASTEXITCODE -ne 0) { throw 'A preparação não foi concluída.' }
    Write-Host 'Pronto. Abra CREDENCIAIS.local.txt para consultar o acesso e execute .\iniciar.ps1.'
} finally {
    foreach ($nomeVariavel in $nomesVariaveis) { [Environment]::SetEnvironmentVariable($nomeVariavel, $variaveisAnteriores[$nomeVariavel], 'Process') }
    if ($senhaBancoSegura) { $senhaBancoSegura.Dispose() }
}
