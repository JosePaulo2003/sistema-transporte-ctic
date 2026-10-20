'use strict';

// Toda persistência passa pelo servidor; nenhum dado de transporte é confiado ao localStorage.
const nomesStatus = {pendente: 'Pendente', analise: 'Em análise', aprovada: 'Aprovada', recusada: 'Recusada', concluida: 'Concluída'};
const usuarioTransporte = window.CTIC_USUARIO;
const paginaTransporte = window.location.pathname;
let passageirosRascunho = [];
let listaTransporte = [];

function elementoTransporte(tipo, texto, classe) {
    const elemento = document.createElement(tipo);
    if (texto !== undefined) elemento.textContent = texto;
    if (classe) elemento.className = classe;
    return elemento;
}

function avisarTransporte(erro) {
    const mensagem = document.getElementById('aviso-transporte');
    mensagem.textContent = erro.message || String(erro);
    mensagem.hidden = false;
    mensagem.focus();
}

async function consultarTransporte(caminho, metodo = 'GET', dados) {
    const cabecalhos = {};
    if (metodo !== 'GET') {
        const respostaToken = await fetch('/api/autenticacao/csrf', {credentials: 'same-origin'});
        if (!respostaToken.ok) throw new Error('Não foi possível validar a sessão.');
        cabecalhos['X-CSRF-Token'] = (await respostaToken.json()).csrf;
        cabecalhos['Content-Type'] = 'application/json';
    }
    const resposta = await fetch('/api/solicitacoes' + caminho, {
        method: metodo, credentials: 'same-origin', headers: cabecalhos,
        body: dados === undefined ? undefined : JSON.stringify(dados),
    });
    const resultado = await resposta.json();
    if (resposta.status === 401) window.location.replace('/entrar');
    if (!resposta.ok) throw new Error(resultado.erro || 'Não foi possível concluir a operação.');
    return resultado;
}

// Bloqueia cliques repetidos enquanto uma gravação está em andamento e preserva erros na tela.
function executarFormulario(formulario, acao) {
    formulario.addEventListener('submit', async evento => {
        evento.preventDefault();
        const botao = formulario.querySelector('[type="submit"]');
        botao.disabled = true;
        try { await acao(); } catch (erro) { avisarTransporte(erro); }
        finally { botao.disabled = false; }
    });
}

const camposViagem = {
    tipo_deslocamento: 'tipo-deslocamento', destino: 'destino', finalidade: 'finalidade',
    local_embarque: 'local-embarque', centro_custo: 'centro-custo', justificativa: 'justificativa',
};

function exibirPassageiros() {
    const lista = document.querySelector('.lista-passageiros');
    lista.replaceChildren();
    passageirosRascunho.forEach((pessoa, indice) => {
        const cartao = elementoTransporte('article', undefined, 'card-passageiro');
        cartao.append(elementoTransporte('strong', pessoa.nome), elementoTransporte('span', `${pessoa.setor} · ${pessoa.vinculo}`));
        const remover = elementoTransporte('button', 'Remover');
        remover.type = 'button';
        remover.addEventListener('click', () => { passageirosRascunho.splice(indice, 1); exibirPassageiros(); });
        cartao.append(remover);
        lista.append(cartao);
    });
    if (!passageirosRascunho.length) lista.append(elementoTransporte('p', 'Nenhum passageiro adicionado.'));
}

function preencherResumo(rascunho) {
    const viagem = rascunho.viagem;
    const contato = rascunho.contato;
    const listas = document.querySelectorAll('.lista-resumo');
    const grupos = [
        [viagem.tipo_deslocamento, viagem.destino, viagem.finalidade, `Saída: ${viagem.saida_em.replace('T', ' ')}`, `Retorno: ${viagem.retorno_em.replace('T', ' ')}`, `Embarque: ${viagem.local_embarque}`, `Centro de custo: ${viagem.centro_custo}`, viagem.justificativa],
        [usuarioTransporte.nome, usuarioTransporte.email, contato.telefone, contato.setor, contato.vinculo],
        rascunho.passageiros.map(pessoa => `${pessoa.nome} · ${pessoa.setor} · ${pessoa.vinculo}`),
    ];
    listas.forEach((lista, indice) => lista.replaceChildren(...grupos[indice].map(texto => elementoTransporte('li', texto))));
    document.querySelectorAll('.card-resumo h3')[2].textContent = `Passageiros (${rascunho.passageiros.length})`;
}

async function iniciarEtapas() {
    const {rascunho} = await consultarTransporte('/rascunho');
    if (paginaTransporte !== '/nova-solicitacao' && !rascunho.viagem) {
        window.location.replace('/nova-solicitacao'); return;
    }
    if (paginaTransporte === '/nova-solicitacao') {
        const viagem = rascunho.viagem || {};
        Object.entries(camposViagem).forEach(([campo, identificador]) => { document.getElementById(identificador).value = viagem[campo] || ''; });
        for (const tipo of ['saida', 'retorno']) {
            const [data = '', hora = ''] = (viagem[`${tipo}_em`] || '').split('T');
            document.getElementById(`data-${tipo}`).value = data;
            document.getElementById(`hora-${tipo}`).value = hora;
        }
        executarFormulario(document.getElementById('form-nova-solicitacao'), async () => {
            const viagem = {};
            Object.entries(camposViagem).forEach(([campo, identificador]) => { viagem[campo] = document.getElementById(identificador).value.trim(); });
            for (const tipo of ['saida', 'retorno']) viagem[`${tipo}_em`] = `${document.getElementById(`data-${tipo}`).value}T${document.getElementById(`hora-${tipo}`).value}`;
            await consultarTransporte('/rascunho', 'PUT', {viagem});
            window.location.assign('/solicitantes');
        });
    }
    if (paginaTransporte === '/solicitantes') {
        // A identidade do responsável vem do cadastro autenticado e não pode ser substituída no formulário.
        for (const [identificador, valor] of [['nome-completo', usuarioTransporte.nome], ['email-institucional', usuarioTransporte.email]]) {
            document.getElementById(identificador).value = valor;
            document.getElementById(identificador).readOnly = true;
        }
        for (const campo of ['telefone', 'setor', 'vinculo']) document.getElementById(campo).value = rascunho.contato?.[campo] || (campo === 'setor' ? usuarioTransporte.setor : '');
        executarFormulario(document.getElementById('form-solicitante'), async () => {
            const contato = {};
            for (const campo of ['telefone', 'setor', 'vinculo']) contato[campo] = document.getElementById(campo).value.trim();
            await consultarTransporte('/rascunho', 'PUT', {contato});
            window.location.assign('/passageiros');
        });
    }
    if (['/passageiros', '/revisao-envio'].includes(paginaTransporte) && !rascunho.contato) {
        window.location.replace('/solicitantes'); return;
    }
    if (paginaTransporte === '/passageiros') {
        passageirosRascunho = rascunho.passageiros || [];
        exibirPassageiros();
        executarFormulario(document.getElementById('form-passageiro'), async () => {
            if (passageirosRascunho.length >= 50) throw new Error('O limite é de 50 passageiros.');
            const pessoa = {};
            for (const campo of ['nome', 'setor', 'vinculo']) pessoa[campo] = document.getElementById(`passageiro-${campo}`).value.trim();
            if (Object.values(pessoa).some(valor => !valor)) throw new Error('Preencha todos os dados do passageiro.');
            passageirosRascunho.push(pessoa);
            document.getElementById('form-passageiro').reset();
            exibirPassageiros();
        });
        document.querySelector('.botoes-acao .btn-continuar').addEventListener('click', async evento => {
            evento.preventDefault();
            try {
                await consultarTransporte('/rascunho', 'PUT', {passageiros: passageirosRascunho});
                window.location.assign('/revisao-envio');
            } catch (erro) { avisarTransporte(erro); }
        });
    }
    if (paginaTransporte === '/revisao-envio') {
        if (!rascunho.passageiros?.length) { window.location.replace('/passageiros'); return; }
        preencherResumo(rascunho);
        const botao = document.getElementById('enviar-solicitacao');
        botao.addEventListener('click', async () => {
            const declaracao = document.getElementById('declaracao-normas');
            if (!declaracao.reportValidity()) return;
            botao.disabled = true;
            try {
                await consultarTransporte('', 'POST', {declaracao: true});
                window.location.assign('/solicitacoes?enviada=1');
            } catch (erro) { avisarTransporte(erro); botao.disabled = false; }
        });
    }
}

async function mostrarDetalhes(id) {
    const {solicitacao} = await consultarTransporte(`/${id}`);
    let painel = document.getElementById('detalhes-solicitacao');
    if (!painel) {
        painel = elementoTransporte('section'); painel.id = 'detalhes-solicitacao';
        document.querySelector('main').append(painel);
    }
    painel.replaceChildren(elementoTransporte('h2', `Solicitação #${solicitacao.id}`));
    for (const [campo, titulo] of Object.entries({nome:'Responsável', email:'E-mail', tipo_deslocamento:'Tipo de deslocamento',destino:'Destino',finalidade:'Finalidade',saida_em:'Saída',retorno_em:'Retorno',local_embarque:'Embarque',centro_custo:'Centro de custo',justificativa:'Justificativa',telefone:'Telefone',setor:'Setor',vinculo:'Vínculo'})) {
        painel.append(elementoTransporte('p', `${titulo}: ${solicitacao[campo]}`));
    }
    painel.append(elementoTransporte('h3', 'Passageiros'));
    solicitacao.passageiros.forEach(pessoa => painel.append(elementoTransporte('p', `${pessoa.nome} · ${pessoa.setor} · ${pessoa.vinculo}`)));
    painel.append(elementoTransporte('h3', 'Histórico (horários em UTC)'));
    solicitacao.historico.forEach(item => painel.append(elementoTransporte('p', `${item.criado_em} · ${item.nome} · ${nomesStatus[item.status_novo]}`)));
    painel.scrollIntoView({behavior: 'smooth'});
}

// Usa textContent para exibir também nomes e destinos sem interpretar HTML recebido do banco.
// A própria etiqueta abre as ações, preservando o visual sem duplicar o status em um select nativo.
function fecharMenusStatus() {
    document.querySelectorAll('.status-container').forEach(recipiente => {
        const menu = recipiente.querySelector('.menu-interativo');
        const botao = recipiente.querySelector('button.tag-status');
        if (menu) menu.hidden = true;
        if (botao) botao.setAttribute('aria-expanded', 'false');
    });
}

document.addEventListener('click', evento => {
    if (!evento.target.closest('.status-container')) fecharMenusStatus();
});
document.addEventListener('keydown', evento => {
    if (evento.key === 'Escape') {
        const botao = document.querySelector('.status-container button[aria-expanded="true"]');
        fecharMenusStatus();
        if (botao) botao.focus();
    }
});

function controleStatus(item) {
    const recipiente = elementoTransporte('div', undefined, 'status-container');
    const administrador = usuarioTransporte.perfil === 'administrador';
    const etiqueta = elementoTransporte(administrador ? 'button' : 'span',
        nomesStatus[item.status] + (administrador ? ' ▾' : ''), `tag-status status-${item.status}`);
    recipiente.append(etiqueta);
    if (administrador) {
        etiqueta.type = 'button';
        etiqueta.setAttribute('aria-expanded', 'false');
        etiqueta.setAttribute('aria-label', `Alterar status da solicitação ${item.id}: ${nomesStatus[item.status]}`);
        const menu = elementoTransporte('div', undefined, 'menu-interativo');
        menu.hidden = true;
        etiqueta.addEventListener('click', () => {
            const abrir = menu.hidden;
            fecharMenusStatus();
            menu.hidden = !abrir;
            etiqueta.setAttribute('aria-expanded', String(abrir));
        });
        Object.entries(nomesStatus).forEach(([valor, nome]) => {
            if (valor === item.status) return;
            const opcao = elementoTransporte('button', nome);
            opcao.type = 'button';
            opcao.addEventListener('click', async () => {
                fecharMenusStatus();
                etiqueta.disabled = true;
                try {
                    await consultarTransporte(`/${item.id}/status`, 'PATCH', {status: valor});
                    await carregarLista();
                } catch (erro) { avisarTransporte(erro); }
                finally { etiqueta.disabled = false; }
            });
            menu.append(opcao);
        });
        recipiente.append(menu);
    }
    return recipiente;
}

function renderizarTransporte() {
    const painel = paginaTransporte === '/painel';
    const termo = document.getElementById('input-busca')?.value.toLocaleLowerCase() || '';
    const status = document.getElementById('filtro-status')?.value || '';
    const dias = Number(document.getElementById('filtro-periodo')?.value || 0);
    let dados = listaTransporte.filter(item =>
        `${item.id} ${item.nome} ${item.destino}`.toLocaleLowerCase().includes(termo)
        && (!status || item.status === status)
        && (!dias || Date.now() - new Date(item.criado_em.replace(' ', 'T') + 'Z').getTime() <= dias * 86400000));
    if (painel) {
        for (const [identificador, quantidade] of Object.entries({
            'stat-abertas': listaTransporte.filter(item => ['pendente','analise','aprovada'].includes(item.status)).length,
            'stat-aguardando': listaTransporte.filter(item => ['pendente','analise'].includes(item.status)).length,
            'stat-aprovadas': listaTransporte.filter(item => item.status === 'aprovada').length,
        })) document.getElementById(identificador).textContent = quantidade;
        dados = dados.slice(0, 5);
    } else document.getElementById('contador-registros').textContent = `${dados.length} registros`;
    const tabela = document.getElementById(painel ? 'tabela-recente-corpo' : 'tabela-corpo');
    const cartoes = document.getElementById(painel ? 'cards-recente-mobile' : 'cards-mobile-corpo');
    tabela.replaceChildren(); cartoes.replaceChildren();
    dados.forEach(item => {
        const linha = elementoTransporte('tr');
        const codigo = elementoTransporte('td');
        const botao = elementoTransporte('button', `#${item.id}`, 'link-solicitacao');
        botao.type = 'button'; botao.addEventListener('click', () => mostrarDetalhes(item.id).catch(avisarTransporte));
        codigo.append(botao); linha.append(codigo);
        for (const valor of [item.nome, item.destino, item.saida_em.slice(0, 16)]) linha.append(elementoTransporte('td', valor));
        const celulaStatus = elementoTransporte('td'); celulaStatus.append(controleStatus(item)); linha.append(celulaStatus);
        tabela.append(linha);
        const cartao = elementoTransporte('article', undefined, 'card-solicitacao-item');
        const detalhes = elementoTransporte('button', `#${item.id} · ${item.nome}`, 'link-solicitacao');
        detalhes.type = 'button'; detalhes.addEventListener('click', () => mostrarDetalhes(item.id).catch(avisarTransporte));
        cartao.append(detalhes, elementoTransporte('p', item.destino), controleStatus(item)); cartoes.append(cartao);
    });
    if (!dados.length) {
        const linha = elementoTransporte('tr'); const celula = elementoTransporte('td', 'Nenhuma solicitação encontrada.');
        celula.colSpan = 5; linha.append(celula); tabela.append(linha);
        cartoes.append(elementoTransporte('p', 'Nenhuma solicitação encontrada.'));
    }
}

async function carregarLista() {
    listaTransporte = (await consultarTransporte('')).solicitacoes;
    renderizarTransporte();
}

async function iniciarTransporte() {
    const aviso = elementoTransporte('p'); aviso.id = 'aviso-transporte'; aviso.hidden = true;
    aviso.setAttribute('role', 'alert'); aviso.tabIndex = -1; document.querySelector('main').prepend(aviso);
    const nome = document.getElementById('nome-usuario');
    if (nome) nome.textContent = usuarioTransporte.nome;
    const avatar = document.getElementById('avatar-usuario');
    if (avatar) avatar.textContent = usuarioTransporte.nome.trim().split(/\s+/).map(parte => parte[0]).slice(0,2).join('').toUpperCase();
    if (['/painel', '/solicitacoes'].includes(paginaTransporte)) {
        await carregarLista();
        for (const identificador of ['input-busca','filtro-status','filtro-periodo']) document.getElementById(identificador)?.addEventListener('input', renderizarTransporte);
        if (new URLSearchParams(window.location.search).get('enviada') === '1') document.getElementById('mensagem-sucesso').style.display = '';
    } else await iniciarEtapas();
}
iniciarTransporte().catch(avisarTransporte);
