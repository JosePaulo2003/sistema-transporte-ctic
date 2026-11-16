<?php
declare(strict_types=1);

function aplicar_migracoes(PDO $conexao): void
{
    // Eu registro as migrações para não repetir alteração de tabela toda vez que preciso ganhar meu salário.
    $nomeTrava = 'ctic_migracoes_' . substr(hash('sha256', (string)$conexao->query('SELECT DATABASE()')->fetchColumn()), 0, 30);
    $trava = $conexao->prepare('SELECT GET_LOCK(?,10)');
    $trava->execute([$nomeTrava]);
    if ((int)$trava->fetchColumn() !== 1) throw new RuntimeException('Outra preparação do banco está em andamento.');
    try {
        $conexao->exec('CREATE TABLE IF NOT EXISTS migracoes_aplicadas (nome VARCHAR(190) PRIMARY KEY, resumo CHAR(64) NOT NULL, aplicada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4');
        $arquivos = glob(RAIZ_PROJETO . '/banco-de-dados/migracoes/*.sql');
        sort($arquivos);
        foreach ($arquivos as $arquivo) {
            $nome = basename($arquivo);
            $conteudo = file_get_contents($arquivo);
            $resumo = hash('sha256', str_replace("\r\n", "\n", $conteudo));
            $consulta = $conexao->prepare('SELECT resumo FROM migracoes_aplicadas WHERE nome=?');
            $consulta->execute([$nome]);
            $aplicada = $consulta->fetchColumn();
            if ($aplicada !== false) {
                if (!hash_equals($aplicada, $resumo)) throw new RuntimeException('Uma migração já aplicada foi alterada: ' . $nome);
                continue;
            }
            // Eu aceito aqui os scripts SQL simples do projeto, sem procedimentos ou delimitadores próprios.
            $instrucoes = preg_replace('/^\s*--.*$/m', '', $conteudo);
            foreach (explode(';', $instrucoes) as $instrucao) if (trim($instrucao) !== '') $conexao->exec($instrucao);
            $consulta = $conexao->prepare('INSERT INTO migracoes_aplicadas (nome,resumo) VALUES (?,?)');
            $consulta->execute([$nome, $resumo]);
            echo 'Migração aplicada: ' . $nome . PHP_EOL;
        }
    } finally {
        $consulta = $conexao->prepare('SELECT RELEASE_LOCK(?)');
        $consulta->execute([$nomeTrava]);
    }
}
