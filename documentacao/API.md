# SISTEMA DE TRANSPORTES CTIC — CONTRATO HTTP

*Estado de referência: 16/11/2026*


## CONVENÇÕES


Base local: http://127.0.0.1:8080
Corpos: Content-Type: application/json; charset=utf-8.
Cookies: enviar a sessão do mesmo navegador.
Escritas: cabeçalho X-CSRF-Token obtido em GET /api/autenticacao/csrf.
As escritas exigem CSRF inclusive em login, recuperação e redefinição.
Quando houver corpo, enviar objeto JSON; máximo 16 KiB.
As senhas dos exemplos são marcadores, não credenciais utilizáveis.
IDs são inteiros positivos. Erros usam {"erro":"mensagem"}.
Sucessos normalmente usam mensagem, id ou um objeto/lista nomeado.


## AUTENTICAÇÃO


### `GET /api/autenticacao/csrf`

Público. Retorna {"csrf":"<token-da-sessao>"}.
Pode iniciar uma sessão ainda sem usuário.


### `POST /api/autenticacao/entrar`

Público, com CSRF.
Corpo:

```json
{
  "email": "pessoa@example.invalid",
  "senha": "<senha-local>"
}
```

200: usuario com id, nome, email, perfil e setor; novo csrf.
401: credenciais inválidas ou conta inativa.
422: formato inválido; 429: excesso de tentativas, Retry-After 900.


### `GET /api/autenticacao/usuario`

Autenticado. Retorna usuario e csrf; 401 se a sessão não é válida.


### `POST /api/autenticacao/sair`

Autenticado, com CSRF; sem corpo obrigatório.
Encerra a sessão e expira o cookie. Retorna mensagem.


### `POST /api/autenticacao/recuperar`

Público, com CSRF.
Corpo:

```json
{
  "email": "pessoa@example.invalid"
}
```

200: mensagem genérica, independentemente da existência da conta.
422: e-mail inválido. 429: limite de recuperação, Retry-After 900.
A mensagem local é privada; o link bruto não é retornado pela API.


### `POST /api/autenticacao/redefinir`

Público, com CSRF.
Corpo:

```json
{
  "token": "<token-recebido>",
  "senha": "<senha-local>",
  "confirmacao_senha": "<senha-local>"
}
```

Token: 64 caracteres hexadecimais, uso único, 30 minutos de validade.
200: senha alterada; exige novo login.
422: token inválido, expirado, usado, conta inativa ou senha inválida.


## CONTA PRÓPRIA


### `GET /api/conta`

Autenticado. Retorna usuario, sem hash ou senha.


### `PUT /api/conta`

Autenticado, com CSRF.
Corpo:

```json
{
  "nome": "Nome de exemplo",
  "setor": "Setor de exemplo"
}
```

200: mensagem e usuario atualizado.
Somente esses dois campos são gravados; e-mail, perfil e ativo não mudam.


### `PUT /api/conta/senha`

Autenticado, com CSRF.
Corpo:

```json
{
  "senha_atual": "<senha-local>",
  "nova_senha": "<senha-local>",
  "confirmacao_senha": "<senha-local>"
}
```

200: senha alterada, outras sessões invalidadas.
A sessão atual é renovada e recebe nova assinatura e novo CSRF no servidor.
422: senha atual incorreta, confirmação diferente ou nova senha inválida.


## PASSAGEIROS DO CATÁLOGO


Todas as rotas são autenticadas e limitadas ao catálogo do próprio usuário,
inclusive para administradores. Escritas exigem CSRF. Um registro alheio retorna 404.


### `GET /api/passageiros`

200: {"passageiros":[...]} ordenados por nome e ID, somente ativos.
Campos: id, nome, cpf, telefone, setor, vinculo.
Busca da tela ocorre sobre essa listagem; não há filtro de busca na API.


### `POST /api/passageiros`

Corpo: nome, cpf, telefone, setor e vinculo; todos obrigatórios.
CPF aceita pontuação prevista, normaliza para 11 dígitos e valida verificadores.
201: id e mensagem. 409: CPF ativo já cadastrado pelo mesmo dono.


### `GET /api/passageiros/{id}`

200: {"passageiro":{...}}; somente ativo e pertencente ao usuário.


### `PUT /api/passageiros/{id}`

Corpo completo com os mesmos cinco campos do cadastro.
200: id e mensagem. 409: duplicidade de CPF ativo.


### `DELETE /api/passageiros/{id}`

Sem corpo obrigatório. Marca ativo=0.
200: mensagem. Não altera passageiros já registrados em viagens.


## RASCUNHO


### `GET /api/solicitacoes/rascunho`

Autenticado. 200: {"rascunho":{...}}; objeto vazio quando não há rascunho.


### `PUT /api/solicitacoes/rascunho`

Autenticado, com CSRF. Atualiza somente as etapas presentes no objeto enviado.

viagem:
tipo_deslocamento: até 100 bytes
destino: até 200 bytes
finalidade: até 200 bytes
local_embarque: até 200 bytes
centro_custo: até 100 bytes
justificativa: até 4000 bytes
saida_em e retorno_em: AAAA-MM-DDTHH:MM (Manaus)
Os textos são obrigatórios, sem valor composto só de espaços.

contato:
telefone: até 30 bytes, com 8 a 15 dígitos e pontuação permitida
setor e vinculo: até 100 bytes cada, obrigatórios

passageiros_ids:
Lista de inteiros positivos distintos, de 0 a 50 no rascunho.
Só aceita os próprios cadastros ativos.
O servidor guarda cadastro_id, nome, setor e vinculo na sessão.

passageiros (compatibilidade):
Lista de 1 a 50 objetos com nome (150 bytes), setor (100) e vinculo (100).
Não cria cadastro reutilizável e não exige CPF.
Caso os dois formatos sejam enviados, passageiros_ids é processado por último.

Exemplo sem dados reais:
{"viagem":{"tipo_deslocamento":"Intermunicipal","destino":"Destino de exemplo",
"finalidade":"Atendimento","local_embarque":"Campus","centro_custo":"CTIC",
"justificativa":"Justificativa de exemplo","saida_em":"2027-01-20T08:00",
"retorno_em":"2027-01-20T18:00"}}

200: rascunho resultante; 422 para etapa ou seleção inválida.
As etapas são validadas antes de substituir o rascunho da sessão.


### `DELETE /api/solicitacoes/rascunho`

Autenticado, com CSRF, sem corpo obrigatório.
200: rascunho vazio; não apaga pedidos já enviados.


## SOLICITAÇÕES PERSISTIDAS


### `GET /api/solicitacoes`

Autenticado. Solicitante vê os seus; administrador vê todos.
Filtros opcionais na query:
busca: até 200 bytes, procura destino, nome ou ID sem o prefixo #
status: pendente, analise, aprovada, recusada, concluida ou cancelada
periodo: 30, 60 ou 90, em dias desde a criação do pedido
Parâmetro recebido como lista em vez de texto é inválido.
200: {"solicitacoes":[...]} em ordem decrescente de ID; sem paginação.


### `POST /api/solicitacoes`

Autenticado, com CSRF.
Corpo:

```json
{
  "declaracao": true
}
```

Revalida viagem, contato e 1–50 passageiros do rascunho.
201: id e mensagem. Limpa o rascunho somente após o commit.
422: declaração ausente/falsa ou rascunho incompleto/inválido.


### `GET /api/solicitacoes/{id}`

Dono ou administrador. 404 se inexistente ou alheio para solicitante.
200: {"solicitacao":{...}} com:
dados do pedido, nome/e-mail do dono, veiculo, motorista,
motivo_cancelamento, passageiros e historico.
Histórico: status_anterior, status_novo, criado_em (UTC), nome do autor,
observacao quando houver. Passageiros históricos não contêm CPF.


### `PATCH /api/solicitacoes/{id}/status`

Somente administrador, com CSRF.
Corpo: {"status":"analise"}; observacao opcional, não vazia, até 2000 bytes.
Estados aceitos nessa operação: pendente, analise, aprovada, recusada, concluida.
A transição precisa estar prevista no estado atual.
Para aprovada, também são obrigatórios veiculo e motorista (150 bytes cada).
200: mensagem. 409: transição não permitida. Mesmo estado não cria histórico.


### `POST /api/solicitacoes/{id}/analise`

Mesma autorização, campos e regra de status acima, usando POST.
A tela usa esta rota para aprovar ou recusar e PATCH para iniciar análise.


### `POST /api/solicitacoes/{id}/cancelar`

Dono ou administrador, com CSRF.
Corpo: {"motivo":"Motivo de exemplo"}, obrigatório, até 2000 bytes.
200: mensagem. 409: pedido concluído ou recusado.
Repetir o cancelamento de pedido já cancelado, com motivo válido, retorna 200
sem alterar o motivo anterior nem gerar outro histórico.
Registra o motivo em atendimento e observação do histórico.


## ADMINISTRAÇÃO DE USUÁRIOS


Todas as rotas abaixo exigem administrador. Escritas exigem CSRF.


### `GET /api/usuarios`

200: {"usuarios":[...]} com id, nome, email, setor, perfil, ativo e ultimo_acesso_em.
Não retorna hash_senha. Campos numéricos do PDO podem variar entre número e texto;
clientes devem normalizar IDs e o indicador ativo ao trabalhar com a resposta.


### `POST /api/usuarios`

Corpo completo: nome (150 bytes), email (254), setor (100), perfil,
ativo (booleano JSON) e senha (12 a 72 bytes).
Perfil: administrador ou solicitante.
201: id e mensagem. 409: e-mail duplicado. 422: dados inválidos.


### `PUT /api/usuarios/{id}`

Corpo completo: nome, email, setor, perfil e ativo; não muda senha.
200: id e mensagem. 404: inexistente. 409: e-mail duplicado.
422: tentativa de desativar/rebaixar a própria conta ou remover o último admin.


### `POST /api/usuarios/{id}/senha`

Corpo:

```json
{
  "senha": "<senha-local>"
}
```

200: id e mensagem; sessões anteriores são invalidadas na próxima consulta.
Não envia e-mail nem impõe troca no primeiro acesso.


## CÓDIGOS COMUNS


400 JSON inválido ou corpo que não é objeto; 401 autenticação necessária;
403 perfil sem permissão; 404 rota/registro inexistente ou registro alheio;
405 método não permitido, com Allow; 409 conflito; 413 corpo grande;
415 tipo de conteúdo incorreto; 419 CSRF ausente/inválido; 422 validação;
429 limite de tentativas; 503 erro interno de infraestrutura.

Não execute os exemplos contra registros reais para fazer testes. A suite de
integração cria dados identificados como teste e deve usar uma instalação separada.
