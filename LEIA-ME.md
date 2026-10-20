# Sistema de Transportes — CTIC

## O que já pode ser testado

Entrada com e-mail e senha cadastrados no banco, sessão PHP, páginas protegidas e saída pelo botão “Sair”. As senhas ficam como hash no banco. A identidade exibida no cabeçalho vem do servidor.

Solicitações, solicitantes, passageiros e revisão continuam como protótipos: os dados de transporte ainda são demonstrativos ou ficam no navegador. Essa parte ainda não usa a API de transporte.

## Credenciais locais

Abra `CREDENCIAIS.local.md` nesta pasta. Ele contém o nome do banco, o usuário e a senha de conexão, além do e-mail e da senha do primeiro administrador do sistema.

Os arquivos locais foram gerados com permissão `600` e são ignorados pelo Git. As credenciais só passam a existir no banco após os passos de preparação abaixo. O usuário do banco é diferente do usuário de entrada no sistema. Nenhuma senha de `root` ou do Linux foi definida ou alterada.

## Preparar o ambiente no Arch/Nyarch Linux

PHP e MariaDB não foram encontrados neste ambiente. Execute a instalação no terminal:

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

## Verificação nesta entrega

Foram realizadas conferências estáticas de JavaScript, scripts de terminal, referências e consistência dos campos e consultas. Os testes de execução PHP/MySQL e de navegador precisam ser executados após instalar as dependências; não foram executados neste ambiente.

Código, comentários e documentação seguem as convenções em `AGENTS.md`.
