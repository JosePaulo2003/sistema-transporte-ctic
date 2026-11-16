# SISTEMA DE TRANSPORTES CTIC — ENTREGA SEM CONTEÚDO LOCAL

*Estado de referência: 16/11/2026*


## COMO DEVOLVER O PROJETO


  1. Execute preparar-entrega.cmd na raiz do projeto.
     Alternativa: python comandos/entrega.py
  2. Aguarde a mensagem de verificação aprovada.
  3. Envie somente o ZIP indicado, criado em entregas/.
     O arquivo .sha256.txt ao lado permite conferir a integridade do ZIP recebido.

Não compacte a pasta inteira pelo Explorer. Um ZIP manual inclui arquivos que
o Git ignora, como credenciais e configuração local. O exportador não interfere
no funcionamento da sua instalação: mantém esses arquivos no computador e cria
uma cópia filtrada para compartilhar.


## O QUE ENTRA


Código PHP, JavaScript, CSS, HTML, lançadores, migrações de estrutura, testes,
modelos sem senha, política de entrega, convenções e documentação TXT/draw.io/SVG.
As duas imagens PNG institucionais atuais são autorizadas por caminho exato.
Os critérios estão em configuracao/entrega.json.


## O QUE FICA FORA


*.local.*, .env e variantes, arquivos de credenciais, armazenamento, mensagens
de recuperação, logs, históricos e banco local, dumps, cópias de segurança,
arquivos compactados, chaves/certificados, caches Python, dependências instaladas,
configuração de IDE, Git e sua história, entregas anteriores e material legado.
Arquivos desconhecidos fora da política também não entram.
Executáveis PHP, MySQL, Workbench e draw.io não são distribuídos com o projeto.


## COMO A VERIFICAÇÃO FUNCIONA


O comando seleciona por caminhos e extensões permitidos, antes de gerar o ZIP.
Recusa vínculos simbólicos, pontos de análise do Windows e arquivos especiais
quando aparecem como arquivos compartilháveis; não atravessa pastas vinculadas.
Limita cada arquivo a 5 MiB e requer UTF-8 para conteúdo textual.

Procura padrões de chaves privadas, tokens, senha em URL, segredo literal e links
reais de recuperação. Compara também o conteúdo com senhas dos arquivos locais
PHP de configuração, sem imprimir esses valores. Arquivos locais nunca são
executados para realizar essa leitura. Migrações com INSERT, REPLACE ou LOAD DATA
são recusadas para evitar incluir dados sob o nome de migração.

Senhas explicitamente fictícias nos testes são permitidas como fixtures, mas uma
senha local copiada para um teste continua bloqueada. Exemplos distribuídos usam
senhas vazias ou marcadores. Novas imagens binárias exigem autorização na política;
imagens e texto livre ainda precisam de revisão humana quanto a dados pessoais.

Se houver problema, a geração é interrompida e os motivos identificam o arquivo
sem mostrar o segredo. Um ZIP temporário incompleto é removido. Depois de gravar,
o ZIP é reaberto e comparado com todos os bytes selecionados.

O pacote contém MANIFESTO-ENTREGA.json com caminho, tamanho e SHA-256 de cada arquivo
do projeto, além de ORIENTACOES-DA-ENTREGA.txt. Não inclui uma lista dos nomes dos
arquivos privados excluídos. Nenhuma credencial padrão é criada dentro do pacote.


## PROTEÇÃO NO GIT


.gitignore: evita adicionar os padrões privados por acidente. Não remove arquivos
que já estejam rastreados e não limpa o histórico de commits.

.gitattributes: marca arquivos locais com export-ignore para git archive.
Essa política precisa estar no commit exportado; git archive não faz a verificação
de conteúdo do exportador. O ZIP de preparar-entrega.cmd é o caminho recomendado.

.githooks/pre-commit: verifica o conteúdo preparado no índice, não apenas os bytes
visíveis na pasta. Isso evita preparar um segredo e depois limpar o arquivo sem
atualizar a área de stage. Bloqueia também nomes privados já rastreados no índice.

.githooks/pre-push: verifica os commits que serão enviados, incluindo versões
anteriores do conteúdo. Assim, apagar um segredo no último commit não basta para
liberar um histórico que ainda contenha o valor.

Ativação em cada clone:

```text
python comandos/entrega.py --instalar-ganchos
```


O comando configura core.hooksPath=.githooks somente no repositório local. Se houver
outro diretório de ganchos configurado, ele recusa substituí-lo silenciosamente.
Ganchos não são ativados automaticamente por um clone Git recebido de terceiros.

O projeto pode ter alterações ainda não preparadas para commit. A ativação dos
ganchos não cria commits, não prepara arquivos, não apaga alterações e não reescreve
histórico. Um histórico antigo pode ser bloqueado por um push; corrija-o de forma
consciente antes de enviar Git, ou use a entrega filtrada sem .git.

Auditoria desta entrega: o histórico anterior contém uma versão de LEIA-ME.md com
caminho pessoal e um cache Python antigo em testes/__pycache__/. O gancho de push
bloqueia o envio desse histórico. Ele foi preservado, sem reescrita automática.
Esses itens não entram no ZIP gerado: a seleção usa os arquivos atuais permitidos
e exclui todo o diretório .git e os caches.


## COMANDOS ÚTEIS


```text
python comandos/entrega.py --verificar
```

    Inspeciona os candidatos da pasta atual sem produzir um pacote.


```text
python comandos/entrega.py --pre-commit
```

    Inspeciona os arquivos preparados no índice Git.


```text
python testes/entrega.py
```

    Testa exclusão, ZIP, manifesto, senhas copiadas, stage e histórico em pastas
    temporárias; não acessa o banco nem altera o stage do projeto.


## AO RECEBER UM PACOTE


Extraia em uma pasta nova, instale os requisitos e execute configurar.cmd.
A configuração e as credenciais serão próprias da nova instalação.
Ative os ganchos se for trabalhar com Git nesse clone e mantenha os modelos vazios.


## LIMITES


Não é possível impedir que o dono do computador envie manualmente outro ZIP,
desative ganchos ou use --no-verify. O scanner identifica padrões; não reconhece
todo dado pessoal, informação de negócio ou segredo disfarçado/codificado.
O hash de integridade não é uma assinatura digital de autoria.

O mecanismo reduz envios acidentais e fornece um pacote concreto para revisar.
Compartilhe o pacote gerado, revise arquivos novos e nunca troque a configuração
local pela senha de uma pessoa dentro dos modelos ou da documentação.
