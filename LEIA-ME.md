# Sistema de Transportes — CTIC

## O que já pode ser testado

Entrada com e-mail e senha cadastrados no banco, sessão PHP, páginas protegidas e saída pelo botão “Sair”. As senhas ficam como hash no banco. A identidade exibida no cabeçalho vem do servidor.

O fluxo de transporte agora usa a API PHP: dados da viagem, contato do solicitante, passageiros e revisão. O rascunho fica na sessão do servidor e o envio final grava a solicitação, os passageiros e o histórico no MariaDB. Painel e listagem consultam o banco. Dados antigos do localStorage não são importados.

## Credenciais locais

Abra `CREDENCIAIS.local.md` nesta pasta. Ele contém o nome do banco, o usuário e a senha de conexão, além do e-mail e da senha do primeiro administrador do sistema.

Os arquivos locais foram gerados com permissão `600` e são ignorados pelo Git. As credenciais só passam a existir no banco após os passos de preparação abaixo. O usuário do banco é diferente do usuário de entrada no sistema. Nenhuma senha de `root` ou do Linux foi definida ou alterada.

## Preparar o ambiente no Arch/Nyarch Linux

Se PHP e MariaDB ainda não estiverem instalados, execute no terminal do computador:

```bash
sudo pacman -Syu php mariadb
```

Se o MariaDB foi instalado agora e ainda não possui uma base inicializada, execute **uma única vez**:

```bash
sudo mariadb-install-db --user=mysql --basedir=/usr --datadir=/var/lib/mysql
```

Depois inicie o serviço:

```bash
sudo systemctl start mariadb
```

Em uma instalação existente, preserve o banco e pule a inicialização. Referências: [PHP no Arch](https://wiki.archlinux.org/title/PHP) e [MariaDB no Arch](https://wiki.archlinux.org/title/MariaDB).

O projeto exige PHP 8.1 ou superior e o driver `pdo_mysql`. Os scripts abaixo carregam esse driver automaticamente quando ele não está habilitado no `php.ini`. Se o PHP não conseguir carregá-lo, confira a instalação e a orientação `extension=pdo_mysql` na documentação acima.

## Criar o banco e o primeiro usuário

Entre na pasta do projeto:

```bash
cd '/home/ayanodev/Documentos/01 - Trabalho e Clientes/CTIC/Sistemas/sistema-transporte-ctic'
```

Crie o banco e a conta de conexão usando a configuração local já preparada:

```bash
sudo mariadb < configuracao/preparar-banco.local.sql
```

O comando acima usa a conta administrativa local via `sudo`. Se a sua instalação usa senha administrativa no MariaDB, utilize `mariadb -u root -p < configuracao/preparar-banco.local.sql`; a senha solicitada é a do administrador do banco, não a senha da aplicação anotada no arquivo local.

Crie as tabelas e o primeiro administrador do sistema:

```bash
./comandos/php.sh comandos/preparar.php
```

A preparação pode ser repetida: não apaga dados nem redefine a senha de um usuário já existente. Se uma conta `transporte_aplicacao` já existia no servidor, o SQL também preserva sua senha; nesse caso ajuste `configuracao/aplicacao.local.php` para usar a senha existente.

## Abrir e testar

```bash
./iniciar.sh
```

Abra **http://127.0.0.1:8080** e entre com as credenciais anotadas em `CREDENCIAIS.local.md`. O e-mail inicial é `admin.transporte@uea.edu.br`: ele identifica apenas uma conta local de teste, sem criar uma caixa postal ou integrar o login institucional da UEA.

Confira:

1. Uma senha incorreta deve mostrar erro sem abrir o painel.
2. As credenciais corretas devem abrir o painel e exibir o nome do administrador.
3. Clique em “Sair” e tente acessar `/painel`: o sistema deve voltar à entrada.
4. Em janela anônima, as páginas internas também devem exigir autenticação.

Com o servidor aberto, execute em outro terminal, nesta mesma pasta:

```bash
python3 testes/autenticacao.py
```

O teste usa as credenciais locais sem imprimir senhas. Ele verifica entrada, senha incorreta, CSRF, renovação da sessão, páginas protegidas, bloqueio de arquivos internos e saída. Ele realiza uma tentativa inválida seguida de um login válido. Não altera solicitações ou passageiros.

Para encerrar o servidor, pressione **Ctrl+C** no terminal. O banco preserva os usuários cadastrados.

## Estrutura

- `aplicacao/inicializacao.php`: configuração, PDO, sessão e autenticação.
- `aplicacao/tela-entrada.php`: formulário de entrada com token CSRF.
- `configuracao/aplicacao.exemplo.php`: modelo de conexão sem credenciais reais.
- `configuracao/*.local.php` e `*.local.sql`: configurações privadas deste computador.
- `banco-de-dados/migracoes/001_autenticacao.sql`: tabelas `usuarios` e `tentativas_acesso`.
- `comandos/preparar.php`: criação inicial das tabelas e do administrador.
- `public/index.php`: controlador das rotas e páginas protegidas.
- `public/assets/js/entrada.js` e `sessao.js`: integração do frontend com a API.
- `roteador.php`: encaminhamento e proteção dos arquivos no servidor de desenvolvimento.

## API de autenticação

| Método | Rota | Finalidade |
| --- | --- | --- |
| GET | `/api/autenticacao/csrf` | Obter o token CSRF |
| POST | `/api/autenticacao/entrar` | Autenticar com JSON contendo `email` e `senha` |
| GET | `/api/autenticacao/usuario` | Consultar o usuário da sessão |
| POST | `/api/autenticacao/sair` | Encerrar a sessão |

Entrada e saída exigem o cabeçalho `X-CSRF-Token`. As respostas usam `usuario`, `erro` e `mensagem`. As páginas exigem sessão, e usuários desativados deixam de ter acesso na próxima verificação. O limite de tentativas usa uma janela de 15 minutos.

## Hospedagem posterior

O servidor embutido é para desenvolvimento local. Ao hospedar, configure HTTPS e use `public/` como diretório público no Apache com `mod_rewrite` e permissão para as regras do `.htaccess`. Os arquivos de configuração e credenciais devem permanecer fora do diretório público. A hospedagem em subpasta ainda não está configurada.

## Atualizar uma instalação existente

Com o MariaDB ativo, execute na raiz do projeto:

```bash
./comandos/php.sh comandos/preparar.php
```

O preparador aplica as migrações SQL em ordem, incluindo `002_solicitacoes.sql`, antes de verificar o administrador. As migrações atuais usam `CREATE TABLE IF NOT EXISTS`: preservam registros e senhas existentes. Esse preparador não é um gerenciador de futuras alterações de colunas.

## Fluxo de solicitações

1. Abra Nova solicitação e preencha os dados da viagem.
2. Confirme o contato. Nome e e-mail vêm do usuário autenticado.
3. Adicione de 1 a 50 passageiros e clique em Revisar solicitação para salvar essa etapa.
4. Confira o resumo, marque a declaração e envie.
5. Consulte o painel ou a listagem. Clique no código para ver os detalhes e o histórico.

Solicitantes consultam apenas seus pedidos. Administradores consultam todos e podem alterar o status entre pendente, em análise, aprovada, recusada e concluída. Cada mudança efetiva registra o usuário responsável e o estado anterior, na mesma transação. Ainda não existe uma regra de transições obrigatórias entre esses estados.

O rascunho é temporário, compartilhado entre abas da mesma sessão e perdido ao encerrar ou expirar a autenticação. Adições e remoções na tela de passageiros são confirmadas ao avançar para a revisão. O responsável deve ser incluído na lista se também viajar. Cada envio cria passageiros próprios daquela solicitação, sem deduplicação ou catálogo global. Veículos e motoristas ainda não estão implementados.

As datas de viagem usam o horário local de Manaus. As datas de criação e do histórico ficam em UTC. Todos os campos são validados no servidor, e os textos são exibidos no navegador sem interpretação de HTML.

## API de transporte

Todas as rotas exigem autenticação. Operações de escrita também exigem `X-CSRF-Token` e usam JSON quando recebem dados.

| Método | Rota | Finalidade |
| --- | --- | --- |
| GET | `/api/solicitacoes` | Listar os pedidos permitidos ao usuário |
| GET | `/api/solicitacoes/rascunho` | Consultar o rascunho da sessão |
| PUT | `/api/solicitacoes/rascunho` | Salvar `viagem`, `contato` ou `passageiros` |
| DELETE | `/api/solicitacoes/rascunho` | Descartar o rascunho |
| POST | `/api/solicitacoes` | Enviar o rascunho com `{"declaracao": true}` |
| GET | `/api/solicitacoes/{id}` | Consultar detalhes, passageiros e histórico |
| PATCH | `/api/solicitacoes/{id}/status` | Administrador altera o status com `{"status": "analise"}` |

O rascunho usa os campos `tipo_deslocamento`, `destino`, `finalidade`, `saida_em`, `retorno_em`, `local_embarque`, `centro_custo` e `justificativa` em `viagem`; `telefone`, `setor` e `vinculo` em `contato`; e uma lista de objetos com `nome`, `setor` e `vinculo` em `passageiros`. As datas devem seguir `AAAA-MM-DDTHH:MM`. O limite de corpo JSON da aplicação é de 16 KiB.

## Testar a etapa de transporte

Validações isoladas, sem alterar o banco:

```bash
./comandos/php.sh testes/validacao-solicitacoes.php
```

Com as migrações aplicadas e o servidor iniciado, confira primeiro a autenticação:

```bash
python3 testes/autenticacao.py
```

O teste seguinte usa o administrador local e **cria uma solicitação de teste no banco**, com passageiro e histórico. O registro permanece identificado como TESTE AUTOMATIZADO. Execute em banco de desenvolvimento:

```bash
python3 testes/solicitacoes.py
```

Ele verifica autenticação, CSRF, datas, rascunho, declaração, envio, bloqueio de reenvio, passageiros, listagem e histórico de status. Para conferir o isolamento entre usuários, entre também com contas de perfil solicitante e verifique que cada uma lista apenas seus próprios pedidos e recebe 404 ao consultar um pedido alheio. O teste automatizado usa apenas o administrador e não cobre esse cenário entre contas.

## Administração de usuários

Entre como administrador e use o link **Usuários** no cabeçalho, ou abra `/usuarios`. A tela permite cadastrar, buscar, editar, ativar/desativar contas e redefinir senhas. A ativação é alterada pela opção Conta ativa no formulário de edição. Os controles usam as cores e a tipografia do sistema.

O cadastro exige nome, e-mail único, setor, perfil e senha inicial de 12 a 72 bytes. O limite é contado em bytes para evitar truncamento pelo bcrypt. Na edição, a senha é alterada somente pelo formulário específico de redefinição. Os hashes nunca são enviados à interface ou à API administrativa.

A página e a API exigem perfil administrador validado no servidor. A própria conta administrativa não pode ser desativada ou rebaixada pelo usuário conectado. As alterações administrativas são serializadas por transação para preservar pelo menos um administrador ativo em alterações concorrentes.

Não há exclusão de contas: a desativação preserva os vínculos e o histórico das solicitações. As sessões de uma conta desativada ou com senha redefinida são recusadas na próxima requisição. Alterações de perfil são verificadas novamente em cada acesso. Ao instalar esta atualização, sessões já abertas sem a nova assinatura de senha exigirão novo login.

A redefinição não envia e-mail nem exige troca obrigatória no primeiro acesso. O administrador informa a nova senha ao titular por um canal apropriado. Se alterar a senha do primeiro administrador, os testes que leem `configuracao/primeiro-usuario.local.php` precisarão que essa configuração local corresponda à nova senha; repetir o preparador não redefine senhas existentes.

| Método | Rota | Finalidade |
| --- | --- | --- |
| GET | `/api/usuarios` | Listar cadastros sem senhas ou hashes |
| POST | `/api/usuarios` | Criar com `nome`, `email`, `setor`, `perfil`, `ativo` e `senha` |
| PUT | `/api/usuarios/{id}` | Editar `nome`, `email`, `setor`, `perfil` e `ativo` |
| POST | `/api/usuarios/{id}/senha` | Redefinir com `senha` |

O campo `ativo` deve ser booleano JSON, e o perfil deve ser `administrador` ou `solicitante`. Escritas exigem CSRF. Retornos principais: 401 sem autenticação, 403 sem permissão, 404 para conta inexistente, 409 para e-mail duplicado e 422 para dados inválidos. Esta etapa usa a tabela `usuarios` existente e não exige migração adicional.

Validação isolada, sem banco:

```bash
./comandos/php.sh testes/validacao-usuarios.php
```

Com o servidor em `http://127.0.0.1:8080`, execute as regressões e o novo teste:

```bash
python3 testes/autenticacao.py
python3 testes/solicitacoes.py
python3 testes/usuarios.py
```

O teste `usuarios.py` cria duas contas solicitantes com identificadores aleatórios e um pedido de teste. Verifica cadastro, duplicidade de e-mail, edição, CSRF, bloqueio da administração para solicitantes, isolamento de listagem e detalhes, bloqueio da alteração de status, redefinição de senha, invalidação de sessão, desativação e reativação. As contas são desativadas ao finalizar; os registros permanecem no banco para preservar o histórico. Execute somente no banco de desenvolvimento. Os testes de integração usam a senha do administrador local e não imprimem senhas.

## Verificação nesta entrega

Nesta etapa foram conferidos os scripts de terminal, a sintaxe Python, a leitura dos documentos HTML e as referências do fluxo. O ambiente de edição não disponibiliza PHP, MariaDB ou Node.js: os testes PHP, HTTP e de navegador desta etapa ainda precisam ser executados no computador com o banco ativo.

Código, comentários e documentação seguem as convenções em `AGENTS.md`.
