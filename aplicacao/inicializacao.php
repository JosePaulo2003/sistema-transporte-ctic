<?php
declare(strict_types=1);

const RAIZ_PROJETO = __DIR__ . '/..';

// Carrega a configuração local uma única vez, mantendo as credenciais fora do código versionado.
function configuracao(): array
{
    static $configuracao;
    if ($configuracao === null) {
        $arquivo = RAIZ_PROJETO . '/configuracao/aplicacao.local.php';
        if (!is_file($arquivo)) {
            throw new RuntimeException('Configuração ausente. Consulte LEIA-ME.md.');
        }
        $configuracao = require $arquivo;
    }
    return $configuracao;
}

// Reutiliza a conexão e usa consultas preparadas nativas; as datas do banco ficam em UTC.
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

// Restringe o identificador de sessão ao cookie e configura a proteção do navegador.
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

// Mantém um token imprevisível para validar as operações desta sessão.
function token_csrf(): string
{
    return $_SESSION['csrf'] ??= bin2hex(random_bytes(32));
}

// Rejeita alterações sem o token enviado pelo formulário ou pelo cabeçalho da API.
function validar_csrf(): void
{
    $token = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? ($_POST['csrf'] ?? '');
    if (!is_string($token) || !hash_equals(token_csrf(), $token)) {
        responder_json(['erro' => 'Sessão de formulário inválida. Atualize a página e tente novamente.'], 419);
    }
}

// Envia a resposta da API e encerra o processamento para evitar conteúdo adicional.
function responder_json(array $dados, int $codigoHttp = 200): never
{
    http_response_code($codigoHttp);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($dados, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
    exit;
}

// Verifica o tipo original antes da conversão: {} é um objeto válido, enquanto [] é uma lista.
function decodificar_objeto_json(string $conteudo): array
{
    $objeto = json_decode($conteudo, false, 16, JSON_THROW_ON_ERROR);
    if (!$objeto instanceof stdClass) {
        throw new InvalidArgumentException('Envie um objeto JSON.');
    }
    // Mantém os objetos internos como arrays, conforme o contrato das validações existentes.
    return json_decode($conteudo, true, 16, JSON_THROW_ON_ERROR);
}

// Aceita apenas um objeto JSON e limita o tamanho da entrada recebida.
function ler_json(): array
{
    if (strtolower(trim(explode(';', $_SERVER['CONTENT_TYPE'] ?? '')[0])) !== 'application/json') {
        responder_json(['erro' => 'Envie os dados em JSON.'], 415);
    }
    if ((int) ($_SERVER['CONTENT_LENGTH'] ?? 0) > 16384) {
        responder_json(['erro' => 'Dados muito grandes.'], 413);
    }
    try {
        $dados = decodificar_objeto_json(file_get_contents('php://input', false, null, 0, 16385));
    } catch (JsonException $erro) {
        responder_json(['erro' => 'JSON inválido.'], 400);
    } catch (InvalidArgumentException $erro) {
        responder_json(['erro' => $erro->getMessage()], 400);
    }
    return $dados;
}

// Expõe apenas os dados de identificação; o hash da senha nunca sai do servidor.
function dados_publicos_usuario(array $usuario): array
{
    return array_intersect_key($usuario, array_flip(['id', 'nome', 'email', 'perfil', 'setor']));
}

// Verifica a validade da sessão e consulta novamente se o usuário continua ativo.
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
    // A assinatura fica somente no servidor e muda quando a senha é redefinida.
    if (!$usuario || !hash_equals(hash('sha256', $usuario['hash_senha']), $_SESSION['assinatura_senha'] ?? '')) {
        $_SESSION = [];
        session_regenerate_id(true);
        return null;
    }
    $_SESSION['ultima_atividade'] = $agora;
    return dados_publicos_usuario($usuario);
}

// Valida as credenciais, limita tentativas e renova a sessão após a autenticação.
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
    // REMOTE_ADDR é a origem real do servidor; não confiamos em X-Forwarded-For arbitrário.
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
    // Conta a tentativa antes da verificação para não permitir rajadas concorrentes durante o hash.
    $consulta = $conexao->prepare('INSERT INTO tentativas_acesso (chave_email, chave_ip) VALUES (?, ?)');
    $consulta->execute([$chaveEmail, $chaveIp]);
    $consulta = $conexao->prepare('SELECT * FROM usuarios WHERE email = ? LIMIT 1');
    $consulta->execute([$email]);
    $usuario = $consulta->fetch();
    // Verifica um hash mesmo para e-mail inexistente, reduzindo diferenças no tempo de resposta.
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

// Remove os dados da sessão e expira o cookie de identificação no navegador.
function encerrar_sessao(): void
{
    $_SESSION = [];
    $parametrosCookie = session_get_cookie_params();
    setcookie(session_name(), '', ['expires' => time() - 3600, 'path' => $parametrosCookie['path'],
        'secure' => $parametrosCookie['secure'], 'httponly' => true, 'samesite' => 'Lax']);
    session_destroy();
}
