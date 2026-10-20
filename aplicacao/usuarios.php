<?php
declare(strict_types=1);

// Normaliza somente os campos permitidos, impedindo alterações arbitrárias no cadastro.
function validar_cadastro_usuario(array $dados): array
{
    $cadastro = [];
    foreach (['nome'=>150, 'email'=>254, 'setor'=>100] as $campo=>$limite) {
        $valor = $dados[$campo] ?? null;
        if (!is_string($valor) || trim($valor) === '' || strlen($valor) > $limite) {
            throw new InvalidArgumentException('Preencha corretamente o campo ' . $campo . '.');
        }
        $cadastro[$campo] = trim($valor);
    }
    $cadastro['email'] = strtolower($cadastro['email']);
    if (!filter_var($cadastro['email'], FILTER_VALIDATE_EMAIL)) {
        throw new InvalidArgumentException('Informe um e-mail válido.');
    }
    if (!in_array($dados['perfil'] ?? null, ['administrador', 'solicitante'], true)) {
        throw new InvalidArgumentException('Selecione um perfil válido.');
    }
    if (!is_bool($dados['ativo'] ?? null)) {
        throw new InvalidArgumentException('Informe se o usuário está ativo.');
    }
    $cadastro['perfil'] = $dados['perfil'];
    $cadastro['ativo'] = (int)$dados['ativo'];
    return $cadastro;
}

function validar_senha_usuario(mixed $senha): string
{
    // O limite de 72 bytes evita o truncamento silencioso de senhas pelo bcrypt.
    if (!is_string($senha) || strlen($senha) < 12 || strlen($senha) > 72 || str_contains($senha, "\0") || trim($senha) === '') {
        throw new InvalidArgumentException('A senha deve conter de 12 a 72 bytes e não pode ser composta apenas de espaços.');
    }
    return $senha;
}

function atender_usuarios(string $caminho, string $metodo): never
{
    $detalhe = preg_match('~^/api/usuarios/([1-9][0-9]*)(/senha)?$~D', $caminho, $partes);
    $permitidos = $caminho === '/api/usuarios' ? ['GET', 'POST'] : ($detalhe ? [isset($partes[2]) ? 'POST' : 'PUT'] : []);
    if (!$permitidos) responder_json(['erro'=>'Rota não encontrada.'], 404);
    $administrador = usuario_atual();
    if (!$administrador) responder_json(['erro'=>'Autenticação necessária.'], 401);
    if ($administrador['perfil'] !== 'administrador') responder_json(['erro'=>'Acesso exclusivo para administradores.'], 403);
    if (!in_array($metodo, $permitidos, true)) {
        header('Allow: ' . implode(', ', $permitidos));
        responder_json(['erro'=>'Método não permitido.'], 405);
    }
    if ($metodo !== 'GET') validar_csrf();
    $conexao = banco();
    if ($metodo === 'GET') {
        // Nunca devolve o hash, mesmo na listagem administrativa.
        $consulta = $conexao->query('SELECT id,nome,email,setor,perfil,ativo,ultimo_acesso_em FROM usuarios ORDER BY nome,id');
        responder_json(['usuarios'=>$consulta->fetchAll()]);
    }
    try {
        $dados = ler_json();
        $senha = null;
        $cadastro = null;
        if (!$detalhe || !isset($partes[2])) $cadastro = validar_cadastro_usuario($dados);
        if (!$detalhe || isset($partes[2])) $senha = password_hash(validar_senha_usuario($dados['senha'] ?? null), PASSWORD_DEFAULT);
        $conexao->beginTransaction();
        try {
            // Serializa a administração para impedir que duas alterações concorrentes removam o último administrador.
            $consulta = $conexao->query("SELECT id FROM usuarios WHERE perfil='administrador' AND ativo=1 ORDER BY id FOR UPDATE");
            $administradores = array_map('intval', $consulta->fetchAll(PDO::FETCH_COLUMN));
            if (!in_array((int)$administrador['id'], $administradores, true)) {
                $conexao->rollBack();
                responder_json(['erro'=>'Seu acesso administrativo foi alterado. Atualize a página.'], 403);
            }
            if (!$detalhe) {
                $consulta = $conexao->prepare('INSERT INTO usuarios (nome,email,setor,perfil,ativo,hash_senha) VALUES (?,?,?,?,?,?)');
                $consulta->execute([...array_values($cadastro), $senha]);
                $identificador = (int)$conexao->lastInsertId();
            } else {
                $identificador = (int)$partes[1];
                $consulta = $conexao->prepare('SELECT id FROM usuarios WHERE id=? FOR UPDATE');
                $consulta->execute([$identificador]);
                if (!$consulta->fetch()) {
                    $conexao->rollBack();
                    responder_json(['erro'=>'Usuário não encontrado.'], 404);
                }
                if ($cadastro !== null) {
                    $removeAcesso = !$cadastro['ativo'] || $cadastro['perfil'] !== 'administrador';
                    if ($removeAcesso && $identificador === (int)$administrador['id']) {
                        throw new InvalidArgumentException('Você não pode desativar sua própria conta nem remover seu próprio perfil de administrador.');
                    }
                    if ($removeAcesso && count($administradores) === 1 && in_array($identificador, $administradores, true)) {
                        throw new InvalidArgumentException('É necessário manter um administrador ativo.');
                    }
                    $consulta = $conexao->prepare('UPDATE usuarios SET nome=?,email=?,setor=?,perfil=?,ativo=? WHERE id=?');
                    $consulta->execute([...array_values($cadastro), $identificador]);
                } else {
                    $consulta = $conexao->prepare('UPDATE usuarios SET hash_senha=? WHERE id=?');
                    $consulta->execute([$senha, $identificador]);
                }
            }
            $conexao->commit();
        } catch (Throwable $erro) {
            if ($conexao->inTransaction()) $conexao->rollBack();
            throw $erro;
        }
        responder_json(['id'=>$identificador, 'mensagem'=>$senha !== null && $detalhe ? 'Senha redefinida. As sessões anteriores foram invalidadas.' : 'Usuário salvo.'], $detalhe ? 200 : 201);
    } catch (InvalidArgumentException $erro) {
        responder_json(['erro'=>$erro->getMessage()], 422);
    } catch (PDOException $erro) {
        if ((int)($erro->errorInfo[1] ?? 0) === 1062) responder_json(['erro'=>'Já existe um usuário com este e-mail.'], 409);
        throw $erro;
    }
}
