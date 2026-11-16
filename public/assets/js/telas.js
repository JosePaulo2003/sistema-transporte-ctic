'use strict';

const pagina = window.location.pathname;
const parametros = new URLSearchParams(window.location.search);
const usuarioAtual = window.CTIC_USUARIO;
const estados = {pendente:'Pendente', analise:'Em análise', aprovada:'Aprovada', recusada:'Recusada', concluida:'Concluída', cancelada:'Cancelada'};
const criar = (tipo, texto, classe) => CTIC.elemento(tipo, texto, classe);
const consultar = (caminho, metodo = 'GET', dados) => CTIC.requisitar('/api/solicitacoes' + caminho, metodo, dados);
const valor = identificador => document.getElementById(identificador).value.trim();
const camposViagem = {tipo_deslocamento:'tipo-deslocamento', destino:'destino', finalidade:'finalidade',
    local_embarque:'local-embarque', centro_custo:'centro-custo', justificativa:'justificativa'};

function identificadorUrl() {
    const texto = parametros.get('id');
    if (!texto || !/^[1-9][0-9]*$/.test(texto) || !Number.isSafeInteger(Number(texto))) {
        throw new Error('Selecione um registro na listagem para abrir esta tela.');
    }
    return Number(texto);
}

function preencherTextos(recipiente, textos) {
    recipiente.replaceChildren(...textos.map(texto => criar('p', texto)));
}

async function iniciarViagem() {
    const {rascunho} = await consultar('/rascunho');
    if (pagina !== '/nova-solicitacao' && !rascunho.viagem) { window.location.replace('/nova-solicitacao'); return; }
    if (pagina === '/nova-solicitacao') {
        const viagem = rascunho.viagem || {};
        for (const [campo, identificador] of Object.entries(camposViagem)) document.getElementById(identificador).value = viagem[campo] || '';
        for (const tipo of ['saida','retorno']) {
            const [data = '', hora = ''] = (viagem[`${tipo}_em`] || '').split('T');
            document.getElementById(`data-${tipo}`).value = data;
            document.getElementById(`hora-${tipo}`).value = hora;
        }
        CTIC.formulario(document.getElementById('form-nova-solicitacao'), async () => {
            const viagem = Object.fromEntries(Object.entries(camposViagem).map(([campo, identificador]) => [campo, valor(identificador)]));
            for (const tipo of ['saida','retorno']) viagem[`${tipo}_em`] = `${valor(`data-${tipo}`)}T${valor(`hora-${tipo}`)}`;
            await consultar('/rascunho', 'PUT', {viagem});
            window.location.assign('/solicitantes');
        });
    }
    if (pagina === '/solicitantes') {
        for (const [identificador, conteudo] of [['nome-completo', usuarioAtual.nome], ['email-institucional', usuarioAtual.email]]) {
            const campo = document.getElementById(identificador); campo.value = conteudo; campo.readOnly = true;
        }
        for (const campo of ['telefone','setor','vinculo']) document.getElementById(campo).value = rascunho.contato?.[campo] || (campo === 'setor' ? usuarioAtual.setor : '');
        CTIC.formulario(document.getElementById('form-solicitante'), async () => {
            const contato = Object.fromEntries(['telefone','setor','vinculo'].map(campo => [campo, valor(campo)]));
            await consultar('/rascunho', 'PUT', {contato});
            window.location.assign('/passageiros');
        });
    }
    if (['/passageiros','/revisao-envio'].includes(pagina) && !rascunho.contato) { window.location.replace('/solicitantes'); return; }
    if (pagina === '/passageiros') await selecionarPassageiros(rascunho);
    if (pagina === '/revisao-envio') {
        if (!rascunho.passageiros?.length) { window.location.replace('/passageiros'); return; }
        const viagem = rascunho.viagem;
        const contato = rascunho.contato;
        const resumos = [
            [`Tipo: ${viagem.tipo_deslocamento}`, `Destino: ${viagem.destino}`, `Finalidade: ${viagem.finalidade}`,
                `Saída: ${CTIC.data(viagem.saida_em)}`, `Retorno: ${CTIC.data(viagem.retorno_em)}`, `Embarque: ${viagem.local_embarque}`,
                `Centro de custo: ${viagem.centro_custo}`, `Justificativa: ${viagem.justificativa}`],
            [usuarioAtual.nome, usuarioAtual.email, contato.telefone, contato.setor, contato.vinculo],
            rascunho.passageiros.map(pessoa => `${pessoa.nome} · ${pessoa.setor} · ${pessoa.vinculo}`),
        ];
        document.querySelectorAll('.lista-resumo').forEach((lista, indice) => preencherTextos(lista, resumos[indice]));
        document.querySelectorAll('.card-resumo h3')[2].textContent = `Passageiros (${rascunho.passageiros.length})`;
        const declaracao = document.getElementById('declaracao-normas');
        const botao = document.getElementById('btn-enviar');
        declaracao.addEventListener('change', () => { botao.disabled = !declaracao.checked; });
        let enviando = false;
        CTIC.acao(botao, async () => {
            if (enviando || !declaracao.checked) return;
            enviando = true; botao.disabled = true;
            try {
                const pedido = await consultar('', 'POST', {declaracao: true});
                window.location.assign(`/solicitacao-enviada?id=${pedido.id}`);
            } finally { enviando = false; botao.disabled = !declaracao.checked; }
        });
    }
}

async function selecionarPassageiros(rascunho) {
    const {passageiros} = await CTIC.requisitar('/api/passageiros');
    const selecionados = new Set((rascunho.passageiros || []).map(pessoa => Number(pessoa.cadastro_id)));
    const lista = document.getElementById('lista-passageiros');
    lista.replaceChildren();
    document.querySelector('.btn-adicionar-passageiro').href = '/adicionar-passageiro?origem=viagem';
    for (const pessoa of passageiros) {
        const rotulo = criar('label', undefined, 'passageiro-selecionavel');
        const opcao = criar('input'); opcao.type = 'checkbox'; opcao.value = pessoa.id;
        opcao.checked = selecionados.has(Number(pessoa.id)); opcao.name = 'passageiros';
        const dados = criar('div', undefined, 'dados-passageiro');
        dados.append(criar('strong', pessoa.nome), criar('span', `${pessoa.setor} · ${pessoa.vinculo}`));
        rotulo.append(opcao, dados); lista.append(rotulo);
    }
    if (!passageiros.length) lista.append(criar('p', 'Cadastre um passageiro para selecionar nesta viagem.'));
    const escolhidos = () => [...lista.querySelectorAll('input:checked')].map(campo => Number(campo.value));
    // Eu enfileiro a gravação para que um clique atrasado não desfaça o anterior: já basta trabalhar pelo salário.
    let gravacao = Promise.resolve();
    lista.addEventListener('change', () => {
        const passageiros_ids = escolhidos();
        gravacao = gravacao.catch(() => {}).then(() => consultar('/rascunho', 'PUT', {passageiros_ids}));
        gravacao.catch(erro => CTIC.avisar(erro));
    });
    CTIC.acao(document.querySelector('.botoes-acao .btn-continuar'), async () => {
        await gravacao;
        const passageiros_ids = escolhidos();
        if (!passageiros_ids.length) throw new Error('Selecione ao menos um passageiro.');
        await consultar('/rascunho', 'PUT', {passageiros_ids});
        window.location.assign('/revisao-envio');
    });
}

async function iniciarCadastroPassageiro() {
    const edicao = pagina === '/editar-passageiro';
    const identificador = edicao ? identificadorUrl() : null;
    if (edicao) {
        const {passageiro} = await CTIC.requisitar(`/api/passageiros/${identificador}`);
        for (const [campo, seletor] of Object.entries({nome:'nome-completo', cpf:'cpf', telefone:'telefone', setor:'setor', vinculo:'vinculo'})) {
            const entrada = document.getElementById(seletor);
            if (entrada.tagName === 'SELECT' && ![...entrada.options].some(opcao => opcao.value === passageiro[campo])) entrada.add(new Option(passageiro[campo], passageiro[campo]));
            entrada.value = passageiro[campo];
        }
        CTIC.acao(document.getElementById('remover-passageiro'), async () => {
            if (!window.confirm('Remover este passageiro do cadastro? Os pedidos anteriores serão preservados.')) return;
            await CTIC.requisitar(`/api/passageiros/${identificador}`, 'DELETE');
            window.location.assign('/passageiro-removido');
        });
    }
    document.getElementById('cpf').addEventListener('input', evento => {
        evento.target.value = evento.target.value.replace(/\D/g, '').slice(0, 11).replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    });
    CTIC.formulario(document.getElementById(edicao ? 'form-edicao' : 'form-passageiro'), async () => {
        const cadastro = {nome: valor('nome-completo'), cpf: valor('cpf'), telefone: valor('telefone'), setor: valor('setor'), vinculo: valor('vinculo')};
        const resposta = await CTIC.requisitar('/api/passageiros' + (edicao ? `/${identificador}` : ''), edicao ? 'PUT' : 'POST', cadastro);
        if (parametros.get('origem') === 'viagem') {
            const {rascunho} = await consultar('/rascunho');
            const passageiros_ids = [...new Set([...(rascunho.passageiros || []).map(pessoa => Number(pessoa.cadastro_id)).filter(Number.isSafeInteger), resposta.id])];
            await consultar('/rascunho', 'PUT', {passageiros_ids});
        }
        window.location.assign(`/passageiro-salvo?id=${resposta.id}${parametros.get('origem') === 'viagem' ? '&origem=viagem' : ''}`);
    });
}

async function listarPassageiros() {
    const {passageiros} = await CTIC.requisitar('/api/passageiros');
    const busca = document.getElementById('busca-passageiro');
    busca.value = parametros.get('busca') || '';
    const renderizar = () => {
        const lista = document.getElementById('lista-passageiros'); lista.replaceChildren();
        const termo = busca.value.trim().toLocaleLowerCase('pt-BR');
        const filtrados = passageiros.filter(pessoa => `${pessoa.nome} ${pessoa.cpf} ${pessoa.setor}`.toLocaleLowerCase('pt-BR').includes(termo)
            || (termo.replace(/\D/g, '').length >= 3 && pessoa.cpf.includes(termo.replace(/\D/g, ''))));
        for (const pessoa of filtrados) {
            const item = criar('article', undefined, 'item-passageiro');
            const avatar = criar('div', pessoa.nome.split(/\s+/).map(parte => parte[0]).slice(0,2).join(''), 'avatar-passageiro');
            const dados = criar('div', undefined, 'dados-passageiro');
            dados.append(criar('strong', pessoa.nome), criar('span', `${pessoa.vinculo} · ${pessoa.setor}`));
            const editar = criar('a', 'Editar', 'link-solicitacao'); editar.href = `/editar-passageiro?id=${pessoa.id}`;
            item.append(avatar, dados, editar); lista.append(item);
        }
        document.getElementById('mensagem-vazia').hidden = filtrados.length !== 0;
    };
    busca.addEventListener('input', renderizar); renderizar();
}

async function listarSolicitacoes() {
    const painel = pagina === '/painel';
    const filtrada = pagina === '/solicitacoes-filtradas';
    const campos = {busca:'input-busca', status:'filtro-status', periodo:'filtro-periodo'};
    for (const [campo, identificador] of Object.entries(campos)) {
        const entrada = document.getElementById(identificador);
        if (entrada) entrada.value = parametros.get(campo) || '';
    }
    let sequencia = 0;
    const carregar = async () => {
        const atual = ++sequencia;
        const filtros = filtrada ? new URLSearchParams(parametros) : new URLSearchParams();
        if (!filtrada) for (const [campo, identificador] of Object.entries(campos)) {
            const entrada = document.getElementById(identificador);
            if (entrada?.value) filtros.set(campo, entrada.value);
        }
        const {solicitacoes} = await consultar('?' + filtros);
        if (atual !== sequencia) return;
        if (painel) {
            document.getElementById('stat-abertas').textContent = solicitacoes.filter(item => ['pendente','analise','aprovada'].includes(item.status)).length;
            document.getElementById('stat-aguardando').textContent = solicitacoes.filter(item => ['pendente','analise'].includes(item.status)).length;
            document.getElementById('stat-aprovadas').textContent = solicitacoes.filter(item => item.status === 'aprovada').length;
        }
        const dados = painel ? solicitacoes.slice(0,5) : solicitacoes;
        const tabela = document.getElementById(painel ? 'tabela-recente-corpo' : 'tabela-corpo');
        const cartoes = document.getElementById(filtrada ? 'cards-resultado' : painel ? 'cards-recente-mobile' : 'cards-mobile-corpo');
        tabela?.replaceChildren(); cartoes.replaceChildren();
        for (const item of dados) {
            const link = () => { const elemento = criar('a', `#${item.id}`, 'link-solicitacao'); elemento.href = `/detalhes-solicitacao?id=${item.id}`; return elemento; };
            const etiqueta = () => criar('span', estados[item.status], `tag-status status-${item.status}`);
            if (tabela) {
                const linha = criar('tr'); const codigo = criar('td'); codigo.append(link()); linha.append(codigo);
                for (const texto of [item.nome, item.destino, CTIC.data(item.saida_em)]) linha.append(criar('td', texto));
                const status = criar('td'); status.append(etiqueta()); linha.append(status); tabela.append(linha);
            }
            const cartao = criar('article', undefined, 'card-solicitacao-item');
            const topo = criar('div', undefined, 'card-topo'); topo.append(link(), criar('span', item.nome));
            const rodape = criar('div', undefined, 'card-rodape'); rodape.append(criar('span', item.destino), etiqueta());
            cartao.append(topo, rodape, criar('p', CTIC.data(item.saida_em))); cartoes.append(cartao);
        }
        if (!dados.length) {
            cartoes.append(criar('p', 'Nenhuma solicitação encontrada.'));
            if (tabela) { const linha = criar('tr'); const celula = criar('td', 'Nenhuma solicitação encontrada.'); celula.colSpan = 5; linha.append(celula); tabela.append(linha); }
        }
        const contador = document.getElementById(filtrada ? 'contador-resultados' : 'contador-registros');
        if (contador) contador.textContent = `${solicitacoes.length} registros`;
        if (filtrada) {
            document.getElementById('resumo-filtros').textContent = [filtros.get('busca'), estados[filtros.get('status')], filtros.get('periodo') ? `Últimos ${filtros.get('periodo')} dias` : ''].filter(Boolean).join(' · ') || 'Todos os registros';
            document.getElementById('estado-vazio').hidden = dados.length !== 0;
        }
        const linkFiltradas = document.getElementById('link-filtradas');
        if (linkFiltradas) linkFiltradas.href = '/solicitacoes-filtradas?' + filtros;
    };
    let temporizador;
    for (const identificador of Object.values(campos)) document.getElementById(identificador)?.addEventListener('input', () => {
        clearTimeout(temporizador); temporizador = setTimeout(() => carregar().catch(erro => CTIC.avisar(erro)), 250);
    });
    await carregar();
}

async function mostrarSolicitacao() {
    const identificador = identificadorUrl();
    const {solicitacao: pedido} = await consultar(`/${identificador}`);
    document.querySelector('.texto-titulo p').textContent = `#${pedido.id} · ${pedido.destino} · ${pedido.nome}`;
    const grupos = document.querySelectorAll('.informacoes');
    if (grupos.length) {
        preencherTextos(grupos[0], [`${pedido.tipo_deslocamento} · ${pedido.finalidade}`, `Destino: ${pedido.destino}`,
            `Saída: ${CTIC.data(pedido.saida_em)}`, `Retorno: ${CTIC.data(pedido.retorno_em)}`, `Embarque: ${pedido.local_embarque}`, `Centro de custo: ${pedido.centro_custo}`]);
        preencherTextos(grupos[1], [pedido.justificativa]);
        preencherTextos(grupos[2], [`${pedido.nome} · ${pedido.setor} · ${pedido.vinculo}`, `${pedido.email} · ${pedido.telefone}`,
            ...pedido.passageiros.map(pessoa => `Passageiro: ${pessoa.nome} · ${pessoa.setor} · ${pessoa.vinculo}`),
            ...(pedido.veiculo ? [`Veículo: ${pedido.veiculo}`, `Motorista: ${pedido.motorista}`] : []),
            ...(pedido.motivo_cancelamento ? [`Motivo do cancelamento: ${pedido.motivo_cancelamento}`] : [])]);
    }
    const historico = document.querySelector('.historico');
    if (historico) preencherTextos(historico, pedido.historico.map(item => `${CTIC.data(item.criado_em, true)} · ${item.nome} · ${estados[item.status_novo]}${item.observacao ? ' · ' + item.observacao : ''}`));
    const status = document.querySelector('.caixa-status strong');
    if (status) status.textContent = `Situação: ${estados[pedido.status]}`;
    const encerrada = ['recusada','concluida','cancelada'].includes(pedido.status);
    for (const link of document.querySelectorAll('a[href="/detalhes-solicitacao"],a[href="/analisar-solicitacao"],a[href="/cancelar-solicitacao"]')) {
        if (link.getAttribute('href') === '/analisar-solicitacao') link.hidden = usuarioAtual.perfil !== 'administrador' || !['pendente','analise'].includes(pedido.status);
        if (link.getAttribute('href') === '/cancelar-solicitacao') link.hidden = encerrada;
        link.setAttribute('href', link.getAttribute('href') + `?id=${identificador}`);
    }
    if (pagina === '/detalhes-solicitacao' && usuarioAtual.perfil === 'administrador' && pedido.status === 'aprovada') {
        const concluir = criar('button', 'Concluir viagem', 'btn-continuar'); concluir.type = 'button';
        document.querySelector('.botoes-acao').prepend(concluir);
        CTIC.acao(concluir, async () => {
            await consultar(`/${identificador}/status`, 'PATCH', {status:'concluida'});
            window.location.reload();
        });
    }
    if (pagina === '/analisar-solicitacao') {
        if (!['pendente','analise'].includes(pedido.status)) throw new Error('Este pedido não está disponível para análise.');
        const formulario = document.getElementById('form-analise');
        CTIC.formulario(formulario, async () => {
            await consultar(`/${identificador}/analise`, 'POST', {status:'aprovada', veiculo: valor('veiculo'), motorista: valor('motorista')});
            window.location.assign(`/detalhes-solicitacao?id=${identificador}`);
        });
        const iniciar = criar('button', 'Iniciar análise', 'btn-cancelar'); iniciar.type = 'button';
        if (pedido.status === 'pendente') {
            formulario.querySelector('.botoes-acao').prepend(iniciar);
            CTIC.acao(iniciar, async () => {
                await consultar(`/${identificador}/status`, 'PATCH', {status:'analise'});
                iniciar.hidden = true; status.textContent = 'Situação: Em análise';
            });
        }
        CTIC.acao(document.getElementById('recusar-solicitacao'), async () => {
            if (!window.confirm('Recusar esta solicitação?')) return;
            await consultar(`/${identificador}/analise`, 'POST', {status:'recusada'});
            window.location.assign(`/detalhes-solicitacao?id=${identificador}`);
        });
    }
    if (pagina === '/cancelar-solicitacao') {
        if (encerrada) throw new Error('Este pedido já está encerrado.');
        CTIC.formulario(document.getElementById('form-cancelamento'), async () => {
            await consultar(`/${identificador}/cancelar`, 'POST', {motivo: valor('motivo-cancelamento')});
            window.location.assign(`/detalhes-solicitacao?id=${identificador}`);
        });
    }
    document.querySelector('.secao-formulario').hidden = false;
}

function iniciarConta() {
    const criarFormulario = (titulo, campos) => {
        const formulario = criar('form', undefined, 'formulario-conta'); formulario.append(criar('h2', titulo));
        for (const [nome, rotulo, tipo, conteudo] of campos) {
            const etiqueta = criar('label', rotulo); const entrada = criar('input');
            entrada.name = nome; entrada.id = nome; entrada.type = tipo; entrada.required = true;
            entrada.value = conteudo || ''; entrada.maxLength = tipo === 'password' ? 72 : nome === 'nome' ? 150 : 100;
            if (tipo === 'password') entrada.autocomplete = nome === 'senha_atual' ? 'current-password' : 'new-password';
            etiqueta.append(entrada); formulario.append(etiqueta);
        }
        const salvar = criar('button', 'Salvar'); salvar.type = 'submit'; formulario.append(salvar);
        document.querySelector('.secao-formulario').append(formulario); return formulario;
    };
    const perfil = criarFormulario('Editar meus dados', [['nome','Nome completo','text',usuarioAtual.nome], ['setor','Setor','text',usuarioAtual.setor]]);
    CTIC.formulario(perfil, async () => { await CTIC.requisitar('/api/conta', 'PUT', Object.fromEntries(new FormData(perfil))); window.location.reload(); });
    const senha = criarFormulario('Alterar senha', [['senha_atual','Senha atual','password'], ['nova_senha','Nova senha (12 a 72 bytes)','password'], ['confirmacao_senha','Confirme a nova senha','password']]);
    CTIC.formulario(senha, async () => {
        const resposta = await CTIC.requisitar('/api/conta/senha', 'PUT', Object.fromEntries(new FormData(senha)));
        senha.reset(); CTIC.avisar(resposta.mensagem, true);
    });
}

async function iniciarTela() {
    if (['/nova-solicitacao','/solicitantes','/passageiros','/revisao-envio'].includes(pagina)) await iniciarViagem();
    if (['/adicionar-passageiro','/editar-passageiro'].includes(pagina)) await iniciarCadastroPassageiro();
    if (pagina === '/passageiros-cadastrados') await listarPassageiros();
    if (['/painel','/solicitacoes','/solicitacoes-filtradas'].includes(pagina)) await listarSolicitacoes();
    if (['/detalhes-solicitacao','/analisar-solicitacao','/cancelar-solicitacao'].includes(pagina)) await mostrarSolicitacao();
    if (pagina === '/buscar-passageiro') document.getElementById('form-busca').action = '/passageiros-cadastrados';
    if (pagina === '/minha-conta') iniciarConta();
    if (pagina === '/descartar-solicitacao') CTIC.acao(document.querySelector('.btn-descartar'), async () => {
        await consultar('/rascunho', 'DELETE'); window.location.assign('/painel');
    });
    if (pagina === '/passageiro-salvo') {
        const {passageiro} = await CTIC.requisitar(`/api/passageiros/${identificadorUrl()}`);
        const cartao = criar('article', undefined, 'item-passageiro');
        const dados = criar('div', undefined, 'dados-passageiro');
        dados.append(criar('strong', passageiro.nome), criar('span', `${passageiro.vinculo} · ${passageiro.setor}`));
        const editar = criar('a', 'Editar', 'link-solicitacao'); editar.href = `/editar-passageiro?id=${passageiro.id}`;
        cartao.append(dados, editar);
        document.getElementById('lista-passageiros').replaceChildren(cartao);
        const texto = document.getElementById('nome-passageiro-salvo');
        if (texto) texto.textContent = passageiro.nome;
        document.querySelector('.botoes-acao .btn-continuar').href = parametros.get('origem') === 'viagem' ? '/passageiros' : '/passageiros-cadastrados';
        if (parametros.get('origem') !== 'viagem') document.querySelector('.botoes-acao .btn-continuar').textContent = 'Ver passageiros cadastrados';
    }
    if (pagina === '/solicitacao-enviada') {
        const {solicitacao} = await consultar(`/${identificadorUrl()}`);
        document.getElementById('protocolo').textContent = `#${solicitacao.id}`;
        document.getElementById('resumo-solicitacao').textContent = `${solicitacao.destino} · ${CTIC.data(solicitacao.saida_em)} · ${estados[solicitacao.status]}`;
        document.querySelector('a[href="/detalhes-solicitacao"]').setAttribute('href', `/detalhes-solicitacao?id=${solicitacao.id}`);
    }
}
iniciarTela().catch(erro => CTIC.avisar(erro)).finally(() => document.querySelector('main').setAttribute('aria-busy', 'false'));
