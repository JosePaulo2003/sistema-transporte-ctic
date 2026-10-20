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
    if (!filter_var($usuario['email'] ?? '', FILTER_VALIDATE_EMAIL)
        || !is_string($usuario['senha'] ?? null) || strlen($usuario['senha']) < 12
        || !is_string($usuario['nome'] ?? null) || trim($usuario['nome']) === '') {
        throw new RuntimeException('Preencha nome, e-mail válido e senha com pelo menos 12 caracteres.');
    }
    $conexao = banco();
    // Aplica as estruturas em ordem antes de verificar o administrador existente.
    $arquivos = glob(RAIZ_PROJETO . '/banco-de-dados/migracoes/*.sql');
    sort($arquivos);
    foreach ($arquivos as $arquivo) {
        $migracao = file_get_contents($arquivo);
        foreach (explode(';', $migracao) as $instrucao) {
            if (trim($instrucao) !== '') $conexao->exec($instrucao);
        }
    }
    $consulta = $conexao->prepare('SELECT id FROM usuarios WHERE email = ?');
    $consulta->execute([strtolower(trim($usuario['email']))]);
    if ($consulta->fetch()) {
        echo "Tabelas verificadas. O usuário já existe; sua senha não foi alterada.\n";
        exit(0);
    }
    $consulta = $conexao->prepare('INSERT INTO usuarios (nome, email, hash_senha, perfil, setor) VALUES (?, ?, ?, ?, ?)');
    $consulta->execute([trim($usuario['nome']), strtolower(trim($usuario['email'])),
        password_hash($usuario['senha'], PASSWORD_DEFAULT), 'administrador', $usuario['setor'] ?? 'CTIC']);
    echo "Tabelas e primeiro administrador criados. Consulte CREDENCIAIS.local.md para entrar.\n";
} catch (Throwable $erro) {
    fwrite(STDERR, "Falha na preparação: " . $erro->getMessage() . "\nConsulte LEIA-ME.md e confira se o banco foi criado.\n");
    exit(1);
}
