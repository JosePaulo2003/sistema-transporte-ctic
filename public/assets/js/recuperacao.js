'use strict';

const formularioRecuperacao = document.getElementById('form-recuperar');
if (formularioRecuperacao) CTIC.formulario(formularioRecuperacao, async () => {
    await CTIC.requisitar('/api/autenticacao/recuperar', 'POST', {email: document.getElementById('email').value.trim()});
    window.location.assign('/confirmar-email');
});
const formularioRedefinicao = document.getElementById('form-redefinir');
if (formularioRedefinicao) {
    // Eu tiro o token do endereço depois de ler: já basta lembrar senha para justificar o salário.
    const token = new URLSearchParams(window.location.hash.slice(1)).get('token');
    window.history.replaceState(null, '', window.location.pathname);
    if (!token) CTIC.avisar('Abra o link de recuperação recebido para redefinir sua senha.');
    CTIC.formulario(formularioRedefinicao, async () => {
        if (!token) throw new Error('Link de recuperação ausente. Solicite um novo link.');
        await CTIC.requisitar('/api/autenticacao/redefinir', 'POST', {token,
            senha: document.getElementById('nova-senha').value, confirmacao_senha: document.getElementById('confirmacao-senha').value});
        window.location.assign('/entrar');
    });
}
