# Pipeline de dados abertos do TSE 2026

[English](README.md) | Português

Este repositório transforma os dados abertos de 2026 do Tribunal Superior Eleitoral em arquivos CSV e Parquet prontos para análise. O pipeline baixa os pacotes oficiais, confere os arquivos, monta as tabelas com DuckDB e dbt e valida a exportação com Great Expectations.

## Fluxo

`TSE CDN → ZIP/CSV bruto → DuckDB + dbt → Great Expectations → CSV/Parquet → Kaggle`

O catálogo em [pipeline/sources.py](pipeline/sources.py) usa 14 pacotes oficiais. Os modelos em [dbt/models](dbt/models) geram 22 tabelas sobre candidaturas, bens declarados, eleitorado, contas partidárias, financiamento de campanha e pesquisas eleitorais registradas. O [mapa das fontes](docs/SOURCES.md) relaciona cada entrada ao seu produto.

## Executar localmente

Use Python 3.11 na raiz do repositório:

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python -m pytest -q
python -m pipeline.ingest
dbt build --project-dir . --profiles-dir .
python -m pipeline.export
```

No PowerShell, ative o ambiente com `.venv\Scripts\Activate.ps1` antes de usar o `pip`. Se os ZIPs do TSE já estiverem no computador, `python -m pipeline.ingest --archive-dir D:\TSE2026\downloads` reaproveita esses arquivos.

A pasta `output/` recebe um CSV e um Parquet por tabela, além de `metrics.json`. Os ZIPs originais, o banco DuckDB local e os arquivos gerados não entram no Git. Para usar Docker, execute `docker build -t tse-2026-elt .` e depois `docker run --rm -v "$PWD/output:/app/output" tse-2026-elt`.

## Métricas do projeto

Cada pacote precisa conter os CSVs nacionais esperados e as colunas exigidas. O manifesto da coleta registra o checksum das fontes. O dbt testa o modelo de candidaturas; o Great Expectations verifica todas as tabelas exportadas e bloqueia a publicação se algum teste falhar. O arquivo `output/metrics.json` registra fontes, linhas publicadas e resultados dos testes. A contagem de linhas da origem considera linhas físicas, que podem diferir do número de registros CSV.

| Métrica | Origem |
| --- | --- |
| Fontes, arquivos e linhas físicas de origem | `output/metrics.json`; linhas físicas podem diferir de registros CSV quando há quebras dentro de campos |
| Linhas publicadas por tabela | `output/metrics.json` e resumo do workflow |
| Testes de qualidade aprovados | dbt test + Great Expectations; execução falha se um teste crítico falhar |
| Uptime do pipeline | proporção de execuções agendadas bem-sucedidas no histórico do CI |
| Downloads do dataset | página de estatísticas do Kaggle após publicação |

Os arquivos públicos não incluem CPF, CNPJ, e-mail, identificadores individuais de eleitor, URLs individuais de redes sociais nem números de processo. Doadores e fornecedores aparecem apenas em dados agregados. Contas eleitorais de campanha e contas partidárias anuais são bases diferentes; não some seus valores sem definir antes a métrica.

## Agendamento e publicação

O [GitHub Actions](.github/workflows/pipeline.yml) roda em pushes e pull requests, aceita execução manual e tem agendamento para segunda-feira às 08:17 UTC. Pushes e pull requests geram um artefato validado. As execuções agendadas e manuais também publicam um dataset público no Kaggle quando estas configurações estiverem cadastradas no repositório:

- Secrets: `KAGGLE_USERNAME` e `KAGGLE_KEY`
- Variable: `KAGGLE_DATASET_ID` no formato `usuario/slug-do-dataset`

Sem essas configurações, a publicação no Kaggle não está ativa. O arquivo `.gitlab-ci.yml` executa o mesmo build; o agendamento precisa ser criado no GitLab. A [CLI oficial do Kaggle](https://github.com/Kaggle/kaggle-cli/blob/main/docs/datasets.md) faz a criação e as atualizações do dataset.

## Fonte

Os arquivos vêm do [Portal de Dados Abertos do TSE](https://dadosabertos.tse.jus.br/): [Candidatos 2026](https://dadosabertos.tse.jus.br/dataset/candidatos-2026), [Eleitorado 2026](https://dadosabertos.tse.jus.br/dataset/eleitorado-2026) e [Contas eleitorais 2026](https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-eleitorais-2026), entre outras bases. O [mapa das fontes](docs/SOURCES.md) reúne os arquivos selecionados e o que ficou fora do produto. Os dados podem mudar: cada exportação é um retrato datado, não um resultado definitivo da eleição. Credite o TSE ao redistribuir dados derivados e confira as condições nas páginas oficiais.
