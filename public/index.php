<?php
declare(strict_types=1);
require __DIR__ . '/../aplicacao/inicializacao.php';
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('Referrer-Policy: same-origin');
$caminho = rawurldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/');
$metodo = $_SERVER['REQUEST_METHOD'];
$ehApi = str_starts_with($caminho, '/api/');
try {
    iniciar_sessao();
    if ($ehApi) {
        // A API confere o perfil no servidor, independentemente dos links exibidos na interface.
        if ($caminho === '/api/usuarios' || str_starts_with($caminho, '/api/usuarios/')) {
            require __DIR__ . '/../aplicacao/usuarios.php';
            atender_usuarios($caminho, $metodo);
        }
        // As rotas de transporte compartilham a autenticação e a sessão existentes.
        if ($caminho === '/api/solicitacoes' || str_starts_with($caminho, '/api/solicitacoes/')) {
            require __DIR__ . '/../aplicacao/solicitacoes.php';
            atender_solicitacoes($caminho, $metodo);
        }
        $rotas = ['/api/autenticacao/csrf' => 'GET', '/api/autenticacao/entrar' => 'POST',
            '/api/autenticacao/usuario' => 'GET', '/api/autenticacao/sair' => 'POST'];
        if (!isset($rotas[$caminho])) {
            responder_json(['erro' => 'Rota da API não encontrada.'], 404);
        }
        if ($metodo !== $rotas[$caminho]) {
            header('Allow: ' . $rotas[$caminho]);
            responder_json(['erro' => 'Método não permitido.'], 405);
        }
        if ($caminho === '/api/autenticacao/csrf') {
            responder_json(['csrf' => token_csrf()]);
        }
        if ($caminho === '/api/autenticacao/entrar') {
            validar_csrf();
            $resultado = autenticar(ler_json());
            $codigoHttp = $resultado['codigo_http'];
            unset($resultado['codigo_http']);
            if ($codigoHttp === 429) header('Retry-After: 900');
            responder_json($resultado, $codigoHttp);
        }
        $usuario = usuario_atual();
        if (!$usuario) responder_json(['erro' => 'Autenticação necessária.'], 401);
        if ($caminho === '/api/autenticacao/usuario') responder_json(['usuario' => $usuario, 'csrf' => token_csrf()]);
        validar_csrf();
        encerrar_sessao();
        responder_json(['mensagem' => 'Sessão encerrada.']);
    }
    if ($metodo !== 'GET') {
        header('Allow: GET');
        http_response_code(405);
        exit('Método não permitido.');
    }
    // Preserva os endereços do protótipo, redirecionando para as rotas controladas pelo servidor.
    $enderecosAntigos = ['/public/views/pages/index.html' => '/entrar', '/public/views/pages/login.php' => '/entrar',
        '/public/views/pages/login.html' => '/painel', '/index.php' => '/', '/public/index.php' => '/'];
    $paginas = ['/painel' => 'login.html', '/nova-solicitacao' => 'nova-solicitacao.html',
        '/solicitacoes' => 'solicitacoes.html', '/solicitantes' => 'solicitantes.html',
        '/passageiros' => 'passageiros.html', '/revisao-envio' => 'revisao-envio.html', '/usuarios' => 'usuarios.html'];
    foreach ($paginas as $rota => $arquivo) $enderecosAntigos['/public/views/pages/' . $arquivo] = $rota;
    if (isset($enderecosAntigos[$caminho])) {
        header('Location: ' . $enderecosAntigos[$caminho], true, 302);
        exit;
    }
    $usuario = usuario_atual();
    if ($caminho === '/') {
        header('Location: ' . ($usuario ? '/painel' : '/entrar'));
        exit;
    }
    if ($caminho === '/entrar') {
        if ($usuario) { header('Location: /painel'); exit; }
        require __DIR__ . '/../aplicacao/tela-entrada.php';
        exit;
    }
    if (!isset($paginas[$caminho])) { http_response_code(404); exit('Página não encontrada.'); }
    if (!$usuario) { header('Location: /entrar'); exit; }
    if ($caminho === '/usuarios' && $usuario['perfil'] !== 'administrador') {
        http_response_code(403);
        exit('Acesso exclusivo para administradores.');
    }
    $conteudoHtml = file_get_contents(__DIR__ . '/views/pages/' . $paginas[$caminho]);
    $conteudoHtml = str_replace('../css/', '/public/views/css/', $conteudoHtml);
    $conteudoHtml = str_replace('../img/', '/public/views/img/', $conteudoHtml);
    foreach ($paginas as $rota => $arquivo) $conteudoHtml = str_replace('href="' . $arquivo . '"', 'href="' . $rota . '"', $conteudoHtml);
    // O link administrativo também fica disponível no celular, fora da barra inferior compacta.
    if ($usuario['perfil'] === 'administrador') {
        $conteudoHtml = str_replace('</header>', '<a class="ctic-sair" href="/usuarios">Usuários</a></header>', $conteudoHtml);
    }
    // Escapa a identidade ao inseri-la no HTML para impedir que dados sejam interpretados como código.
    $identidade = json_encode($usuario, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_UNESCAPED_UNICODE);
    $conteudoHtml = str_replace('</head>', '<link rel="stylesheet" href="/public/assets/autenticacao.css">'
        . '<script>window.CTIC_USUARIO = ' . $identidade . ';</script><script src="/public/assets/js/sessao.js" defer></script></head>', $conteudoHtml);
    $conteudoHtml = str_replace('</header>', '<button type="button" class="ctic-sair" id="ctic-sair">Sair</button></header>', $conteudoHtml);
    echo $conteudoHtml;
} catch (Throwable $erro) {
    error_log((string) $erro);
    if ($ehApi) responder_json(['erro' => 'Serviço indisponível. Verifique a configuração do servidor e do banco.'], 503);
    http_response_code(503);
    echo 'Sistema indisponível. Verifique a configuração e as migrações descritas no LEIA-ME.md.';
}
