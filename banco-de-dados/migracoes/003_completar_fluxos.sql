-- Eu separo o cadastro reutilizável dos passageiros da viagem, porque refazer histórico não cabe no salário.
CREATE TABLE IF NOT EXISTS cadastros_passageiros (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE solicitacoes MODIFY COLUMN status ENUM('pendente','analise','aprovada','recusada','concluida','cancelada') NOT NULL DEFAULT 'pendente';

CREATE TABLE IF NOT EXISTS atendimentos_solicitacoes (
 solicitacao_id BIGINT UNSIGNED PRIMARY KEY,
 veiculo VARCHAR(150) NULL,
 motorista VARCHAR(150) NULL,
 motivo_cancelamento VARCHAR(2000) NULL,
 FOREIGN KEY (solicitacao_id) REFERENCES solicitacoes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS observacoes_historico (
 historico_id BIGINT UNSIGNED PRIMARY KEY,
 observacao VARCHAR(2400) NOT NULL,
 FOREIGN KEY (historico_id) REFERENCES historico_solicitacoes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recuperacoes_senha (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 usuario_id BIGINT UNSIGNED NOT NULL,
 hash_token CHAR(64) NOT NULL,
 assinatura_senha CHAR(64) NOT NULL,
 expira_em DATETIME NOT NULL,
 usado_em DATETIME NULL,
 criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY recuperacoes_token (hash_token),
 FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tentativas_recuperacao (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 chave_email CHAR(64) NOT NULL,
 chave_ip CHAR(64) NOT NULL,
 criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 INDEX recuperacao_email_data (chave_email, criado_em),
 INDEX recuperacao_ip_data (chave_ip, criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
