'use strict';

let usuariosCadastrados = [];
let identificadorEdicao = null;
let identificadorSenha = null;
const formularioUsuario = document.getElementById('formulario-usuario');
const formularioSenha = document.getElementById('formulario-senha');

function informarUsuarios(texto, erro = false) {
    const mensagem = document.getElementById('mensagem-usuarios');
    mensagem.textContent = texto;
    mensagem.classList.toggle('erro', erro);
    mensagem.setAttribute('role', erro ? 'alert' : 'status');
    mensagem.hidden = false;
    mensagem.focus();
}

async function requisitarUsuarios(caminho = '', metodo = 'GET', dados) {
    const cabecalhos = {};
    if (metodo !== 'GET') {
        const respostaToken = await fetch('/api/autenticacao/csrf', {credentials: 'same-origin'});
        if (!respostaToken.ok) throw new Error('Não foi possível validar a sessão.');
        cabecalhos['X-CSRF-Token'] = (await respostaToken.json()).csrf;
        cabecalhos['Content-Type'] = 'application/json';
    }
    const resposta = await fetch('/api/usuarios' + caminho, {method: metodo, credentials: 'same-origin',
        headers: cabecalhos, body: dados === undefined ? undefined : JSON.stringify(dados)});
    const resultado = await resposta.json();
    if (resposta.status === 401) window.location.replace('/entrar');
    if (!resposta.ok) throw new Error(resultado.erro || 'Não foi possível concluir a operação.');
    return resultado;
}

// Cria textos e ações pelo DOM para que os dados cadastrados nunca sejam interpretados como HTML.
function criarElementoUsuario(tipo, texto, classe) {
    const elemento = document.createElement(tipo);
    if (texto !== undefined) elemento.textContent = texto;
    if (classe) elemento.className = classe;
    return elemento;
}

function cancelarEdicaoUsuario() {
    identificadorEdicao = null;
    formularioUsuario.reset();
    document.getElementById('usuario-perfil').disabled = false;
    document.getElementById('usuario-ativo').disabled = false;
    document.getElementById('campo-senha-inicial').hidden = false;
    document.getElementById('usuario-senha').required = true;
    document.getElementById('cancelar-edicao').hidden = true;
    document.getElementById('titulo-formulario').textContent = 'Novo usuário';
}

function editarUsuario(usuario) {
    cancelarEdicaoUsuario();
    identificadorEdicao = usuario.id;
    for (const campo of ['nome', 'email', 'setor', 'perfil']) document.getElementById(`usuario-${campo}`).value = usuario[campo];
    document.getElementById('usuario-ativo').checked = Boolean(Number(usuario.ativo));
    const propriaConta = Number(usuario.id) === Number(window.CTIC_USUARIO.id);
    document.getElementById('usuario-perfil').disabled = propriaConta;
    document.getElementById('usuario-ativo').disabled = propriaConta;
    document.getElementById('campo-senha-inicial').hidden = true;
    document.getElementById('usuario-senha').required = false;
    document.getElementById('cancelar-edicao').hidden = false;
    document.getElementById('titulo-formulario').textContent = `Editar ${usuario.nome}`;
    document.getElementById('usuario-nome').focus();
}

function abrirSenhaUsuario(usuario) {
    identificadorSenha = usuario.id;
    formularioSenha.reset();
    document.getElementById('painel-senha').hidden = false;
    document.getElementById('titulo-senha').textContent = `Redefinir senha de ${usuario.nome}`;
    document.getElementById('nova-senha').focus();
}

function renderizarUsuarios() {
    const termo = document.getElementById('busca-usuarios').value.toLocaleLowerCase();
    const usuarios = usuariosCadastrados.filter(usuario => `${usuario.nome} ${usuario.email} ${usuario.setor}`.toLocaleLowerCase().includes(termo));
    const lista = document.getElementById('lista-usuarios');
    lista.replaceChildren();
    document.getElementById('quantidade-usuarios').textContent = `${usuarios.length} usuários`;
    usuarios.forEach(usuario => {
        const linha = criarElementoUsuario('tr');
        for (const texto of [usuario.nome, usuario.email, usuario.setor, usuario.perfil === 'administrador' ? 'Administrador' : 'Solicitante', Number(usuario.ativo) ? 'Ativo' : 'Inativo']) linha.append(criarElementoUsuario('td', texto));
        const celula = criarElementoUsuario('td');
        const acoes = criarElementoUsuario('div', undefined, 'acoes-usuarios');
        for (const [texto, acao] of [['Editar', () => editarUsuario(usuario)], ['Redefinir senha', () => abrirSenhaUsuario(usuario)]]) {
            const botao = criarElementoUsuario('button', texto, 'botao-usuario secundario');
            botao.type = 'button'; botao.addEventListener('click', acao); acoes.append(botao);
        }
        celula.append(acoes); linha.append(celula); lista.append(linha);
    });
    if (!usuarios.length) {
        const linha = criarElementoUsuario('tr'); const celula = criarElementoUsuario('td', 'Nenhum usuário encontrado.');
        celula.colSpan = 6; linha.append(celula); lista.append(linha);
    }
}

async function carregarUsuarios() {
    usuariosCadastrados = (await requisitarUsuarios()).usuarios;
    renderizarUsuarios();
}

// Desabilita as ações do cadastro durante a gravação, evitando dois envios concorrentes pela tela.
function prepararFormularioUsuario(formulario, acao) {
    formulario.addEventListener('submit', async evento => {
        evento.preventDefault();
        const botoes = [...document.querySelectorAll('.pagina-usuarios button')];
        botoes.forEach(botao => { botao.disabled = true; });
        try { await acao(); } catch (erro) { informarUsuarios(erro.message, true); }
        finally { botoes.forEach(botao => { botao.disabled = false; }); }
    });
}

prepararFormularioUsuario(formularioUsuario, async () => {
    const dados = {};
    for (const campo of ['nome', 'email', 'setor', 'perfil']) dados[campo] = document.getElementById(`usuario-${campo}`).value.trim();
    dados.ativo = document.getElementById('usuario-ativo').checked;
    if (identificadorEdicao === null) dados.senha = document.getElementById('usuario-senha').value;
    const resultado = await requisitarUsuarios(identificadorEdicao === null ? '' : `/${identificadorEdicao}`, identificadorEdicao === null ? 'POST' : 'PUT', dados);
    // Limpa a senha assim que o servidor confirma o cadastro, mesmo se a atualização da lista falhar.
    cancelarEdicaoUsuario();
    informarUsuarios(resultado.mensagem);
    await carregarUsuarios();
});
prepararFormularioUsuario(formularioSenha, async () => {
    const resultado = await requisitarUsuarios(`/${identificadorSenha}/senha`, 'POST', {senha: document.getElementById('nova-senha').value});
    formularioSenha.reset(); document.getElementById('painel-senha').hidden = true;
    informarUsuarios(resultado.mensagem);
    if (Number(identificadorSenha) === Number(window.CTIC_USUARIO.id)) window.location.replace('/entrar');
});
document.getElementById('cancelar-edicao').addEventListener('click', cancelarEdicaoUsuario);
document.getElementById('cancelar-senha').addEventListener('click', () => { formularioSenha.reset(); identificadorSenha = null; document.getElementById('painel-senha').hidden = true; });
document.getElementById('busca-usuarios').addEventListener('input', renderizarUsuarios);
document.getElementById('nome-usuario').textContent = window.CTIC_USUARIO.nome;
document.getElementById('avatar-usuario').textContent = window.CTIC_USUARIO.nome.trim().split(/\s+/).map(parte => parte[0]).slice(0, 2).join('').toUpperCase();
carregarUsuarios().catch(erro => informarUsuarios(erro.message, true));
