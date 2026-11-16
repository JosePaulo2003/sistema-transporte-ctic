# SISTEMA DE TRANSPORTES CTIC — OPERAÇÃO E TESTES

*Estado de referência: 16/11/2026*


## 1. DEPENDÊNCIAS


PHP 8.1 ou superior e extensão pdo_mysql. O ambiente de referência usa PHP 8.4
e MySQL 8.0. PHP, MySQL, Workbench, Python e draw.io não acompanham a entrega.
Não há dependências Composer ou npm da aplicação.

Python 3.10 ou superior é necessário para preparar entregas e gerar diagramas,
mas não para servir a aplicação. Playwright é exclusivo do teste visual.

Referências de instalação:
  PHP: https://www.php.net/downloads.php
  MySQL: https://dev.mysql.com/downloads/mysql/
  draw.io Desktop: https://github.com/jgraph/drawio-desktop/releases


## 2. PRIMEIRA INSTALAÇÃO NO WINDOWS


  a) Instale PHP com pdo_mysql e um servidor MySQL local; inicie o serviço MySQL.
  b) Extraia o ZIP de entrega em uma pasta nova.
  c) Execute configurar.cmd e informe host, porta, banco e acesso administrativo.
  d) Abra CREDENCIAIS.local.txt para consultar o primeiro acesso do sistema.
  e) Execute iniciar.cmd e abra http://127.0.0.1:8080.

O configurador cria o banco apenas se não existir e cria uma conta aleatória
restrita a esse banco. As permissões concedidas são SELECT, INSERT, UPDATE, DELETE,
CREATE, ALTER, INDEX e REFERENCES. A conta é criada para localhost; a preparação
assistida foi validada para servidor local, não como instalador remoto genérico.

O acesso administrativo é usado só na preparação e não fica na configuração
da aplicação. A senha do primeiro administrador é gerada aleatoriamente, salvo
se a variável CTIC_ADMIN_SENHA for fornecida ao configurar.php.

Arquivos gerados e privados:
  configuracao/aplicacao.local.php
  configuracao/primeiro-usuario.local.php
  CREDENCIAIS.local.txt

Esses arquivos não acompanham o pacote. Cada instalação recebe seus próprios.
O configurador não sobrescreve uma configuração local existente. Se ela existe,
configurar.ps1 apenas executa a preparação das migrações e da conta inicial.

php.ps1 procura CTIC_PHP, depois php no PATH e por último o PHP local em
%LOCALAPPDATA%/CTIC/php/php.exe. Esse último caminho é uma conveniência desta
instalação; o executável não é incluído no projeto. Defina CTIC_PHP para usar
outro caminho, ou coloque um PHP corretamente configurado no PATH.

Os lançadores CMD usam a política de execução apenas no processo PowerShell
que inicia o script; não alteram a configuração permanente do Windows.


## 3. PREPARAÇÃO MANUAL / LINUX


Crie o banco utf8mb4 e uma conta com as permissões necessárias, usando um usuário
administrativo do MySQL. Configure essa conta em uma cópia local de
configuracao/aplicacao.exemplo.php chamada aplicacao.local.php.

Copie configuracao/primeiro-usuario.exemplo.php para primeiro-usuario.local.php
e preencha nome, e-mail, setor e uma senha local de 12 a 72 bytes.
Nenhum dos modelos distribuídos contém senha utilizável.

Na raiz do projeto:

```text
./comandos/php.sh comandos/preparar.php
./iniciar.sh
```


php.sh habilita pdo_mysql na linha de execução se ele estiver instalado, mas
desabilitado no php.ini. Não instala pacotes do sistema operacional.
Confirme as permissões de execução dos scripts .sh ao extrair fora de Git.


## 4. CONFIGURAÇÃO


banco_de_dados.dsn: mysql com host, port, dbname e charset=utf8mb4.
banco_de_dados.usuario / senha: conta própria da aplicação; não usar root.
segundos_inatividade_sessao: padrão 1800.
segundos_duracao_sessao: padrão 28800.
cookie_seguro: false no HTTP local; true com HTTPS na hospedagem.
ambiente_local: true apenas para ambiente local.
endereco_aplicacao: base dos links de recuperação, sem depender do Host da requisição.
emails.transporte: arquivo para mensagem local; mail para o serviço de e-mail do PHP.
emails.remetente: e-mail válido quando usar mail.

CTIC_CONFIGURACAO pode apontar o processo PHP para outro arquivo de configuração,
por exemplo em uma instalação isolada de testes. Ela não recebe dados do navegador.
O nome do banco não é um nome de conexão do Workbench; Workbench é apenas o cliente.


## 5. ATUALIZAÇÕES E MIGRAÇÕES


Faça uma cópia de segurança antes de mudanças de estrutura. Execute preparar.php
na raiz com o PHP configurado. O preparador exige o arquivo do primeiro usuário,
mesmo quando o administrador já existe.

migrar.php adquire GET_LOCK com um nome derivado do banco e espera até 10 segundos.
Aplica arquivos .sql em ordem de nome e registra nome e SHA-256, normalizando CRLF.
Uma migração registrada com conteúdo diferente é recusada. Libera a trava ao sair.

001 cria autenticação; 002 cria pedidos e histórico; 003 completa os fluxos.
O registro de migrações é a 12ª tabela. Os scripts existentes são simples, sem
procedimentos armazenados; o executor separa instruções por ponto e vírgula.
Não edite uma migração já aplicada: crie outra. DDL MySQL não tem rollback geral;
um erro no meio de uma nova migração pode exigir correção antes de repeti-la.

Repetir a preparação não muda a senha de uma conta já existente. Para alterá-la,
use Minha conta ou a administração de usuários. Se testes usam o primeiro usuário,
o arquivo de credenciais de teste precisa corresponder à senha atual desse banco.


## 6. HOSPEDAGEM


Use Apache com DocumentRoot no diretório public/, mod_rewrite e regras .htaccess
habilitadas. Configure HTTPS, cookie_seguro=true, ambiente_local=false e a URL
pública em endereco_aplicacao. Configure o envio de e-mail do PHP antes de usar
emails.transporte=mail. O código não fornece SMTP autenticado diretamente.

Configuração, credenciais, armazenamento, testes, documentação e .git ficam fora
do DocumentRoot. Configure display_errors=Off e um destino privado para os erros.
O servidor PHP embutido é o ambiente de desenvolvimento usado pelos lançadores.
As rotas partem da raiz do domínio; hospedagem em subpasta exige adaptação.

Para e-mails locais, armazenamento/emails é criado quando necessário. Não há
expurgo automático desses TXT; eles contêm links de recuperação e são privados.
Logs variam com a forma de execução; quando redirecionados para armazenamento/,
também ficam fora da entrega e do acesso HTTP.


## 7. TESTES SEM BANCO


Na raiz:
  PHP: testes/validacao-solicitacoes.php
  PHP: testes/validacao-usuarios.php
  Python: python testes/entrega.py

Execute arquivos PHP com comandos/php.ps1 no Windows ou comandos/php.sh no Linux.
Os dois testes PHP validam regras isoladas. O teste de entrega usa pastas e
repositórios Git temporários; não modifica o banco nem o índice Git do projeto.


## 8. TESTES DE INTEGRAÇÃO HTTP


Use banco e servidor de desenvolvimento separados, acessíveis na porta 8080.
Os testes atuais usam essa porta fixa; não aponte a suite para a instalação real.


```text
python testes/autenticacao.py
python testes/solicitacoes.py
python testes/usuarios.py
python testes/fluxos-completos.py
```


Por padrão, leem configuracao/primeiro-usuario.local.php. CTIC_TESTE_USUARIO permite
indicar outro arquivo com os dados da conta de teste. O processo PHP precisa usar
a configuração do banco isolado correspondente, por exemplo via CTIC_CONFIGURACAO.

autenticacao.py: login, senha incorreta, CSRF, renovação de sessão e proteção de arquivos.
solicitacoes.py: cria um pedido de teste e verifica rascunho, envio e histórico.
usuarios.py: cria contas e pedido de teste; testa isolamento e desativa as contas.
fluxos-completos.py: catálogo, CPF, cópias históricas, aprovação, cancelamento e conta.
  Com CTIC_TESTE_EMAIL_LOCAL=1, verifica também o link TXT e o uso único do token.

As contas e os pedidos criados permanecem no banco de desenvolvimento. Essa é a
razão para separar os ambientes; não são removidos para preservar os vínculos.


## 9. TESTE VISUAL


Instale a dependência de teste:

```text
python -m pip install playwright
```


O teste usa Microsoft Edge quando encontrado no caminho padrão do Windows.
CTIC_TESTE_NAVEGADOR pode indicar outro executável Chromium compatível.
Se não houver navegador instalado pelo Playwright, instale-o com:

```text
python -m playwright install chromium
```


Execute: python testes/navegacao.py
Ele cria passageiro e pedido identificados como teste, percorre aprovação e
conclusão, verifica desktop e celular e confirma ausência de erros JavaScript.
Requisições a fontes e outros recursos externos são bloqueadas no teste para
manter o ensaio local. Isso não altera os arquivos de estilo da aplicação.


## 10. DOCUMENTAÇÃO E ENTREGA


```text
python comandos/gerar-diagramas.py
python comandos/gerar-diagramas.py --exportar
python comandos/entrega.py --verificar
```


```text
preparar-entrega.cmd
```


O primeiro comando gera o .drawio; --exportar usa o draw.io Desktop para SVGs.
Atualize também os TXT se mudar regras, rotas, permissões, esquema ou operação.
Consulte SEGURANCA-E-ENTREGA.md antes de compartilhar o projeto.
