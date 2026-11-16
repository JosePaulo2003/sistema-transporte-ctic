<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }

function gravar_configuracao_local(string $arquivo, array $dados): void
{
    if (file_put_contents($arquivo, "<?php\n// Eu guardo esta configuração só nesta máquina: senha versionada não paga meu salário.\nreturn " . var_export($dados, true) . ";\n", LOCK_EX) === false) {
        throw new RuntimeException('Não foi possível gravar a configuração local.');
    }
    chmod($arquivo, 0600);
}

try {
    $raiz = dirname(__DIR__);
    if (is_file($raiz . '/configuracao/aplicacao.local.php')) throw new RuntimeException('Já existe uma configuração local. Ajuste esse arquivo para usar outra conexão.');
    $servidor = getenv('CTIC_BANCO_HOST') ?: '127.0.0.1';
    $porta = getenv('CTIC_BANCO_PORTA') ?: '3306';
    $nomeBanco = getenv('CTIC_BANCO_NOME') ?: 'transporte_ctic';
    if (!preg_match('/^[a-zA-Z][a-zA-Z0-9_]{0,63}$/D', $nomeBanco)
        || !preg_match('/^[a-zA-Z0-9_.:-]+$/D', $servidor) || !ctype_digit($porta) || (int)$porta < 1 || (int)$porta > 65535) {
        throw new RuntimeException('Servidor, porta ou nome do banco inválido.');
    }
    $email = strtolower(trim(getenv('CTIC_ADMIN_EMAIL') ?: 'admin.transporte@uea.edu.br'));
    $nome = trim(getenv('CTIC_ADMIN_NOME') ?: 'Administrador de Transportes');
    $senhaAdministrador = getenv('CTIC_ADMIN_SENHA') ?: bin2hex(random_bytes(12));
    require_once $raiz . '/aplicacao/usuarios.php';
    validar_senha_usuario($senhaAdministrador);
    if (!filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 254 || $nome === '' || strlen($nome) > 150) throw new RuntimeException('Confira nome e e-mail do administrador.');
    $dsnServidor = 'mysql:host=' . $servidor . ';port=' . $porta . ';charset=utf8mb4';
    $conexao = new PDO($dsnServidor, getenv('CTIC_BANCO_ADMIN') ?: 'root', getenv('CTIC_BANCO_SENHA') ?: '', [PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION]);
    $conexao->exec('CREATE DATABASE IF NOT EXISTS `' . $nomeBanco . '` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci');
    $contaBanco = 'ctic_' . bin2hex(random_bytes(6));
    $senhaBanco = bin2hex(random_bytes(24));
    $conta = $conexao->quote($contaBanco) . "@'localhost'";
    // Eu crio uma conta só para este banco: usar root na aplicação aumenta meu trabalho sem aumentar o salário.
    $conexao->exec('CREATE USER ' . $conta . ' IDENTIFIED BY ' . $conexao->quote($senhaBanco));
    $conexao->exec('GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES ON `' . $nomeBanco . '`.* TO ' . $conta);
    gravar_configuracao_local($raiz . '/configuracao/aplicacao.local.php', [
        'banco_de_dados'=>['dsn'=>'mysql:host=' . $servidor . ';port=' . $porta . ';dbname=' . $nomeBanco . ';charset=utf8mb4', 'usuario'=>$contaBanco, 'senha'=>$senhaBanco],
        'segundos_inatividade_sessao'=>1800, 'segundos_duracao_sessao'=>28800, 'cookie_seguro'=>false,
        'ambiente_local'=>true, 'endereco_aplicacao'=>'http://127.0.0.1:8080', 'emails'=>['transporte'=>'arquivo', 'remetente'=>''],
    ]);
    gravar_configuracao_local($raiz . '/configuracao/primeiro-usuario.local.php', ['nome'=>$nome, 'email'=>$email, 'senha'=>$senhaAdministrador, 'setor'=>'CTIC']);
    $credenciais = "ACESSO LOCAL — TRANSPORTES CTIC\n\nEndereço: http://127.0.0.1:8080\nE-mail: " . $email . "\nSenha inicial: " . $senhaAdministrador
        . "\n\nMYSQL / WORKBENCH\nHost: " . $servidor . "\nPorta: " . $porta . "\nBanco: " . $nomeBanco . "\nUsuário: " . $contaBanco . "\nSenha: " . $senhaBanco
        . "\n\nEste arquivo é privado, ignorado pelo Git e não deve ser compartilhado.\n";
    if (file_put_contents($raiz . '/CREDENCIAIS.local.txt', $credenciais, LOCK_EX) === false) throw new RuntimeException('Não foi possível gravar o acesso local.');
    chmod($raiz . '/CREDENCIAIS.local.txt', 0600);
    echo "Conexão configurada. As credenciais estão em CREDENCIAIS.local.txt.\n";
} catch (Throwable $erro) {
    // Eu não imprimo o conteúdo de uma exceção SQL que possa carregar senha na instrução.
    fwrite(STDERR, $erro instanceof PDOException ? "Não foi possível configurar o MySQL. Confira as credenciais e as permissões da conta informada.\n" : $erro->getMessage() . PHP_EOL);
    exit(1);
}
