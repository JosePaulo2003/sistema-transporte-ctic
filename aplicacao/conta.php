<?php
declare(strict_types=1);

function atender_conta(string $caminho, string $metodo): never
{
    $usuario = exigir_usuario();
    exigir_metodo($metodo, $caminho === '/api/conta/senha' ? ['PUT'] : ['GET','PUT']);
    if ($metodo === 'GET') responder_json(['usuario'=>$usuario]);
    validar_csrf();
    try {
        $dados = ler_json();
        $conexao = banco();
        if ($caminho === '/api/conta/senha') {
            $novaSenha = validar_senha_usuario($dados['nova_senha'] ?? null);
            if ($novaSenha !== ($dados['confirmacao_senha'] ?? null)) throw new InvalidArgumentException('As senhas não conferem.');
            $conexao->beginTransaction();
            try {
                $consulta = $conexao->prepare('SELECT hash_senha FROM usuarios WHERE id=? AND ativo=1 FOR UPDATE');
                $consulta->execute([$usuario['id']]);
                $hash = $consulta->fetchColumn();
                if (!$hash || !is_string($dados['senha_atual'] ?? null) || !password_verify($dados['senha_atual'], $hash)) {
                    throw new InvalidArgumentException('Senha atual incorreta.');
                }
                $novoHash = password_hash($novaSenha, PASSWORD_DEFAULT);
                $consulta = $conexao->prepare('UPDATE usuarios SET hash_senha=? WHERE id=?');
                $consulta->execute([$novoHash, $usuario['id']]);
                $conexao->commit();
                session_regenerate_id(true);
                $_SESSION['assinatura_senha'] = hash('sha256', $novoHash);
                $_SESSION['csrf'] = bin2hex(random_bytes(32));
            } catch (Throwable $erro) {
                if ($conexao->inTransaction()) $conexao->rollBack();
                throw $erro;
            }
            responder_json(['mensagem'=>'Senha alterada. As outras sessões foram encerradas.']);
        }
        $nome = texto_solicitacao($dados, 'nome', 150);
        $setor = texto_solicitacao($dados, 'setor', 100);
        // Eu deixo perfil e e-mail fora dessa escrita, porque pagar boleto não inclui consertar promoção indevida.
        $consulta = $conexao->prepare('UPDATE usuarios SET nome=?,setor=? WHERE id=? AND ativo=1');
        $consulta->execute([$nome, $setor, $usuario['id']]);
        responder_json(['mensagem'=>'Dados atualizados.', 'usuario'=>usuario_atual()]);
    } catch (InvalidArgumentException $erro) {
        responder_json(['erro'=>$erro->getMessage()], 422);
    }
}

function enviar_recuperacao(string $email, string $token): void
{
    $configuracao = configuracao();
    $base = rtrim($configuracao['endereco_aplicacao'] ?? 'http://127.0.0.1:8080', '/');
    $mensagem = "Recebi um pedido de recuperação da sua conta no Sistema de Transportes CTIC.\n\n"
        . "Use o endereço abaixo em até 30 minutos:\n" . $base . '/redefinir-senha#token=' . $token
        . "\n\nSe você não fez o pedido, ignore esta mensagem.\n";
    $transporte = $configuracao['emails']['transporte'] ?? 'arquivo';
    if ($transporte === 'arquivo') {
        // Eu gravo a mensagem só no ambiente local: sem servidor de e-mail, não vou fingir entrega pelo salário.
        if (!(bool)($configuracao['ambiente_local'] ?? false)) throw new RuntimeException('Configure o envio de e-mail para este ambiente.');
        $pasta = RAIZ_PROJETO . '/armazenamento/emails';
        if (!is_dir($pasta) && !mkdir($pasta, 0700, true) && !is_dir($pasta)) throw new RuntimeException('Não foi possível preparar o envio local.');
        $arquivo = $pasta . '/' . bin2hex(random_bytes(16)) . '.txt';
        if (file_put_contents($arquivo, 'Para: ' . $email . "\n\n" . $mensagem, LOCK_EX) === false) throw new RuntimeException('Não foi possível gravar o e-mail local.');
        chmod($arquivo, 0600);
        return;
    }
    if ($transporte !== 'mail') throw new RuntimeException('Transporte de e-mail inválido.');
    $remetente = $configuracao['emails']['remetente'] ?? '';
    if (!filter_var($remetente, FILTER_VALIDATE_EMAIL) || preg_match('/[\r\n]/', $remetente)) throw new RuntimeException('Configure um remetente válido.');
    if (!mail($email, 'Recuperar acesso - Transportes CTIC', $mensagem,
        ['From'=>$remetente, 'Content-Type'=>'text/plain; charset=UTF-8'])) {
        throw new RuntimeException('O servidor de e-mail recusou o envio.');
    }
}

function atender_recuperacao(string $caminho, string $metodo): never
{
    exigir_metodo($metodo, ['POST']);
    validar_csrf();
    $conexao = banco();
    try {
        $dados = ler_json();
        if ($caminho === '/api/autenticacao/recuperar') {
            $email = strtolower(texto_solicitacao($dados, 'email', 254));
            if (!filter_var($email, FILTER_VALIDATE_EMAIL)) throw new InvalidArgumentException('Informe um e-mail válido.');
            $chaveEmail = hash('sha256', $email);
            $chaveIp = hash('sha256', $_SERVER['REMOTE_ADDR'] ?? 'cli');
            $conexao->exec('DELETE FROM tentativas_recuperacao WHERE criado_em < UTC_TIMESTAMP() - INTERVAL 1 DAY');
            $consulta = $conexao->prepare('SELECT COUNT(*) FROM tentativas_recuperacao WHERE criado_em > UTC_TIMESTAMP() - INTERVAL 15 MINUTE AND (chave_email=? OR chave_ip=?)');
            $consulta->execute([$chaveEmail, $chaveIp]);
            if ((int)$consulta->fetchColumn() >= 5) {
                header('Retry-After: 900');
                responder_json(['erro'=>'Muitas solicitações. Aguarde 15 minutos.'], 429);
            }
            $consulta = $conexao->prepare('INSERT INTO tentativas_recuperacao (chave_email,chave_ip) VALUES (?,?)');
            $consulta->execute([$chaveEmail, $chaveIp]);
            $consulta = $conexao->prepare('SELECT id,hash_senha FROM usuarios WHERE email=? AND ativo=1');
            $consulta->execute([$email]);
            $usuario = $consulta->fetch();
            if ($usuario) {
                $token = bin2hex(random_bytes(32));
                $consulta = $conexao->prepare('INSERT INTO recuperacoes_senha (usuario_id,hash_token,assinatura_senha,expira_em) VALUES (?,?,?,UTC_TIMESTAMP() + INTERVAL 30 MINUTE)');
                $consulta->execute([$usuario['id'], hash('sha256', $token), hash('sha256', $usuario['hash_senha'])]);
                try { enviar_recuperacao($email, $token); }
                catch (Throwable $erro) {
                    error_log('Falha no transporte da recuperação: ' . $erro->getMessage());
                    $consulta = $conexao->prepare('UPDATE recuperacoes_senha SET usado_em=UTC_TIMESTAMP() WHERE hash_token=?');
                    $consulta->execute([hash('sha256', $token)]);
                }
            }
            // Eu devolvo a mesma mensagem para todos: descobrir contas alheias não faz parte do serviço.
            responder_json(['mensagem'=>'Se o e-mail estiver cadastrado, as instruções de recuperação serão geradas.']);
        }
        $token = $dados['token'] ?? null;
        if (!is_string($token) || !preg_match('/^[a-f0-9]{64}$/D', $token)) throw new InvalidArgumentException('Link de recuperação inválido ou expirado.');
        $senha = validar_senha_usuario($dados['senha'] ?? null);
        if ($senha !== ($dados['confirmacao_senha'] ?? null)) throw new InvalidArgumentException('As senhas não conferem.');
        $conexao->beginTransaction();
        try {
            $consulta = $conexao->prepare('SELECT r.id,r.usuario_id,r.assinatura_senha,u.hash_senha FROM recuperacoes_senha r JOIN usuarios u ON u.id=r.usuario_id WHERE r.hash_token=? AND r.usado_em IS NULL AND r.expira_em>UTC_TIMESTAMP() AND u.ativo=1 FOR UPDATE');
            $consulta->execute([hash('sha256', $token)]);
            $recuperacao = $consulta->fetch();
            if (!$recuperacao || !hash_equals($recuperacao['assinatura_senha'], hash('sha256', $recuperacao['hash_senha']))) {
                throw new InvalidArgumentException('Link de recuperação inválido ou expirado.');
            }
            $consulta = $conexao->prepare('UPDATE usuarios SET hash_senha=? WHERE id=?');
            $consulta->execute([password_hash($senha, PASSWORD_DEFAULT), $recuperacao['usuario_id']]);
            $consulta = $conexao->prepare('UPDATE recuperacoes_senha SET usado_em=UTC_TIMESTAMP() WHERE usuario_id=? AND usado_em IS NULL');
            $consulta->execute([$recuperacao['usuario_id']]);
            $conexao->commit();
        } catch (Throwable $erro) {
            if ($conexao->inTransaction()) $conexao->rollBack();
            throw $erro;
        }
        encerrar_sessao();
        responder_json(['mensagem'=>'Senha redefinida. Entre novamente.']);
    } catch (InvalidArgumentException $erro) {
        responder_json(['erro'=>$erro->getMessage()], 422);
    }
}
