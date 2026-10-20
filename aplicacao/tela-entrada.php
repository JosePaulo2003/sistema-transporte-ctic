<?php
// A sessão já foi iniciada pelo controlador; o token vincula o envio a este navegador.
$tokenFormulario = htmlspecialchars(token_csrf(), ENT_QUOTES, 'UTF-8');
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Entrar — Transportes CTIC</title>
    <link rel="stylesheet" href="/public/views/css/style.css">
    <link rel="stylesheet" href="/public/assets/autenticacao.css">
    <script src="/public/assets/js/entrada.js" defer></script>
</head>
<body>
    <aside class="background">
        <img src="/public/views/img/uea_new_logo_negativo_400.png" alt="Logo da UEA" class="logo">
        <h1>UEA</h1>
        <p>Universidade do Estado do Amazonas</p>
    </aside>
    <main class="container">
        <form id="formulario-entrada" action="/api/autenticacao/entrar" method="post">
            <h1>Bem-vindo(a)</h1>
            <p>Entre com suas credenciais do Sistema de Transportes.</p>
            <input type="hidden" id="token-csrf" value="<?= $tokenFormulario ?>">
            <div class="input-box">
                <label for="email">E-mail institucional</label>
                <input id="email" name="email" type="email" placeholder="nome@uea.edu.br" autocomplete="username" maxlength="254" required>
            </div>
            <div class="input-box">
                <label for="senha">Senha</label>
                <input id="senha" name="senha" type="password" placeholder="Digite sua senha" autocomplete="current-password" maxlength="1024" required>
            </div>
            <div id="erro-entrada" class="erro-autenticacao" role="alert" hidden></div>
            <button id="botao-entrar" type="submit">Entrar</button>
            <p>Acesso restrito a usuários autorizados.</p>
            <noscript>Habilite o JavaScript para entrar no sistema.</noscript>
        </form>
    </main>
</body>
</html>
