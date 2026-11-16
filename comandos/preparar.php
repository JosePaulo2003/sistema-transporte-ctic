<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}
require __DIR__ . '/../aplicacao/inicializacao.php';
try {
    $arquivoUsuario = RAIZ_PROJETO . '/configuracao/primeiro-usuario.local.php';
    if (!is_file($arquivoUsuario)) {
        throw new RuntimeException('Arquivo de configuração do primeiro usuário não encontrado.');
    }
    $usuario = require $arquivoUsuario;
    require_once __DIR__ . '/../aplicacao/usuarios.php';
    validar_senha_usuario($usuario['senha'] ?? null);
    if (!filter_var($usuario['email'] ?? '', FILTER_VALIDATE_EMAIL)
        || !is_string($usuario['senha'] ?? null) || strlen($usuario['senha']) < 12
        || !is_string($usuario['nome'] ?? null) || trim($usuario['nome']) === '') {
        throw new RuntimeException('Preencha nome, e-mail válido e senha com pelo menos 12 caracteres.');
    }
    $conexao = banco();
    require_once __DIR__ . '/migrar.php';
    aplicar_migracoes($conexao);
    $consulta = $conexao->prepare('SELECT id FROM usuarios WHERE email = ?');
    $consulta->execute([strtolower(trim($usuario['email']))]);
    if ($consulta->fetch()) {
        echo "Tabelas verificadas. O usuário já existe; sua senha não foi alterada.\n";
        exit(0);
    }
    $consulta = $conexao->prepare('INSERT INTO usuarios (nome, email, hash_senha, perfil, setor) VALUES (?, ?, ?, ?, ?)');
    $consulta->execute([trim($usuario['nome']), strtolower(trim($usuario['email'])),
        password_hash($usuario['senha'], PASSWORD_DEFAULT), 'administrador', $usuario['setor'] ?? 'CTIC']);
    echo "Tabelas e primeiro administrador criados. Consulte CREDENCIAIS.local.txt para entrar.\n";
} catch (Throwable $erro) {
    fwrite(STDERR, "Falha na preparação: " . $erro->getMessage() . "\nExecute comandos/configurar.ps1 e confira se o MySQL está ativo.\n");
    exit(1);
}
