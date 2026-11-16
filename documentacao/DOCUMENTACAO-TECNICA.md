# SISTEMA DE TRANSPORTES CTIC — DOCUMENTAÇÃO TÉCNICA

*Estado de referência: 16/11/2026*


## 1. OBJETIVO E ESCOPO


Aplicação web para solicitar transporte institucional, manter um catálogo privado
de passageiros, analisar pedidos e consultar o histórico das decisões.

Perfis existentes: solicitante e administrador. Não há perfil de motorista.
O sistema contém login, controle de sessão, painel, quatro etapas de solicitação,
listagem e filtros, detalhes, análise, cancelamento, cadastro de passageiros,
administração de usuários, edição da própria conta e recuperação de senha.

Veículo e motorista são informações textuais do atendimento. A interface apresenta
opções de veículo e um campo para o nome do motorista. Não existe cadastro de frota,
agenda de disponibilidade, capacidade validada ou prevenção de alocação simultânea.


## 2. TECNOLOGIAS E ORGANIZAÇÃO


Backend: PHP 8.1 ou superior, PDO e driver pdo_mysql; sem framework ou Composer.
Banco validado: MySQL 8.0, com InnoDB e utf8mb4.
Frontend: HTML, CSS e JavaScript nativo, usando fetch e JSON.
Sessão: mecanismo nativo do PHP, com armazenamento configurado no servidor PHP.
Entrega e geração de diagramas: Python 3.10 ou superior, biblioteca padrão.
Navegador automatizado: Playwright, dependência exclusiva do teste visual.
Diagramas: XML nativo do draw.io, acompanhado de visualizações SVG.

aplicacao/                 Serviços PHP, validação, sessão, regras e autorização.
banco-de-dados/migracoes/   Estrutura SQL versionada; não contém dumps de dados.
comandos/                  Preparação, migrações, entrega e geração dos diagramas.
configuracao/              Modelos públicos, política de entrega e arquivos locais.
public/                    Único diretório que deve ser público na hospedagem.
public/assets/             JavaScript, estilos de integração e imagem SVG da marca.
public/views/              Telas, seus estilos e imagens institucionais.
testes/                    Validações isoladas, testes HTTP, de navegador e entrega.
documentacao/              Arquivos TXT e diagramas sem dados da instalação.
.githooks/                 Verificação local antes de commit e push.
armazenamento/             Mensagens e registros locais; excluído da entrega.
entregas/                  ZIPs e resumos SHA-256 gerados; excluído do próximo ZIP.


## 3. ENTRADA DE REQUISIÇÕES


index.php encaminha para public/index.php. Em desenvolvimento, iniciar.ps1 ou
iniciar.sh inicia o servidor PHP com roteador.php. O roteador permite somente
recursos estáticos de assets/ e views/css/ ou views/img/, com extensões previstas.
Ele usa realpath para impedir que o recurso escape do diretório public/.

No Apache, as regras .htaccess encaminham as requisições para public/index.php.
A configuração recomendada usa DocumentRoot em public/ e mod_rewrite ativo.

public/index.php identifica a rota e o método, inicia a sessão e despacha a API
ou carrega a página. Páginas protegidas sem autenticação redirecionam para /entrar.
As APIs protegidas retornam 401. As telas /usuarios e /analisar-solicitacao exigem
administrador também no servidor. Os endereços antigos dos HTMLs são redirecionados,
preservando a consulta da URL.

O controlador reescreve links e caminhos de recursos das telas e injeta a identidade
pública da sessão. O painel continua armazenado em login.html por compatibilidade;
a página real de entrada é aplicacao/tela-entrada.php.

Cabeçalhos comuns: Cache-Control no-store, X-Content-Type-Options nosniff,
X-Frame-Options DENY e Referrer-Policy same-origin. Exceções internas são registradas;
a resposta pública de falha informa indisponibilidade sem retornar o erro SQL.


## 4. RESPONSABILIDADES DOS MÓDULOS


aplicacao/inicializacao.php
  Carrega a configuração local, abre uma conexão PDO reutilizável, configura a
  sessão e implementa login, logout, CSRF, leitura JSON e identificação pública.
  usuario_atual() reconsulta a conta e valida os tempos e a assinatura da senha.

aplicacao/solicitacoes.php
  Normaliza texto, valida telefone, viagem, contato e lista de passageiros.
  Inclui o módulo de atendimento das rotas de transporte.

aplicacao/fluxo-solicitacoes.php
  Mantém o rascunho da sessão, cria pedidos e cópias dos passageiros em uma
  transação, filtra consultas, retorna detalhes e histórico, e controla estados.
  Usa bloqueio de linha ao alterar um pedido para preservar o estado anterior.

aplicacao/passageiros.php
  Valida CPF com dígitos verificadores e atende o catálogo reutilizável.
  Impõe propriedade do cadastro inclusive para o perfil administrador.
  A seleção por IDs consulta exclusivamente cadastros ativos do usuário.

aplicacao/usuarios.php
  Administra contas. Valida cadastro e senha, impede e-mail duplicado e protege
  o último administrador ativo em alterações concorrentes. Não exclui usuários.

aplicacao/conta.php
  Edita nome e setor da própria conta, troca a senha com confirmação da senha
  atual e implementa recuperação e redefinição por token temporário.

public/assets/js/api.js
  Centraliza requisições JSON, consulta de CSRF e mensagens; bloqueia envios
  repetidos por um mesmo formulário ou ação durante o processamento.

public/assets/js/sessao.js
  Preenche a identidade visível, trata saída e verifica a sessão ao retornar
  à página ou aba. Falha de rede isolada não é tratada como logout.

public/assets/js/telas.js
  Integra painel, filtros, etapas, catálogo, análise, cancelamento, detalhes,
  confirmações e edição da conta. Usa textContent para dados vindos da API.

public/assets/js/entrada.js, recuperacao.js e usuarios.js
  Implementam, respectivamente, entrada, recuperação e administração de contas.


## 5. IDENTIDADE E AUTORIZAÇÃO


O login aceita e-mail e senha de uma conta cadastrada e ativa. A senha é validada
com password_verify e o hash é atualizado quando password_needs_rehash indicar.
O hash de simulação usado para conta inexistente é dado público de teste, não uma
credencial de acesso ao sistema.

O servidor registra a tentativa antes da verificação e limita a janela de 15 minutos
a 5 tentativas por e-mail ou 30 por IP. Os identificadores usados nesse controle são
hashes SHA-256, e registros com mais de um dia são limpos pelo fluxo de login.

Após o login, o ID da sessão e o CSRF são renovados. O cookie é HttpOnly, SameSite=Lax
e Secure quando há HTTPS ou cookie_seguro=true. Não usa ID de sessão na URL.
Os padrões são 30 minutos sem atividade e 8 horas desde a autenticação.

A sessão mantém usuario_id, tempos e uma assinatura do hash da senha. Conta
desativada ou assinatura diferente invalida a sessão na próxima verificação.
Mudanças de perfil passam a valer na próxima consulta autenticada.

Toda escrita pela API exige X-CSRF-Token. O corpo, quando presente, precisa ser
um objeto JSON, não uma lista. O limite é 16 KiB e a profundidade máxima é 16.
O endpoint de saída não exige corpo JSON.

Pedidos de outra pessoa retornam 404 para solicitantes. O administrador pode
consultar todos os pedidos; isso não lhe concede acesso ao catálogo alheio de CPF.
O perfil e os IDs enviados pelo navegador não substituem a autorização do servidor.


## 6. SOLICITAÇÕES


Etapa 1: viagem. Tipo, destino, finalidade, embarque, centro de custo e justificativa
são obrigatórios. As datas precisam existir e o retorno não pode anteceder a saída.
O código não impõe antecedência mínima nem proíbe datas passadas.

Etapa 2: contato. Nome e e-mail vêm da conta; telefone, setor e vínculo são informados.
Telefone precisa conter de 8 a 15 dígitos e usar somente a pontuação permitida.

Etapa 3: passageiros. A interface seleciona IDs distintos de cadastros ativos do
próprio usuário. O rascunho pode ter seleção vazia; o envio exige de 1 a 50 pessoas.
A API também mantém compatibilidade com objetos de nome, setor e vínculo informados
diretamente no rascunho. Essa forma não exige CPF e não cria um catálogo reutilizável.

Etapa 4: revisão. A declaração precisa ser o booleano JSON true. O servidor valida
novamente o rascunho e grava pedido, cópias dos passageiros, vínculos e histórico
inicial em uma transação. Falhas desfazem as escritas transacionais.

O rascunho fica na sessão PHP, compartilhado entre as abas dessa sessão. Não é
persistente no banco e se perde após logout ou expiração. O envio bem-sucedido limpa
o rascunho; repetir o envio com o rascunho vazio é recusado. Não há chave global de
idempotência entre sessões diferentes. O responsável precisa ser selecionado como
passageiro se também viajar.

Saída e retorno representam horário local de Manaus e ficam como DATETIME local.
Criação, histórico, tentativas e expiração usam UTC no banco. A interface converte
os registros UTC para America/Manaus ao exibir.


## 7. ESTADOS E HISTÓRICO


pendente  -> analise, aprovada, recusada ou cancelada
analise   -> aprovada, recusada ou cancelada
aprovada  -> concluida ou cancelada
recusada, concluida e cancelada -> terminais

Repetir o estado atual é uma operação sem novo histórico. Reabrir ou executar uma
transição não prevista retorna 409. Somente o administrador usa status e análise.
A aprovação exige veículo e motorista. O cancelamento exige motivo e pode ser
feito pelo dono ou por administrador enquanto o pedido estiver aberto.

A API aceita observação opcional na análise/status; a tela atual não oferece um
campo de justificativa da recusa. A recusa registra o estado e o responsável.
Na aprovação, a observação do histórico também recebe veículo e motorista.

O bloqueio SELECT ... FOR UPDATE permite registrar o estado anterior correto.
Alteração do status, atendimento e histórico participam da mesma transação.


## 8. CATÁLOGO E CÓPIAS DE PASSAGEIROS


cadastros_passageiros contém nome, CPF normalizado, telefone, setor, vínculo e dono.
CPF ativo é único por dono; pessoas diferentes podem manter seus próprios cadastros
da mesma pessoa. Remover significa ativo=0, liberando o CPF para um novo cadastro.

passageiros contém cópias históricas de nome, setor e vínculo de cada envio.
solicitacao_passageiros associa essas cópias à viagem. Não existe FK do catálogo
para as cópias; mudar ou remover o cadastro não reescreve pedidos antigos.
CPF e telefone do passageiro não são copiados para a lista histórica da viagem.


## 9. CONTAS E SENHAS


Administração: cadastro com nome, e-mail, setor, perfil, ativo e senha inicial.
E-mail deve ser único; ativo precisa ser booleano JSON. A senha tem de 12 a 72 bytes,
não pode ter NUL nem ser composta só de espaços. A contagem em bytes evita o limite
silencioso do bcrypt. Os hashes nunca são retornados na listagem administrativa.

O administrador não pode desativar ou rebaixar a própria conta; o banco precisa
manter pelo menos um administrador ativo. A operação serializa os administradores
ativos para proteger essa regra em alterações concorrentes.

Minha conta permite nome e setor. Não permite trocar e-mail, perfil ou ativação.
A troca de senha exige senha atual, nova senha e confirmação; renova a sessão
que fez a troca e invalida as demais pela mudança da assinatura.

Recuperação: limite de 5 pedidos por e-mail ou IP em 15 minutos; token aleatório
de 32 bytes, SHA-256 no banco e expiração de 30 minutos. O link usa fragmento #token,
retirado da URL após a leitura. Uso, expiração ou troca da senha invalidam o token.
A redefinição marca todos os tokens pendentes da conta como usados.

Modo local: mensagem TXT em armazenamento/emails; não há envio externo.
Modo mail: usa mail() e requer serviço de e-mail e remetente configurados. Não há
cliente SMTP autenticado próprio. Falhas de envio são registradas sem revelar
a existência da conta na resposta pública.


## 10. EVOLUÇÃO E LIMITES ATUAIS


Não há integração com login institucional, caixa postal institucional, pagamentos,
notificações automáticas de status, frota, agenda ou perfil de motorista.
Não há recuperação persistente de rascunhos nem migração de dados do localStorage.
Listagens não têm paginação de banco. Filtros de período aceitam 30, 60 ou 90 dias
e consideram a data de criação do pedido. A implantação em subpasta não foi adaptada;
as rotas e recursos usam endereços absolutos a partir da raiz do domínio.

A entrega filtrada protege o compartilhamento do código. Ela não substitui controle
de acesso ao sistema, configuração de HTTPS, manutenção do servidor ou revisão
humana de dados pessoais que alguém acrescente ao conteúdo de arquivos permitidos.

Documentos complementares: API.md, DICIONARIO-DE-DADOS.md, OPERACAO-E-TESTES.md
e SEGURANCA-E-ENTREGA.md. Diagramas: diagramas/projeto-ctic.drawio.
