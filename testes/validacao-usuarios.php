<?php
declare(strict_types=1);
require __DIR__ . '/../aplicacao/usuarios.php';

// Exercita a validação sem criar usuários ou conectar ao banco.
function conferir_usuario(bool $condicao, string $mensagem): void
{
    if (!$condicao) throw new RuntimeException($mensagem);
}
function rejeitar_usuario(callable $operacao): void
{
    try { $operacao(); } catch (InvalidArgumentException $erro) { return; }
    throw new RuntimeException('Dados inválidos foram aceitos.');
}
$cadastro = ['nome'=>' Pessoa de teste ', 'email'=>'PESSOA@example.com', 'setor'=>'CTIC', 'perfil'=>'solicitante', 'ativo'=>true];
$validado = validar_cadastro_usuario($cadastro);
conferir_usuario($validado['nome'] === 'Pessoa de teste' && $validado['email'] === 'pessoa@example.com', 'Normalização incorreta.');
foreach (['nome'=>' ', 'email'=>'invalido', 'setor'=>[], 'perfil'=>'root', 'ativo'=>'false'] as $campo=>$valor) {
    rejeitar_usuario(fn()=>validar_cadastro_usuario(array_replace($cadastro, [$campo=>$valor])));
}
rejeitar_usuario(fn()=>validar_cadastro_usuario(array_replace($cadastro, ['nome'=>str_repeat('a',151)])));
foreach ([null, [], 'curta', str_repeat(' ',12), str_repeat('a',73), "senha-com-nulo\0teste"] as $senha) {
    rejeitar_usuario(fn()=>validar_senha_usuario($senha));
}
conferir_usuario(validar_senha_usuario(str_repeat('a',12)) === str_repeat('a',12), 'Senha mínima rejeitada.');
conferir_usuario(strlen(validar_senha_usuario(str_repeat('a',72))) === 72, 'Senha máxima rejeitada.');
echo "APROVADO: cadastro, normalização, perfis, ativação e limites de senha.\n";
