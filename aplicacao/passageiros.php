<?php
declare(strict_types=1);

function validar_cpf(mixed $valor): string
{
    if (!is_string($valor) || !preg_match('/^[0-9. -]{11,14}$/D', $valor)) {
        throw new InvalidArgumentException('Informe um CPF válido.');
    }
    $cpf = preg_replace('/\D/', '', $valor);
    if (strlen($cpf) !== 11 || preg_match('/^(\d)\1{10}$/D', $cpf)) {
        throw new InvalidArgumentException('Informe um CPF válido.');
    }
    for ($posicao = 9; $posicao < 11; $posicao++) {
        $soma = 0;
        for ($indice = 0; $indice < $posicao; $indice++) $soma += (int)$cpf[$indice] * ($posicao + 1 - $indice);
        $digito = ($soma * 10) % 11;
        if ($digito === 10) $digito = 0;
        if ($digito !== (int)$cpf[$posicao]) throw new InvalidArgumentException('Informe um CPF válido.');
    }
    return $cpf;
}

function validar_cadastro_passageiro(array $dados): array
{
    $cadastro = [];
    foreach (['nome'=>150, 'setor'=>100, 'vinculo'=>100, 'telefone'=>30] as $campo=>$limite) {
        $cadastro[$campo] = texto_solicitacao($dados, $campo, $limite);
    }
    validar_telefone($cadastro['telefone']);
    $cadastro['cpf'] = validar_cpf($dados['cpf'] ?? null);
    return $cadastro;
}

function selecionar_passageiros(array $identificadores, array $usuario): array
{
    if (!array_is_list($identificadores) || count($identificadores) > 50
        || count(array_unique($identificadores, SORT_REGULAR)) !== count($identificadores)) {
        throw new InvalidArgumentException('Selecione até 50 passageiros diferentes.');
    }
    $consulta = banco()->prepare('SELECT id,nome,setor,vinculo FROM cadastros_passageiros WHERE id=? AND usuario_id=? AND ativo=1');
    $passageiros = [];
    foreach ($identificadores as $identificador) {
        if (!is_int($identificador) || $identificador < 1) throw new InvalidArgumentException('Passageiro inválido.');
        $consulta->execute([$identificador, $usuario['id']]);
        $pessoa = $consulta->fetch();
        if (!$pessoa) throw new InvalidArgumentException('Um passageiro selecionado não está disponível no seu cadastro.');
        $passageiros[] = ['cadastro_id'=>(int)$pessoa['id'], 'nome'=>$pessoa['nome'], 'setor'=>$pessoa['setor'], 'vinculo'=>$pessoa['vinculo']];
    }
    return $passageiros;
}

function atender_passageiros(string $caminho, string $metodo): never
{
    $detalhe = preg_match('~^/api/passageiros/([1-9][0-9]*)$~D', $caminho, $partes);
    $permitidos = $caminho === '/api/passageiros' ? ['GET','POST'] : ($detalhe ? ['GET','PUT','DELETE'] : []);
    if (!$permitidos) responder_json(['erro'=>'Rota não encontrada.'], 404);
    $usuario = exigir_usuario();
    exigir_metodo($metodo, $permitidos);
    if ($metodo !== 'GET') validar_csrf();
    $conexao = banco();
    try {
        if (!$detalhe && $metodo === 'GET') {
            // Eu limito a consulta ao dono do cadastro, porque salário nenhum paga vazamento de CPF.
            $consulta = $conexao->prepare('SELECT id,nome,cpf,telefone,setor,vinculo FROM cadastros_passageiros WHERE usuario_id=? AND ativo=1 ORDER BY nome,id');
            $consulta->execute([$usuario['id']]);
            responder_json(['passageiros'=>$consulta->fetchAll()]);
        }
        if ($detalhe) {
            $consulta = $conexao->prepare('SELECT id,nome,cpf,telefone,setor,vinculo FROM cadastros_passageiros WHERE id=? AND usuario_id=? AND ativo=1');
            $consulta->execute([$partes[1], $usuario['id']]);
            $passageiro = $consulta->fetch();
            if (!$passageiro) responder_json(['erro'=>'Passageiro não encontrado.'], 404);
            if ($metodo === 'GET') responder_json(['passageiro'=>$passageiro]);
            if ($metodo === 'DELETE') {
                // Eu desativo em vez de apagar: o histórico já dá trabalho suficiente sem perder referência.
                $consulta = $conexao->prepare('UPDATE cadastros_passageiros SET ativo=0 WHERE id=? AND usuario_id=?');
                $consulta->execute([$partes[1], $usuario['id']]);
                responder_json(['mensagem'=>'Passageiro removido do cadastro.']);
            }
        }
        $cadastro = validar_cadastro_passageiro(ler_json());
        if ($detalhe) {
            $consulta = $conexao->prepare('UPDATE cadastros_passageiros SET nome=?,setor=?,vinculo=?,telefone=?,cpf=? WHERE id=? AND usuario_id=? AND ativo=1');
            $consulta->execute([...array_values($cadastro), $partes[1], $usuario['id']]);
            $identificador = (int)$partes[1];
        } else {
            $consulta = $conexao->prepare('INSERT INTO cadastros_passageiros (nome,setor,vinculo,telefone,cpf,usuario_id) VALUES (?,?,?,?,?,?)');
            $consulta->execute([...array_values($cadastro), $usuario['id']]);
            $identificador = (int)$conexao->lastInsertId();
        }
        responder_json(['id'=>$identificador, 'mensagem'=>'Passageiro salvo.'], $detalhe ? 200 : 201);
    } catch (InvalidArgumentException $erro) {
        responder_json(['erro'=>$erro->getMessage()], 422);
    } catch (PDOException $erro) {
        if ((int)($erro->errorInfo[1] ?? 0) === 1062) responder_json(['erro'=>'Já existe um passageiro com esse CPF no seu cadastro.'], 409);
        throw $erro;
    }
}
