-- Estrutura inicial de autenticação: usuários autorizados e controle de tentativas.
-- As senhas devem ser armazenadas como hash, nunca como texto puro.

CREATE TABLE IF NOT EXISTS usuarios (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tentativas_acesso (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    chave_email CHAR(64) NOT NULL,
    chave_ip CHAR(64) NOT NULL,
    tentativa_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX tentativas_email_data (chave_email, tentativa_em),
    INDEX tentativas_ip_data (chave_ip, tentativa_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
