# Documentação do Sistema de Transportes CTIC

Estado de referência: **16/11/2026**.

| Documento | Conteúdo |
| --- | --- |
| [Documentação técnica](DOCUMENTACAO-TECNICA.md) | Arquitetura, módulos, permissões e regras do sistema. |
| [API HTTP](API.md) | Endpoints, campos, respostas e exemplos sem credenciais. |
| [Dicionário de dados](DICIONARIO-DE-DADOS.md) | As 12 tabelas, campos e relações reais. |
| [Operação e testes](OPERACAO-E-TESTES.md) | Instalação, execução, atualização, hospedagem e validação. |
| [Segurança e entrega](SEGURANCA-E-ENTREGA.md) | Pacote filtrado, verificações de conteúdo e ganchos Git. |

## Diagramas

O [arquivo editável do draw.io](diagramas/projeto-ctic.drawio) contém 12 páginas:

1. Contexto e implantação.
2. Componentes do código.
3. Modelo físico das 12 tabelas.
4. Autenticação e sessão.
5. Solicitação de transporte.
6. Estados da solicitação.
7. Passageiros e privacidade.
8. Recuperação e troca de senha.
9. API e autorização.
10. Navegação das telas.
11. Preparação e operação.
12. Entrega sem dados locais.

Os SVGs da pasta `diagramas/` são visualizações exportadas pelo draw.io Desktop.
Abra o `.drawio` para editar e selecione a aba desejada.

## Atualizar os diagramas e o dicionário

```sh
python comandos/gerar-diagramas.py
python comandos/gerar-diagramas.py --exportar
```

O segundo comando exige draw.io Desktop; `CTIC_DRAWIO` pode indicar o executável.
O modelo físico usa as migrações. Revise os demais fluxos no gerador quando o código mudar.

## Compartilhar o projeto

Execute `preparar-entrega.cmd` e compartilhe somente o ZIP indicado em `entregas/`.
A documentação contém estrutura e exemplos; não inclui credenciais ou registros reais.

## Referências

- [Formato XML do draw.io](https://www.drawio.com/docs/manual/advanced/diagram-source-edit/).
- [Exportação no draw.io](https://www.drawio.com/docs/manual/export/export-to-pdf/).
