<?php
declare(strict_types=1);

function validar_transicao_solicitacao(string $anterior, string $novo): void
{
    $transicoes = [
        'pendente'=>['analise','aprovada','recusada','cancelada'],
        'analise'=>['aprovada','recusada','cancelada'],
        'aprovada'=>['concluida','cancelada'],
        'recusada'=>[], 'concluida'=>[], 'cancelada'=>[],
    ];
    if ($anterior !== $novo && !in_array($novo, $transicoes[$anterior] ?? [], true)) {
        throw new DomainException('Esta alteração não é permitida para a situação atual do pedido.');
    }
}

function alterar_solicitacao(int $identificador, array $usuario, string $acao, array $dados): void
{
    $conexao = banco();
    $conexao->beginTransaction();
    try {
        // Eu travo o pedido antes de decidir: disputa de clique já seria serviço demais para o meu salário.
        $consulta = $conexao->prepare('SELECT usuario_id,status FROM solicitacoes WHERE id=? FOR UPDATE');
        $consulta->execute([$identificador]);
        $solicitacao = $consulta->fetch();
        if (!$solicitacao || ($usuario['perfil'] !== 'administrador' && (int)$solicitacao['usuario_id'] !== (int)$usuario['id'])) {
            $conexao->rollBack();
            responder_json(['erro'=>'Solicitação não encontrada.'], 404);
        }
        $observacao = '';
        if ($acao === 'cancelar') {
            $novoStatus = 'cancelada';
            $observacao = texto_solicitacao($dados, 'motivo', 2000);
        } else {
            if ($usuario['perfil'] !== 'administrador') {
                $conexao->rollBack();
                responder_json(['erro'=>'Somente administradores podem analisar ou alterar o status.'], 403);
            }
            $novoStatus = $dados['status'] ?? null;
            if (!is_string($novoStatus) || !in_array($novoStatus, ['pendente','analise','aprovada','recusada','concluida'], true)) {
                throw new InvalidArgumentException('Status inválido.');
            }
            if (isset($dados['observacao'])) $observacao = texto_solicitacao($dados, 'observacao', 2000);
        }
        validar_transicao_solicitacao($solicitacao['status'], $novoStatus);
        if ($solicitacao['status'] === $novoStatus) {
            $conexao->commit();
            return;
        }
        if ($novoStatus === 'aprovada') {
            $veiculo = texto_solicitacao($dados, 'veiculo', 150);
            $motorista = texto_solicitacao($dados, 'motorista', 150);
            $consulta = $conexao->prepare('INSERT INTO atendimentos_solicitacoes (solicitacao_id,veiculo,motorista) VALUES (?,?,?) ON DUPLICATE KEY UPDATE veiculo=VALUES(veiculo),motorista=VALUES(motorista)');
            $consulta->execute([$identificador, $veiculo, $motorista]);
            $observacao = trim($observacao . ' Veículo: ' . $veiculo . '. Motorista: ' . $motorista . '.');
        }
        if ($novoStatus === 'cancelada') {
            $consulta = $conexao->prepare('INSERT INTO atendimentos_solicitacoes (solicitacao_id,motivo_cancelamento) VALUES (?,?) ON DUPLICATE KEY UPDATE motivo_cancelamento=VALUES(motivo_cancelamento)');
            $consulta->execute([$identificador, $observacao]);
        }
        $consulta = $conexao->prepare('UPDATE solicitacoes SET status=? WHERE id=?');
        $consulta->execute([$novoStatus, $identificador]);
        $consulta = $conexao->prepare('INSERT INTO historico_solicitacoes (solicitacao_id,usuario_id,status_anterior,status_novo) VALUES (?,?,?,?)');
        $consulta->execute([$identificador, $usuario['id'], $solicitacao['status'], $novoStatus]);
        if ($observacao !== '') {
            $historico = $conexao->lastInsertId();
            $consulta = $conexao->prepare('INSERT INTO observacoes_historico (historico_id,observacao) VALUES (?,?)');
            $consulta->execute([$historico, $observacao]);
        }
        $conexao->commit();
    } catch (Throwable $erro) {
        if ($conexao->inTransaction()) $conexao->rollBack();
        throw $erro;
    }
}

function atender_solicitacoes(string $caminho, string $metodo): never
{
    $detalhe = preg_match('~^/api/solicitacoes/([1-9][0-9]*)(/(status|analise|cancelar))?$~D', $caminho, $partes);
    $rotas = ['/api/solicitacoes'=>['GET','POST'], '/api/solicitacoes/rascunho'=>['GET','PUT','DELETE']];
    $acao = $detalhe ? ($partes[3] ?? '') : '';
    $permitidos = $detalhe ? ($acao === '' ? ['GET'] : ($acao === 'status' ? ['PATCH'] : ['POST'])) : ($rotas[$caminho] ?? []);
    if (!$permitidos) responder_json(['erro'=>'Rota não encontrada.'], 404);
    $usuario = exigir_usuario();
    exigir_metodo($metodo, $permitidos);
    if ($metodo !== 'GET') validar_csrf();
    try {
        if ($caminho === '/api/solicitacoes/rascunho') {
            if ($metodo === 'DELETE') unset($_SESSION['rascunho_solicitacao']);
            if ($metodo === 'PUT') {
                $dados = ler_json();
                $rascunho = $_SESSION['rascunho_solicitacao'] ?? [];
                if (isset($dados['viagem'])) {
                    if (!is_array($dados['viagem'])) throw new InvalidArgumentException('Viagem inválida.');
                    $rascunho['viagem'] = validar_viagem($dados['viagem']);
                }
                if (isset($dados['contato'])) {
                    if (!is_array($dados['contato'])) throw new InvalidArgumentException('Contato inválido.');
                    $rascunho['contato'] = validar_contato($dados['contato']);
                }
                if (array_key_exists('passageiros', $dados)) $rascunho['passageiros'] = validar_passageiros($dados['passageiros']);
                if (array_key_exists('passageiros_ids', $dados)) {
                    if (!is_array($dados['passageiros_ids'])) throw new InvalidArgumentException('Seleção de passageiros inválida.');
                    $rascunho['passageiros'] = selecionar_passageiros($dados['passageiros_ids'], $usuario);
                }
                $_SESSION['rascunho_solicitacao'] = $rascunho;
            }
            responder_json(['rascunho'=>$_SESSION['rascunho_solicitacao'] ?? new stdClass()]);
        }
        $conexao = banco();
        if ($caminho === '/api/solicitacoes' && $metodo === 'POST') {
            $dados = ler_json();
            if (($dados['declaracao'] ?? false) !== true) throw new InvalidArgumentException('Confirme a declaração antes de enviar.');
            $rascunho = $_SESSION['rascunho_solicitacao'] ?? [];
            $viagem = validar_viagem($rascunho['viagem'] ?? []);
            $contato = validar_contato($rascunho['contato'] ?? []);
            $passageiros = validar_passageiros($rascunho['passageiros'] ?? []);
            $conexao->beginTransaction();
            try {
                $campos = array_merge(['usuario_id'=>$usuario['id']], $viagem, $contato);
                foreach (['saida_em','retorno_em'] as $campo) $campos[$campo] = str_replace('T', ' ', $campos[$campo]) . ':00';
                $consulta = $conexao->prepare('INSERT INTO solicitacoes (' . implode(',', array_keys($campos)) . ') VALUES (' . implode(',', array_fill(0, count($campos), '?')) . ')');
                $consulta->execute(array_values($campos));
                $identificador = (int)$conexao->lastInsertId();
                foreach ($passageiros as $pessoa) {
                    // Eu guardo uma cópia por viagem: mudar o cadastro amanhã não deve reescrever meu trabalho de hoje.
                    $consulta = $conexao->prepare('INSERT INTO passageiros (usuario_id,nome,setor,vinculo) VALUES (?,?,?,?)');
                    $consulta->execute([$usuario['id'], $pessoa['nome'], $pessoa['setor'], $pessoa['vinculo']]);
                    $passageiroId = $conexao->lastInsertId();
                    $consulta = $conexao->prepare('INSERT INTO solicitacao_passageiros (solicitacao_id,passageiro_id) VALUES (?,?)');
                    $consulta->execute([$identificador, $passageiroId]);
                }
                $consulta = $conexao->prepare("INSERT INTO historico_solicitacoes (solicitacao_id,usuario_id,status_novo) VALUES (?,?,'pendente')");
                $consulta->execute([$identificador, $usuario['id']]);
                $conexao->commit();
            } catch (Throwable $erro) {
                if ($conexao->inTransaction()) $conexao->rollBack();
                throw $erro;
            }
            unset($_SESSION['rascunho_solicitacao']);
            responder_json(['id'=>$identificador, 'mensagem'=>'Solicitação enviada.'], 201);
        }
        if (!$detalhe) {
            $condicoes = [];
            $parametros = [];
            if ($usuario['perfil'] !== 'administrador') { $condicoes[] = 's.usuario_id=?'; $parametros[] = $usuario['id']; }
            foreach (['busca','status','periodo'] as $campo) {
                if (isset($_GET[$campo]) && !is_string($_GET[$campo])) throw new InvalidArgumentException('Filtro inválido.');
            }
            if (($_GET['status'] ?? '') !== '') {
                if (!in_array($_GET['status'], ['pendente','analise','aprovada','recusada','concluida','cancelada'], true)) throw new InvalidArgumentException('Status inválido.');
                $condicoes[] = 's.status=?'; $parametros[] = $_GET['status'];
            }
            if (($_GET['busca'] ?? '') !== '') {
                if (strlen($_GET['busca']) > 200) throw new InvalidArgumentException('Busca muito longa.');
                $condicoes[] = '(s.destino LIKE ? OR u.nome LIKE ? OR CAST(s.id AS CHAR)=?)';
                array_push($parametros, '%' . $_GET['busca'] . '%', '%' . $_GET['busca'] . '%', ltrim($_GET['busca'], '#'));
            }
            if (($_GET['periodo'] ?? '') !== '') {
                if (!in_array($_GET['periodo'], ['30','60','90'], true)) throw new InvalidArgumentException('Período inválido.');
                $condicoes[] = 's.criado_em>=?'; $parametros[] = gmdate('Y-m-d H:i:s', time() - (int)$_GET['periodo'] * 86400);
            }
            $consulta = $conexao->prepare('SELECT s.*,u.nome FROM solicitacoes s JOIN usuarios u ON u.id=s.usuario_id'
                . ($condicoes ? ' WHERE ' . implode(' AND ', $condicoes) : '') . ' ORDER BY s.id DESC');
            $consulta->execute($parametros);
            responder_json(['solicitacoes'=>$consulta->fetchAll()]);
        }
        $identificador = (int)$partes[1];
        if ($acao !== '') {
            alterar_solicitacao($identificador, $usuario, $acao, ler_json());
            responder_json(['mensagem'=>$acao === 'cancelar' ? 'Solicitação cancelada.' : 'Solicitação atualizada.']);
        }
        $consulta = $conexao->prepare('SELECT s.*,u.nome,u.email,a.veiculo,a.motorista,a.motivo_cancelamento FROM solicitacoes s JOIN usuarios u ON u.id=s.usuario_id LEFT JOIN atendimentos_solicitacoes a ON a.solicitacao_id=s.id WHERE s.id=?');
        $consulta->execute([$identificador]);
        $solicitacao = $consulta->fetch();
        if (!$solicitacao || ($usuario['perfil'] !== 'administrador' && (int)$solicitacao['usuario_id'] !== (int)$usuario['id'])) responder_json(['erro'=>'Solicitação não encontrada.'], 404);
        $consulta = $conexao->prepare('SELECT p.nome,p.setor,p.vinculo FROM passageiros p JOIN solicitacao_passageiros sp ON sp.passageiro_id=p.id WHERE sp.solicitacao_id=? ORDER BY p.id');
        $consulta->execute([$identificador]);
        $solicitacao['passageiros'] = $consulta->fetchAll();
        $consulta = $conexao->prepare('SELECT h.status_anterior,h.status_novo,h.criado_em,u.nome,o.observacao FROM historico_solicitacoes h JOIN usuarios u ON u.id=h.usuario_id LEFT JOIN observacoes_historico o ON o.historico_id=h.id WHERE h.solicitacao_id=? ORDER BY h.id');
        $consulta->execute([$identificador]);
        $solicitacao['historico'] = $consulta->fetchAll();
        responder_json(['solicitacao'=>$solicitacao]);
    } catch (InvalidArgumentException $erro) {
        responder_json(['erro'=>$erro->getMessage()], 422);
    } catch (DomainException $erro) {
        responder_json(['erro'=>$erro->getMessage()], 409);
    }
}
