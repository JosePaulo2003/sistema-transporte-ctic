<?php
declare(strict_types=1);
require_once __DIR__ . '/../aplicacao/inicializacao.php';
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
        require_once __DIR__ . '/../aplicacao/solicitacoes.php';
        require_once __DIR__ . '/../aplicacao/passageiros.php';
        require_once __DIR__ . '/../aplicacao/usuarios.php';
        require_once __DIR__ . '/../aplicacao/conta.php';
        if (in_array($caminho, ['/api/autenticacao/recuperar','/api/autenticacao/redefinir'], true)) atender_recuperacao($caminho, $metodo);
        if ($caminho === '/api/conta' || $caminho === '/api/conta/senha') atender_conta($caminho, $metodo);
        foreach (['usuarios','passageiros','solicitacoes'] as $recurso) {
            if ($caminho === '/api/' . $recurso || str_starts_with($caminho, '/api/' . $recurso . '/')) {
                ('atender_' . $recurso)($caminho, $metodo);
            }
        }
        $rotas = ['/api/autenticacao/csrf'=>'GET', '/api/autenticacao/entrar'=>'POST', '/api/autenticacao/usuario'=>'GET', '/api/autenticacao/sair'=>'POST'];
        if (!isset($rotas[$caminho])) responder_json(['erro'=>'Rota da API não encontrada.'], 404);
        exigir_metodo($metodo, [$rotas[$caminho]]);
        if ($caminho === '/api/autenticacao/csrf') responder_json(['csrf'=>token_csrf()]);
        if ($caminho === '/api/autenticacao/entrar') {
            validar_csrf();
            $resultado = autenticar(ler_json());
            $codigoHttp = $resultado['codigo_http'];
            unset($resultado['codigo_http']);
            if ($codigoHttp === 429) header('Retry-After: 900');
            responder_json($resultado, $codigoHttp);
        }
        $usuario = exigir_usuario();
        if ($caminho === '/api/autenticacao/usuario') responder_json(['usuario'=>$usuario, 'csrf'=>token_csrf()]);
        validar_csrf();
        encerrar_sessao();
        responder_json(['mensagem'=>'Sessão encerrada.']);
    }
    exigir_metodo($metodo, ['GET']);
    $paginas = ['/painel'=>'login.html'];
    foreach (['nova-solicitacao','solicitantes','passageiros','revisao-envio','solicitacoes','usuarios',
        'passageiros-cadastrados','adicionar-passageiro','editar-passageiro','buscar-passageiro',
        'passageiro-salvo','passageiro-removido','detalhes-solicitacao','analisar-solicitacao',
        'cancelar-solicitacao','descartar-solicitacao','solicitacao-enviada','solicitacoes-filtradas',
        'minha-conta','sair-da-conta','como-funciona','recuperar-senha','confirmar-email','redefinir-senha'] as $pagina) {
        $paginas['/' . $pagina] = $pagina . '.html';
    }
    $enderecosAntigos = ['/public/views/pages/index.html'=>'/entrar', '/public/views/pages/login.php'=>'/entrar',
        '/index.php'=>'/', '/public/index.php'=>'/', '/index.html'=>'/entrar', '/login.php'=>'/entrar'];
    foreach ($paginas as $rota=>$arquivo) {
        $enderecosAntigos['/public/views/pages/' . $arquivo] = $rota;
        $enderecosAntigos['/views/pages/' . $arquivo] = $rota;
        $enderecosAntigos['/' . $arquivo] = $rota;
    }
    if (isset($enderecosAntigos[$caminho])) {
        $consulta = $_SERVER['QUERY_STRING'] ?? '';
        header('Location: ' . $enderecosAntigos[$caminho] . ($consulta !== '' ? '?' . $consulta : ''), true, 302);
        exit;
    }
    $usuario = usuario_atual();
    if ($caminho === '/') { header('Location: ' . ($usuario ? '/painel' : '/entrar')); exit; }
    if ($caminho === '/entrar') {
        if ($usuario) { header('Location: /painel'); exit; }
        require __DIR__ . '/../aplicacao/tela-entrada.php';
        exit;
    }
    if (!isset($paginas[$caminho])) { http_response_code(404); exit('Página não encontrada.'); }
    $publica = in_array($caminho, ['/recuperar-senha','/confirmar-email','/redefinir-senha'], true);
    if (!$publica && !$usuario) { header('Location: /entrar'); exit; }
    if (in_array($caminho, ['/usuarios','/analisar-solicitacao'], true) && $usuario['perfil'] !== 'administrador') {
        http_response_code(403); exit('Acesso exclusivo para administradores.');
    }
    $conteudo = file_get_contents(__DIR__ . '/views/pages/' . $paginas[$caminho]);
    $conteudo = str_replace(['../css/', '../img/'], ['/public/views/css/', '/public/views/img/'], $conteudo);
    $links = ['index.html'=>'/entrar', 'login.php'=>'/entrar'];
    foreach ($paginas as $rota=>$arquivo) $links[$arquivo] = $rota;
    // Eu traduzo os links antigos aqui: perseguir cada cabeçalho copiado não rende adicional no salário.
    $conteudo = preg_replace_callback('~\b(href|action)="([^"?#]+)([^" ]*)"~', function (array $trecho) use ($links): string {
        return $trecho[1] . '="' . ($links[$trecho[2]] ?? $trecho[2]) . $trecho[3] . '"';
    }, $conteudo);
    $scripts = '<link rel="stylesheet" href="/public/assets/autenticacao.css">'
        . '<link rel="stylesheet" href="/public/assets/funcionalidades.css">'
        . '<script src="/public/assets/js/api.js" defer></script>';
    if ($publica) {
        $scripts .= '<script src="/public/assets/js/recuperacao.js" defer></script>';
        if ($caminho === '/confirmar-email' && (configuracao()['emails']['transporte'] ?? 'arquivo') === 'arquivo'
            && (configuracao()['ambiente_local'] ?? false)) {
            $conteudo = str_replace('O próximo passo está na sua caixa de entrada.', 'Ambiente local: consulte a mensagem gerada em armazenamento/emails.', $conteudo);
            $conteudo = str_replace('Link enviado', 'Pedido processado', $conteudo);
            $conteudo = str_replace('Se o e-mail estiver cadastrado, você receberá as instruções de recuperação.',
                'Se o e-mail estiver cadastrado, o link foi salvo na pasta local de e-mails. Não houve envio externo.', $conteudo);
        }
    } else {
        $conteudo = preg_replace('~<main\b~', '<main aria-busy="true"', $conteudo, 1);
        $identidade = json_encode($usuario, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_UNESCAPED_UNICODE);
        $scripts .= '<script>window.CTIC_USUARIO=' . $identidade . ';</script><script src="/public/assets/js/sessao.js" defer></script>';
        $scripts .= '<script src="/public/assets/js/' . ($caminho === '/usuarios' ? 'usuarios' : 'telas') . '.js" defer></script>';
        $acoes = '<button type="button" class="ctic-sair" id="ctic-sair">Sair</button>';
        if ($usuario['perfil'] === 'administrador') $acoes = '<a class="ctic-sair" href="/usuarios">Usuários</a>' . $acoes;
        $conteudo = str_replace('</header>', $acoes . '</header>', $conteudo);
    }
    echo str_replace('</head>', $scripts . '</head>', $conteudo);
} catch (Throwable $erro) {
    error_log((string)$erro);
    if ($ehApi) responder_json(['erro'=>'Serviço indisponível. Verifique a conexão com o MySQL e a preparação do banco.'], 503);
    http_response_code(503);
    echo 'Sistema indisponível. Confira a configuração local, o serviço MySQL e execute comandos/preparar.php.';
}
