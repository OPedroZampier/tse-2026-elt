# Fontes e produtos

Catálogo consultado no Portal de Dados Abertos do TSE em 22/09/2026. As URLs concretas dos ZIPs e os nomes dos CSVs esperados estão em [pipeline/sources.py](../pipeline/sources.py).

| Família oficial | Dados usados | Produto |
| --- | --- | --- |
| [Candidatos 2026](https://dadosabertos.tse.jus.br/dataset/candidatos-2026) | Candidatos e complementares | `candidaturas_limpas`, `candidaturas_complementares` |
| Candidatos 2026 | Bens, coligações, vagas e redes sociais | `bens_candidatos`, `coligacoes`, `vagas`, `presenca_digital` |
| Candidatos 2026 | Motivo da cassação e histórico | `motivos_cassacao`, `historico_candidaturas` |
| [Eleitorado 2026](https://dadosabertos.tse.jus.br/dataset/eleitorado-2026) | Perfil geral nacional e perfil com deficiência | `eleitorado_municipio`, `eleitorado_perfil_uf`, `eleitorado_deficiencia` |
| [Contas partidárias 2026](https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-partidarias-2026) | Receitas e despesas anuais | `partidos_receitas`, `partidos_despesas` |
| [Contas eleitorais 2026](https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-eleitorais-2026) | Receitas, doador originário e despesas de candidatos | `campanha_receitas`, `campanha_doadores_originarios`, `campanha_despesas_contratadas`, `campanha_despesas_pagas` |
| Contas eleitorais 2026 | Receitas, doador originário e despesas de órgãos partidários | `campanha_partidos_receitas`, `campanha_partidos_doadores_originarios`, `campanha_partidos_despesas`, `campanha_partidos_pagamentos` |
| [Pesquisas eleitorais 2026](https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026) | Pesquisas registradas | `pesquisas_eleitorais` |

## Critérios

- Preferem-se os CSVs nacionais `BRASIL` para evitar duplicar registros ao juntar arquivos por UF.
- Cada fonte é verificada por presença do arquivo esperado, cabeçalho e SHA-256. CSVs são convertidos de Latin-1 para UTF-8 antes do dbt.
- CPF, CNPJ, e-mail, título eleitoral, identificador de eleitor, URLs individuais de redes sociais e número de processo não entram nos arquivos públicos.
- Contagens de doadores e fornecedores são calculadas com identificadores no processamento local, mas esses identificadores não são exportados.
- `eleitorado_deficiencia` é agregado por município e tipo de deficiência; o identificador individual de eleitor é descartado.
- O TSE oferece ainda fotos, propostas de governo, certidões, locais de votação, transferências, notas fiscais, CNPJ de campanha e extratos bancários. Eles ficam fora deste produto por serem binários, não sustentarem as seis áreas analíticas atuais ou exigirem outra modelagem.
- Pesquisas registradas não representam intenção de voto nem resultados eleitorais; o produto publica apenas quantidades de pesquisas e entrevistas previstas.
- As licenças indicadas nas páginas oficiais são Creative Commons Atribuição; a fonte TSE deve ser creditada em qualquer redistribuição.
