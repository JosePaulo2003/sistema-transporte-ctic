<?php
declare(strict_types=1);

// Eu valido no servidor também, porque ninguém me paga a mais para confiar em formulário.
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
    // Eu preservo o horário de Manaus na viagem para não ganhar uma discussão de fuso no lugar de aumento.
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
    validar_telefone($contato['telefone']);
    return $contato;
}

function validar_telefone(string $telefone): void
{
    $quantidadeDigitos = strlen(preg_replace('/\D/', '', $telefone));
    if (!preg_match('/^[0-9()+ .-]{8,30}$/D', $telefone) || $quantidadeDigitos < 8 || $quantidadeDigitos > 15) {
        throw new InvalidArgumentException('Informe um telefone válido.');
    }
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

require_once __DIR__ . '/fluxo-solicitacoes.php';
