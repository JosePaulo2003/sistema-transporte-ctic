'use strict';

window.CTIC = {
    async requisitar(caminho, metodo = 'GET', dados) {
        const cabecalhos = {Accept: 'application/json'};
        if (metodo !== 'GET') {
            const resposta = await fetch('/api/autenticacao/csrf', {credentials: 'same-origin'});
            if (!resposta.ok) throw new Error('Não foi possível consultar a sessão.');
            cabecalhos['X-CSRF-Token'] = (await resposta.json()).csrf;
            cabecalhos['Content-Type'] = 'application/json';
        }
        const resposta = await fetch(caminho, {method: metodo, credentials: 'same-origin', headers: cabecalhos,
            body: dados === undefined ? undefined : JSON.stringify(dados)});
        let resultado;
        try { resultado = await resposta.json(); }
        catch { throw new Error('O servidor retornou uma resposta inválida. Confira o serviço PHP.'); }
        if (resposta.status === 401 && window.CTIC_USUARIO) window.location.replace('/entrar');
        if (!resposta.ok) throw new Error(resultado.erro || 'Não foi possível concluir a operação.');
        return resultado;
    },
    elemento(tipo, texto, classe) {
        const elemento = document.createElement(tipo);
        if (texto !== undefined) elemento.textContent = texto;
        if (classe) elemento.className = classe;
        return elemento;
    },
    avisar(erro, sucesso = false) {
        let aviso = document.getElementById('aviso-sistema');
        if (!aviso) {
            aviso = this.elemento('p'); aviso.id = 'aviso-sistema'; aviso.tabIndex = -1;
            (document.querySelector('main') || document.body).prepend(aviso);
        }
        aviso.textContent = erro.message || String(erro);
        aviso.className = sucesso ? 'aviso-sucesso' : 'erro-autenticacao';
        aviso.setAttribute('role', sucesso ? 'status' : 'alert');
        aviso.hidden = false; aviso.focus();
    },
    formulario(formulario, acao) {
        let executando = false;
        formulario.addEventListener('submit', async evento => {
            evento.preventDefault();
            if (executando || !formulario.reportValidity()) return;
            executando = true;
            const botoes = [...formulario.querySelectorAll('button')];
            botoes.forEach(botao => { botao.disabled = true; });
            try { await acao(); } catch (erro) { this.avisar(erro); }
            finally { executando = false; botoes.forEach(botao => { botao.disabled = false; }); }
        });
    },
    acao(botao, acao) {
        let executando = false;
        botao.addEventListener('click', async evento => {
            evento.preventDefault();
            if (executando) return;
            executando = true; botao.setAttribute('aria-disabled', 'true');
            try { await acao(); } catch (erro) { this.avisar(erro); }
            finally { executando = false; botao.removeAttribute('aria-disabled'); }
        });
    },
    data(valor, utc = false) {
        if (!valor) return 'Não informado';
        const data = new Date(valor.replace(' ', 'T') + (utc ? 'Z' : ''));
        return data.toLocaleString('pt-BR', {timeZone: 'America/Manaus', dateStyle: 'short', timeStyle: 'short'});
    },
};
