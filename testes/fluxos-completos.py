#!/usr/bin/env python3
"""Confere os fluxos adicionais em banco de desenvolvimento com contas e pedidos identificados como teste."""
import os
from pathlib import Path
import re
import secrets
from usuarios import ClienteTeste, conferir


def cpf_teste():
    numeros = [int(numero) for numero in str(secrets.randbelow(900000000) + 100000000)]
    for tamanho in (9, 10):
        digito = sum(numero * (tamanho + 1 - indice) for indice, numero in enumerate(numeros)) * 10 % 11
        numeros.append(0 if digito == 10 else digito)
    return ''.join(map(str, numeros))


def executar():
    arquivo = Path(os.environ.get('CTIC_TESTE_USUARIO', Path(__file__).resolve().parent.parent / 'configuracao/primeiro-usuario.local.php'))
    configuracao = arquivo.read_text(encoding='utf-8')
    email = re.search(r"'email'\s*=>\s*'([^']+)'", configuracao)[1]
    senha = re.search(r"'senha'\s*=>\s*'([^']+)'", configuracao)[1]
    administrador = ClienteTeste()
    conferir(administrador.entrar(email, senha)[0] == 200, 'Falha na entrada administrativa.')
    marcador = secrets.token_hex(6)
    senha_teste = secrets.token_hex(16)
    cadastros = []
    try:
        for indice in range(2):
            cadastro = {'nome': f'TESTE FLUXOS {marcador} {indice}', 'email': f'fluxos-{marcador}-{indice}@example.com',
                        'setor': 'CTIC', 'perfil': 'solicitante', 'ativo': True}
            codigo, resposta = administrador.requisitar('/api/usuarios', 'POST', dict(cadastro, senha=senha_teste))
            conferir(codigo == 201, 'Cadastro de teste falhou.')
            cadastro['id'] = resposta['id']
            cadastros.append(cadastro)
        dono, outro = ClienteTeste(), ClienteTeste()
        conferir(dono.requisitar('/api/passageiros')[0] == 401, 'Catálogo sem autenticação.')
        conferir(dono.entrar(cadastros[0]['email'], senha_teste)[0] == 200, 'Falha na entrada do solicitante.')
        conferir(outro.entrar(cadastros[1]['email'], senha_teste)[0] == 200, 'Falha na entrada da segunda conta.')
        passageiro = {'nome': 'PASSAGEIRO TESTE <texto>', 'cpf': cpf_teste(), 'telefone': '(92) 99999-0000', 'setor': 'CTIC', 'vinculo': 'Servidor'}
        conferir(dono.requisitar('/api/passageiros', 'POST', passageiro, proteger=False)[0] == 419, 'Cadastro sem CSRF.')
        conferir(dono.requisitar('/api/passageiros', 'POST', dict(passageiro, cpf='11111111111'))[0] == 422, 'CPF inválido aceito.')
        codigo, resposta = dono.requisitar('/api/passageiros', 'POST', passageiro)
        conferir(codigo == 201, 'Cadastro de passageiro falhou.')
        pessoa = resposta['id']
        conferir(dono.requisitar('/api/passageiros', 'POST', passageiro)[0] == 409, 'CPF duplicado aceito.')
        for metodo, dados in [('GET', None), ('PUT', passageiro), ('DELETE', None)]:
            conferir(outro.requisitar(f'/api/passageiros/{pessoa}', metodo, dados)[0] == 404, 'Passageiro exposto a outra conta.')
        conferir(not outro.requisitar('/api/passageiros')[1]['passageiros'], 'Listagem de passageiros expôs outra conta.')
        conferir(outro.requisitar('/api/solicitacoes/rascunho', 'PUT', {'passageiros_ids': [pessoa]})[0] == 422, 'Selecionou passageiro alheio.')
        conferir(dono.requisitar('/api/solicitacoes/rascunho', 'PUT', {'passageiros_ids': [pessoa, pessoa]})[0] == 422, 'Passageiro repetido aceito.')
        viagem = {'tipo_deslocamento': 'Intermunicipal', 'destino': 'TESTE FLUXO ' + marcador, 'finalidade': 'Validação',
                  'saida_em': '2026-12-20T08:00', 'retorno_em': '2026-12-20T18:00', 'local_embarque': 'CTIC',
                  'centro_custo': 'CTIC', 'justificativa': 'TESTE AUTOMATIZADO'}

        def enviar():
            codigo, resposta = dono.requisitar('/api/solicitacoes/rascunho', 'PUT', {'viagem': viagem,
                'contato': {'telefone': '(92) 99999-0000', 'setor': 'CTIC', 'vinculo': 'Servidor'}, 'passageiros_ids': [pessoa]})
            conferir(codigo == 200, 'Falha no rascunho.')
            codigo, resposta = dono.requisitar('/api/solicitacoes', 'POST', {'declaracao': True})
            conferir(codigo == 201, 'Falha no envio.')
            return resposta['id']

        pedido = enviar()
        conferir(dono.requisitar(f'/api/passageiros/{pessoa}', 'PUT', dict(passageiro, nome='NOME EDITADO'))[0] == 200, 'Edição de passageiro falhou.')
        conferir(dono.requisitar(f'/api/solicitacoes/{pedido}')[1]['solicitacao']['passageiros'][0]['nome'] == passageiro['nome'], 'Edição mudou viagem antiga.')
        conferir(dono.requisitar(f'/api/solicitacoes/{pedido}/analise', 'POST', {'status': 'aprovada'})[0] == 403, 'Solicitante analisou pedido.')
        conferir(administrador.requisitar(f'/api/solicitacoes/{pedido}/analise', 'POST', {'status': 'aprovada'})[0] == 422, 'Aprovou sem veículo e motorista.')
        conferir(administrador.requisitar(f'/api/solicitacoes/{pedido}/analise', 'POST', {'status': 'aprovada', 'veiculo': 'Van de teste', 'motorista': 'Motorista teste'})[0] == 200, 'Aprovação falhou.')
        detalhes = dono.requisitar(f'/api/solicitacoes/{pedido}')[1]['solicitacao']
        conferir(detalhes['veiculo'] == 'Van de teste' and detalhes['motorista'] == 'Motorista teste', 'Designação não foi salva.')
        conferir(len(detalhes['historico']) == 2 and detalhes['historico'][1]['observacao'], 'Histórico de aprovação ausente.')
        conferir(administrador.requisitar(f'/api/solicitacoes/{pedido}/status', 'PATCH', {'status': 'concluida'})[0] == 200, 'Conclusão falhou.')
        conferir(administrador.requisitar(f'/api/solicitacoes/{pedido}/status', 'PATCH', {'status': 'pendente'})[0] == 409, 'Pedido concluído reaberto.')
        conferir(dono.requisitar(f'/api/solicitacoes/{pedido}/cancelar', 'POST', {'motivo': 'Teste'})[0] == 409, 'Pedido concluído cancelado.')
        cancelado = enviar()
        conferir(outro.requisitar(f'/api/solicitacoes/{cancelado}/cancelar', 'POST', {'motivo': 'Teste'})[0] == 404, 'Pedido alheio cancelado.')
        conferir(dono.requisitar(f'/api/solicitacoes/{cancelado}/cancelar', 'POST', {})[0] == 422, 'Cancelou sem motivo.')
        conferir(dono.requisitar(f'/api/solicitacoes/{cancelado}/cancelar', 'POST', {'motivo': 'TESTE CANCELAMENTO'})[0] == 200, 'Cancelamento falhou.')
        detalhes = dono.requisitar(f'/api/solicitacoes/{cancelado}')[1]['solicitacao']
        conferir(detalhes['status'] == 'cancelada' and detalhes['motivo_cancelamento'] == 'TESTE CANCELAMENTO', 'Motivo não foi salvo.')
        codigo, resposta = dono.requisitar('/api/solicitacoes?status=cancelada&busca=' + marcador)
        conferir(codigo == 200 and len(resposta['solicitacoes']) == 1, 'Filtros da API falharam.')
        conferir(dono.requisitar('/api/solicitacoes?status=inexistente')[0] == 422, 'Filtro inválido aceito.')
        conferir(dono.requisitar(f'/api/passageiros/{pessoa}', 'DELETE')[0] == 200, 'Remoção de passageiro falhou.')
        conferir(dono.requisitar(f'/api/solicitacoes/{pedido}')[1]['solicitacao']['passageiros'], 'Remoção apagou histórico.')
        conferir(dono.requisitar('/api/passageiros', 'POST', passageiro)[0] == 201, 'CPF removido não pôde ser recadastrado.')
        codigo, _ = dono.requisitar('/api/conta', 'PUT', {'nome': 'NOME ATUALIZADO', 'setor': 'NTI', 'perfil': 'administrador', 'email': 'alterado@example.com'})
        conferir(codigo == 200, 'Atualização da conta falhou.')
        usuario = dono.requisitar('/api/conta')[1]['usuario']
        conferir(usuario['perfil'] == 'solicitante' and usuario['email'] == cadastros[0]['email'], 'Edição da conta elevou permissões.')
        sessao_antiga = ClienteTeste()
        conferir(sessao_antiga.entrar(cadastros[0]['email'], senha_teste)[0] == 200, 'Segunda sessão falhou.')
        nova_senha = secrets.token_hex(16)
        conferir(dono.requisitar('/api/conta/senha', 'PUT', {'senha_atual': 'errada', 'nova_senha': nova_senha, 'confirmacao_senha': nova_senha})[0] == 422, 'Senha atual ignorada.')
        conferir(dono.requisitar('/api/conta/senha', 'PUT', {'senha_atual': senha_teste, 'nova_senha': nova_senha, 'confirmacao_senha': nova_senha})[0] == 200, 'Troca de senha falhou.')
        conferir(sessao_antiga.requisitar('/api/conta')[0] == 401, 'Troca de senha preservou sessão antiga.')
        conferir(dono.requisitar('/api/conta')[0] == 200, 'Troca de senha encerrou a própria sessão.')

        visitante = ClienteTeste()
        visitante.token = visitante.requisitar('/api/autenticacao/csrf')[1]['csrf']
        conferir(visitante.requisitar('/api/autenticacao/recuperar', 'POST', {'email': cadastros[0]['email']}, proteger=False)[0] == 419, 'Recuperação sem CSRF.')
        codigo, mensagem_real = visitante.requisitar('/api/autenticacao/recuperar', 'POST', {'email': cadastros[0]['email']})
        codigo_falso, mensagem_falsa = visitante.requisitar('/api/autenticacao/recuperar', 'POST', {'email': f'inexistente-{marcador}@example.com'})
        conferir(codigo == codigo_falso == 200 and mensagem_real == mensagem_falsa, 'Recuperação revelou cadastro.')
        if os.environ.get('CTIC_TESTE_EMAIL_LOCAL') == '1':
            # Eu leio só a mensagem de teste para verificar o token sem mostrar segredos no terminal.
            pasta = Path(__file__).resolve().parent.parent / 'armazenamento/emails'
            mensagens = [p for p in pasta.glob('*.txt') if cadastros[0]['email'] in p.read_text(encoding='utf-8')]
            conferir(len(mensagens) == 1, 'Mensagem de recuperação não foi gerada.')
            token = re.search(r'#token=([a-f0-9]{64})', mensagens[0].read_text(encoding='utf-8'))[1]
            senha_recuperada = secrets.token_hex(16)
            dados = {'token': token, 'senha': senha_recuperada, 'confirmacao_senha': senha_recuperada}
            conferir(visitante.requisitar('/api/autenticacao/redefinir', 'POST', dados)[0] == 200, 'Recuperação de senha falhou.')
            conferir(dono.requisitar('/api/conta')[0] == 401, 'Recuperação não invalidou sessão.')
            visitante.token = visitante.requisitar('/api/autenticacao/csrf')[1]['csrf']
            conferir(visitante.requisitar('/api/autenticacao/redefinir', 'POST', dados)[0] == 422, 'Token reutilizado.')
            conferir(visitante.entrar(cadastros[0]['email'], senha_recuperada)[0] == 200, 'Senha recuperada não funciona.')
            mensagens[0].unlink()
        print('APROVADO: passageiros, CPF, isolamento, seleção, histórico preservado, aprovação, conclusão, cancelamento, filtros, conta e recuperação.')
    finally:
        for cadastro in cadastros:
            administrador.requisitar(f"/api/usuarios/{cadastro['id']}", 'PUT', dict(cadastro, ativo=False))


if __name__ == '__main__':
    executar()
