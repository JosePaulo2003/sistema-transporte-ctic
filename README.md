# Sistema de Transportes CTIC

Aplicação PHP e MySQL para solicitar transporte institucional, manter passageiros,
analisar pedidos e acompanhar o histórico de decisões.

## Executar localmente

Requisitos: PHP 8.1+ com `pdo_mysql` e servidor MySQL local. Python 3.10+ é usado
pelos comandos de entrega, documentação e testes, não pelo servidor web.

No Windows:

```powershell
.\configurar.cmd
.\iniciar.cmd
```

Abra **http://127.0.0.1:8080**. O configurador gera os dados de acesso em
`CREDENCIAIS.local.txt`, privado e ignorado pelo Git. Cada instalação precisa
gerar suas próprias credenciais.

## Documentação

- [Índice da documentação](documentacao/INDICE.md).
- [Arquitetura e regras](documentacao/DOCUMENTACAO-TECNICA.md).
- [API HTTP](documentacao/API.md).
- [Dicionário das 12 tabelas](documentacao/DICIONARIO-DE-DADOS.md).
- [Instalação, hospedagem e testes](documentacao/OPERACAO-E-TESTES.md).
- [Segurança e entrega](documentacao/SEGURANCA-E-ENTREGA.md).

## Diagramas

O [projeto no draw.io](documentacao/diagramas/projeto-ctic.drawio) contém 12 páginas
editáveis sobre arquitetura, modelo de dados, telas, permissões e fluxos.

## Conferir antes de compartilhar

```powershell
python comandos/entrega.py --verificar
python testes/entrega.py
```

Para compartilhar um ZIP filtrado, execute `preparar-entrega.cmd`. O pacote contém
código, modelos vazios, testes e documentação; exclui credenciais, dados locais,+logs e histórico Git. Consulte a documentação para os limites da verificação.
