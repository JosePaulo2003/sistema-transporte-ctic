# Dicionário de dados — Sistema de Transportes CTIC
Estado de referência: 16/11/2026

Fonte: migrações 001, 002 e 003 e o ledger criado por comandos/migrar.php.
Esquema após todas as migrações. Somente estrutura; nenhum registro real.
InnoDB e utf8mb4 nas tabelas. FKs não têm ON DELETE CASCADE.
DATETIME de viagem: Manaus. Datas de criação, acesso e expiração: UTC.

PK = chave primária; FK = chave estrangeira; UNIQUE KEY = restrição de unicidade.

## 01. `usuarios`

**Finalidade:** Contas autorizadas e hash de senha. E-mail único; conta é desativada, não excluída.

**Origem:** `001_autenticacao.sql`

Definição dos campos e restrições:

```sql
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(150) NOT NULL,
  email VARCHAR(254) NOT NULL,
  hash_senha VARCHAR(255) NOT NULL,
  perfil ENUM('administrador', 'solicitante') NOT NULL DEFAULT 'solicitante',
  setor VARCHAR(100) NOT NULL DEFAULT 'CTIC',
  ativo TINYINT(1) NOT NULL DEFAULT 1,
  ultimo_acesso_em DATETIME NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY usuarios_email_unico (email)
```

## 02. `tentativas_acesso`

**Finalidade:** Limites de login por hashes de e-mail/IP. Sem FK de usuário para incluir contas inexistentes.

**Origem:** `001_autenticacao.sql`

Definição dos campos e restrições:

```sql
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  chave_email CHAR(64) NOT NULL,
  chave_ip CHAR(64) NOT NULL,
  tentativa_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX tentativas_email_data (chave_email, tentativa_em),
  INDEX tentativas_ip_data (chave_ip, tentativa_em)
```

## 03. `solicitacoes`

**Finalidade:** Pedido, responsável, viagem e contato. Saída/retorno são horários locais de Manaus.

**Origem:** `002_solicitacoes.sql + alteração do ENUM em 003_completar_fluxos.sql`

Definição dos campos e restrições:

```sql
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id BIGINT UNSIGNED NOT NULL,
  tipo_deslocamento VARCHAR(100) NOT NULL,
  destino VARCHAR(200) NOT NULL,
  finalidade VARCHAR(200) NOT NULL,
  saida_em DATETIME NOT NULL,
  retorno_em DATETIME NOT NULL,
  local_embarque VARCHAR(200) NOT NULL,
  centro_custo VARCHAR(100) NOT NULL,
  justificativa TEXT NOT NULL,
  telefone VARCHAR(30) NOT NULL,
  setor VARCHAR(100) NOT NULL,
  vinculo VARCHAR(100) NOT NULL,
  status ENUM('pendente','analise','aprovada','recusada','concluida','cancelada') NOT NULL DEFAULT 'pendente',
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  INDEX solicitacoes_usuario_data (usuario_id, criado_em)
```

## 04. `passageiros`

**Finalidade:** Cópia dos participantes de cada envio. Sem CPF e sem FK para o catálogo reutilizável.

**Origem:** `002_solicitacoes.sql`

Definição dos campos e restrições:

```sql
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id BIGINT UNSIGNED NOT NULL,
  nome VARCHAR(150) NOT NULL,
  setor VARCHAR(100) NOT NULL,
  vinculo VARCHAR(100) NOT NULL,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
```

## 05. `solicitacao_passageiros`

**Finalidade:** Associação com PK composta entre viagem e cópia de passageiro.

**Origem:** `002_solicitacoes.sql`

Definição dos campos e restrições:

```sql
  solicitacao_id BIGINT UNSIGNED NOT NULL,
  passageiro_id BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (solicitacao_id, passageiro_id),
  FOREIGN KEY (solicitacao_id) REFERENCES solicitacoes(id),
  FOREIGN KEY (passageiro_id) REFERENCES passageiros(id)
```

## 06. `historico_solicitacoes`

**Finalidade:** Eventos de status, autor e data UTC. A criação inicial tem status_anterior nulo.

**Origem:** `002_solicitacoes.sql`

Definição dos campos e restrições:

```sql
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  solicitacao_id BIGINT UNSIGNED NOT NULL,
  usuario_id BIGINT UNSIGNED NOT NULL,
  status_anterior VARCHAR(20) NULL,
  status_novo VARCHAR(20) NOT NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (solicitacao_id) REFERENCES solicitacoes(id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
```

## 07. `cadastros_passageiros`

**Finalidade:** Catálogo privado reutilizável. cpf_ativo gerado permite unicidade só entre os ativos de um dono.

**Origem:** `003_completar_fluxos.sql`

Definição dos campos e restrições:

```sql
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id BIGINT UNSIGNED NOT NULL,
  nome VARCHAR(150) NOT NULL,
  cpf CHAR(11) NOT NULL,
  telefone VARCHAR(30) NOT NULL,
  setor VARCHAR(100) NOT NULL,
  vinculo VARCHAR(100) NOT NULL,
  ativo TINYINT(1) NOT NULL DEFAULT 1,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  cpf_ativo CHAR(11) GENERATED ALWAYS AS (CASE WHEN ativo=1 THEN cpf ELSE NULL END) STORED,
  UNIQUE KEY passageiros_cpf_usuario (usuario_id, cpf_ativo),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
```

## 08. `atendimentos_solicitacoes`

**Finalidade:** Extensão opcional 1:1 do pedido; registra veículo, motorista e motivo de cancelamento.

**Origem:** `003_completar_fluxos.sql`

Definição dos campos e restrições:

```sql
  solicitacao_id BIGINT UNSIGNED PRIMARY KEY,
  veiculo VARCHAR(150) NULL,
  motorista VARCHAR(150) NULL,
  motivo_cancelamento VARCHAR(2000) NULL,
  FOREIGN KEY (solicitacao_id) REFERENCES solicitacoes(id)
```

## 09. `observacoes_historico`

**Finalidade:** Extensão opcional 1:1 do evento; registra observação, designação ou motivo.

**Origem:** `003_completar_fluxos.sql`

Definição dos campos e restrições:

```sql
  historico_id BIGINT UNSIGNED PRIMARY KEY,
  observacao VARCHAR(2400) NOT NULL,
  FOREIGN KEY (historico_id) REFERENCES historico_solicitacoes(id)
```

## 10. `recuperacoes_senha`

**Finalidade:** Hash de token, assinatura da senha, expiração e uso. O token bruto não é armazenado aqui.

**Origem:** `003_completar_fluxos.sql`

Definição dos campos e restrições:

```sql
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id BIGINT UNSIGNED NOT NULL,
  hash_token CHAR(64) NOT NULL,
  assinatura_senha CHAR(64) NOT NULL,
  expira_em DATETIME NOT NULL,
  usado_em DATETIME NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY recuperacoes_token (hash_token),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
```

## 11. `tentativas_recuperacao`

**Finalidade:** Limites da recuperação, sem vínculo direto a uma conta.

**Origem:** `003_completar_fluxos.sql`

Definição dos campos e restrições:

```sql
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  chave_email CHAR(64) NOT NULL,
  chave_ip CHAR(64) NOT NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX recuperacao_email_data (chave_email, criado_em),
  INDEX recuperacao_ip_data (chave_ip, criado_em)
```

## 12. `migracoes_aplicadas`

**Finalidade:** Ledger de estrutura: nome da migração, SHA-256 e data de aplicação.

**Origem:** `comandos/migrar.php`

Definição dos campos e restrições:

```sql
  nome VARCHAR(190) PRIMARY KEY,
  resumo CHAR(64) NOT NULL,
  aplicada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
```

## Relações e ciclo de vida

usuarios 1:N solicitacoes, passageiros, cadastros_passageiros, historico_solicitacoes e recuperacoes_senha.
solicitacoes 1:N historico_solicitacoes e solicitacao_passageiros.
passageiros 1:N solicitacao_passageiros (a aplicação cria uma cópia por viagem).
solicitacoes 1:0..1 atendimentos_solicitacoes; historico_solicitacoes 1:0..1 observacoes_historico.
Não há FK entre cadastros_passageiros e passageiros; a seleção é copiada no envio.
Tentativas e ledger não referenciam usuários por FK.

No fluxo da aplicação, todo pedido tem pelo menos um passageiro e um evento inicial.
Essas duas regras de quantidade são garantidas pela transação da aplicação, não por uma FK de contagem.
As contas são desativadas; a exclusão de catálogos marca ativo=0.
Senhas usam hash de password_hash. Os CHAR(64) usados nos controles são SHA-256, não valores de acesso.

## Índices e validação

Índices e restrições UNIQUE estão declarados acima. CPF e estados têm validação adicional no PHP.
Novas mudanças estruturais precisam de uma nova migração; regenere este documento e revise o diagrama 03.
