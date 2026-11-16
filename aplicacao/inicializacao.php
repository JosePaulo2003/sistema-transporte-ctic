<?php
declare(strict_types=1);

const RAIZ_PROJETO = __DIR__ . '/..';

// Eu carrego a configuração local uma vez e deixo as senhas fora do Git, porque incidente não melhora meu salário.
function configuracao(): array
{
    static $configuracao;
    if ($configuracao === null) {
        $arquivo = getenv('CTIC_CONFIGURACAO') ?: RAIZ_PROJETO . '/configuracao/aplicacao.local.php';
        if (!is_file($arquivo)) {
            throw new RuntimeException('Configuração ausente. Execute comandos/configurar.ps1.');
        }
        $configuracao = require $arquivo;
    }
    return $configuracao;
}

// Eu reutilizo o PDO com consultas preparadas e UTC no banco para não colecionar problema de conexão e fuso.
function banco(): PDO
{
    static $conexao;
    if ($conexao === null) {
        $configuracoes = configuracao()['banco_de_dados'];
        $conexao = new PDO($configuracoes['dsn'], $configuracoes['usuario'], $configuracoes['senha'], [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]);
        $conexao->exec("SET time_zone = '+00:00'");
    }
    return $conexao;
}

// Eu restrinjo a sessão ao cookie: já basta rastrear bug, não vou rastrear identificador vazado na URL.
function iniciar_sessao(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) {
        return;
    }
    ini_set('session.use_strict_mode', '1');
    ini_set('session.use_only_cookies', '1');
    session_name('sessao_transporte_ctic');
    $conexaoHttps = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off';
    session_set_cookie_params([
        'lifetime' => 0, 'path' => '/', 'secure' => $conexaoHttps || (configuracao()['cookie_seguro'] ?? false),
        'httponly' => true, 'samesite' => 'Lax',
    ]);
    session_start();
}

// Eu mantenho um token imprevisível para a sessão, porque requisição forjada só aumenta o meu trabalho.
function token_csrf(): string
{
    return $_SESSION['csrf'] ??= bin2hex(random_bytes(32));
}

// Eu recuso escrita sem CSRF válido para não passar o expediente desfazendo alteração alheia.
function validar_csrf(): void
{
    $token = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? ($_POST['csrf'] ?? '');
    if (!is_string($token) || !hash_equals(token_csrf(), $token)) {
        responder_json(['erro' => 'Sessão de formulário inválida. Atualize a página e tente novamente.'], 419);
    }
}

// Eu encerro a resposta aqui: HTML sobrando no JSON já me toma tempo demais pelo salário.
function responder_json(array $dados, int $codigoHttp = 200): never
{
    http_response_code($codigoHttp);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($dados, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
    exit;
}

// Eu separo objeto de lista antes de converter, porque até JSON arruma serviço quando facilito.
function decodificar_objeto_json(string $conteudo): array
{
    $objeto = json_decode($conteudo, false, 16, JSON_THROW_ON_ERROR);
    if (!$objeto instanceof stdClass) {
        throw new InvalidArgumentException('Envie um objeto JSON.');
    }
    // Eu mantenho os arrays internos para não refazer as validações sem receber por outra implementação.
    return json_decode($conteudo, true, 16, JSON_THROW_ON_ERROR);
}

// Eu limito o corpo a um objeto JSON pequeno: memória também não é salário infinito.
function ler_json(): array
{
    if (strtolower(trim(explode(';', $_SERVER['CONTENT_TYPE'] ?? '')[0])) !== 'application/json') {
        responder_json(['erro' => 'Envie os dados em JSON.'], 415);
    }
    if ((int) ($_SERVER['CONTENT_LENGTH'] ?? 0) > 16384) {
        responder_json(['erro' => 'Dados muito grandes.'], 413);
    }
    try {
        $conteudo = file_get_contents('php://input', false, null, 0, 16385);
        if ($conteudo === false || strlen($conteudo) > 16384) responder_json(['erro'=>'Dados muito grandes.'], 413);
        $dados = decodificar_objeto_json($conteudo);
    } catch (JsonException $erro) {
        responder_json(['erro' => 'JSON inválido.'], 400);
    } catch (InvalidArgumentException $erro) {
        responder_json(['erro' => $erro->getMessage()], 400);
    }
    return $dados;
}

// Eu exponho só a identificação e guardo o hash no servidor para não comprar mais problema.
function dados_publicos_usuario(array $usuario): array
{
    return array_intersect_key($usuario, array_flip(['id', 'nome', 'email', 'perfil', 'setor']));
}

// Eu confiro a conta a cada acesso para não deixar sessão antiga decidir permissão por mim.
function usuario_atual(): ?array
{
    if (!isset($_SESSION['usuario_id'])) {
        return null;
    }
    $agora = time();
    if ($agora - ($_SESSION['ultima_atividade'] ?? 0) >= (configuracao()['segundos_inatividade_sessao'] ?? 1800)
        || $agora - ($_SESSION['autenticado_em'] ?? 0) >= (configuracao()['segundos_duracao_sessao'] ?? 28800)) {
        $_SESSION = [];
        session_regenerate_id(true);
        return null;
    }
    $consulta = banco()->prepare('SELECT id, nome, email, perfil, setor, hash_senha FROM usuarios WHERE id = ? AND ativo = 1');
    $consulta->execute([$_SESSION['usuario_id']]);
    $usuario = $consulta->fetch();
    // Eu comparo a assinatura da senha para encerrar sessões antigas sem ter de caçar uma por uma.
    if (!$usuario || !hash_equals(hash('sha256', $usuario['hash_senha']), $_SESSION['assinatura_senha'] ?? '')) {
        $_SESSION = [];
        session_regenerate_id(true);
        return null;
    }
    $_SESSION['ultima_atividade'] = $agora;
    return dados_publicos_usuario($usuario);
}

// Eu limito tentativas e renovo a sessão no login, porque ataque automatizado não deveria automatizar meu plantão.
function autenticar(array $entrada): array
{
    $email = $entrada['email'] ?? '';
    $senha = $entrada['senha'] ?? '';
    if (!is_string($email) || !is_string($senha) || strlen($senha) > 1024
        || strlen($email) > 254 || !filter_var(trim($email), FILTER_VALIDATE_EMAIL) || $senha === '') {
        return ['codigo_http' => 422, 'erro' => 'Informe um e-mail válido e a senha.'];
    }
    $email = strtolower(trim($email));
    $chaveEmail = hash('sha256', $email);
    // Eu uso REMOTE_ADDR e não confio em cabeçalho inventado pelo cliente: já basta a papelada inventada para mim.
    $chaveIp = hash('sha256', $_SERVER['REMOTE_ADDR'] ?? 'cli');
    $conexao = banco();
    $conexao->exec('DELETE FROM tentativas_acesso WHERE tentativa_em < UTC_TIMESTAMP() - INTERVAL 1 DAY');
    $consulta = $conexao->prepare('SELECT COUNT(*) FROM tentativas_acesso WHERE tentativa_em > UTC_TIMESTAMP() - INTERVAL 15 MINUTE AND chave_email = ?');
    $consulta->execute([$chaveEmail]);
    $quantidadeTentativasEmail = (int) $consulta->fetchColumn();
    $consulta = $conexao->prepare('SELECT COUNT(*) FROM tentativas_acesso WHERE tentativa_em > UTC_TIMESTAMP() - INTERVAL 15 MINUTE AND chave_ip = ?');
    $consulta->execute([$chaveIp]);
    if ($quantidadeTentativasEmail >= 5 || (int) $consulta->fetchColumn() >= 30) {
        return ['codigo_http' => 429, 'erro' => 'Muitas tentativas. Aguarde 15 minutos e tente novamente.'];
    }
    // Eu conto antes do hash para não deixar uma rajada furar o limite enquanto trabalho na senha.
    $consulta = $conexao->prepare('INSERT INTO tentativas_acesso (chave_email, chave_ip) VALUES (?, ?)');
    $consulta->execute([$chaveEmail, $chaveIp]);
    $consulta = $conexao->prepare('SELECT * FROM usuarios WHERE email = ? LIMIT 1');
    $consulta->execute([$email]);
    $usuario = $consulta->fetch();
    // Eu verifico um hash mesmo sem conta para reduzir pistas de tempo, apesar do serviço extra pelo mesmo salário.
    $hashSimulado = '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2uheWG/igi.';
    $senhaValida = password_verify($senha, $usuario ? $usuario['hash_senha'] : $hashSimulado);
    if (!$senhaValida || !$usuario || !(bool) $usuario['ativo']) {
        return ['codigo_http' => 401, 'erro' => 'E-mail ou senha inválidos.'];
    }
    if (password_needs_rehash($usuario['hash_senha'], PASSWORD_DEFAULT)) {
        $consulta = $conexao->prepare('UPDATE usuarios SET hash_senha = ? WHERE id = ?');
        $usuario['hash_senha'] = password_hash($senha, PASSWORD_DEFAULT);
        $consulta->execute([$usuario['hash_senha'], $usuario['id']]);
    }
    $consulta = $conexao->prepare('UPDATE usuarios SET ultimo_acesso_em = UTC_TIMESTAMP() WHERE id = ?');
    $consulta->execute([$usuario['id']]);
    $consulta = $conexao->prepare('DELETE FROM tentativas_acesso WHERE chave_email = ? AND chave_ip = ?');
    $consulta->execute([$chaveEmail, $chaveIp]);
    session_regenerate_id(true);
    $_SESSION = ['usuario_id' => $usuario['id'], 'autenticado_em' => time(), 'ultima_atividade' => time(),
        'csrf' => bin2hex(random_bytes(32)), 'assinatura_senha' => hash('sha256', $usuario['hash_senha'])];
    return ['codigo_http' => 200, 'usuario' => dados_publicos_usuario($usuario), 'csrf' => token_csrf()];
}

// Eu limpo a sessão e expiro o cookie para que sair seja sair, sem me render chamado depois.
function encerrar_sessao(): void
{
    $_SESSION = [];
    $parametrosCookie = session_get_cookie_params();
    setcookie(session_name(), '', ['expires' => time() - 3600, 'path' => $parametrosCookie['path'],
        'secure' => $parametrosCookie['secure'], 'httponly' => true, 'samesite' => 'Lax']);
    session_destroy();
}

function exigir_usuario(): array
{
    $usuario = usuario_atual();
    if (!$usuario) responder_json(['erro'=>'Autenticação necessária.'], 401);
    return $usuario;
}

function exigir_metodo(string $metodo, array $permitidos): void
{
    if (!in_array($metodo, $permitidos, true)) {
        header('Allow: ' . implode(', ', $permitidos));
        responder_json(['erro'=>'Método não permitido.'], 405);
    }
}
