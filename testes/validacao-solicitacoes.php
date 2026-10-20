<?php
declare(strict_types=1);
require __DIR__ . '/../aplicacao/solicitacoes.php';

// Testa regras de negócio isoladamente, sem depender de banco ou sessão HTTP.
function conferir(bool $condicao, string $mensagem): void
{
    if (!$condicao) throw new RuntimeException($mensagem);
}
function deve_rejeitar(callable $operacao): void
{
    try { $operacao(); } catch (InvalidArgumentException $erro) { return; }
    throw new RuntimeException('A validação aceitou dados inválidos.');
}
$viagem = [
    'tipo_deslocamento'=>'Intermunicipal', 'destino'=>'Itacoatiara', 'finalidade'=>'Visita técnica',
    'local_embarque'=>'Campus', 'centro_custo'=>'CTIC', 'justificativa'=>'Atendimento técnico',
    'saida_em'=>'2026-11-20T08:00', 'retorno_em'=>'2026-11-20T18:00',
];
conferir(validar_viagem($viagem)['destino'] === 'Itacoatiara', 'Destino alterado indevidamente.');
deve_rejeitar(fn()=>validar_viagem(array_replace($viagem, ['destino'=>'  '])));
deve_rejeitar(fn()=>validar_viagem(array_replace($viagem, ['destino'=>[]])));
deve_rejeitar(fn()=>validar_viagem(array_replace($viagem, ['saida_em'=>'2026-02-30T08:00'])));
deve_rejeitar(fn()=>validar_viagem(array_replace($viagem, ['retorno_em'=>'2026-11-19T18:00'])));
deve_rejeitar(fn()=>validar_viagem(array_replace($viagem, ['saida_em'=>'2026-11-20T25:00'])));
deve_rejeitar(fn()=>validar_contato(['telefone'=>'abcdefgh', 'setor'=>'CTIC', 'vinculo'=>'Servidor']));
conferir(validar_contato(['telefone'=>'(92) 99999-0000', 'setor'=>'CTIC', 'vinculo'=>'Servidor'])['setor'] === 'CTIC', 'Contato válido rejeitado.');
deve_rejeitar(fn()=>validar_passageiros([]));
deve_rejeitar(fn()=>validar_passageiros(['nome'=>'Pessoa']));
deve_rejeitar(fn()=>validar_passageiros([['nome'=>'Pessoa', 'setor'=>'', 'vinculo'=>'Servidor']]));
deve_rejeitar(fn()=>validar_passageiros(array_fill(0, 51, ['nome'=>'Pessoa','setor'=>'CTIC','vinculo'=>'Servidor'])));
conferir(count(validar_passageiros([['nome'=>'Pessoa','setor'=>'CTIC','vinculo'=>'Servidor']])) === 1, 'Passageiro válido rejeitado.');
echo "APROVADO: datas, ordem de retorno, campos obrigatórios, telefone e limites de passageiros.\n";
