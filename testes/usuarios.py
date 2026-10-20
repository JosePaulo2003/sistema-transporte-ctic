#!/usr/bin/env python3
"""Testa administração e isolamento. Mantém duas contas desativadas e um pedido de teste no banco."""
import http.cookiejar
import json
from pathlib import Path
import re
import secrets
import urllib.error
import urllib.request


class ClienteTeste:
    # Cada cliente tem seus próprios cookies e token, simulando navegadores diferentes.
    def __init__(self):
        self.navegador = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.token = None

    def requisitar(self, caminho, metodo='GET', dados=None, proteger=True):
        cabecalhos = {'Content-Type': 'application/json'}
        if proteger and self.token:
            cabecalhos['X-CSRF-Token'] = self.token
        pedido = urllib.request.Request('http://127.0.0.1:8080' + caminho, method=metodo,
            headers=cabecalhos, data=json.dumps(dados).encode() if dados is not None else None)
        try:
            resposta = self.navegador.open(pedido, timeout=10)
        except urllib.error.HTTPError as erro:
            resposta = erro
        with resposta:
            conteudo = resposta.read().decode()
            return resposta.status, json.loads(conteudo) if resposta.headers.get_content_type() == 'application/json' else conteudo

    def entrar(self, email, senha):
        self.token = self.requisitar('/api/autenticacao/csrf')[1]['csrf']
        codigo, dados = self.requisitar('/api/autenticacao/entrar', 'POST', {'email': email, 'senha': senha})
        if codigo == 200:
            self.token = dados['csrf']
        return codigo, dados


def conferir(condicao, mensagem):
    if not condicao:
        raise AssertionError(mensagem)


def executar():
    configuracao = (Path(__file__).resolve().parent.parent / 'configuracao/primeiro-usuario.local.php').read_text()
    email = re.search(r"'email'\s*=>\s*'([^']+)'", configuracao)[1]
    senha = re.search(r"'senha'\s*=>\s*'([^']+)'", configuracao)[1]
    administrador = ClienteTeste()
    conferir(administrador.requisitar('/api/usuarios')[0] == 401, 'Listagem sem autenticação foi permitida.')
    codigo, entrada = administrador.entrar(email, senha)
    conferir(codigo == 200, 'Falha ao entrar como administrador local.')
    conferir(administrador.requisitar('/usuarios')[0] == 200, 'Tela administrativa indisponível.')
    conferir(administrador.requisitar('/api/usuarios', 'POST', {}, proteger=False)[0] == 419, 'Cadastro sem CSRF foi aceito.')
    codigo, resposta = administrador.requisitar('/api/usuarios', 'POST', {})
    conferir(codigo == 422, f'Cadastro vazio: esperado HTTP 422, recebido {codigo}: {resposta}')
    conferir(administrador.requisitar('/api/usuarios', 'POST', [])[0] == 400, 'Uma lista JSON foi aceita como cadastro.')
    proprio = dict(entrada['usuario'], ativo=False)
    conferir(administrador.requisitar(f"/api/usuarios/{proprio['id']}", 'PUT', proprio)[0] == 422, 'Administrador conseguiu desativar a própria conta.')
    proprio.update(ativo=True, perfil='solicitante')
    conferir(administrador.requisitar(f"/api/usuarios/{proprio['id']}", 'PUT', proprio)[0] == 422, 'Administrador conseguiu remover o próprio perfil.')
    cadastros = []
    senhaTeste = secrets.token_hex(16)
    marcador = secrets.token_hex(6)
    try:
        for indice in range(2):
            cadastro = {'nome': f'TESTE PERMISSÕES {marcador} {indice}', 'email': f'teste-{marcador}-{indice}@example.com',
                'setor': 'CTIC', 'perfil': 'solicitante', 'ativo': True}
            codigo, dados = administrador.requisitar('/api/usuarios', 'POST', dict(cadastro, senha=senhaTeste))
            conferir(codigo == 201, 'Falha ao cadastrar solicitante.')
            cadastro['id'] = dados['id']
            cadastros.append(cadastro)
        conferir(administrador.requisitar('/api/usuarios', 'POST', dict(cadastros[0], senha=senhaTeste))[0] == 409, 'E-mail duplicado foi aceito.')
        registros = administrador.requisitar('/api/usuarios')[1]['usuarios']
        conferir(all('hash_senha' not in pessoa and 'senha' not in pessoa for pessoa in registros), 'A listagem expôs uma senha.')
        cadastros[0]['setor'] = 'SETOR DE TESTE'
        conferir(administrador.requisitar(f"/api/usuarios/{cadastros[0]['id']}", 'PUT', cadastros[0])[0] == 200, 'Edição falhou.')
        clientes = [ClienteTeste(), ClienteTeste()]
        for cliente, cadastro in zip(clientes, cadastros):
            conferir(cliente.entrar(cadastro['email'], senhaTeste)[0] == 200, 'Solicitante não conseguiu entrar.')
            conferir(cliente.requisitar('/usuarios')[0] == 403, 'Solicitante abriu a tela administrativa.')
            for caminho, metodo, dados in [('/api/usuarios', 'GET', None), ('/api/usuarios', 'POST', dict(cadastro, senha=senhaTeste)),
                (f"/api/usuarios/{cadastro['id']}", 'PUT', dict(cadastro, perfil='administrador')),
                (f"/api/usuarios/{cadastro['id']}/senha", 'POST', {'senha': senhaTeste})]:
                conferir(cliente.requisitar(caminho, metodo, dados)[0] == 403, 'Solicitante acessou a administração.')
        viagem = {'tipo_deslocamento': 'Intermunicipal', 'destino': 'TESTE DE ISOLAMENTO', 'finalidade': 'Verificação de permissões',
            'saida_em': '2026-11-20T08:00', 'retorno_em': '2026-11-20T18:00', 'local_embarque': 'CTIC',
            'centro_custo': 'CTIC', 'justificativa': 'Teste automatizado entre duas contas'}
        codigo, _ = clientes[0].requisitar('/api/solicitacoes/rascunho', 'PUT', {'viagem': viagem,
            'contato': {'telefone': '(92) 99999-0000', 'setor': 'CTIC', 'vinculo': 'Servidor'},
            'passageiros': [{'nome': 'Passageiro de teste', 'setor': 'CTIC', 'vinculo': 'Servidor'}]})
        conferir(codigo == 200, 'Não foi possível montar o rascunho.')
        codigo, dados = clientes[0].requisitar('/api/solicitacoes', 'POST', {'declaracao': True})
        conferir(codigo == 201, 'Solicitante não conseguiu enviar o pedido.')
        pedido = dados['id']
        conferir(clientes[0].requisitar(f'/api/solicitacoes/{pedido}')[0] == 200, 'Responsável não consultou seu pedido.')
        conferir(clientes[1].requisitar(f'/api/solicitacoes/{pedido}')[0] == 404, 'Outro solicitante consultou pedido alheio.')
        conferir(administrador.requisitar(f'/api/solicitacoes/{pedido}')[0] == 200, 'Administrador não consultou o pedido.')
        for cliente, cadastro in zip(clientes, cadastros):
            lista = cliente.requisitar('/api/solicitacoes')[1]['solicitacoes']
            conferir(all(int(item['usuario_id']) == cadastro['id'] for item in lista), 'Listagem expôs pedidos alheios.')
        conferir(clientes[0].requisitar(f'/api/solicitacoes/{pedido}/status', 'PATCH', {'status': 'aprovada'})[0] == 403, 'Solicitante alterou o status.')
        conferir(clientes[1].requisitar(f'/api/solicitacoes/{pedido}/status', 'PATCH', {'status': 'aprovada'})[0] == 404, 'Pedido alheio foi exposto ao alterar status.')
        novaSenha = secrets.token_hex(16)
        caminhoSenha = f"/api/usuarios/{cadastros[0]['id']}/senha"
        conferir(administrador.requisitar(caminhoSenha, 'POST', {'senha': novaSenha}, proteger=False)[0] == 419, 'Redefinição sem CSRF foi aceita.')
        conferir(administrador.requisitar(caminhoSenha, 'POST', {'senha': 'curta'})[0] == 422, 'Senha curta foi aceita.')
        conferir(administrador.requisitar(caminhoSenha, 'POST', {'senha': novaSenha})[0] == 200, 'Redefinição falhou.')
        conferir(clientes[0].requisitar('/api/autenticacao/usuario')[0] == 401, 'Sessão antiga sobreviveu à redefinição.')
        conferir(clientes[0].entrar(cadastros[0]['email'], senhaTeste)[0] == 401, 'Senha antiga ainda funciona.')
        conferir(clientes[0].entrar(cadastros[0]['email'], novaSenha)[0] == 200, 'Nova senha não funciona.')
        cadastros[1]['ativo'] = False
        conferir(administrador.requisitar(f"/api/usuarios/{cadastros[1]['id']}", 'PUT', cadastros[1])[0] == 200, 'Desativação falhou.')
        conferir(clientes[1].requisitar('/api/solicitacoes')[0] == 401, 'Usuário inativo manteve acesso.')
        conferir(clientes[1].entrar(cadastros[1]['email'], senhaTeste)[0] == 401, 'Usuário inativo conseguiu entrar.')
        cadastros[1]['ativo'] = True
        conferir(administrador.requisitar(f"/api/usuarios/{cadastros[1]['id']}", 'PUT', cadastros[1])[0] == 200, 'Reativação falhou.')
        conferir(clientes[1].entrar(cadastros[1]['email'], senhaTeste)[0] == 200, 'Reativado não conseguiu entrar.')
        print(f'APROVADO: usuários, CSRF, senhas, ativação e isolamento entre solicitantes. Pedido de teste: #{pedido}.')
    finally:
        # Preserva o histórico do teste, mas encerra o acesso das contas criadas.
        for cadastro in cadastros:
            codigo, _ = administrador.requisitar(f"/api/usuarios/{cadastro['id']}", 'PUT', dict(cadastro, ativo=False))
            if codigo != 200:
                print(f"Não foi possível desativar a conta de teste #{cadastro['id']}; confira a tela Usuários.")


if __name__ == '__main__':
    try:
        executar()
    except (AssertionError, OSError, ValueError, TypeError, KeyError) as erro:
        raise SystemExit('Teste não concluído: ' + str(erro)) from None
