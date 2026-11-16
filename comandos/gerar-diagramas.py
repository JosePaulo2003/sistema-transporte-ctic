#!/usr/bin/env python3
"""Gera diagramas nativos editáveis do draw.io e, opcionalmente, suas visualizações SVG."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import textwrap
import unicodedata
import xml.etree.ElementTree as XML


RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / 'documentacao/diagramas'
CORES = {
    'verde': ('#E5F4EC', '#087443'), 'azul': ('#EAF1FB', '#386AA3'),
    'amarelo': ('#FFF5D8', '#A77B16'), 'vermelho': ('#FCE9E9', '#B04747'),
    'cinza': ('#F0F3F5', '#657786'), 'branco': ('#FFFFFF', '#AAB8B1'),
}


class Pagina:
    def __init__(self, arquivo, numero, nome, subtitulo, altura=1100, largura=1700):
        self.numero = numero
        self.nome = nome
        self.largura = largura
        self.altura = altura
        pagina = XML.SubElement(arquivo, 'diagram', id='ctic-' + str(numero), name=f'{numero:02d} {nome}')
        modelo = XML.SubElement(pagina, 'mxGraphModel', dx=str(largura), dy=str(altura), grid='1', gridSize='10',
                                guides='1', tooltips='1', connect='1', arrows='1', fold='1', page='1',
                                pageScale='1', pageWidth=str(largura), pageHeight=str(altura), background='#FFFFFF', math='0', shadow='0')
        self.raiz = XML.SubElement(modelo, 'root')
        XML.SubElement(self.raiz, 'mxCell', id='0')
        XML.SubElement(self.raiz, 'mxCell', id='1', parent='0')
        self.indice = 1
        self.texto(45, 24, largura - 90, 42, f'{numero:02d}  /  {nome.upper()}', 26, '#075C35', True)
        self.texto(45, 78, largura - 90, 45, subtitulo, 15, '#56665F')
        self.texto(45, altura - 45, largura - 90, 25, 'CTIC  •  Sistema de Transportes  •  Estado documentado em 16/11/2026  •  Sem dados ou credenciais da instalação', 12, '#657786')

    def identificador(self):
        self.indice += 1
        return f'p{self.numero}-n{self.indice}'

    def celula(self, texto, estilo, x, y, largura, altura, pai='1'):
        identificador = self.identificador()
        celula = XML.SubElement(self.raiz, 'mxCell', id=identificador, value=texto, style=estilo,
                               vertex='1', parent=pai)
        XML.SubElement(celula, 'mxGeometry', x=str(x), y=str(y), width=str(largura), height=str(altura), **{'as': 'geometry'})
        return identificador

    def texto(self, x, y, largura, altura, texto, tamanho=15, cor='#213D30', negrito=False):
        texto = '\n'.join(textwrap.fill(linha, width=max(10,int(largura / (tamanho * .54))), break_long_words=False, break_on_hyphens=False) for linha in texto.splitlines())
        return self.celula(texto, f'text;html=0;whiteSpace=wrap;align=left;verticalAlign=middle;fontFamily=Arial;fontSize={tamanho};fontColor={cor};fontStyle={1 if negrito else 0};spacing=0;', x, y, largura, altura)

    def caixa(self, x, y, largura, altura, titulo, linhas=(), cor='verde', forma='retangulo'):
        fundo, borda = CORES[cor]
        formato = {'retangulo': 'rounded=1;arcSize=8;', 'decisao': 'rhombus;', 'banco': 'shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=18;',
                   'estado': 'rounded=1;arcSize=40;'}[forma]
        identificador = self.celula('', formato + f'html=0;whiteSpace=wrap;fillColor={fundo};strokeColor={borda};strokeWidth=1.5;', x, y, largura, altura)
        if forma == 'decisao':
            self.celula(titulo + ('\n' + '\n'.join(linhas) if linhas else ''), 'text;html=0;whiteSpace=wrap;align=center;verticalAlign=middle;fontSize=15;fontFamily=Arial;fontStyle=1;', 10, 5, largura - 20, altura - 10, identificador)
        else:
            margem = 25 if forma == 'banco' else 12
            self.celula(titulo, 'text;html=0;whiteSpace=wrap;align=left;verticalAlign=middle;fontSize=16;fontFamily=Arial;fontStyle=1;fontColor=#163E2A;', 16, margem, largura - 32, 34, identificador)
            if linhas:
                corpo = '\n'.join(textwrap.fill(linha, width=max(10,int((largura - 32) / 7.56)), break_long_words=False, break_on_hyphens=False) for linha in linhas)
                self.celula(corpo, 'text;html=0;whiteSpace=wrap;align=left;verticalAlign=top;fontSize=14;fontFamily=Arial;spacingTop=2;fontColor=#263E31;', 16, margem + 42, largura - 32, altura - margem - 52, identificador)
        return identificador

    def seta(self, origem, destino, rotulo='', tracejada=False, pontos=(), estilo=''):
        identificador = self.identificador()
        celula = XML.SubElement(self.raiz, 'mxCell', id=identificador, value=rotulo, edge='1', parent='1', source=origem, target=destino,
                               style='edgeStyle=orthogonalEdgeStyle;rounded=1;html=0;endArrow=block;endFill=1;strokeColor=#61766B;strokeWidth=1.5;'
                               'fontFamily=Arial;fontSize=12;labelBackgroundColor=#FFFFFF;' + ('dashed=1;' if tracejada else '') + estilo)
        geometria = XML.SubElement(celula, 'mxGeometry', relative='1', **{'as': 'geometry'})
        if pontos:
            vetor = XML.SubElement(geometria, 'Array', **{'as': 'points'})
            for x, y in pontos:
                XML.SubElement(vetor, 'mxPoint', x=str(x), y=str(y))
        return identificador

    def faixa(self, y, titulo):
        self.texto(45, y, self.largura - 90, 30, titulo, 18, '#075C35', True)


def criar_diagramas():
    arquivo = XML.Element('mxfile', host='Electron', agent='CTIC', version='32.6.10', type='device', compressed='false')
    p = Pagina(arquivo, 1, 'Contexto e implantação', 'Pessoas, aplicação, persistência e fronteiras entre o ambiente local e a hospedagem.')
    solicitante = p.caixa(50, 170, 280, 145, 'Solicitante', ['Gerencia seus passageiros', 'Envia e acompanha seus pedidos', 'Cancela pedidos ainda abertos'])
    admin = p.caixa(50, 405, 280, 155, 'Administrador', ['Consulta todos os pedidos', 'Analisa, aprova e conclui', 'Administra contas de acesso'], 'azul')
    navegador = p.caixa(435, 245, 300, 185, 'Navegador', ['HTML + CSS + JavaScript', 'fetch com JSON', 'Cookie de sessão HttpOnly', 'Sem persistência no localStorage'])
    servidor = p.caixa(855, 245, 325, 185, 'Servidor PHP', ['public/index.php', 'Sessão, CSRF e autorização', 'Regras em aplicacao/', 'Consultas preparadas PDO'])
    banco = p.caixa(1290, 225, 320, 205, 'MySQL', ['12 tabelas', 'Dados + histórico + controles', 'Conta restrita à aplicação'], 'azul', 'banco')
    local = p.caixa(855, 565, 325, 170, 'Arquivos privados locais', ['configuracao/*.local.php', 'CREDENCIAIS.local.txt', 'armazenamento/emails e logs', 'Não entram na entrega'], 'amarelo')
    workbench = p.caixa(1290, 565, 320, 170, 'MySQL Workbench', ['Cliente administrativo separado', 'Acessa o mesmo servidor MySQL', 'Não é o servidor do sistema'], 'cinza')
    p.seta(solicitante, navegador, 'usa'); p.seta(admin, navegador, 'usa'); p.seta(navegador, servidor, 'HTTP / JSON')
    p.seta(servidor, banco, 'PDO + transações'); p.seta(servidor, local, 'configuração e mensagens'); p.seta(workbench, banco, 'conexão administrativa', True)
    p.faixa(815, 'DOIS MODOS DE EXECUÇÃO')
    p.caixa(50, 870, 725, 115, 'Desenvolvimento', ['iniciar.cmd ou iniciar.sh → PHP em 127.0.0.1:8080', 'roteador.php permite somente recursos estáticos públicos.'], 'cinza')
    p.caixa(855, 870, 755, 115, 'Hospedagem', ['Apache com DocumentRoot em public/ + mod_rewrite + HTTPS', 'Configuração, documentação, testes, Git e dados ficam fora do diretório público.'], 'cinza')

    p = Pagina(arquivo, 2, 'Componentes do código', 'Responsabilidade de cada módulo e dependências internas. O projeto não utiliza um framework de aplicação.')
    entrada = p.caixa(55, 170, 300, 145, 'Entradas', ['index.php → public/index.php', 'roteador.php (servidor local)', '.htaccess / public/.htaccess'])
    controlador = p.caixa(475, 170, 350, 160, 'public/index.php', ['Despacha páginas e APIs', 'Preserva links antigos', 'Injeta identidade e scripts', 'Bloqueia páginas administrativas'])
    inicializacao = p.caixa(995, 170, 625, 160, 'aplicacao/inicializacao.php', ['Configuração + PDO + sessão + CSRF', 'Login, limites de tentativa, resposta JSON e identidade pública', 'Verifica usuário ativo e assinatura da senha em cada acesso'], 'azul')
    regras = [
        (55, 'solicitacoes.php', ['Validação dos campos', 'Datas locais e passageiros']),
        (450, 'fluxo-solicitacoes.php', ['Rascunho e envio', 'Consulta, status e histórico']),
        (845, 'passageiros.php', ['CPF e cadastro reutilizável', 'Seleção somente pelo dono']),
        (1240, 'usuarios.php / conta.php', ['Administração e perfil próprio', 'Senha e recuperação']),
    ]
    ids = [p.caixa(x, 460, 335, 145, titulo, linhas, 'verde') for x, titulo, linhas in regras]
    p.seta(entrada, controlador); p.seta(controlador, inicializacao, 'serviços compartilhados')
    for identificador in ids:
        p.seta(controlador, identificador, 'API', pontos=[(650, 385)])
    p.caixa(55, 780, 460, 200, 'Frontend', ['views/pages/ + views/css/', 'api.js: requisições e CSRF', 'sessao.js: identidade e saída', 'telas.js: fluxo e cadastros', 'usuarios.js / entrada.js / recuperacao.js'], 'azul')
    p.caixa(605, 780, 460, 200, 'Operação', ['configurar.php / configurar.ps1', 'preparar.php → migrar.php', 'banco-de-dados/migracoes/*.sql', 'php.ps1 / php.sh / iniciar.*'], 'cinza')
    p.caixa(1155, 780, 460, 200, 'Qualidade e entrega', ['testes/*.php e *.py', 'entrega.py + entrega.json', '.githooks/pre-commit e pre-push', 'documentacao/ e diagramas'], 'amarelo')

    p = Pagina(arquivo, 3, 'Modelo físico de dados', 'PK = chave primária; FK = chave estrangeira; UK = unicidade. Relações representam as restrições reais do banco.', altura=1530, largura=1940)
    tabelas = []
    for caminho in sorted((RAIZ / 'banco-de-dados/migracoes').glob('*.sql')):
        tabelas.extend(re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\) ENGINE', caminho.read_text(encoding='utf-8'), re.S))
    campos = {}
    for nome, corpo in tabelas:
        linhas = []
        for linha in corpo.splitlines():
            linha = linha.strip().rstrip(',')
            if not linha or linha.startswith(('FOREIGN KEY','UNIQUE KEY','INDEX')):
                continue
            if linha.startswith('PRIMARY KEY'):
                linhas.append('PK composta: solicitacao_id + passageiro_id'); continue
            campo, _, tipo = linha.partition(' ')
            estrangeira = campo in {'usuario_id','solicitacao_id','passageiro_id','historico_id'}
            rotulo = ('PK/FK ' if estrangeira else 'PK ') if 'PRIMARY KEY' in tipo else 'FK ' if estrangeira else '    '
            if nome == 'solicitacoes' and campo == 'status': tipo = 'ENUM (inclui cancelada após 003)'
            elif campo == 'cpf_ativo': tipo = 'CHAR(11) gerado; UK com usuario_id'
            else: tipo = re.sub(r'\s+(NOT NULL|NULL|DEFAULT|AUTO_INCREMENT|PRIMARY KEY|ON UPDATE|GENERATED).*', '', tipo)
            linhas.append(rotulo + campo + '  ' + tipo)
        campos[nome] = linhas
    campos['migracoes_aplicadas'] = ['PK nome VARCHAR(190)', '    resumo CHAR(64)', '    aplicada_em DATETIME', 'Criada por comandos/migrar.php']
    posicoes = {
        'usuarios': (50,160,350,335), 'solicitacoes': (545,160,400,600),
        'passageiros': (1080,160,350,230), 'solicitacao_passageiros': (1080,515,350,180),
        'historico_solicitacoes': (1530,160,350,285), 'observacoes_historico': (1530,555,350,145),
        'cadastros_passageiros': (50,640,350,385), 'atendimentos_solicitacoes': (545,885,400,175),
        'recuperacoes_senha': (50,1140,350,255), 'tentativas_acesso': (1080,1130,350,190),
        'tentativas_recuperacao': (1530,1130,350,190), 'migracoes_aplicadas': (545,1205,400,165),
    }
    ids = {}
    for nome, (x,y,l,a) in posicoes.items():
        ids[nome] = p.caixa(x,y,l,a,nome,campos[nome], 'azul' if nome in {'usuarios','solicitacoes'} else 'branco')
    for origem, destino, rotulo, pontos, ancoras in [
        ('usuarios','solicitacoes','1 → 0..N',[],(1,.5,0,.25)),
        ('usuarios','cadastros_passageiros','1 → 0..N',[],(.5,1,.5,0)),
        ('usuarios','recuperacoes_senha','1 → 0..N',[(20,428),(20,1110),(225,1110)],(0,.8,.5,0)),
        ('usuarios','passageiros','1 → 0..N',[(450,200),(450,130),(1255,130)],(1,.12,.5,0)),
        ('usuarios','historico_solicitacoes','1 → 0..N (autor)',[(470,260),(470,145),(1705,145)],(1,.3,.5,0)),
        ('solicitacoes','solicitacao_passageiros','1 → 0..N',[],(1,.68,0,.4)),
        ('passageiros','solicitacao_passageiros','1 → 0..N',[],(.5,1,.5,0)),
        ('solicitacoes','historico_solicitacoes','1 → 0..N',[(1000,430),(1470,430),(1470,300)],(1,.45,0,.5)),
        ('solicitacoes','atendimentos_solicitacoes','1 → 0..1',[],(.5,1,.5,0)),
        ('historico_solicitacoes','observacoes_historico','1 → 0..1',[],(.5,1,.5,0)),
    ]:
        sx,sy,tx,ty=ancoras
        p.seta(ids[origem],ids[destino],rotulo,pontos=pontos,estilo=f'exitX={sx};exitY={sy};entryX={tx};entryY={ty};')
    p.texto(1080,800,800,160,'SEM FK DIRETA: cadastros_passageiros → passageiros. O envio copia nome, setor e vínculo para preservar a viagem.\n\nTentativas e migrações são tabelas independentes. CPF ativo é único por usuário; e-mail de usuário e hash_token também são únicos.',15)

    p = Pagina(arquivo, 4, 'Autenticação e sessão', 'Sequência do login e verificações posteriores; as setas numeradas indicam a ordem.')
    a = p.caixa(55,170,290,150,'Navegador / entrada.js',['GET /entrar', 'Recebe token CSRF no formulário'])
    b = p.caixa(480,170,320,150,'API /autenticacao/entrar',['POST com e-mail e senha', 'X-CSRF-Token obrigatório'])
    c = p.caixa(955,170,350,175,'autenticar()',['Valida formato e limites', 'Registra tentativa antes do hash', 'password_verify + conta ativa'], 'azul')
    d = p.caixa(955,480,350,175,'MySQL',['usuarios + tentativas_acesso', '5 tentativas/e-mail em 15 min', '30 tentativas/IP em 15 min'], 'azul','banco')
    e = p.caixa(480,490,320,185,'Sessão renovada',['Novo ID + novo CSRF', 'usuario_id e tempos no servidor', 'Assinatura SHA-256 do hash', 'Cookie HttpOnly / SameSite=Lax'])
    f = p.caixa(55,500,290,175,'GET /painel',['Identidade vem do servidor', 'Somente campos públicos', 'HTML e JSON com escape'])
    p.seta(a,b,'1. enviar');p.seta(b,c,'2. validar');p.seta(c,d,'3. consultar / atualizar');p.seta(c,e,'4. credenciais válidas');p.seta(e,f,'5. abrir painel')
    p.faixa(810,'A CADA REQUISIÇÃO AUTENTICADA')
    p.caixa(55,860,730,140,'usuario_atual()',['Reconsulta usuário ativo e perfil; compara assinatura da senha.', 'Expira após 30 minutos de inatividade ou 8 horas de duração (configuráveis).'], 'cinza')
    p.caixa(890,860,730,140,'Recusa e saída',['Sem sessão: API 401; página protegida redireciona para /entrar.', 'Conta desativada, senha redefinida ou logout invalidam o acesso.'], 'vermelho')

    p = Pagina(arquivo,5,'Solicitação de transporte','O rascunho é da sessão; somente o envio final cria a viagem e seus passageiros no MySQL.')
    a=p.caixa(45,170,320,150,'1. Dados da viagem',['/nova-solicitacao','Tipo, destino, finalidade, datas','Embarque, centro e justificativa'])
    b=p.caixa(465,170,320,150,'2. Contato do responsável',['/solicitantes','Nome/e-mail da conta autenticada','Telefone, setor e vínculo'])
    c=p.caixa(885,170,320,150,'3. Passageiros',['/passageiros','Seleciona cadastros próprios','De 1 a 50 no envio'])
    d=p.caixa(1305,170,320,150,'4. Revisão e declaração',['/revisao-envio','Revê todos os dados','Declaração precisa ser true'])
    r=p.caixa(465,445,740,150,'Rascunho na sessão PHP',['PUT /api/solicitacoes/rascunho por etapa','Ainda não há solicitação gravada; descartar usa DELETE.','É compartilhado entre abas da mesma sessão.'],'azul')
    for x,y in [(a,b),(b,c),(c,d)]:p.seta(x,y)
    for x in [a,b,c]:p.seta(x,r,'salvar etapa',True)
    envio=p.caixa(1305,465,320,140,'POST /api/solicitacoes',['Validação completa no servidor','Declaração + CSRF + sessão'])
    tx=p.caixa(885,775,740,175,'Uma transação MySQL',['INSERT solicitacoes → cópias em passageiros → vínculos','INSERT histórico inicial com status pendente → COMMIT','Falha em qualquer etapa: ROLLBACK. Sucesso: limpa rascunho.'],'azul')
    sucesso=p.caixa(45,775,610,175,'Confirmação e acompanhamento',['/solicitacao-enviada?id=... → protocolo real','/detalhes-solicitacao?id=... → dados e histórico','Listagem e painel consultam somente os pedidos permitidos.'])
    p.seta(d,envio);p.seta(envio,tx);p.seta(tx,sucesso,'201 + identificador')

    p=Pagina(arquivo,6,'Estados da solicitação','Transições reais de validar_transicao_solicitacao(). Operações repetidas no mesmo estado não geram novo histórico.')
    pendente=p.caixa(80,205,300,130,'PENDENTE',['Estado inicial após o envio'],forma='estado')
    analise=p.caixa(620,205,300,130,'EM ANÁLISE',['Ação administrativa'], 'azul','estado')
    aprovada=p.caixa(1160,205,340,150,'APROVADA',['Exige veículo e motorista','Ação administrativa'],forma='estado')
    recusada=p.caixa(350,595,300,145,'RECUSADA',['Estado terminal','Ação administrativa'],'vermelho','estado')
    cancelada=p.caixa(830,595,300,145,'CANCELADA',['Estado terminal; exige motivo','Dono do pedido ou administrador'],'amarelo','estado')
    concluida=p.caixa(1305,595,300,145,'CONCLUÍDA',['Estado terminal','Ação administrativa'],'azul','estado')
    p.seta(pendente,analise,'iniciar análise',estilo='exitX=1;exitY=.5;entryX=0;entryY=.5;')
    p.seta(analise,aprovada,'aprovar',estilo='exitX=1;exitY=.5;entryX=0;entryY=.5;')
    p.seta(aprovada,concluida,'concluir',pontos=[(1398,470),(1455,470)],estilo='exitX=.7;exitY=1;entryX=.5;entryY=0;')
    p.seta(pendente,aprovada,'aprovar diretamente',pontos=[(230,145),(1330,145)],estilo='exitX=.5;exitY=0;entryX=.5;entryY=0;')
    p.seta(pendente,recusada,'recusar',pontos=[(170,440),(440,440)],estilo='exitX=.3;exitY=1;entryX=.3;entryY=0;')
    p.seta(analise,recusada,'recusar',pontos=[(695,405),(560,405)],estilo='exitX=.25;exitY=1;entryX=.7;entryY=0;')
    p.seta(pendente,cancelada,'cancelar',pontos=[(290,505),(905,505)],estilo='exitX=.7;exitY=1;entryX=.25;entryY=0;')
    p.seta(analise,cancelada,'cancelar',pontos=[(845,450),(980,450)],estilo='exitX=.75;exitY=1;entryX=.5;entryY=0;')
    p.seta(aprovada,cancelada,'cancelar',pontos=[(1245,490),(1055,490)],estilo='exitX=.25;exitY=1;entryX=.75;entryY=0;')
    p.caixa(80,865,1525,125,'Integridade do histórico',['SELECT ... FOR UPDATE bloqueia o pedido durante a mudança. Status, atendimento e histórico são gravados na mesma transação.', 'Pedido alheio retorna 404. Transição proibida retorna 409. Estados terminais não são reabertos pela API.'],'cinza')

    p=Pagina(arquivo,7,'Passageiros e privacidade','O catálogo reutilizável e os passageiros de uma viagem têm finalidades e ciclos de vida diferentes.')
    usuario=p.caixa(55,185,300,170,'Usuário autenticado',['Cadastro é sempre privado por dono','Administrador também consulta','somente seu próprio catálogo'])
    catalogo=p.caixa(500,185,445,230,'cadastros_passageiros',['Nome, CPF válido, telefone, setor e vínculo','CPF ativo único por usuario_id','GET / POST / PUT / DELETE na API','DELETE marca ativo=0; não apaga histórico'],'azul','banco')
    draft=p.caixa(1130,185,470,230,'Seleção para o rascunho',['passageiros_ids: inteiros distintos','Somente cadastros ativos do próprio usuário','Até 50; zero é aceito apenas no rascunho','API copia os dados para a sessão'])
    snapshot=p.caixa(500,630,445,220,'passageiros + vínculo da viagem',['O envio final cria cópias independentes','Somente nome, setor, vínculo e usuario_id','solicitacao_passageiros faz a associação','Sem FK para o catálogo reutilizável'],'azul','banco')
    edits=p.caixa(1130,660,470,175,'Editar ou remover depois',['Afeta apenas o catálogo','As cópias das viagens não mudam','Passageiros alheios retornam 404'],'amarelo')
    p.seta(usuario,catalogo,'seu cadastro');p.seta(catalogo,draft,'selecionar');p.seta(draft,snapshot,'envio final');p.seta(catalogo,edits,'manutenção');p.seta(edits,snapshot,'não altera',True)
    p.texto(55,925,1545,70,'A API legada também aceita passageiros informados diretamente no rascunho (nome, setor e vínculo); a interface atual usa o catálogo privado. Nenhum cadastro real ou dump com pessoas deve acompanhar a entrega.',15)

    p=Pagina(arquivo,8,'Recuperação e troca de senha','O token bruto aparece somente no link gerado; o banco guarda seu hash. A recuperação não revela se uma conta existe.')
    pedido=p.caixa(45,175,340,160,'Solicitar recuperação',['/recuperar-senha','POST /api/autenticacao/recuperar','E-mail válido + CSRF'])
    validacao=p.caixa(535,175,390,190,'Servidor',['Limite: 5 pedidos por e-mail OU IP','Janela de 15 minutos','Mesmo texto para conta inexistente','Conta existente precisa estar ativa'],'azul')
    token=p.caixa(1090,175,520,190,'recuperacoes_senha',['Token aleatório de 32 bytes (64 hex)','SHA-256 do token + assinatura do hash da senha','Expiração em 30 minutos','Marca de uso impede reutilização'],'azul','banco')
    mensagem=p.caixa(1090,530,520,180,'Entrega da mensagem',['Local: TXT privado em armazenamento/emails','Externo: mail() com remetente e servidor configurados','Sem configuração, não há entrega externa.'],'amarelo')
    redefinir=p.caixa(535,530,390,205,'Redefinir senha',['/redefinir-senha#token=...','Token sai da URL após leitura','POST /api/autenticacao/redefinir','12–72 bytes + confirmação','Validação e atualização transacionais'])
    fim=p.caixa(45,550,340,175,'Novo acesso',['Hash de senha é substituído','Todos os tokens pendentes são usados','Sessões antigas são recusadas','Usuário entra novamente'])
    p.seta(pedido,validacao);p.seta(validacao,token,'somente conta ativa');p.seta(token,mensagem,'link com token bruto');p.seta(mensagem,redefinir,'abrir link');p.seta(redefinir,fim,'senha salva')
    p.caixa(45,875,1565,120,'Outras duas formas de alterar senha',['Minha conta: exige a senha atual, preserva a sessão que fez a troca e invalida as outras.', 'Administração: administrador redefine a senha de uma conta; não envia e-mail nem exige troca no próximo login.'],'cinza')

    p=Pagina(arquivo,9,'API e autorização','Todas as escritas exigem CSRF. Respostas usam JSON e dados pessoais nunca são retornados sem autorização.',altura=1210)
    p.caixa(45,170,490,270,'Acesso público + CSRF nas escritas',['GET  /api/autenticacao/csrf','POST /api/autenticacao/entrar','POST /api/autenticacao/recuperar','POST /api/autenticacao/redefinir','Formatos e limites são validados no servidor.'],'azul')
    p.caixa(605,170,490,270,'Usuário autenticado',['GET /api/autenticacao/usuario','POST /api/autenticacao/sair','GET/PUT /api/conta','PUT /api/conta/senha','GET/POST /api/passageiros','GET/PUT/DELETE /api/passageiros/{id}'])
    p.caixa(1165,170,490,270,'Dono ou administrador: pedidos',['GET/POST /api/solicitacoes','GET/PUT/DELETE /.../rascunho','GET /api/solicitacoes/{id}','POST /api/solicitacoes/{id}/cancelar','Solicitante vê somente seus pedidos.'])
    p.caixa(45,570,760,235,'Somente administrador',['GET/POST /api/usuarios','PUT /api/usuarios/{id}','POST /api/usuarios/{id}/senha','PATCH /api/solicitacoes/{id}/status','POST /api/solicitacoes/{id}/analise'],'azul')
    p.caixa(900,570,755,235,'Matriz de acesso: solicitante / administrador',['Catálogo de passageiros: próprio / próprio','Pedidos: próprios / todos','Análise e status: não / sim','Cancelamento: próprio / qualquer pedido aberto','Administração de usuários: não / sim'],'cinza')
    p.caixa(45,925,1610,140,'Respostas e proteções comuns',['400 JSON inválido • 401 sem sessão • 403 sem permissão • 404 inexistente ou alheio • 405 método incorreto', '409 conflito / transição inválida • 413 corpo >16 KiB • 415 tipo inválido • 419 CSRF • 422 validação • 429 limite • 503 serviço indisponível', 'Usuários ativos, perfil e assinatura da senha são conferidos pelo servidor; ocultar botões não é uma barreira de segurança.'],'amarelo')

    p=Pagina(arquivo,10,'Navegação das telas','Rotas atuais; os arquivos HTML antigos são redirecionados pelo controlador. O painel usa login.html por compatibilidade.',altura=1300)
    a=p.caixa(45,175,325,140,'Acesso público',['/entrar','/recuperar-senha','/confirmar-email /redefinir-senha'],'azul')
    painel=p.caixa(500,175,360,140,'/painel',['Indicadores e pedidos recentes','Entrada após login real'])
    pedidos=p.caixa(1050,175,560,140,'Consultas de solicitações',['/solicitacoes → /solicitacoes-filtradas','/detalhes-solicitacao?id=...'])
    viagem=p.caixa(45,465,455,220,'Nova solicitação: quatro etapas',['/nova-solicitacao → /solicitantes','→ /passageiros → /revisao-envio','→ /solicitacao-enviada?id=...','/descartar-solicitacao limpa o rascunho'])
    catalogo=p.caixa(600,465,455,220,'Passageiros cadastrados',['/passageiros-cadastrados','/buscar-passageiro','/adicionar-passageiro /editar-passageiro','/passageiro-salvo /passageiro-removido'])
    analise=p.caixa(1155,465,455,220,'Ações sobre um pedido',['/analisar-solicitacao?id=... (administrador)','Aprovar / recusar / iniciar análise','/cancelar-solicitacao?id=...','Concluir é uma ação nos detalhes'],'azul')
    conta=p.caixa(45,890,455,190,'Conta e sessão',['/minha-conta: perfil e troca de senha','/sair-da-conta: confirmação de saída'])
    usuarios=p.caixa(600,890,455,190,'Administração de usuários',['/usuarios (somente administrador)','Cadastro, edição, ativação e senha'],'azul')
    ajuda=p.caixa(1155,890,455,190,'Ajuda',['/como-funciona','Explica o fluxo e os estados do pedido'],'cinza')
    p.seta(a,painel,'login');p.seta(painel,pedidos);p.seta(painel,viagem);p.seta(painel,catalogo);p.seta(pedidos,analise)
    p.seta(viagem,catalogo,'cadastrar e selecionar',True);p.seta(painel,conta,'perfil',pontos=[(545,800),(270,800)])
    p.texto(45,1150,1565,60,'Os links para edição, detalhe, análise, cancelamento e confirmações carregam identificadores reais. O backend revalida o acesso ao registro.',15)

    p=Pagina(arquivo,11,'Preparação e operação','O instalador configura um MySQL existente; o Workbench serve para administrá-lo. Não inclui binários ou dados na entrega.')
    a=p.caixa(45,180,340,180,'Ambiente necessário',['PHP 8.1+ com PDO MySQL','MySQL com InnoDB e utf8mb4','Python 3.10+ para entrega/testes','draw.io para editar os diagramas'],'cinza')
    b=p.caixa(525,180,470,200,'configurar.cmd / configurar.ps1',['Recebe acesso administrativo local','Cria banco se ele não existe','Cria uma conta restrita à aplicação','Gera configuração e acesso locais'])
    c=p.caixa(1155,180,460,200,'preparar.php → migrar.php',['GET_LOCK evita preparações simultâneas','Aplica migrações SQL em ordem','Registra nomes e hashes SHA-256','Cria administrador somente se não existe'],'azul')
    d=p.caixa(1155,595,460,185,'MySQL preparado',['001: autenticação','002: solicitações e histórico','003: catálogo e fluxos completos','Ledger: migracoes_aplicadas'],'azul','banco')
    e=p.caixa(525,610,470,170,'iniciar.cmd / iniciar.ps1',['php -S 127.0.0.1:8080 roteador.php','Linux: iniciar.sh com comandos/php.sh','Desenvolvimento local'])
    f=p.caixa(45,610,340,170,'Validação',['PHP: regras isoladas','Python: integração HTTP','Playwright: navegador','Entrega: testes sem banco'],'cinza')
    p.seta(a,b);p.seta(b,c);p.seta(c,d);p.seta(d,e,'configuração válida');p.seta(e,f,'verificar')
    p.texto(45,900,1570,95,'Hospedagem: DocumentRoot em public/, HTTPS, cookie_seguro=true, ambiente_local=false, remetente e serviço de e-mail configurados. As migrações atuais não contêm dados pessoais. DDL não é revertido automaticamente pelo MySQL; faça backup antes de futuras mudanças de estrutura.',15)

    p=Pagina(arquivo,12,'Entrega sem dados locais','O caminho recomendado para compartilhar é o ZIP produzido pelo comando; um ZIP manual da pasta não passa por estas barreiras.')
    raiz=p.caixa(45,170,360,210,'Projeto de trabalho',['Código + modelos + documentação','Credenciais e configuração privadas','Logs, mensagens, caches e banco local','Git e cópias de segurança'],'cinza')
    politica=p.caixa(555,170,490,220,'entrega.py + entrega.json',['Lista de diretórios, arquivos e extensões','Recusa segredos identificados no conteúdo','Compara com as senhas locais sem exibi-las','Recusa vínculos e dumps com dados','Guarda só código e documentação revisáveis'])
    pacote=p.caixa(1205,170,420,220,'entregas/*.zip',['Sem .git, *.local.*, .env ou credenciais','Sem armazenamento, dumps e backups','Manifesto com SHA-256 de cada arquivo','ZIP relido e conferido antes de liberar'],'azul')
    p.seta(raiz,politica,'preparar-entrega.cmd');p.seta(politica,pacote,'ZIP verificado')
    p.faixa(535,'CAMADAS PARA GIT')
    ignore=p.caixa(45,600,440,180,'.gitignore / .gitattributes',['Ignora arquivos locais na preparação','export-ignore evita itens no git archive','Não remove segredos de commits antigos.'],'cinza')
    commit=p.caixa(625,600,440,180,'Gancho pre-commit',['Verifica os bytes do índice Git','Bloqueia arquivos privados rastreados','Não confia só no arquivo da pasta.'])
    push=p.caixa(1205,600,420,180,'Gancho pre-push',['Inspeciona os commits a enviar','Detecta segredo apagado no commit seguinte','Não reescreve o histórico automaticamente.'])
    p.seta(ignore,commit,'git add / commit');p.seta(commit,push,'git push')
    p.caixa(45,910,1580,100,'Limite da automação',['Os ganchos são locais e podem ser ignorados manualmente; padrões não reconhecem todo dado pessoal em texto livre ou imagem.', 'Revise os arquivos permitidos e compartilhe somente o ZIP gerado. As credenciais locais continuam funcionando na sua instalação.'],'amarelo')
    return arquivo


def validar_modelo(arquivo):
    for pagina in arquivo.findall('diagram'):
        celulas = pagina.findall('./mxGraphModel/root/mxCell')
        ids = {celula.get('id') for celula in celulas}
        if len(ids) != len(celulas):
            raise ValueError('Identificador repetido em ' + pagina.get('name'))
        for celula in celulas:
            for referencia in ['parent','source','target']:
                if celula.get(referencia) and celula.get(referencia) not in ids:
                    raise ValueError('Referência inválida no diagrama.')


def gerar_dicionario():
    finalidades = {
        'usuarios': 'Contas autorizadas e hash de senha. E-mail único; conta é desativada, não excluída.',
        'tentativas_acesso': 'Limites de login por hashes de e-mail/IP. Sem FK de usuário para incluir contas inexistentes.',
        'solicitacoes': 'Pedido, responsável, viagem e contato. Saída/retorno são horários locais de Manaus.',
        'passageiros': 'Cópia dos participantes de cada envio. Sem CPF e sem FK para o catálogo reutilizável.',
        'solicitacao_passageiros': 'Associação com PK composta entre viagem e cópia de passageiro.',
        'historico_solicitacoes': 'Eventos de status, autor e data UTC. A criação inicial tem status_anterior nulo.',
        'cadastros_passageiros': 'Catálogo privado reutilizável. cpf_ativo gerado permite unicidade só entre os ativos de um dono.',
        'atendimentos_solicitacoes': 'Extensão opcional 1:1 do pedido; registra veículo, motorista e motivo de cancelamento.',
        'observacoes_historico': 'Extensão opcional 1:1 do evento; registra observação, designação ou motivo.',
        'recuperacoes_senha': 'Hash de token, assinatura da senha, expiração e uso. O token bruto não é armazenado aqui.',
        'tentativas_recuperacao': 'Limites da recuperação, sem vínculo direto a uma conta.',
        'migracoes_aplicadas': 'Ledger de estrutura: nome da migração, SHA-256 e data de aplicação.',
    }
    tabelas = []
    for caminho in sorted((RAIZ / 'banco-de-dados/migracoes').glob('*.sql')):
        tabelas.extend((nome, corpo.strip(), caminho.name) for nome, corpo in
                       re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\) ENGINE', caminho.read_text(encoding='utf-8'), re.S))
    tabelas.append(('migracoes_aplicadas',
                    'nome VARCHAR(190) PRIMARY KEY,\nresumo CHAR(64) NOT NULL,\naplicada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP',
                    'comandos/migrar.php'))
    linhas = ['# Dicionário de dados — Sistema de Transportes CTIC', 'Estado de referência: 16/11/2026', '',
              'Fonte: migrações 001, 002 e 003 e o ledger criado por comandos/migrar.php.',
              'Esquema após todas as migrações. Somente estrutura; nenhum registro real.',
              'InnoDB e utf8mb4 nas tabelas. FKs não têm ON DELETE CASCADE.',
              'DATETIME de viagem: Manaus. Datas de criação, acesso e expiração: UTC.', '',
              'PK = chave primária; FK = chave estrangeira; UNIQUE KEY = restrição de unicidade.', '']
    for numero, (nome, corpo, origem) in enumerate(tabelas, 1):
        if nome == 'solicitacoes':
            corpo = corpo.replace("ENUM('pendente','analise','aprovada','recusada','concluida')", "ENUM('pendente','analise','aprovada','recusada','concluida','cancelada')")
            origem += ' + alteração do ENUM em 003_completar_fluxos.sql'
        linhas.extend([f'## {numero:02d}. `{nome}`', '', '**Finalidade:** ' + finalidades[nome], '', '**Origem:** `' + origem + '`', '', 'Definição dos campos e restrições:', '', '```sql'])
        linhas.extend('  ' + linha.strip() for linha in corpo.splitlines() if linha.strip())
        linhas.extend(['```', ''])
    linhas.extend(['## Relações e ciclo de vida', '',
                   'usuarios 1:N solicitacoes, passageiros, cadastros_passageiros, historico_solicitacoes e recuperacoes_senha.',
                   'solicitacoes 1:N historico_solicitacoes e solicitacao_passageiros.',
                   'passageiros 1:N solicitacao_passageiros (a aplicação cria uma cópia por viagem).',
                   'solicitacoes 1:0..1 atendimentos_solicitacoes; historico_solicitacoes 1:0..1 observacoes_historico.',
                   'Não há FK entre cadastros_passageiros e passageiros; a seleção é copiada no envio.',
                   'Tentativas e ledger não referenciam usuários por FK.', '',
                   'No fluxo da aplicação, todo pedido tem pelo menos um passageiro e um evento inicial.',
                   'Essas duas regras de quantidade são garantidas pela transação da aplicação, não por uma FK de contagem.',
                   'As contas são desativadas; a exclusão de catálogos marca ativo=0.',
                   'Senhas usam hash de password_hash. Os CHAR(64) usados nos controles são SHA-256, não valores de acesso.', '',
                   '## Índices e validação', '',
                   'Índices e restrições UNIQUE estão declarados acima. CPF e estados têm validação adicional no PHP.',
                   'Novas mudanças estruturais precisam de uma nova migração; regenere este documento e revise o diagrama 03.', ''])
    (RAIZ / 'documentacao/DICIONARIO-DE-DADOS.md').write_text('\n'.join(linhas), encoding='utf-8')


def principal():
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument('--exportar', action='store_true', help='usa o draw.io Desktop para exportar um SVG por página')
    opcoes = argumentos.parse_args()
    arquivo = criar_diagramas()
    validar_modelo(arquivo)
    PASTA.mkdir(parents=True, exist_ok=True)
    destino = PASTA / 'projeto-ctic.drawio'
    XML.indent(arquivo, space='  ')
    XML.ElementTree(arquivo).write(destino, encoding='utf-8', xml_declaration=True)
    gerar_dicionario()
    print('Arquivo draw.io criado com ' + str(len(arquivo.findall('diagram'))) + ' páginas editáveis.')
    if opcoes.exportar:
        executavel = os.environ.get('CTIC_DRAWIO') or shutil.which('drawio') or shutil.which('draw.io')
        if not executavel and os.name == 'nt':
            candidato = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'draw.io/draw.io.exe'
            if candidato.is_file():
                executavel = str(candidato)
        if not executavel:
            raise SystemExit('draw.io Desktop não encontrado. Defina CTIC_DRAWIO ou abra o .drawio no editor.')
        for numero, pagina in enumerate(arquivo.findall('diagram'), 1):
            titulo_ascii = unicodedata.normalize('NFKD', pagina.get('name')[3:]).encode('ascii', 'ignore').decode().lower()
            nome = f'{numero:02d}-' + re.sub(r'[^a-z0-9]+','-',titulo_ascii).strip('-') + '.svg'
            resultado = subprocess.run([executavel,'--disable-update','--export','--format','svg','--page-index',str(numero),
                                       '--embed-svg-fonts','false','--theme','light','--border','20','--output',str(PASTA/nome),str(destino)],
                                      capture_output=True, timeout=45, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if resultado.returncode or not (PASTA / nome).is_file():
                raise SystemExit('O draw.io não conseguiu exportar a página ' + str(numero) + '.')
            XML.parse(PASTA / nome)
            print('SVG exportado pelo draw.io: ' + nome, flush=True)


if __name__ == '__main__':
    principal()
