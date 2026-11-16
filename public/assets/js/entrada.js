'use strict';

const formularioEntrada = document.getElementById('formulario-entrada');
const botaoEntrar = document.getElementById('botao-entrar');
const erroEntrada = document.getElementById('erro-entrada');

formularioEntrada.addEventListener('submit', async evento => {
    evento.preventDefault();
    botaoEntrar.disabled = true;
    botaoEntrar.textContent = 'Entrando…';
    erroEntrada.hidden = true;
    try {
        const resposta = await fetch('/api/autenticacao/entrar', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': document.getElementById('token-csrf').value,
            },
            body: JSON.stringify({
                email: document.getElementById('email').value.trim(),
                senha: document.getElementById('senha').value,
            }),
        });
        const dados = await resposta.json();
        if (!resposta.ok) {
            // Eu renovo o token perdido para não mandar a pessoa recarregar a tela e depois me abrir um chamado.
            if (resposta.status === 419) {
                const respostaToken = await fetch('/api/autenticacao/csrf');
                if (respostaToken.ok) {
                    const dadosToken = await respostaToken.json();
                    document.getElementById('token-csrf').value = dadosToken.csrf;
                }
            }
            throw new Error(dados.erro || 'Não foi possível entrar.');
        }
        // Eu uso a identidade do servidor e limpo a demonstração antiga para não perseguir nome errado pelo mesmo salário.
        localStorage.removeItem('nomeLogado');
        localStorage.removeItem('iniciaisLogado');
        window.location.assign('/painel');
    } catch (erro) {
        erroEntrada.textContent = erro instanceof TypeError
            ? 'Não foi possível conectar ao servidor. Tente novamente.' : erro.message;
        erroEntrada.hidden = false;
    } finally {
        document.getElementById('senha').value = '';
        botaoEntrar.disabled = false;
        botaoEntrar.textContent = 'Entrar';
    }
});
