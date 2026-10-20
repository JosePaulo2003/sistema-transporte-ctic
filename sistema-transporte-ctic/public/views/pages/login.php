<?php
session_start();
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login</title>
    <link rel="stylesheet" href="/public/views/css/login.css">
</head>
<body>
    <div class="flexbox-login">
        <!-- Coluna verde à esquerda. -->
        <aside class="grade-flexbox-login">
            <img src="/public/assets/images/Logo-uea-branco.svg" alt="Logo da Universidade do Estado do Amazonas">
            <small>Universidade do Estado do Amazonas</small>
        </aside>

        <!-- Área branca com o formulário centralizado. -->
        <main class="area-login">
            <form class="caixa-login" method="post">
                <h1>Bem-vindo(a)</h1>
                <p>Entre com suas credenciais institucionais.</p>

                <label for="email">E-mail institucional</label>
                <input id="email" name="email" type="email"
                       placeholder="nome@uea.edu.br" autocomplete="username" required>

                <label for="senha">Senha</label>
                <input id="senha" name="senha" type="password"
                       placeholder="Digite sua senha" autocomplete="current-password" required>

                <div class="opcoes-login">
                    <label class="lembrar-acesso">
                        <input type="checkbox" name="lembrar">
                        Lembrar acesso
                    </label>
                    <!-- Habilitar quando existir uma página de recuperação. -->
                    <button class="recuperar-senha" type="button" disabled>Esqueci minha senha</button>
                </div>

                <!-- Habilitar após implementar a autenticação no PHP. -->
                <button class="botao-entrar" type="submit" disabled>Entrar</button>
                <small class="aviso">Acesso restrito a usuários autorizados.</small>
            </form>
        </main>
    </div>
</body>
</html>
