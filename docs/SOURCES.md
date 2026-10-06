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

## Resultados do primeiro turno (2026)

Coleta em `pipeline/results.py`: 137 JSONs oficiais de `https://resultados.tse.jus.br/oficial/ele2026/`. Eleição 6257 para Presidente; 6259 para Governador, Senador, Deputado Federal e Estadual/Distrital. Turno 1, documentos oficiais (`f=o`). O consolidado BR de Presidente é usado apenas na reconciliação.

| Produto | Conteúdo e unidade |
| --- | --- |
| `resultados_primeiro_turno` | Uma linha por UF/cargo, incluindo exterior para Presidente: votos, comparecimento, abstenções e seções totalizadas. |
| `votos_candidatos_primeiro_turno` | Uma linha por abrangência/cargo/candidato: votos, destino dos votos, percentual oficial e resultado, incluindo eleitos e segundo turno. |
| `votos_partidos_primeiro_turno` | Uma linha por abrangência/cargo/partido: votos nominais, de legenda e anulados conforme o TSE. |
| `quociente_eleitoral_primeiro_turno` | QE e vagas por UF/cargo proporcional. |
| `eleitos_qp_media_primeiro_turno` | Quantidade de eleitos proporcionais por UF/cargo/partido/classificação oficial QP ou média. |

Os IDs de candidatura e números de partido/candidato são texto nos modelos de resultados. Datas de geração são datas; percentuais são frações (0 a 1). Os votos devem ser agregados por cargo. Comparecimento e abstenções devem usar o recorte Presidente para evitar contar o mesmo eleitor em vários cargos. Os totais de partido e candidato preservam a definição do TSE, inclusive destino de votos, e não devem ser tratados como equivalentes sem esse filtro. A classificação QP não prova uma relação entre um "puxador" específico e outro eleito. Resultados podem ser atualizados pelo TSE.

O manifesto `first_round_results` em `metrics.json` documenta a extração e valida BR = UFs + exterior, votos válidos = nominais + legenda, total de votos e comparecimento + abstenções. Falha de coleta, cobertura ou reconciliação interrompe o build antes da publicação.

## Critérios gerais

- Preferem-se os CSVs nacionais `BRASIL` para evitar duplicar registros ao juntar arquivos por UF.
- Cada fonte é verificada por presença do arquivo esperado, cabeçalho e SHA-256. CSVs são convertidos de Latin-1 para UTF-8 antes do dbt.
- CPF, CNPJ, e-mail, título eleitoral, identificador de eleitor, URLs individuais de redes sociais e número de processo não entram nos arquivos públicos.
- Contagens de doadores e fornecedores são calculadas com identificadores no processamento local, mas esses identificadores não são exportados.
- `eleitorado_deficiencia` é agregado por município e tipo de deficiência; o identificador individual de eleitor é descartado.
- O TSE oferece ainda fotos, propostas de governo, certidões, locais de votação, transferências, notas fiscais, CNPJ de campanha e extratos bancários. Eles ficam fora deste produto por serem binários, não sustentarem as seis áreas analíticas atuais ou exigirem outra modelagem.
- Pesquisas registradas não representam intenção de voto nem resultados eleitorais; o produto publica apenas quantidades de pesquisas e entrevistas previstas.
- As licenças indicadas nas páginas oficiais são Creative Commons Atribuição; a fonte TSE deve ser creditada em qualquer redistribuição.
