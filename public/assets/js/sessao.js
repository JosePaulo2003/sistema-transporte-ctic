'use strict';

// Confere a sessão ao retornar à aba, inclusive se outra aba já tiver encerrado o acesso.
let verificandoSessao = false;
async function verificarSessao() {
    if (verificandoSessao || document.hidden) return;
    verificandoSessao = true;
    try {
        const resposta = await fetch('/api/autenticacao/usuario', {credentials: 'same-origin'});
        if (resposta.status === 401) window.location.replace('/entrar');
    } catch {
        // Uma falha de rede não significa que a sessão tenha sido encerrada.
    } finally {
        verificandoSessao = false;
    }
}

document.addEventListener('visibilitychange', verificarSessao);
window.addEventListener('pageshow', verificarSessao);

const botaoSair = document.getElementById('ctic-sair');
botaoSair.addEventListener('click', async () => {
    botaoSair.disabled = true;
    try {
        const respostaToken = await fetch('/api/autenticacao/csrf', {credentials: 'same-origin'});
        if (!respostaToken.ok) throw new Error('Não foi possível consultar a sessão.');
        const dadosToken = await respostaToken.json();
        const resposta = await fetch('/api/autenticacao/sair', {
            method: 'POST', credentials: 'same-origin',
            headers: {'X-CSRF-Token': dadosToken.csrf},
        });
        if (!resposta.ok && resposta.status !== 401) throw new Error('Não foi possível encerrar a sessão.');
        localStorage.removeItem('nomeLogado');
        localStorage.removeItem('iniciaisLogado');
        window.location.replace('/entrar');
    } catch (erro) {
        alert(erro.message || 'Falha de conexão. Tente sair novamente.');
        botaoSair.disabled = false;
    }
});

// Atualiza o setor com o cadastro real, sem alterar a estrutura visual do cabeçalho.
const setorUsuario = document.querySelector('.dados-usuario span');
if (setorUsuario) setorUsuario.textContent = window.CTIC_USUARIO.setor;
