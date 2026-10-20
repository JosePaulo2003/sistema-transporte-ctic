#!/usr/bin/env python3
"""Verifica a autenticação no servidor local já iniciado, sem pacotes adicionais."""
import http.cookiejar
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

RAIZ = Path(__file__).resolve().parent.parent
ENDERECO = 'http://127.0.0.1:8080'


def executar():
    # Lê as credenciais locais sem imprimir senhas ou colocá-las nos argumentos do processo.
    configuracao = (RAIZ / 'configuracao/primeiro-usuario.local.php').read_text()
    email = re.search(r"'email'\s*=>\s*'([^']+)'", configuracao)[1]
    senha = re.search(r"'senha'\s*=>\s*'([^']+)'", configuracao)[1]
    cookies = http.cookiejar.CookieJar()
    navegador = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

    def requisitar(caminho, metodo='GET', dados=None, token=None):
        cabecalhos = {'Content-Type': 'application/json'}
        if token:
            cabecalhos['X-CSRF-Token'] = token
        requisicao = urllib.request.Request(
            ENDERECO + caminho, method=metodo, headers=cabecalhos,
            data=json.dumps(dados).encode() if dados is not None else None,
        )
        try:
            resposta = navegador.open(requisicao, timeout=10)
        except urllib.error.HTTPError as erro:
            resposta = erro
        with resposta:
            conteudo = resposta.read().decode()
            return resposta.status, resposta.url, conteudo

    def requisitar_json(*argumentos, **opcoes):
        codigo, _, conteudo = requisitar(*argumentos, **opcoes)
        return codigo, json.loads(conteudo)

    codigo, dados = requisitar_json('/api/autenticacao/usuario')
    assert codigo == 401, 'A API permitiu acesso sem sessão.'
    codigo, destino, conteudo = requisitar('/painel')
    assert codigo == 200 and destino.endswith('/entrar'), 'O painel não redirecionou para a entrada.'
    assert 'formulario-entrada' in conteudo
    for caminho in ['/configuracao/aplicacao.local.php', '/CREDENCIAIS.local.md',
                    '/configuracao/primeiro-usuario.local.php', '/banco-de-dados/migracoes/001_autenticacao.sql']:
        codigo, _, _ = requisitar(caminho)
        assert codigo == 404, 'Um arquivo interno ficou acessível pela web.'
    codigo, dados = requisitar_json('/api/autenticacao/csrf')
    assert codigo == 200 and len(dados['csrf']) == 64
    token = dados['csrf']
    identificadorAnterior = next(cookie.value for cookie in cookies if cookie.name == 'sessao_transporte_ctic')
    codigo, _ = requisitar_json('/api/autenticacao/entrar', 'POST', {'email': email, 'senha': senha})
    assert codigo == 419, 'O login aceitou um envio sem proteção CSRF.'
    codigo, _ = requisitar_json('/api/autenticacao/entrar', 'POST', {'email': email, 'senha': senha + 'invalida'}, token)
    assert codigo == 401, 'O login não rejeitou a senha incorreta.'
    codigo, dados = requisitar_json('/api/autenticacao/entrar', 'POST', {'email': email, 'senha': senha}, token)
    assert codigo == 200, 'Falha ao entrar. Execute a preparação do banco e confira as credenciais.'
    assert dados['usuario']['email'] == email and 'hash_senha' not in dados['usuario']
    assert dados['csrf'] != token, 'O token CSRF não foi renovado.'
    identificadorAtual = next(cookie.value for cookie in cookies if cookie.name == 'sessao_transporte_ctic')
    assert identificadorAtual != identificadorAnterior, 'O identificador de sessão não foi renovado.'
    for caminho in ['/painel', '/solicitacoes', '/nova-solicitacao', '/solicitantes', '/passageiros', '/revisao-envio']:
        codigo, destino, conteudo = requisitar(caminho)
        assert codigo == 200 and destino.endswith(caminho), 'Falha na página protegida ' + caminho
        assert 'window.CTIC_USUARIO' in conteudo and 'ctic-sair' in conteudo
    for caminho in ['/public/assets/js/entrada.js', '/public/assets/js/sessao.js', '/public/assets/autenticacao.css']:
        assert requisitar(caminho)[0] == 200, 'Recurso ausente: ' + caminho
    codigo, dados = requisitar_json('/api/autenticacao/usuario')
    assert codigo == 200 and dados['usuario']['email'] == email
    token = dados['csrf']
    assert requisitar_json('/api/autenticacao/sair')[0] == 405
    assert requisitar_json('/api/autenticacao/sair', 'POST')[0] == 419
    assert requisitar_json('/api/autenticacao/sair', 'POST', token=token)[0] == 200
    assert requisitar_json('/api/autenticacao/usuario')[0] == 401
    assert requisitar('/painel')[1].endswith('/entrar')
    print('APROVADO: login, senha incorreta, CSRF, renovação de sessão, páginas protegidas, arquivos internos e saída.')


if __name__ == '__main__':
    try:
        executar()
    except (AssertionError, OSError, ValueError, TypeError) as erro:
        raise SystemExit('Teste não concluído: ' + str(erro)) from None
