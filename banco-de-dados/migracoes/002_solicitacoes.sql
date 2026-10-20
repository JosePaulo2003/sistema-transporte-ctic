-- Datas de viagem representam o horário local de Manaus informado no formulário.
CREATE TABLE IF NOT EXISTS solicitacoes (
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
 status ENUM('pendente','analise','aprovada','recusada','concluida') NOT NULL DEFAULT 'pendente',
 criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
 INDEX solicitacoes_usuario_data (usuario_id, criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
-- Passageiros pertencem ao responsável que os cadastrou, sem catálogo público de pessoas.
CREATE TABLE IF NOT EXISTS passageiros (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 usuario_id BIGINT UNSIGNED NOT NULL,
 nome VARCHAR(150) NOT NULL,
 setor VARCHAR(100) NOT NULL,
 vinculo VARCHAR(100) NOT NULL,
 FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS solicitacao_passageiros (
 solicitacao_id BIGINT UNSIGNED NOT NULL,
 passageiro_id BIGINT UNSIGNED NOT NULL,
 PRIMARY KEY (solicitacao_id, passageiro_id),
 FOREIGN KEY (solicitacao_id) REFERENCES solicitacoes(id),
 FOREIGN KEY (passageiro_id) REFERENCES passageiros(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS historico_solicitacoes (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 solicitacao_id BIGINT UNSIGNED NOT NULL,
 usuario_id BIGINT UNSIGNED NOT NULL,
 status_anterior VARCHAR(20) NULL,
 status_novo VARCHAR(20) NOT NULL,
 criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (solicitacao_id) REFERENCES solicitacoes(id),
 FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
