#!/usr/bin/env python3
"""Verifica a proteção de entrega em diretórios temporários, sem acessar o banco."""
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import tempfile
import unittest
import zipfile


RAIZ = Path(__file__).resolve().parent.parent
ESPECIFICACAO = importlib.util.spec_from_file_location('protecao_entrega', RAIZ / 'comandos/entrega.py')
protecao = importlib.util.module_from_spec(ESPECIFICACAO)
ESPECIFICACAO.loader.exec_module(protecao)


class EntregaTeste(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory(prefix='ctic-teste-entrega-')
        self.addCleanup(self.temporario.cleanup)
        self.raiz = Path(self.temporario.name).resolve()
        self.politica = protecao.carregar_politica(RAIZ)
        self.senha = secrets.token_hex(20)
        self.gravar('index.php', '<?php echo "Entrada";')
        self.gravar('public/index.php', '<?php echo "Controlador";')
        self.gravar('comandos/entrega.py', 'print("Entrega")\n')
        self.gravar('configuracao/aplicacao.exemplo.php', "<?php return ['senha' => ''];")
        self.gravar('configuracao/aplicacao.local.php', "<?php return ['senha' => '" + self.senha + "'];")
        self.gravar('.env', 'DADO_LOCAL=privado')
        self.gravar('CREDENCIAIS.local.txt', self.senha)
        self.gravar('armazenamento/emails/link.txt', 'Arquivo privado')
        self.gravar('banco-de-dados/copia.sql', 'INSERT INTO usuarios VALUES (1);')
        self.gravar('arquivo-desnecessario.csv', 'nome,cpf')

    def gravar(self, nome, conteudo):
        caminho = self.raiz / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding='utf-8')

    def selecionar(self):
        return protecao.selecionar_arquivos(self.raiz, self.politica, protecao.segredos_locais(self.raiz))[0]

    def iniciar_git(self):
        protecao.executar_git(self.raiz, 'init', '-q')
        protecao.executar_git(self.raiz, 'config', 'user.name', 'Teste de entrega')
        protecao.executar_git(self.raiz, 'config', 'user.email', 'teste@example.invalid')

    def test_pacote_exclui_privados_e_confere_manifesto(self):
        arquivos = self.selecionar()
        self.assertNotIn('configuracao/aplicacao.local.php', arquivos)
        self.assertNotIn('.env', arquivos)
        self.assertNotIn('CREDENCIAIS.local.txt', arquivos)
        self.assertNotIn('armazenamento/emails/link.txt', arquivos)
        self.assertNotIn('banco-de-dados/copia.sql', arquivos)
        self.assertNotIn('arquivo-desnecessario.csv', arquivos)
        pacote = protecao.gerar_pacote(self.raiz, self.politica, arquivos, {self.senha.encode()})
        with zipfile.ZipFile(pacote) as arquivo:
            manifesto = json.loads(arquivo.read('sistema-transporte-ctic/MANIFESTO-ENTREGA.json'))
            for entrada in manifesto['arquivos']:
                conteudo = arquivo.read('sistema-transporte-ctic/' + entrada['caminho'])
                self.assertEqual(entrada['sha256'], hashlib.sha256(conteudo).hexdigest())
                self.assertNotIn(self.senha.encode(), conteudo)

    def test_segredo_copiado_bloqueia_sem_exibir_valor(self):
        self.gravar('aplicacao/copia.php', '<?php $valor = "' + self.senha + '";')
        with self.assertRaises(protecao.EntregaInsegura) as erro:
            self.selecionar()
        self.assertNotIn(self.senha, str(erro.exception))
        self.assertFalse((self.raiz / 'entregas').exists())

    def test_backup_do_drawio_nao_entra_na_entrega_nem_no_commit(self):
        original = 'documentacao/diagramas/projeto.drawio'
        backup = 'documentacao/diagramas/.$projeto.drawio.bkp'
        self.gravar(original, '<mxfile/>')
        self.gravar(backup, '<mxfile/>')
        arquivos = self.selecionar()
        self.assertIn(original, arquivos)
        self.assertNotIn(backup, arquivos)
        self.assertFalse(protecao.permitido('documentacao/diagramas/.$projeto.drawio', self.politica))
        self.iniciar_git()
        protecao.executar_git(self.raiz, 'add', '-f', '--', backup)
        with self.assertRaises(protecao.EntregaInsegura):
            protecao.verificar_indice(self.raiz, self.politica, set())

    def test_senha_local_com_aspas_e_barra_e_reconhecida(self):
        senha = self.senha + "'" + '\\fim'
        literal = senha.replace('\\','\\\\').replace("'", "\\'")
        self.gravar('configuracao/aplicacao.local.php', "<?php return ['senha' => '" + literal + "'];")
        self.assertIn(senha.encode(), protecao.segredos_locais(self.raiz))
        self.gravar('aplicacao/copia.php', '<?php // ' + senha)
        with self.assertRaises(protecao.EntregaInsegura):
            self.selecionar()

    def test_senha_literal_e_dados_em_migracao_bloqueados(self):
        self.gravar('aplicacao/cadastro.php', "<?php return ['senha' => 'senha-ficticia-fixa'];")
        with self.assertRaises(protecao.EntregaInsegura):
            self.selecionar()
        (self.raiz / 'aplicacao/cadastro.php').unlink()
        self.gravar('banco-de-dados/migracoes/999_dados.sql', 'INSERT INTO usuarios VALUES (1);')
        with self.assertRaises(protecao.EntregaInsegura):
            self.selecionar()

    def test_vinculo_e_caminho_pessoal_bloqueados(self):
        caminho_pessoal = 'C:' + '/Users/' + 'pessoa/arquivo'
        self.gravar('aplicacao/caminho.php', '<?php $p = "' + caminho_pessoal + '";')
        with self.assertRaises(protecao.EntregaInsegura):
            self.selecionar()
        (self.raiz / 'aplicacao/caminho.php').unlink()
        try:
            (self.raiz / 'aplicacao/atalho.php').symlink_to(self.raiz / 'configuracao/aplicacao.local.php')
        except OSError:
            return
        with self.assertRaises(protecao.EntregaInsegura):
            self.selecionar()

    def test_commit_inspeciona_indice_em_vez_do_arquivo_atual(self):
        self.iniciar_git()
        self.gravar('aplicacao/copia.php', '<?php $dado = "' + self.senha + '";')
        protecao.executar_git(self.raiz, 'add', 'aplicacao/copia.php')
        self.gravar('aplicacao/copia.php', '<?php echo "Arquivo limpo";')
        with self.assertRaises(protecao.EntregaInsegura):
            protecao.verificar_indice(self.raiz, self.politica, {self.senha.encode()})

    def test_arquivo_privado_forcado_no_git_e_bloqueado(self):
        self.iniciar_git()
        protecao.executar_git(self.raiz, 'add', '-f', 'configuracao/aplicacao.local.php')
        with self.assertRaises(protecao.EntregaInsegura):
            protecao.verificar_indice(self.raiz, self.politica, {self.senha.encode()})

    def test_push_detecta_segredo_removido_do_commit_mais_recente(self):
        self.iniciar_git()
        self.gravar('aplicacao/copia.php', '<?php $valor = "' + self.senha + '";')
        protecao.executar_git(self.raiz, 'add', 'aplicacao/copia.php')
        protecao.executar_git(self.raiz, 'commit', '-qm', 'Primeiro estado de teste')
        self.gravar('aplicacao/copia.php', '<?php echo "Sem segredo";')
        protecao.executar_git(self.raiz, 'add', 'aplicacao/copia.php')
        protecao.executar_git(self.raiz, 'commit', '-qm', 'Segundo estado de teste')
        revisao = protecao.executar_git(self.raiz, 'rev-parse', 'HEAD').decode().strip()
        linha = 'refs/heads/main ' + revisao + ' refs/heads/main ' + '0' * 40
        with self.assertRaises(protecao.EntregaInsegura):
            protecao.verificar_envio_git(self.raiz, self.politica, {self.senha.encode()}, linha)


if __name__ == '__main__':
    unittest.main(verbosity=2)
