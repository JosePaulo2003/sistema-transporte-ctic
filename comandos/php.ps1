$ArgumentosPhp = $args
$ErrorActionPreference = 'Stop'
$phpLocal = Join-Path $env:LOCALAPPDATA 'CTIC\php\php.exe'
if ($env:CTIC_PHP -and (Test-Path -LiteralPath $env:CTIC_PHP)) {
    $executavelPhp = $env:CTIC_PHP
} elseif (Get-Command php -ErrorAction SilentlyContinue) {
    $executavelPhp = (Get-Command php).Source
} elseif (Test-Path -LiteralPath $phpLocal) {
    $executavelPhp = $phpLocal
} else {
    throw 'PHP não encontrado. Instale PHP 8.1 ou superior com pdo_mysql, ou defina CTIC_PHP com o caminho do php.exe.'
}
& $executavelPhp @ArgumentosPhp
exit $LASTEXITCODE
