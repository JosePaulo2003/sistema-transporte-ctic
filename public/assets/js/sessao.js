 'use strict';
async function encerrarAcesso() {
    await CTIC.requisitar('/api/autenticacao/sair', 'POST');
    window.location.replace('/entrar');
}
const usuarioSessao = window.CTIC_USUARIO;
const iniciaisSessao = usuarioSessao.nome.trim().split(/\s+/).map(parte => parte[0]).slice(0, 2).join('').toUpperCase();
for (const identificador of ['nome-usuario','nome-conta']) {
    const elemento = document.getElementById(identificador);
    if (elemento) elemento.textContent = usuarioSessao.nome;
}
for (const identificador of ['avatar-usuario','avatar-grande']) {
    const elemento = document.getElementById(identificador);
    if (elemento) elemento.textContent = iniciaisSessao;
}
for (const seletor of ['.dados-usuario span','#setor-conta']) {
    const elemento = document.querySelector(seletor);
    if (elemento) elemento.textContent = usuarioSessao.setor;
}
const emailConta = document.getElementById('email-conta');
if (emailConta) emailConta.textContent = usuarioSessao.email;
for (const identificador of ['ctic-sair','confirmar-saida']) {
    const botao = document.getElementById(identificador);
    if (botao) CTIC.acao(botao, encerrarAcesso);
}
let verificandoSessao = false;
async function verificarSessao() {
    if (verificandoSessao || document.hidden) return;
    verificandoSessao = true;
    try {
        const resposta = await fetch('/api/autenticacao/usuario', {credentials: 'same-origin'});
        if (resposta.status === 401) window.location.replace('/entrar');
    } catch {
        // Eu preservo a tela se a rede cair: reconectar já dá trabalho suficiente pelo mesmo salário.
    } finally { verificandoSessao = false; }
}
document.addEventListener('visibilitychange', verificarSessao);
window.addEventListener('pageshow', verificarSessao);
