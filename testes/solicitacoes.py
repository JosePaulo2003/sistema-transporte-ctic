#!/usr/bin/env python3
"""Testa o fluxo HTTP e cria uma solicitação identificada como teste no banco local."""
import http.cookiejar
import json
from pathlib import Path
import re
import urllib.error
import urllib.request


def executar():
    configuracao = (Path(__file__).resolve().parent.parent / 'configuracao/primeiro-usuario.local.php').read_text()
    email = re.search(r"'email'\s*=>\s*'([^']+)'", configuracao)[1]
    senha = re.search(r"'senha'\s*=>\s*'([^']+)'", configuracao)[1]
    navegador = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    token = None

    def requisitar(caminho, metodo='GET', dados=None, proteger=True):
        cabecalhos = {'Content-Type': 'application/json'}
        if proteger and token:
            cabecalhos['X-CSRF-Token'] = token
        pedido = urllib.request.Request('http://127.0.0.1:8080' + caminho, method=metodo,
            headers=cabecalhos, data=json.dumps(dados).encode() if dados is not None else None)
        try:
            resposta = navegador.open(pedido, timeout=10)
        except urllib.error.HTTPError as erro:
            resposta = erro
        with resposta:
            return resposta.status, json.loads(resposta.read())

    # Verifica a barreira de autenticação antes de usar a conta local.
    assert requisitar('/api/solicitacoes')[0] == 401
    assert requisitar('/api/solicitacoes/rascunho')[0] == 401
    token = requisitar('/api/autenticacao/csrf')[1]['csrf']
    codigo, dados = requisitar('/api/autenticacao/entrar', 'POST', {'email': email, 'senha': senha})
    assert codigo == 200, 'Falha no login.'
    token = dados['csrf']
    assert requisitar('/api/solicitacoes', 'POST', {'declaracao': True}, proteger=False)[0] == 419
    assert requisitar('/api/solicitacoes', 'POST', {'declaracao': False})[0] == 422
    # O teste usa uma sessão própria e não remove rascunhos de outras sessões.
    assert requisitar('/api/solicitacoes/rascunho', 'DELETE')[0] == 200
    assert requisitar('/api/solicitacoes', 'POST', {'declaracao': True})[0] == 422
    viagem = {'tipo_deslocamento': 'Intermunicipal', 'destino': 'TESTE AUTOMATIZADO <texto>',
        'finalidade': 'Validação da API', 'saida_em': '2026-11-20T08:00', 'retorno_em': '2026-11-20T18:00',
        'local_embarque': 'CTIC', 'centro_custo': 'CTIC', 'justificativa': 'Registro de teste automatizado'}
    invalida = dict(viagem, retorno_em='2026-11-19T08:00')
    assert requisitar('/api/solicitacoes/rascunho', 'PUT', {'viagem': invalida})[0] == 422
    assert requisitar('/api/solicitacoes/rascunho', 'PUT', {'passageiros': []})[0] == 422
    assert requisitar('/api/solicitacoes/rascunho', 'PUT', {'viagem': viagem})[0] == 200
    assert requisitar('/api/solicitacoes/rascunho', 'PUT', {'contato': {
        'telefone': '(92) 99999-0000', 'setor': 'CTIC', 'vinculo': 'Servidor'}})[0] == 200
    assert requisitar('/api/solicitacoes/rascunho', 'PUT', {'passageiros': [
        {'nome': 'Passageiro de teste', 'setor': 'CTIC', 'vinculo': 'Servidor'}]})[0] == 200
    codigo, dados = requisitar('/api/solicitacoes', 'POST', {'declaracao': True})
    assert codigo == 201, dados
    identificador = dados['id']
    assert not requisitar('/api/solicitacoes/rascunho')[1]['rascunho']
    assert requisitar('/api/solicitacoes', 'POST', {'declaracao': True})[0] == 422, 'Envio repetido criou outro registro.'
    codigo, dados = requisitar(f'/api/solicitacoes/{identificador}')
    solicitacao = dados['solicitacao']
    assert codigo == 200 and solicitacao['destino'] == viagem['destino']
    assert solicitacao['status'] == 'pendente' and len(solicitacao['passageiros']) == 1
    assert len(solicitacao['historico']) == 1
    assert any(int(item['id']) == identificador for item in requisitar('/api/solicitacoes')[1]['solicitacoes'])
    assert requisitar(f'/api/solicitacoes/{identificador}/status', 'PATCH', {'status': 'invalido'})[0] == 422
    assert requisitar(f'/api/solicitacoes/{identificador}/status', 'PATCH', {'status': 'analise'})[0] == 200
    assert requisitar(f'/api/solicitacoes/{identificador}/status', 'PATCH', {'status': 'analise'})[0] == 200
    solicitacao = requisitar(f'/api/solicitacoes/{identificador}')[1]['solicitacao']
    assert solicitacao['status'] == 'analise' and len(solicitacao['historico']) == 2
    assert requisitar('/api/autenticacao/sair', 'POST')[0] == 200
    assert requisitar(f'/api/solicitacoes/{identificador}')[0] == 401
    print(f'APROVADO: rascunho, validação, envio, passageiros e histórico. Registro de teste: #{identificador}.')


if __name__ == '__main__':
    try:
        executar()
    except (AssertionError, OSError, ValueError, TypeError, KeyError) as erro:
        raise SystemExit('Teste não concluído: ' + str(erro)) from None
