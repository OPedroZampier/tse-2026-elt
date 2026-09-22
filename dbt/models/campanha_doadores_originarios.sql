select
    SG_UF as uf,
    TP_DOADOR_ORIGINARIO as tipo_doador,
    count(distinct nullif(NR_CPF_CNPJ_DOADOR_ORIGINARIO, '#NULO')) as doadores_unicos,
    sum(try_cast(replace(VR_RECEITA, ',', '.') as decimal(20, 2))) as receitas_brl,
    count(*) as lancamentos
from {{ source_csv('contas_eleitorais', 'receitas_candidatos_doador_originario_2026_BRASIL.csv') }}
group by 1, 2
