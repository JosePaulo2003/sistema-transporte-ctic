#!/usr/bin/env bash
set -eu
cd -- "$(dirname -- "$0")"
# O roteador impede o acesso direto aos arquivos de configuração e às páginas protegidas.
echo 'Sistema de Transportes: http://127.0.0.1:8080'
echo 'Para encerrar, pressione Ctrl+C.'
exec ./comandos/php.sh -S 127.0.0.1:8080 roteador.php
