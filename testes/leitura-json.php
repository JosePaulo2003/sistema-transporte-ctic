<?php
declare(strict_types=1);
require __DIR__ . '/../aplicacao/inicializacao.php';

// Regressão: objetos vazios devem alcançar a validação de campos, listas devem ser recusadas.
function conferir_json(bool $condicao, string $mensagem): void
{
    if (!$condicao) throw new RuntimeException($mensagem);
}
conferir_json(decodificar_objeto_json('{}') === [], 'Objeto vazio foi rejeitado.');
conferir_json(decodificar_objeto_json('{"0":"valor"}') === [0=>'valor'], 'Objeto com chave numérica foi rejeitado.');
conferir_json(decodificar_objeto_json('{"viagem":{"destino":"Manaus"},"passageiros":[{"nome":"Pessoa"}]}')
    === ['viagem'=>['destino'=>'Manaus'], 'passageiros'=>[['nome'=>'Pessoa']]], 'Estruturas internas foram alteradas.');
foreach (['[]', '[1]', 'null', 'true', '42', '"texto"'] as $conteudo) {
    try {
        decodificar_objeto_json($conteudo);
    } catch (InvalidArgumentException $erro) {
        continue;
    }
    throw new RuntimeException('Valor JSON sem objeto na raiz foi aceito: ' . $conteudo);
}
try {
    decodificar_objeto_json('{');
    throw new RuntimeException('JSON malformado foi aceito.');
} catch (JsonException $erro) {
    // A leitura HTTP traduz a falha de sintaxe para uma resposta 400.
}
echo "APROVADO: objeto vazio, objetos internos, listas, valores escalares e JSON malformado.\n";
