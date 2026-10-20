#!/usr/bin/env bash
set -eu
# Carrega o driver apenas se ele ainda não estiver habilitado no PHP instalado.
if ! command -v php >/dev/null 2>&1; then
    echo 'PHP não encontrado. Consulte a instalação no LEIA-ME.md.' >&2
    exit 1
fi
if ! php -r 'exit(version_compare(PHP_VERSION, "8.1", ">=") ? 0 : 1);'; then
    echo 'É necessário PHP 8.1 ou superior.' >&2
    exit 1
fi
if php -r 'exit(in_array("mysql", PDO::getAvailableDrivers(), true) ? 0 : 1);'; then
    exec php "$@"
fi
exec php -d extension=pdo_mysql "$@"
