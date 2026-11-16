#!/usr/bin/env python3
"""Verifica código compartilhável e gera um ZIP sem configurações ou dados locais."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import zipfile


RAIZ = Path(__file__).resolve().parent.parent
PASTAS_PRIVADAS = {'.git', 'armazenamento', 'entregas', 'legado', 'node_modules', 'vendor',
                   '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.venv', 'venv',
                   '.idea', '.vscode', 'backups', 'backup', 'tmp', 'temp', 'logs', '.aws', '.ssh', '.codex'}
PADROES_PRIVADOS = ('*.local.*', '.env', '.env.*', '*credenciais*', '*credentials*',
                    '*.log', '*.pyc', '*.pyo', '*.zip', '*.rar', '*.7z', '*.tar', '*.gz',
                    '*.bak', '*.bkp', '*.dtmp', '.$*', '*.backup', '*.dump', '*.sqlite*', '*.db', '*.pem', '*.key',
                    '*.p12', '*.pfx', '*.crt', 'id_rsa*', 'id_ed25519*', '*.swp', '*.tmp',
                    'desktop.ini', 'thumbs.db', '.ds_store')
EXTENSOES_BINARIAS = {'.png'}
PADROES_SEGREDOS = [
    ('chave privada', re.compile(rb'-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----')),
    ('token de acesso', re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16}|sk-(?:proj-)?[A-Za-z0-9_-]{32,})\b')),
    ('senha em endereço de conexão', re.compile(rb'(?:mysql|postgres(?:ql)?|mongodb(?:\+srv)?|https?)://[^\s/:]+:[^\s/@]+@', re.I)),
    ('token de recuperação em link', re.compile(rb'(?:#token=|[?&]token=)[a-f0-9]{64}\b', re.I)),
]
ATRIBUICAO_SEGREDO = re.compile(
    r'''(?im)(?<![A-Za-z0-9_-])(?:['"]?(?:senha|password|passwd|pwd|api[_-]?key|client[_-]?secret|access[_-]?token)['"]?)\s*(?:=>|:|=)\s*(['"])([^'"\r\n]+)\1''')
MARCADORES_EXEMPLO = {'', 'sua_senha', 'sua-senha', 'preencha-localmente', '<senha>',
                      '<senha-local>', 'exemplo', 'changeme'}


class EntregaInsegura(RuntimeError):
    pass


def executar_git(raiz: Path, *argumentos: str, entrada: bytes | None = None) -> bytes:
    resultado = subprocess.run(['git', '-C', str(raiz), *argumentos], input=entrada,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if resultado.returncode:
        raise EntregaInsegura('O Git não conseguiu realizar a verificação solicitada.')
    return resultado.stdout


def carregar_politica(raiz: Path) -> dict:
    politica = json.loads((raiz / 'configuracao/entrega.json').read_text(encoding='utf-8'))
    if politica.get('versao') != 1 or politica.get('nome_projeto') != 'sistema-transporte-ctic':
        raise EntregaInsegura('Política de entrega inválida.')
    return politica


def motivo_privado(nome: str) -> str | None:
    caminho = PurePosixPath(nome)
    if caminho.is_absolute() or '..' in caminho.parts or '\\' in nome or ':' in nome:
        return 'caminho inválido'
    partes = [parte.casefold() for parte in caminho.parts]
    if any(parte in PASTAS_PRIVADAS for parte in partes[:-1]):
        return 'pasta local ou gerada'
    if any(fnmatch.fnmatchcase(partes[-1], padrao) for padrao in PADROES_PRIVADOS):
        return 'arquivo privado ou gerado'
    return None


def permitido(nome: str, politica: dict) -> bool:
    if motivo_privado(nome):
        return False
    if nome in politica['arquivos']:
        return True
    caminho = PurePosixPath(nome)
    return any(nome.startswith(pasta + '/') and caminho.suffix.casefold() in extensoes
               for pasta, extensoes in politica['diretorios'].items())


def eh_vinculo(caminho: Path) -> bool:
    atributos = caminho.lstat()
    return stat.S_ISLNK(atributos.st_mode) or bool(getattr(atributos, 'st_file_attributes', 0)
                                                & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024))


def segredos_locais(raiz: Path) -> set[bytes]:
    # Eu comparo com as senhas locais sem mostrá-las: vazamento não rende adicional no salário.
    valores = set()
    pasta = raiz / 'configuracao'
    for caminho in pasta.glob('*.local.php'):
        if eh_vinculo(caminho):
            continue
        texto = caminho.read_text(encoding='utf-8-sig')
        literais_php = re.finditer(r"""(?im)['"](?:senha|password|passwd)['"]\s*=>\s*'((?:\\.|[^'\\])*)'""", texto)
        for correspondencia in literais_php:
            valor = re.sub(r"\\([\\'])", r'\1', correspondencia.group(1))
            if len(valor) >= 8 and valor.casefold() not in MARCADORES_EXEMPLO:
                valores.add(valor.encode('utf-8'))
        for correspondencia in ATRIBUICAO_SEGREDO.finditer(texto):
            valor = correspondencia.group(2)
            if len(valor) >= 8 and valor.casefold() not in MARCADORES_EXEMPLO:
                valores.add(valor.encode('utf-8'))
    return valores


def verificar_conteudo(nome: str, conteudo: bytes, politica: dict, segredos: set[bytes]) -> list[str]:
    problemas = []
    if len(conteudo) > politica['limite_arquivo_bytes']:
        problemas.append('arquivo maior que o limite de entrega')
    if any(segredo in conteudo for segredo in segredos):
        problemas.append('cópia de uma credencial local')
    for categoria, padrao in PADROES_SEGREDOS:
        if padrao.search(conteudo):
            problemas.append(categoria)
    if PurePosixPath(nome).suffix.casefold() in EXTENSOES_BINARIAS:
        if not conteudo.startswith(b'\x89PNG\r\n\x1a\n'):
            problemas.append('imagem PNG inválida')
        return problemas
    try:
        texto = conteudo.decode('utf-8-sig')
    except UnicodeDecodeError:
        return problemas + ['arquivo de texto não está em UTF-8']
    if '\x00' in texto:
        problemas.append('conteúdo binário em arquivo de texto')
    # Eu aceito as senhas fictícias dos testes, mas nunca uma senha local copiada para eles.
    if not nome.startswith('testes/'):
        for correspondencia in ATRIBUICAO_SEGREDO.finditer(texto):
            if correspondencia.group(2).casefold() not in MARCADORES_EXEMPLO:
                problemas.append('segredo literal atribuído no código')
                break
    if nome.endswith('.sql') and re.search(r'(?im)^\s*(?:INSERT\s+INTO|REPLACE\s+INTO|LOAD\s+DATA)\b', texto):
        problemas.append('migração contém dados ou comandos de importação')
    if re.search(r'(?i)[A-Z]:[\\/]+Users[\\/]+(?!<|%|\$)[^\s\\/"\']+', texto):
        problemas.append('caminho pessoal absoluto do Windows')
    if re.search(r'(?i)/(?:home|Users)/[A-Za-z0-9_.-]+/', texto):
        problemas.append('caminho pessoal absoluto')
    return list(dict.fromkeys(problemas))


def selecionar_arquivos(raiz: Path, politica: dict, segredos: set[bytes]) -> tuple[dict[str, bytes], Counter]:
    arquivos = {}
    exclusoes = Counter()
    erros = []
    for pasta, subpastas, nomes in os.walk(raiz, followlinks=False):
        diretorio = Path(pasta)
        for nome in list(subpastas):
            caminho = diretorio / nome
            if nome.casefold() in PASTAS_PRIVADAS or eh_vinculo(caminho):
                subpastas.remove(nome)
                exclusoes['pastas locais, geradas ou vínculos'] += 1
        for nome in sorted(nomes):
            caminho = diretorio / nome
            relativo = caminho.relative_to(raiz).as_posix()
            if not permitido(relativo, politica):
                exclusoes['arquivos fora da lista permitida'] += 1
                continue
            if eh_vinculo(caminho) or not stat.S_ISREG(caminho.lstat().st_mode):
                erros.append(relativo + ': vínculos e arquivos especiais não são permitidos')
                continue
            if caminho.stat().st_size > politica['limite_arquivo_bytes']:
                erros.append(relativo + ': arquivo maior que o limite de entrega')
                continue
            conteudo = caminho.read_bytes()
            erros.extend(relativo + ': ' + problema for problema in verificar_conteudo(relativo, conteudo, politica, segredos))
            arquivos[relativo] = conteudo
    for essencial in ['index.php','public/index.php','configuracao/aplicacao.exemplo.php','comandos/entrega.py']:
        if essencial not in arquivos:
            erros.append(essencial + ': arquivo essencial ausente')
    if erros:
        raise EntregaInsegura('\n'.join(erros))
    return arquivos, exclusoes


def verificar_indice(raiz: Path, politica: dict, segredos: set[bytes]) -> int:
    todos = executar_git(raiz, 'ls-files', '-z').split(b'\0')
    erros = [nome.decode('utf-8', errors='replace') + ': arquivo privado rastreado pelo Git'
             for nome in todos if nome and motivo_privado(nome.decode('utf-8', errors='replace'))]
    alterados = executar_git(raiz, 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z').split(b'\0')
    quantidade = 0
    for nome_bytes in alterados:
        if not nome_bytes:
            continue
        nome = nome_bytes.decode('utf-8')
        if not permitido(nome, politica):
            erros.append(nome + ': caminho fora da política de entrega')
            continue
        entrada = executar_git(raiz, 'ls-files', '--stage', '-z', '--', nome)
        if entrada.startswith(b'120000 ') or entrada.startswith(b'160000 '):
            erros.append(nome + ': vínculo ou submódulo não permitido')
            continue
        conteudo = executar_git(raiz, 'show', ':' + nome)
        erros.extend(nome + ': ' + problema for problema in verificar_conteudo(nome, conteudo, politica, segredos))
        quantidade += 1
    if erros:
        raise EntregaInsegura('\n'.join(erros))
    return quantidade


def verificar_revisao(raiz: Path, revisao: str, politica: dict, segredos: set[bytes]) -> None:
    entradas = executar_git(raiz, 'ls-tree', '-rz', revisao).split(b'\0')
    erros = []
    for entrada in entradas:
        if not entrada:
            continue
        metadados, nome_bytes = entrada.split(b'\t', 1)
        modo, tipo, identificador = metadados.split()
        nome = nome_bytes.decode('utf-8')
        if motivo_privado(nome):
            erros.append(nome + ': arquivo privado no commit a enviar')
            continue
        if modo in (b'120000', b'160000'):
            erros.append(nome + ': vínculo ou submódulo no commit a enviar')
            continue
        if tipo != b'blob':
            continue
        # Eu verifico também caminhos antigos no histórico enviado: trocar o nome do segredo não apaga o vazamento.
        conteudo = executar_git(raiz, 'cat-file', 'blob', identificador.decode('ascii'))
        if len(conteudo) > politica['limite_arquivo_bytes']:
            erros.append(nome + ': arquivo grande no commit a enviar')
            continue
        if PurePosixPath(nome).suffix.casefold() in {'.php','.py','.js','.json','.sql','.txt','.env','.xml','.drawio','.svg','.sh','.ps1','.cmd','.ini','.yml','.yaml','.md'} or permitido(nome, politica):
            erros.extend(nome + ': ' + problema for problema in verificar_conteudo(nome, conteudo, politica, segredos))
        elif any(segredo in conteudo for segredo in segredos):
            erros.append(nome + ': credencial local no commit a enviar')
    if erros:
        raise EntregaInsegura('\n'.join(erros))


def verificar_envio_git(raiz: Path, politica: dict, segredos: set[bytes], linhas: str) -> int:
    revisoes = set()
    for linha in linhas.splitlines():
        partes = linha.split()
        if len(partes) != 4:
            raise EntregaInsegura('Entrada inválida do gancho pre-push.')
        _, origem, _, destino = partes
        if set(origem) == {'0'}:
            continue
        if not re.fullmatch(r'[0-9a-f]{40,64}', origem) or not re.fullmatch(r'[0-9a-f]{40,64}', destino):
            raise EntregaInsegura('Identificador de revisão inválido.')
        argumentos = [origem] if set(destino) == {'0'} else [destino + '..' + origem]
        revisoes.update(executar_git(raiz, 'rev-list', *argumentos).decode('ascii').splitlines())
    for revisao in revisoes:
        verificar_revisao(raiz, revisao, politica, segredos)
    return len(revisoes)


def gerar_pacote(raiz: Path, politica: dict, arquivos: dict[str, bytes], segredos: set[bytes]) -> Path:
    agora = datetime.now(timezone.utc)
    nome = politica['nome_projeto']
    manifesto = {'projeto': nome, 'gerado_em_utc': agora.isoformat(), 'politica': politica['versao'],
                 'arquivos': [{'caminho': caminho, 'bytes': len(conteudo), 'sha256': hashlib.sha256(conteudo).hexdigest()}
                              for caminho, conteudo in sorted(arquivos.items())]}
    metadados = {
        'MANIFESTO-ENTREGA.json': json.dumps(manifesto, ensure_ascii=False, indent=2).encode('utf-8'),
        'ORIENTACOES-DA-ENTREGA.txt': (
            'ENTREGA DO SISTEMA DE TRANSPORTES CTIC\n\n'
            'Este pacote contém código, modelos sem senhas, testes e documentação.\n'
            'Credenciais, banco com dados, logs, mensagens locais, histórico Git e cópias de segurança foram excluídos.\n'
            'No Windows, execute configurar.cmd para criar suas próprias credenciais e depois iniciar.cmd.\n'
            'Consulte documentacao/INDICE.md e abra os diagramas .drawio no draw.io.\n'
            'O manifesto relaciona os arquivos e seus resumos SHA-256.\n'
        ).encode('utf-8'),
    }
    for caminho, conteudo in metadados.items():
        problemas = verificar_conteudo(caminho, conteudo, politica, segredos)
        if problemas:
            raise EntregaInsegura(caminho + ': ' + ', '.join(problemas))
    pasta = raiz / 'entregas'
    if pasta.exists() and eh_vinculo(pasta):
        raise EntregaInsegura('A pasta de entregas não pode ser um vínculo.')
    pasta.mkdir(exist_ok=True)
    destino = pasta / (nome + '-' + agora.strftime('%Y%m%d-%H%M%S-%f') + '.zip')
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(dir=pasta, suffix='.tmp', delete=False) as arquivo:
            temporario = Path(arquivo.name)
        with zipfile.ZipFile(temporario, 'w', zipfile.ZIP_DEFLATED) as pacote:
            for caminho, conteudo in sorted({**arquivos, **metadados}.items()):
                entrada = zipfile.ZipInfo(nome + '/' + caminho, date_time=agora.timetuple()[:6])
                entrada.compress_type = zipfile.ZIP_DEFLATED
                entrada.external_attr = (0o100755 if caminho.endswith('.sh') or caminho.startswith('.githooks/') else 0o100644) << 16
                pacote.writestr(entrada, conteudo)
        with zipfile.ZipFile(temporario) as pacote:
            esperado = {nome + '/' + caminho: conteudo for caminho, conteudo in {**arquivos, **metadados}.items()}
            if pacote.testzip() or set(pacote.namelist()) != set(esperado):
                raise EntregaInsegura('A conferência estrutural do ZIP falhou.')
            for caminho, conteudo in esperado.items():
                if pacote.read(caminho) != conteudo:
                    raise EntregaInsegura('A conferência do conteúdo do ZIP falhou.')
        temporario.replace(destino)
        temporario = None
        resumo = hashlib.sha256(destino.read_bytes()).hexdigest()
        destino.with_suffix('.sha256.txt').write_text(resumo + '  ' + destino.name + '\n', encoding='utf-8')
        return destino
    finally:
        if temporario is not None and temporario.exists():
            temporario.unlink()


def principal() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__)
    modo = argumentos.add_mutually_exclusive_group()
    modo.add_argument('--verificar', action='store_true', help='confere os arquivos sem criar ZIP')
    modo.add_argument('--pre-commit', action='store_true', help='confere o conteúdo preparado no índice Git')
    modo.add_argument('--pre-push', action='store_true', help='confere os commits que serão enviados')
    modo.add_argument('--instalar-ganchos', action='store_true', help='ativa os ganchos neste clone Git')
    opcoes = argumentos.parse_args()
    try:
        politica = carregar_politica(RAIZ)
        segredos = segredos_locais(RAIZ)
        if opcoes.instalar_ganchos:
            atual = subprocess.run(['git','-C',str(RAIZ),'config','--local','--get','core.hooksPath'], capture_output=True, text=True).stdout.strip()
            if atual and atual != '.githooks':
                raise EntregaInsegura('Já existe outro diretório de ganchos. Integre a verificação nele antes de substituir a configuração.')
            for nome in ['pre-commit','pre-push']:
                gancho = RAIZ / '.githooks' / nome
                if not gancho.is_file() or eh_vinculo(gancho):
                    raise EntregaInsegura('Gancho de proteção ausente ou inválido: ' + nome)
                if os.name != 'nt':
                    gancho.chmod(0o755)
            executar_git(RAIZ, 'config', '--local', 'core.hooksPath', '.githooks')
            print('Proteção de commit e push ativada neste clone Git.')
            return 0
        if opcoes.pre_commit:
            print('Índice Git verificado: ' + str(verificar_indice(RAIZ, politica, segredos)) + ' arquivos preparados.')
            return 0
        if opcoes.pre_push:
            print('Envio Git verificado: ' + str(verificar_envio_git(RAIZ, politica, segredos, sys.stdin.read())) + ' commits.')
            return 0
        arquivos, exclusoes = selecionar_arquivos(RAIZ, politica, segredos)
        print('Verificação aprovada: ' + str(len(arquivos)) + ' arquivos permitidos.')
        print('Arquivos privados e conteúdo gerado permanecem somente no ambiente local.')
        if not opcoes.verificar:
            destino = gerar_pacote(RAIZ, politica, arquivos, segredos)
            print('ENVIE SOMENTE ESTE ZIP: ' + str(destino))
            print('Resumo SHA-256: ' + str(destino.with_suffix('.sha256.txt')))
        return 0
    except (EntregaInsegura, OSError, ValueError) as erro:
        print('ENTREGA BLOQUEADA:\n' + str(erro), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(principal())
