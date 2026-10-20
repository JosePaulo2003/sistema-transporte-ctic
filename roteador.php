<?php
// Roteador do servidor de desenvolvimento. Nunca exponha a raiz como arquivos estáticos.
$caminho = rawurldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/');
$caminhoRecurso = str_starts_with($caminho, '/public/') ? substr($caminho, 7) : $caminho;
$permitido = preg_match('~^/(assets/|views/(css|img)/)~', $caminhoRecurso)
    && preg_match('~\.(css|js|svg|png|jpg|jpeg|webp|ico|woff2?)$~i', $caminhoRecurso);
$arquivo = realpath(__DIR__ . '/public' . $caminhoRecurso);
$diretorioPublico = realpath(__DIR__ . '/public');
if ($permitido && $arquivo && str_starts_with($arquivo, $diretorioPublico . DIRECTORY_SEPARATOR) && is_file($arquivo)) {
    $tipos = ['css'=>'text/css', 'js'=>'text/javascript', 'svg'=>'image/svg+xml', 'png'=>'image/png',
        'jpg'=>'image/jpeg', 'jpeg'=>'image/jpeg', 'webp'=>'image/webp', 'ico'=>'image/x-icon',
        'woff'=>'font/woff', 'woff2'=>'font/woff2'];
    header('Content-Type: ' . $tipos[strtolower(pathinfo($arquivo, PATHINFO_EXTENSION))]);
    header('X-Content-Type-Options: nosniff');
    readfile($arquivo);
    return true;
}
require __DIR__ . '/public/index.php';
