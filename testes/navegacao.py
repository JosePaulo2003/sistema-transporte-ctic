#!/usr/bin/env python3
"""Executa o fluxo visual em desenvolvimento com Playwright e Microsoft Edge ou Chromium."""
import os
from pathlib import Path
import re
from importlib.machinery import SourceFileLoader
from playwright.sync_api import sync_playwright


def executar():
    arquivo = Path(os.environ.get('CTIC_TESTE_USUARIO', Path(__file__).resolve().parent.parent / 'configuracao/primeiro-usuario.local.php'))
    configuracao = arquivo.read_text(encoding='utf-8')
    email = re.search(r"'email'\s*=>\s*'([^']+)'", configuracao)[1]
    senha = re.search(r"'senha'\s*=>\s*'([^']+)'", configuracao)[1]
    regras = SourceFileLoader('fluxos', str(Path(__file__).with_name('fluxos-completos.py'))).load_module()
    with sync_playwright() as ferramentas:
        edge = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
        executavel = os.environ.get('CTIC_TESTE_NAVEGADOR') or (str(edge) if edge.exists() else None)
        navegador = ferramentas.chromium.launch(executable_path=executavel, headless=True)
        contexto = navegador.new_context(viewport={'width': 1440, 'height': 1000}, extra_http_headers={'Connection': 'close'})
        contexto.route('**/*', lambda rota: rota.continue_() if rota.request.url.startswith('http://127.0.0.1:8080') else rota.abort())
        pagina = contexto.new_page()
        erros = []
        pagina.on('pageerror', lambda erro: erros.append(str(erro)))

        def abrir(caminho):
            pagina.goto('http://127.0.0.1:8080' + caminho, wait_until='domcontentloaded')
            pagina.wait_for_function("!document.querySelector('main[aria-busy=\"true\"]')")

        def aguardar(caminho):
            pagina.wait_for_url('**/' + caminho, wait_until='domcontentloaded')
            pagina.wait_for_function("!document.querySelector('main[aria-busy=\"true\"]')")

        def preencher(identificador, texto):
            pagina.locator('#' + identificador).fill(texto)

        abrir('/entrar')
        preencher('email', email)
        preencher('senha', senha)
        pagina.locator('#botao-entrar').click()
        aguardar('painel')
        print('Navegador: login aprovado.', flush=True)
        abrir('/nova-solicitacao')
        for campo, conteudo in {'tipo-deslocamento': 'Intermunicipal', 'destino': 'TESTE NAVEGADOR <texto>',
            'finalidade': 'Verificar telas', 'data-saida': '2026-12-22', 'hora-saida': '08:00', 'data-retorno': '2026-12-22',
            'hora-retorno': '18:00', 'local-embarque': 'CTIC', 'centro-custo': 'CTIC', 'justificativa': 'TESTE AUTOMATIZADO'}.items():
            preencher(campo, conteudo)
        pagina.locator('button[type=submit]').click()
        aguardar('solicitantes')
        assert pagina.locator('#nome-completo').get_attribute('readonly') is not None
        preencher('telefone', '(92) 99999-0000')
        preencher('vinculo', 'Servidor')
        pagina.locator('button[type=submit]').click()
        aguardar('passageiros')
        pagina.locator('.btn-adicionar-passageiro').click()
        aguardar('adicionar-passageiro?origem=viagem')
        preencher('nome-completo', 'PASSAGEIRO NAVEGADOR <texto>')
        preencher('cpf', regras.cpf_teste())
        preencher('telefone', '(92) 99999-0000')
        pagina.locator('#setor').select_option('NTI')
        pagina.locator('#vinculo').select_option('Servidor')
        pagina.locator('button[type=submit]').click()
        aguardar('passageiro-salvo?**')
        pagina.locator('.botoes-acao .btn-continuar').click()
        aguardar('passageiros')
        assert pagina.locator('#lista-passageiros input:checked').count() == 1
        pagina.locator('.botoes-acao .btn-continuar').click()
        aguardar('revisao-envio')
        assert 'TESTE NAVEGADOR <texto>' in pagina.locator('.lista-resumo').first.inner_text()
        pagina.locator('.container-checkbox').click()
        assert pagina.locator('#declaracao-normas').is_checked()
        pagina.locator('#btn-enviar').click()
        aguardar('solicitacao-enviada?**')
        assert pagina.locator('#protocolo').inner_text().startswith('#')
        pagina.locator('a[href^="/detalhes-solicitacao?id="]').click()
        aguardar('detalhes-solicitacao?**')
        assert 'PASSAGEIRO NAVEGADOR <texto>' in pagina.locator('main').inner_text()
        pagina.locator('a[href^="/analisar-solicitacao?id="]').click()
        aguardar('analisar-solicitacao?**')
        pagina.get_by_role('button', name='Iniciar análise', exact=True).click()
        pagina.wait_for_function("document.querySelector('.caixa-status strong').textContent.includes('Em análise')")
        pagina.locator('#veiculo').select_option(index=1)
        preencher('motorista', 'Motorista do teste')
        pagina.get_by_role('button', name='Aprovar solicitação', exact=True).click()
        aguardar('detalhes-solicitacao?**')
        assert 'Motorista do teste' in pagina.locator('main').inner_text()
        pagina.get_by_role('button', name='Concluir viagem', exact=True).click()
        pagina.wait_for_function("document.querySelector('.caixa-status strong').textContent.includes('Concluída')")
        print('Navegador: viagem, passageiro, revisão, envio, análise, aprovação e conclusão aprovados.', flush=True)
        for caminho in ['/painel', '/solicitacoes', '/solicitacoes-filtradas?status=concluida', '/passageiros-cadastrados',
                        '/buscar-passageiro', '/minha-conta', '/como-funciona', '/descartar-solicitacao', '/sair-da-conta', '/usuarios']:
            abrir(caminho)
            aviso = pagina.locator('#aviso-sistema')
            assert not aviso.count() or not aviso.is_visible(), caminho
        abrir('/passageiros-cadastrados')
        pagina.locator('#busca-passageiro').fill('PASSAGEIRO NAVEGADOR')
        pagina.locator('main .link-solicitacao').first.click()
        aguardar('editar-passageiro?**')
        assert pagina.locator('#nome-completo').input_value() == 'PASSAGEIRO NAVEGADOR <texto>'
        preencher('nome-completo', 'PASSAGEIRO EDITADO')
        pagina.locator('button[type=submit]').click()
        aguardar('passageiro-salvo?**')
        pagina.set_viewport_size({'width': 390, 'height': 844})
        abrir('/painel')
        assert pagina.locator('#cards-recente-mobile').is_visible()
        abrir('/sair-da-conta')
        pagina.locator('#confirmar-saida').click()
        aguardar('entrar')
        abrir('/recuperar-senha')
        preencher('email', 'inexistente-navegador@example.com')
        pagina.locator('button[type=submit]').click()
        aguardar('confirmar-email')
        for javascript in (Path(__file__).resolve().parent.parent / 'public/assets/js').glob('*.js'):
            pagina.evaluate('(codigo)=>{new Function(codigo)}', javascript.read_text(encoding='utf-8'))
        assert not erros, erros
        navegador.close()
        print('APROVADO: páginas desktop e celular, edição de passageiro, conta, filtros, saída, recuperação e JavaScript sem erros.')


if __name__ == '__main__':
    executar()
