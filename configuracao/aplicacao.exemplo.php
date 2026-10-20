<?php
// Copie para aplicacao.local.php. Nunca versione credenciais reais.
return [
    'banco_de_dados' => [
        'dsn' => 'mysql:host=127.0.0.1;port=3306;dbname=transporte_ctic;charset=utf8mb4',
        'usuario' => 'transporte_aplicacao',
        'senha' => '',
    ],
    'segundos_inatividade_sessao' => 1800,
    'segundos_duracao_sessao' => 28800,
    'cookie_seguro' => false, // true em produção com HTTPS
];
