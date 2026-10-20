<?php
declare(strict_types=1);

// Validação no servidor também protege chamadas feitas sem as telas do sistema.
function texto_solicitacao(array $dados, string $campo, int $limite): string
{
    $valor = $dados[$campo] ?? null;
    if (!is_string($valor) || trim($valor) === '' || strlen($valor) > $limite) {
        throw new InvalidArgumentException('Preencha corretamente o campo ' . $campo . '.');
    }
    return trim($valor);
}

function validar_viagem(array $dados): array
{
    $viagem = [];
    foreach (['tipo_deslocamento'=>100, 'destino'=>200, 'finalidade'=>200,
        'local_embarque'=>200, 'centro_custo'=>100, 'justificativa'=>4000] as $campo=>$limite) {
        $viagem[$campo] = texto_solicitacao($dados, $campo, $limite);
    }
    // Não converte para UTC: as datas da viagem são horários locais, sem ambiguidade de navegador.
    foreach (['saida_em', 'retorno_em'] as $campo) {
        $valor = texto_solicitacao($dados, $campo, 16);
        $data = DateTimeImmutable::createFromFormat('!Y-m-d\TH:i', $valor, new DateTimeZone('America/Manaus'));
        if (!$data || $data->format('Y-m-d\TH:i') !== $valor) {
            throw new InvalidArgumentException('Informe uma data e um horário válidos.');
        }
        $viagem[$campo] = $valor;
    }
    if ($viagem['retorno_em'] < $viagem['saida_em']) {
        throw new InvalidArgumentException('O retorno não pode ser anterior à saída.');
    }
    return $viagem;
}

function validar_contato(array $dados): array
{
    $contato = [];
    foreach (['telefone'=>30, 'setor'=>100, 'vinculo'=>100] as $campo=>$limite) {
        $contato[$campo] = texto_solicitacao($dados, $campo, $limite);
    }
    if (!preg_match('/^[0-9()+ .-]{8,30}$/', $contato['telefone'])) {
        throw new InvalidArgumentException('Informe um telefone válido.');
    }
    return $contato;
}

function validar_passageiros(mixed $dados): array
{
    if (!is_array($dados) || !array_is_list($dados) || count($dados) < 1 || count($dados) > 50) {
        throw new InvalidArgumentException('Adicione entre 1 e 50 passageiros.');
    }
    $passageiros = [];
    foreach ($dados as $pessoa) {
        if (!is_array($pessoa)) throw new InvalidArgumentException('Passageiro inválido.');
        $passageiros[] = ['nome'=>texto_solicitacao($pessoa, 'nome', 150),
            'setor'=>texto_solicitacao($pessoa, 'setor', 100),
            'vinculo'=>texto_solicitacao($pessoa, 'vinculo', 100)];
    }
    return $passageiros;
}

// Centraliza autenticação e CSRF antes de qualquer leitura privada ou alteração.
function atender_solicitacoes(string $caminho, string $metodo): never
{
    $detalhe = preg_match('~^/api/solicitacoes/([1-9][0-9]*)(/status)?$~D', $caminho, $partes);
    $rotas = ['/api/solicitacoes'=>['GET','POST'], '/api/solicitacoes/rascunho'=>['GET','PUT','DELETE']];
    $permitidos = $detalhe ? [isset($partes[2]) ? 'PATCH' : 'GET'] : ($rotas[$caminho] ?? []);
    if (!$permitidos) responder_json(['erro'=>'Rota não encontrada.'], 404);
    if (!in_array($metodo, $permitidos, true)) {
        header('Allow: ' . implode(', ', $permitidos));
        responder_json(['erro'=>'Método não permitido.'], 405);
    }
    $usuario = usuario_atual();
    if (!$usuario) responder_json(['erro'=>'Autenticação necessária.'], 401);
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
                if (isset($dados['passageiros'])) $rascunho['passageiros'] = validar_passageiros($dados['passageiros']);
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
            // A transação evita solicitações parciais caso algum passageiro não possa ser gravado.
            $conexao->beginTransaction();
            try {
                $campos = array_merge(['usuario_id'=>$usuario['id']], $viagem, $contato);
                $campos['saida_em'] = str_replace('T', ' ', $campos['saida_em']) . ':00';
                $campos['retorno_em'] = str_replace('T', ' ', $campos['retorno_em']) . ':00';
                $consulta = $conexao->prepare('INSERT INTO solicitacoes (' . implode(',', array_keys($campos))
                    . ') VALUES (' . implode(',', array_fill(0, count($campos), '?')) . ')');
                $consulta->execute(array_values($campos));
                $id = $conexao->lastInsertId();
                foreach ($passageiros as $pessoa) {
                    $consulta = $conexao->prepare('INSERT INTO passageiros (usuario_id,nome,setor,vinculo) VALUES (?,?,?,?)');
                    $consulta->execute([$usuario['id'], $pessoa['nome'], $pessoa['setor'], $pessoa['vinculo']]);
                    $passageiroId = $conexao->lastInsertId();
                    $consulta = $conexao->prepare('INSERT INTO solicitacao_passageiros VALUES (?,?)');
                    $consulta->execute([$id, $passageiroId]);
                }
                $consulta = $conexao->prepare("INSERT INTO historico_solicitacoes (solicitacao_id,usuario_id,status_novo) VALUES (?,?,'pendente')");
                $consulta->execute([$id, $usuario['id']]);
                $conexao->commit();
            } catch (Throwable $erro) {
                if ($conexao->inTransaction()) $conexao->rollBack();
                throw $erro;
            }
            unset($_SESSION['rascunho_solicitacao']);
            responder_json(['id'=>(int)$id, 'mensagem'=>'Solicitação enviada.'], 201);
        }
        if (!$detalhe) {
            // O perfil é lido da sessão validada, nunca de parâmetros enviados pelo cliente.
            $consulta = $conexao->prepare('SELECT s.*, u.nome FROM solicitacoes s JOIN usuarios u ON u.id=s.usuario_id'
                . ($usuario['perfil'] === 'administrador' ? '' : ' WHERE s.usuario_id = ?') . ' ORDER BY s.id DESC');
            $consulta->execute($usuario['perfil'] === 'administrador' ? [] : [$usuario['id']]);
            responder_json(['solicitacoes'=>$consulta->fetchAll()]);
        }
        $consulta = $conexao->prepare('SELECT s.*,u.nome,u.email FROM solicitacoes s JOIN usuarios u ON u.id=s.usuario_id WHERE s.id=?');
        $consulta->execute([$partes[1]]);
        $solicitacao = $consulta->fetch();
        if (!$solicitacao || ($usuario['perfil'] !== 'administrador' && (int)$solicitacao['usuario_id'] !== (int)$usuario['id'])) {
            responder_json(['erro'=>'Solicitação não encontrada.'], 404);
        }
        if ($metodo === 'PATCH') {
            if ($usuario['perfil'] !== 'administrador') responder_json(['erro'=>'Somente administradores podem alterar o status.'], 403);
            $dados = ler_json();
            $novoStatus = $dados['status'] ?? '';
            if (!is_string($novoStatus) || !in_array($novoStatus, ['pendente','analise','aprovada','recusada','concluida'], true)) {
                throw new InvalidArgumentException('Status inválido.');
            }
            $conexao->beginTransaction();
            try {
                // Bloqueia a linha para registrar o estado anterior correto em alterações concorrentes.
                $consulta = $conexao->prepare('SELECT status FROM solicitacoes WHERE id=? FOR UPDATE');
                $consulta->execute([$partes[1]]);
                $anterior = $consulta->fetchColumn();
                if ($anterior !== $novoStatus) {
                    $consulta = $conexao->prepare('UPDATE solicitacoes SET status=? WHERE id=?');
                    $consulta->execute([$novoStatus,$partes[1]]);
                    $consulta = $conexao->prepare('INSERT INTO historico_solicitacoes (solicitacao_id,usuario_id,status_anterior,status_novo) VALUES (?,?,?,?)');
                    $consulta->execute([$partes[1],$usuario['id'],$anterior,$novoStatus]);
                }
                $conexao->commit();
            } catch (Throwable $erro) {
                if ($conexao->inTransaction()) $conexao->rollBack();
                throw $erro;
            }
            responder_json(['mensagem'=>'Status atualizado.']);
        }
        $consulta = $conexao->prepare('SELECT p.nome,p.setor,p.vinculo FROM passageiros p JOIN solicitacao_passageiros sp ON sp.passageiro_id=p.id WHERE sp.solicitacao_id=?');
        $consulta->execute([$partes[1]]);
        $solicitacao['passageiros'] = $consulta->fetchAll();
        $consulta = $conexao->prepare('SELECT h.status_anterior,h.status_novo,h.criado_em,u.nome FROM historico_solicitacoes h JOIN usuarios u ON u.id=h.usuario_id WHERE h.solicitacao_id=? ORDER BY h.id');
        $consulta->execute([$partes[1]]);
        $solicitacao['historico'] = $consulta->fetchAll();
        responder_json(['solicitacao'=>$solicitacao]);
    } catch (InvalidArgumentException $erro) {
        responder_json(['erro'=>$erro->getMessage()], 422);
    }
}
